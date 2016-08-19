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

FIELDS['phonology'] = ['handedness','locPrimLH','initial_secondary_loc','final_secondary_loc','domSF','domFlex',
                       'oriChAbd','oriChFlex','subhndsh','movSh']

FIELDS['semantics'] = ['semField','wordClass','wordClass2','lexCatNotes','derivHist','iconType']

FIELDS['frequency'] = ['tokNo','tokNoSgnr']

FIELDS['other'] = []

ECV_FILE = WRITABLE_FOLDER+'ecv/asl.ecv'
GLOSS_VIDEO_DIRECTORY = 'glossvideo'
GLOSS_IMAGE_DIRECTORY = 'glossimage'
CROP_GLOSS_IMAGES = False
OTHER_MEDIA_DIRECTORY = WRITABLE_FOLDER+'othermedia/'
WSGI_FILE = ROOT+'signbank/wsgi.py'
IMAGES_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_images/'
VIDEOS_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_videos/'
OTHER_MEDIA_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_other_media/'
SIGNBANK_PACKAGES_FOLDER = WRITABLE_FOLDER+'packages/'

CNGT_EAF_FILES_LOCATION = ''
CNGT_METADATA_LOCATION = ''