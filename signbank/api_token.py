
import hashlib
import secrets
import string
from datetime import timedelta

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from signbank.dictionary.models import SignbankAPIToken

TOKEN_LENGTH = 40
TOKEN_PREFIX_LENGTH = 6
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
RATE_LIMIT_WINDOW_SECONDS = 3600
# avoid a database write on every API call: last_used_at is only refreshed after this interval
LAST_USED_UPDATE_INTERVAL = timedelta(minutes=1)


def generate_auth_token(length=TOKEN_LENGTH):
    """Generate a random authentication token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_token(token):
    """Hash the token using SHA-256."""
    hash_object = hashlib.sha256(token.encode())
    return hash_object.hexdigest()


def create_api_token(user, name='', expires_at=None, rate_limit=None, read_only=False):
    """
    Create a SignbankAPIToken for the user.
    Returns the token object and the plain token, which is not stored and can only be shown once.
    """
    new_token = generate_auth_token()
    signbank_token = SignbankAPIToken.objects.create(signbank_user=user,
                                                     api_token=hash_token(new_token),
                                                     prefix=new_token[:TOKEN_PREFIX_LENGTH],
                                                     name=name,
                                                     expires_at=expires_at,
                                                     rate_limit=rate_limit,
                                                     read_only=read_only)
    return signbank_token, new_token


class APIAuthException(Exception):
    """ Exception class to raise any problems in authorizing a user for the API"""
    status = 401


class APIPermissionException(APIAuthException):
    status = 403


class APIRateLimitException(APIAuthException):
    status = 429


def check_rate_limit(signbank_token):
    """Count the request in a fixed one hour window, raise an exception when over the limit"""
    limit = signbank_token.effective_rate_limit()
    if not limit:
        return
    window = int(timezone.now().timestamp()) // RATE_LIMIT_WINDOW_SECONDS
    cache_key = f'api_token_rate:{signbank_token.pk}:{window}'
    cache.add(cache_key, 0, RATE_LIMIT_WINDOW_SECONDS)
    try:
        count = cache.incr(cache_key)
    except ValueError:
        # the key expired between add and incr
        cache.set(cache_key, 1, RATE_LIMIT_WINDOW_SECONDS)
        count = 1
    if count > limit:
        raise APIRateLimitException(_("Rate limit exceeded: this token allows %(limit)s requests per hour.")
                                    % {'limit': limit})


def get_api_user(request):
    """
    Return a user if there is a correct API token in the request.
    The HTTP header must contain:

    Authorization:"Bearer XXXXXX"

    where XXXXXX represents the user's API Token
    """
    auth_token_request = request.headers.get('Authorization', '')
    if not auth_token_request:
        return None

    auth_token = auth_token_request.removeprefix('Bearer').strip()
    if not auth_token:
        raise APIAuthException(_("No Authorization token found"))

    hashed_token = hash_token(auth_token)
    signbank_token = SignbankAPIToken.objects.filter(api_token=hashed_token).select_related('signbank_user').first()
    if not signbank_token:
        raise APIAuthException(_("Your Authorization Token does not match anything."))
    if not signbank_token.is_active:
        raise APIAuthException(_("Your Authorization Token has been deactivated."))
    if signbank_token.is_expired():
        raise APIAuthException(_("Your Authorization Token has expired."))
    if not signbank_token.signbank_user.is_active:
        raise APIAuthException(_("The user of this Authorization Token is not active."))
    if signbank_token.read_only and request.method not in SAFE_METHODS:
        raise APIPermissionException(_("Your Authorization Token is read only."))

    check_rate_limit(signbank_token)

    now = timezone.now()
    if not signbank_token.last_used_at or now - signbank_token.last_used_at > LAST_USED_UPDATE_INTERVAL:
        SignbankAPIToken.objects.filter(pk=signbank_token.pk).update(last_used_at=now)

    return signbank_token.signbank_user


def put_api_user_in_request(func):
    """A decorator to replace the request.user with the user found by checking an API token"""
    def wrapper(*args, **kwargs):
        if not args or not isinstance(args[0], HttpRequest):
            return func(*args, **kwargs)

        request = args[0]

        try:
            api_user = get_api_user(request)
        except APIAuthException as api_auth_exception:
            return JsonResponse({'errors': [str(api_auth_exception)]}, status=api_auth_exception.status)

        if api_user:
            request.user = api_user
        return func(*args, **kwargs)
    return wrapper
