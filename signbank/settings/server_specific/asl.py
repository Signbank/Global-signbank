ROOT = '/scratch2/www/ASL-signbank/'
BASE_DIR = ROOT+'repo/NGT-signbank/'
WRITABLE_FOLDER = ROOT+'writable/'

DATABASES = {'default':
                {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': WRITABLE_FOLDER+'database/signbank.db',
                }
            }

ADMINS = (('Wessel Stoop', 'w.stoop@let.ru.nl'))

#Influences which template and css folder are used
SIGNBANK_VERSION_CODE = 'ASL'
URL = 'http://applejack.science.ru.nl/asl-signbank'

LANGUAGES = (
  ('en_US', 'American English'),
)
LANGUAGE_CODE = "en-us"

SEPARATE_ENGLISH_IDGLOSS_FIELD = False

FIELDS = {}

FIELDS['phonology'] = ['handedness','domhndsh','subhndsh','final_domhndsh','final_subhndsh','locprim','locPrimLH','locFocSite','locFocSiteLH','initArtOri','finArtOri','initArtOriLH','finArtOriLH']

FIELDS['semantics'] = ['semField','wordClass','wordClass2','derivHist']

FIELDS['frequency'] = ['tokNo','tokNoSgnr']

ECV_FILE = WRITABLE_FOLDER+'ecv/asl.ecv'
GLOSS_VIDEO_DIRECTORY = 'glossvideo'
GLOSS_IMAGE_DIRECTORY = 'glossimage'
OTHER_VIDEOS_DIRECTORY = WRITABLE_FOLDER+'othervideos/'
WSGI_FILE = ROOT+'signbank/wsgi.py'
VIDEOS_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_videos/'
OTHER_VIDEOS_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_other_videos/'