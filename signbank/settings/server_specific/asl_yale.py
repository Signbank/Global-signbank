ROOT = '/var/www/signbank/'
BASE_DIR = ROOT+'repo/'
WRITABLE_FOLDER = ROOT+'writable/'

DATABASES = {'default':
                {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': WRITABLE_FOLDER+'database/signbank.db',
                }
            }

ADMINS = (('Wessel Stoop', 'w.stoop@let.ru.nl'))

# what do we call this signbank?
LANGUAGE_NAME = "ASL"
COUNTRY_NAME = "United States of America"

#Influences which template and css folder are used
SIGNBANK_VERSION_CODE = 'ASL'
URL = 'https://aslsignbank.haskins.yale.edu/'
ALLOWED_HOSTS = ['spinup-000691.yu.yale.edu','10.5.34.251','aslsignbank.haskins.yale.edu']

LANGUAGES = (
  ('en_US', 'American English'),
)

LANGUAGE_CODE = "en-us"

DEFAULT_KEYWORDS_LANGUAGE = {'language_code_2char': 'en_US'}

SEPARATE_ENGLISH_IDGLOSS_FIELD = False

FIELDS = {}

FIELDS['main'] = ['semField']

FIELDS['phonology'] = ['handedness','locPrimLH','initial_secondary_loc','final_secondary_loc','domSF','domFlex',
                       'oriChAbd','oriChFlex','subhndsh','movSh']

FIELDS['semantics'] = ['wordClass','wordClass2','lexCatNotes','derivHist','iconType']

FIELDS['frequency'] = ['tokNo','tokNoSgnr']

ECV_FILE = WRITABLE_FOLDER+'ecv/asl.ecv'
ECV_SETTINGS = {
    'CV_ID': 'ASL Signbank lexicon',
    'include_phonology_and_frequencies': False,
    # The order of languages matters as the first will
    # be treated as default by ELAN
    'languages': [
        {
            'id': 'eng',
            'description': 'ASL Signbank lexicon',
            'annotation_idgloss_fieldname': 'annotation_idgloss',
            'attributes': {
                'LANG_DEF': 'http://cdb.iso.org/lg/CDB-00138502-001',
                'LANG_ID': 'eng',
                'LANG_LABEL': 'English (eng)'
            }
        },
    ]

}

GLOSS_VIDEO_DIRECTORY = 'glossvideo'
GLOSS_IMAGE_DIRECTORY = 'glossimage'
CROP_GLOSS_IMAGES = False
OTHER_MEDIA_DIRECTORY = WRITABLE_FOLDER+'othermedia/'
WSGI_FILE = ROOT+'signbank/wsgi.py'
IMAGES_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_images/'
VIDEOS_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_videos/'
OTHER_MEDIA_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_other_media/'
SIGNBANK_PACKAGES_FOLDER = WRITABLE_FOLDER+'packages/'

SHOW_MORPHEME_SEARCH = False

CNGT_EAF_FILES_LOCATION = ''
CNGT_METADATA_LOCATION = ''

FFMPEG_PROGRAM = "avconv"
TMP_DIR = "/tmp"

API_FIELDS = [
    'idgloss',
    'annotation_idgloss'
]

SHOW_ENGLISH_ONLY = True

# This is a short mapping between 2 and 3 letter language code
# This needs more complete solution (perhaps a library),
# but then the code cn for Chinese should changed to zh.
LANGUAGE_CODE_MAP = [
    {2:'nl',3:'nld'},
    {2:'en',3:'eng'},
    {2:'zh-hans',3:'chi'}
]

SPEED_UP_RETRIEVING_ALL_SIGNS =	False
import datetime
RECENTLY_ADDED_SIGNS_PERIOD = datetime.timedelta(days=7)
DEFAULT_DATASET_PK = 2
