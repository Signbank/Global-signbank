"""
Helpers for emitting upload receipts on the api_add_video / api_add_image
endpoints.  See `docs/signbank-api-recommendations.md` (#1 and #2) for the
full design rationale; the short version is:

* every upload returns enough metadata that the client can prove later
  *which* file landed (sha256, size, uploaded_at, uploaded_by, stored path);
* if the upload replaced an existing file, the prior file's metadata is
  reported under ``replaced`` so we can audit silent overwrites;
* clients can opt into refusal-on-overwrite by sending ``If-None-Match: *``
  or refusal-on-mismatch via ``If-Match: <sha256>``.
"""

import hashlib
import os
from datetime import datetime, timezone


def _now_iso():
    """RFC 3339 / ISO 8601, UTC, second precision."""
    return datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_of_uploaded_file(uploaded_file):
    """
    Compute the SHA-256 of a Django UploadedFile *without* losing the read
    cursor. Returns the hex digest and the file size in bytes.

    Uses chunked iteration so we don't load large videos into memory.
    """
    h = hashlib.sha256()
    size = 0
    for chunk in uploaded_file.chunks():
        size += len(chunk)
        h.update(chunk)
    # Reset for downstream save() / chunks() calls.
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    return h.hexdigest(), size


def sha256_of_path(path):
    """Compute SHA-256 + size for an existing file on disk, or (None, None) if absent."""
    if not path or not os.path.isfile(path):
        return None, None
    h = hashlib.sha256()
    size = 0
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 64), b''):
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size


def file_summary(path, *, include_path=True):
    """
    Build a plain dict describing the file at `path` — sha256, size_bytes,
    uploaded_at (file mtime), filename, optionally the stored path.

    Returns ``None`` if the file doesn't exist.
    """
    if not path or not os.path.isfile(path):
        return None
    sha, size = sha256_of_path(path)
    info = {
        'filename':    os.path.basename(path),
        'sha256':      sha,
        'size_bytes':  size,
        'uploaded_at': datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }
    if include_path:
        info['stored_path'] = path
    return info


def current_gloss_video_summary(gloss):
    """
    Return a dict describing the gloss's current center video (version 0),
    or ``None`` if no video exists.
    """
    try:
        gv = gloss.glossvideo_set.filter(version=0).first()
    except Exception:
        gv = None
    if not gv or not gv.videofile:
        return None
    try:
        path = gv.videofile.path
    except Exception:
        return None
    return file_summary(path)


def current_gloss_image_summary(gloss):
    """Approximate "current image" lookup based on the convention used by api_add_image."""
    try:
        from django.conf import settings
        from signbank.tools import get_two_letter_dir
        from signbank.settings.server_specific import WRITABLE_FOLDER, GLOSS_IMAGE_DIRECTORY
    except Exception:
        return None
    try:
        base_dir = os.path.join(WRITABLE_FOLDER, GLOSS_IMAGE_DIRECTORY,
                                gloss.lemma.dataset.acronym, get_two_letter_dir(gloss.idgloss))
    except Exception:
        return None
    if not os.path.isdir(base_dir):
        return None
    # api_add_image writes <idgloss>-<pk>.<ext>
    candidates = [f for f in os.listdir(base_dir)
                  if f.startswith(f"{gloss.idgloss}-{gloss.pk}.") or
                     f.startswith(f"{gloss.idgloss}-{gloss.pk}%")]
    if not candidates:
        return None
    candidates.sort(key=lambda f: os.path.getmtime(os.path.join(base_dir, f)), reverse=True)
    return file_summary(os.path.join(base_dir, candidates[0]))


def precondition_failed(message, current=None):
    """Build the JSON body for a 412 Precondition Failed response."""
    body = {
        'ok': False,
        'status_code': 412,
        'errors': [{'field': None, 'code': 'precondition_failed', 'message': message}],
    }
    if current is not None:
        body['current'] = current
    return body


def evaluate_idempotency_headers(request, current_summary):
    """
    Inspect ``If-None-Match`` / ``If-Match`` headers and, if a precondition
    fails, return the JsonResponse the view should return immediately.
    Otherwise returns ``None``.
    """
    from django.http import JsonResponse

    # If-None-Match: * → refuse if a current file already exists.
    if request.headers.get('If-None-Match', '').strip() == '*':
        if current_summary:
            return JsonResponse(
                precondition_failed(
                    "A file already exists for this gloss; refused because of If-None-Match: *.",
                    current=current_summary,
                ),
                status=412,
            )

    # If-Match: <sha256> → refuse unless current sha matches the supplied one.
    if_match = request.headers.get('If-Match', '').strip().strip('"')
    if if_match:
        current_sha = (current_summary or {}).get('sha256')
        if current_sha != if_match:
            return JsonResponse(
                precondition_failed(
                    f"If-Match precondition failed; current sha256 is "
                    f"{current_sha!r} (expected {if_match!r}).",
                    current=current_summary,
                ),
                status=412,
            )

    return None


def upload_receipt(*, ok, gloss, kind, uploaded_at, uploaded_by,
                   incoming_sha256, incoming_size, stored_summary,
                   previous_summary, message):
    """
    Build the unified receipt dict. ``kind`` is "video" or "image".
    """
    receipt = {
        'ok': ok,
        'message':     message,
        'gloss_id':    gloss.pk,
        'kind':        kind,
        'uploaded_at': uploaded_at,
        'uploaded_by': uploaded_by,
        'sha256':      incoming_sha256,
        'size_bytes':  incoming_size,
    }
    if stored_summary:
        # `incoming` keys describe what the client sent, `stored_*` keys
        # describe what landed on disk after save (post-conversion size /
        # hash can differ from the upload).
        receipt['stored_filename']   = stored_summary.get('filename')
        receipt['stored_path']       = stored_summary.get('stored_path')
        receipt['stored_size_bytes'] = stored_summary.get('size_bytes')
        receipt['stored_sha256']     = stored_summary.get('sha256')
    receipt['replaced'] = previous_summary  # may be None
    return receipt


def now_iso():
    return _now_iso()
