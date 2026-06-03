"""
Turns uncaught exceptions on API endpoints into a JSON 500 instead of the
default HTML error page. Browser hits the same URL still get HTML; JSON /
API clients get something they can parse.
"""

import logging

from django.http import JsonResponse

from signbank.api_errors import has_verbose_errors, GENERIC_ERROR_MESSAGE


log = logging.getLogger(__name__)


API_VIEW_MODULES = (
    'signbank.api_',
    'signbank.gloss_update',
    'signbank.zip_interface',
)


def _is_api_view(request):
    """
    Decide whether ``request`` is for an API endpoint without hard-coding
    URL prefixes. Order of preference:

      1. The view that resolved the URL lives in one of the API modules
         listed above (introspected via ``request.resolver_match.func``).
      2. The client explicitly asked for JSON (and not HTML) via the
         ``Accept`` header — covers cases where URL resolution has not run
         yet or the view lives outside ``signbank.api_*``.
    """
    rm = getattr(request, 'resolver_match', None)
    view = getattr(rm, 'func', None) if rm else None
    module = getattr(view, '__module__', '') or ''
    if any(module.startswith(prefix) for prefix in API_VIEW_MODULES):
        return True
    accept = (request.META.get('HTTP_ACCEPT') or '').lower()
    return 'json' in accept and 'html' not in accept


class JsonErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not _is_api_view(request):
            return None
        log.exception(
            "api 500 on %s %s: %s", request.method, request.path, exception
        )
        verbose = has_verbose_errors(getattr(request, 'user', None))
        body = {
            'ok': False,
            'status_code': 500,
            'errors': [{
                'field': None,
                'code': 'internal_error',
                'message': f"{type(exception).__name__}: {exception}" if verbose else GENERIC_ERROR_MESSAGE,
            }],
        }
        if verbose:
            import traceback
            body['traceback'] = traceback.format_exc().splitlines()[-30:]
        return JsonResponse(body, status=500)
