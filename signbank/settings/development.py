from signbank.settings.base import *
from signbank.settings.server_specific import *
from datetime import datetime

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


GLOSS_VIDEO_DIRECTORY = 'glossvideo'
OTHER_VIDEOS_DIRECTORY = '/var/www2/signbank/live/writable/othervideos/'

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

DATABASE_NAME = '/www2/signbank/live/repo/signbank/signbank.db';
EARLIEST_GLOSS_CREATION_DATE = datetime(2015,1,1)
WSGI_FILE = '/var/www2/signbank/live/virtualenv/signbank/lib/python2.7/site-packages/signbank/wsgi.py'
ECV_FILE = '/var/www2/signbank/live/writable/ecv/cngt.ecv'
