"""
Helpers for emitting upload receipts on the api_add_video / api_add_image
endpoints:

* every upload returns metadata the client can use to prove later *which*
  file landed (sha256, size, uploaded_at, uploaded_by, stored path);
* if the upload replaced an existing file, the prior file's metadata is
  reported under ``replaced``;
* clients can opt into refusal-on-overwrite by sending ``If-None-Match: *``
  or refusal-on-mismatch via ``If-Match: "<sha256>"``.

See ``docs/signbank-api-recommendations.md`` (#1 and #2) for the design
rationale.
"""

import hashlib
import os
from datetime import datetime, timezone

from django.http import JsonResponse

from signbank.tools import get_two_letter_dir
from signbank.settings.server_specific import WRITABLE_FOLDER, GLOSS_IMAGE_DIRECTORY


ISO_8601_UTC = '%Y-%m-%dT%H:%M:%SZ'


def _iso_utc(dt):
    """Format a datetime as RFC 3339 / ISO 8601, UTC, second precision."""
    return dt.strftime(ISO_8601_UTC)


def now_iso():
    return _iso_utc(datetime.now(tz=timezone.utc))


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
    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass
    return h.hexdigest(), size


def sha256_of_path(path):
    """Compute SHA-256 + size for an existing file on disk, or (None, None) if absent."""
    if not path or not os.path.isfile(path):
        return None, None
    h = hashlib.sha256()
    size = 0
    with open(path, 'rb') as file:
        for chunk in iter(lambda: file.read(1024 * 64), b''):
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
    mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    info = {
        'filename':    os.path.basename(path),
        'sha256':      sha,
        'size_bytes':  size,
        'uploaded_at': _iso_utc(mtime),
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
        gloss_video = gloss.glossvideo_set.filter(version=0).first()
    except (AttributeError, ValueError):
        gloss_video = None
    if not gloss_video or not gloss_video.videofile:
        return None
    try:
        path = gloss_video.videofile.path
    except (AttributeError, ValueError):
        return None
    return file_summary(path)


def current_gloss_image_summary(gloss):
    """Approximate "current image" lookup based on the convention used by api_add_image."""
    try:
        base_dir = os.path.join(WRITABLE_FOLDER, GLOSS_IMAGE_DIRECTORY,
                                gloss.lemma.dataset.acronym, get_two_letter_dir(gloss.idgloss))
    except (AttributeError, ValueError):
        return None
    if not os.path.isdir(base_dir):
        return None
    prefix = f"{gloss.idgloss}-{gloss.pk}."
    candidates = [name for name in os.listdir(base_dir) if name.startswith(prefix)]
    if not candidates:
        return None
    candidates.sort(key=lambda name: os.path.getmtime(os.path.join(base_dir, name)), reverse=True)
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


def _parse_if_match(header_value):
    """
    Parse an ``If-Match`` header per RFC 9110: a comma-separated list of
    quoted ETag values, or the literal ``*``. Returns a list of unquoted
    ETag strings (``['*']`` for the wildcard, ``[]`` if the header is empty).
    """
    value = (header_value or '').strip()
    if not value:
        return []
    if value == '*':
        return ['*']
    tags = []
    for raw in value.split(','):
        token = raw.strip()
        if token.startswith('W/'):
            token = token[2:].strip()
        if len(token) >= 2 and token.startswith('"') and token.endswith('"'):
            token = token[1:-1]
        if token:
            tags.append(token)
    return tags


def evaluate_idempotency_headers(request, current_summary):
    """
    Inspect ``If-None-Match`` / ``If-Match`` headers and, if a precondition
    fails, return the JsonResponse the view should return immediately.
    Otherwise returns ``None``.
    """
    if not current_summary:
        return None

    if request.headers.get('If-None-Match', '').strip() == '*':
        return JsonResponse(
            precondition_failed(
                "A file already exists for this gloss; refused because of If-None-Match: *.",
                current=current_summary,
            ),
            status=412,
        )

    if_match_tags = _parse_if_match(request.headers.get('If-Match', ''))
    if if_match_tags:
        current_sha = current_summary.get('sha256')
        if '*' not in if_match_tags and current_sha not in if_match_tags:
            return JsonResponse(
                precondition_failed(
                    f"If-Match precondition failed; current sha256 is "
                    f"{current_sha!r} (expected one of {if_match_tags!r}).",
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

    ``incoming_*`` keys describe what the client sent; ``stored_*`` keys
    describe what landed on disk after save (post-conversion size / hash
    can differ from the upload).
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
        receipt['stored_filename']   = stored_summary.get('filename')
        receipt['stored_path']       = stored_summary.get('stored_path')
        receipt['stored_size_bytes'] = stored_summary.get('size_bytes')
        receipt['stored_sha256']     = stored_summary.get('sha256')
    receipt['replaced'] = previous_summary
    return receipt
