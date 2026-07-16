"""
Helpers for shaping error responses returned by the API.

Not all clients holding a valid API token can be trusted with raw Python
exception text — internal paths, query fragments and other sensitive data
may leak through ``str(exc)``. ``has_verbose_errors`` decides who gets the
detail; ``safe_error_message`` returns the appropriate string for the
caller. See PR #1743 (Wessel/Micha review thread) for the discussion.
"""

from django.conf import settings


VERBOSE_ERRORS_GROUP = 'Verbose API Errors'

GENERIC_ERROR_MESSAGE = 'Internal server error.'


def has_verbose_errors(user):
    """
    True if ``user`` is allowed to see raw exception detail in API responses.

    Superusers always qualify, and so do members of the
    ``Verbose API Errors`` group (created by an admin per deployment).
    ``settings.DEBUG`` also enables verbose errors globally — useful for
    development and signbank-test, never for production.
    """
    if getattr(settings, 'DEBUG', False):
        return True
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return user.groups.filter(name=VERBOSE_ERRORS_GROUP).exists()


def safe_error_message(exc, user, *, generic=GENERIC_ERROR_MESSAGE):
    """
    Return either the formatted exception or a generic message, depending
    on whether ``user`` is allowed to see verbose errors.
    """
    if has_verbose_errors(user):
        return f"{type(exc).__name__}: {exc}"
    return generic
