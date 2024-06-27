
import hashlib
import secrets
import string

from django.http import HttpRequest

from signbank.dictionary.models import SignbankAPIToken


def generate_auth_token(length=16):
    """Generate a random authentication token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_token(token):
    """Hash the token using SHA-256."""
    hash_object = hashlib.sha256(token.encode())
    return hash_object.hexdigest()


def get_api_user(request):
    """Return a user based if there is an API token in the request, else None"""
    auth_token_request = request.headers.get('Authorization', '')
    if not auth_token_request:
        return None

    auth_token = auth_token_request.removeprefix('Bearer ')
    if not auth_token:
        return None

    hashed_token = hash_token(auth_token)
    signbank_token = SignbankAPIToken.objects.filter(api_token=hashed_token).first()
    return signbank_token.signbank_user if signbank_token else None


def put_api_user_in_request(func):
    """A decorator to replace the request.user with the user found by checking an API token"""
    def wrapper(*args, **kwargs):
        if isinstance(args[0], HttpRequest):
            request = args[0]
            if api_user := get_api_user(request):
                request.user = api_user
        return func(*args, **kwargs)
    return wrapper
