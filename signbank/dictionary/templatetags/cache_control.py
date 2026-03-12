import os
import urllib.parse

from django.template import Library

register = Library()


@register.filter
def media_version(value):
    """Return the file's modification time as an integer for use as a cache-busting version.

    Accepts either a FileField object or a URL-encoded path string relative to WRITABLE_FOLDER.
    Returns the file's mtime as an integer, or 0 if the file cannot be found.

    Using the file's mtime means the cache is only invalidated when the file actually changes,
    unlike using the current timestamp which invalidates the cache on every page load.
    """
    from django.conf import settings

    try:
        if hasattr(value, 'path'):
            # FileField or similar object with a .path property
            return int(os.path.getmtime(value.path))
        if value:
            decoded_path = urllib.parse.unquote(str(value)).lstrip('/')
            full_path = os.path.join(settings.WRITABLE_FOLDER, decoded_path)
            return int(os.path.getmtime(full_path))
    except (OSError, AttributeError, TypeError, ValueError):
        pass
    return 0
