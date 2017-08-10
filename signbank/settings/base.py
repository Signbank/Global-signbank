# Django settings for signbank project.
import os
from signbank.settings.server_specific import *
from datetime import datetime

DEBUG = True

PROJECT_DIR = os.path.dirname(BASE_DIR)

MANAGERS = ADMINS

TIME_ZONE = 'Europe/Amsterdam'

LOCALE_PATHS = [BASE_DIR+'conf/locale']

SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True


MEDIA_ROOT = WRITABLE_FOLDER
MEDIA_URL = URL+'/media/'
MEDIA_MOBILE_URL = MEDIA_URL

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = URL+'/static/'

# Additional locations of static files
STATICFILES_DIRS = (
        os.path.join(PROJECT_DIR, "media"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '^g=q21r_nnmbz49d!vs*2gvpll-y9b@&amp;t3k2r3c$*u&amp;2la5!%s'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'signbank.pages.middleware.PageFallbackMiddleware',
#    'django_mobile.middleware.MobileDetectionMiddleware',
#    'django_mobile.middleware.SetFlavourMiddleware',
#    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'reversion.middleware.RevisionMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_DIR, 'templates/' + SIGNBANK_VERSION_CODE + '-templates')],
        'OPTIONS': {
            'context_processors': [
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "signbank.context_processors.url",
                "signbank.pages.context_processors.menu",
#                "django_mobile.context_processors.flavour",
            ],
            'loaders': [
#                'django_mobile.loader.Loader',
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]
        },
    },
]

# add the Email backend to allow logins using email as username
AUTHENTICATION_BACKENDS = (
    "signbank.registration.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
)

AUTH_PROFILE_MODULE = 'dictionary.UserProfile'

INTERNAL_IPS = ('127.0.0.1',)

ROOT_URLCONF = 'signbank.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'signbank.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.staticfiles',
    'bootstrap3',
    'django_summernote',
    'signbank.dictionary',
    'signbank.feedback',
    #'signbank.registration',
    'signbank.pages',
    'signbank.attachments',
    'signbank.video',
    'reversion',
    #'django_mobile',
    'tagging',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


# turn on lots of logging or not
DO_LOGGING = False
LOG_FILENAME = "debug.log"


SOUTH_TESTS_MIGRATE = False


## Application settings for signbank


## Settings controlling page contents

# what do we call this signbank?
LANGUAGE_NAME = "NGT"
COUNTRY_NAME = "Netherlands"

# do we implement safe search for anonymous users?
# if True, any gloss that is tagged lexis:crude will be removed from
# search results for users who are not logged in
ANON_SAFE_SEARCH = False

# do we show the tag based search for anonymous users?
ANON_TAG_SEARCH = False


# do we display the previous/next links to signs, requires gloss.sn to be used consistently
SIGN_NAVIGATION = False

# which definition fields do we show and in what order?
DEFINITION_FIELDS = ['general', 'noun', 'verb', 'interact', 'deictic', 'modifier', 'question', 'augment', 'note']

ADMIN_RESULT_FIELDS = ['annotation_idgloss', 'annotation_idgloss_en', 'handedness', 'domhndsh', 'subhndsh', 'locprim']

HANDSHAPE_RESULT_FIELDS = ['machine_value', 'english_name', 'dutch_name', 'hsFingSel', 'hsFingConf', 'hsThumb', 'hsSpread']

# location and URL for uploaded files
UPLOAD_ROOT = MEDIA_ROOT + "upload/"
UPLOAD_URL = MEDIA_URL + "upload/"

# Location for comment videos relative to MEDIA_ROOT
COMMENT_VIDEO_LOCATION = "comments"
# Location for videos associated with pages
PAGES_VIDEO_LOCATION = 'pages'
# location for upload of videos relative to MEDIA_ROOT
# videos are stored here prior to copying over to the main
# storage location
VIDEO_UPLOAD_LOCATION = "upload"

# path to store uploaded attachments relative to MEDIA_ROOT
ATTACHMENT_LOCATION = 'attachments'

# which fields from the Gloss model should be included in the quick update form on the sign view
QUICK_UPDATE_GLOSS_FIELDS = ['language', 'dialect']

# should we always require a login for viewing dictionary content
ALWAYS_REQUIRE_LOGIN = True

# name of the primary css file, relative to the media directory
PRIMARY_CSS = "bootstrap_css/test-server.css"


# do we allow people to register for the site
ALLOW_REGISTRATION = False

ACCOUNT_ACTIVATION_DAYS = 7



# show the number signs page or an under construction page?
SHOW_NUMBERSIGNS = True

LOGIN_URL = URL+'/accounts/login/'
LOGIN_REDIRECT_URL = URL+'/signs/recently_added/'


# location of ffmpeg, used to convert uploaded videos
FFMPEG_PROGRAM = "/Applications/ffmpegX.app/Contents/Resources/ffmpeg"
FFMPEG_TIMEOUT = 60
FFMPEG_OPTIONS = ["-vcodec", "h264", "-an"]


# defines the aspect ratio for videos
VIDEO_ASPECT_RATIO = 3.0/4.0

# settings for django-tagging
FORCE_LOWERCASE_TAGS = False

PRIMARY_CSS = "css/"+SIGNBANK_VERSION_CODE+"/main.css"


# defines the aspect ratio for videos
#VIDEO_ASPECT_RATIO = 360.0/640.0


# what do we call this signbank?
LANGUAGE_NAME = "NGT"
COUNTRY_NAME = "the Netherlands"

# show/don't show sign navigation
SIGN_NAVIGATION = False

# show the number signs page or an under construction page?
#SHOW_NUMBERSIGNS = False

# do we show the 'advanced search' form and implement 'safe' search?
#ADVANCED_SEARCH = False

# which definition fields do we show and in what order?
#DEFINITION_FIELDS = []


#ADMIN_RESULT_FIELDS = ['idgloss', 'annotation_idgloss']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {},
    'loggers': {},
}


import mimetypes
mimetypes.add_type("video/mp4", ".mov", True)



# a list of tags we're allowed to use
XALLOWED_TAGS = [ '',
                 'workflow:needs video',
                 'workflow:redo video',
                 'workflow:problematic',
                 'corpus:attested',
                 'lexis:doubtlex',
                 'phonology:alternating',
                 'phonology:dominant hand only',
                 'phonology:double handed',
                 'phonology:forearm rotation',
                 'phonology:handshape change',
                 'phonology:onehand',
                 'phonology:parallel',
                 'phonology:symmetrical',
                 'phonology:two handed',
                ]

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

EARLIEST_GLOSS_CREATION_DATE = datetime(2015,1,1)
SUPPORTED_CITATION_IMAGE_EXTENSIONS = ['.jpg','.jpeg','.png']
MAXIMUM_UPLOAD_SIZE = 5000000

MINIMUM_OVERLAP_BETWEEN_SIGNING_HANDS_IN_CNGT = 40

DATA_UPLOAD_MAX_NUMBER_FIELDS = None 