from django.db.models import *

from django.contrib.auth.models import User
from signbank.dictionary.models import SignbankToken
import hashlib
import secrets
import string


def generate_auth_token(length=16):
    """Generate a random authentication token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_token(token):
    """Hash the token using SHA-256."""
    hash_object = hashlib.sha256(token.encode())
    return hash_object.hexdigest()


