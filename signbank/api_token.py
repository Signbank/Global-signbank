
import hashlib
import secrets
import string

from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _

from signbank.dictionary.models import SignbankAPIToken


def generate_auth_token(length=16):
    """Generate a random authentication token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_token(token):
    """Hash the token using SHA-256."""
    hash_object = hashlib.sha256(token.encode())
    return hash_object.hexdigest()


class APIAuthException(Exception):
    """ Exception class to raise any problems in authorizing a user for the API"""
    pass


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
    signbank_token = SignbankAPIToken.objects.filter(api_token=hashed_token).first()
    if not signbank_token:
        raise APIAuthException(_("Your Authorization Token does not match anything."))

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
            return JsonResponse({'errors': str(api_auth_exception)})

        if api_user:
            request.user = api_user
        return func(*args, **kwargs)
    return wrapper
