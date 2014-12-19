from signbank.settings.base import *
from signbank.settings.local import *

DEBUG = True
TEMPLATE_DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'cabici_pg',
        'USER': 'cabici_pg',
        'PASSWORD': 'pigeon59',
        'HOST': '',
        'PORT': '',
    }
}


# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = "/home/stevecassidy/webapps/cabicinet_static/"

# should be customised on the production server and not kept in VC
SECRET_KEY = '^g=q21r_nnmbz49d!vs*2gvplfsd((02l-y9b@&amp;t3k2r3c$*u&amp;2la5!%s'

ALLOWED_HOSTS = ['cabici.net']
