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

gettext = lambda s: s
LANGUAGES = (
  ('en_US', gettext('American English')),
)
LANGUAGE_CODE = "en-us"

SEPARATE_ENGLISH_IDGLOSS_FIELD = False

DEFAULT_KEYWORDS_LANGUAGE = {'name': 'English'}

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