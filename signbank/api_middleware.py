"""
Tiny middleware that turns uncaught exceptions on /dictionary/api_* paths
into a JSON 500 instead of an 8 KB HTML error page.

Browser hits the same URL? They still get HTML. JSON / API clients get
something they can parse.

See `docs/signbank-api-recommendations.md` (#5).
"""

import logging

from django.http import JsonResponse


log = logging.getLogger(__name__)

API_PATH_PREFIXES = (
    '/dictionary/api_',
    '/dictionary/get_',
    '/dictionary/upload_',
    '/dictionary/info/',
    '/dictionary/package/',
)


def _is_api_request(request):
    if any(request.path.startswith(p) for p in API_PATH_PREFIXES):
        return True
    accept = (request.META.get('HTTP_ACCEPT') or '').lower()
    return 'json' in accept and 'html' not in accept


class JsonErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not _is_api_request(request):
            return None
        log.exception(
            "api 500 on %s %s: %s", request.method, request.path, exception
        )
        from django.conf import settings
        body = {
            'ok': False,
            'status_code': 500,
            'errors': [{
                'field': None,
                'code': 'internal_error',
                'message': str(exception) if getattr(settings, 'DEBUG', False) else 'Internal server error.',
            }],
        }
        if getattr(settings, 'DEBUG', False):
            import traceback
            body['traceback'] = traceback.format_exc().splitlines()[-30:]
        return JsonResponse(body, status=500)
