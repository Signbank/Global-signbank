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
URL = '/asl-signbank'

LANGUAGES = (
  ('en', 'English'),
)
LANGUAGE_CODE = "en"

SEPARATE_ENGLISH_IDGLOSS_FIELD = False

FIELDS = {}

FIELDS['phonology'] = ['handedness','domhndsh','subhndsh','final_domhndsh','final_subhndsh','locprim','locPrimLH','locFocSite','locFocSiteLH','initArtOri','finArtOri','initArtOriLH','finArtOriLH']

FIELDS['semantics'] = ['semField','wordClass','wordClass2','derivHist']

FIELDS['frequency'] = ['tokNo','tokNoSgnr']

ECV_FILE = WRITABLE_FOLDER+'ecv/asl.ecv'
GLOSS_VIDEO_DIRECTORY = 'glossvideo'
OTHER_VIDEOS_DIRECTORY = WRITABLE_FOLDER+'othervideos/'
WSGI_FILE = ROOT+'signbank/wsgi.py'