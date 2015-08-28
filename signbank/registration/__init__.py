from django.contrib.auth.backends import ModelBackend 
from django.contrib.auth.models import User
import re
email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain

class EmailBackend(ModelBackend):
    """Validate using email address as the username"""
    
    def authenticate(self, username=None, password=None): 
        if email_re.search(username):
            try: 
                user = User.objects.get(email__iexact=username) 
                if user.check_password(password): 
                    return user
            except User.DoesNotExist: 
                return None
        return None
        
        