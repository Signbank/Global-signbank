from signbank.settings.server_specific.default import *

ROOT = '/var/www/signbank/'
ADMINS = (('Wessel Stoop', 'w.stoop@let.ru.nl'))
LANGUAGE_NAME = "ASL"
COUNTRY_NAME = "United States of America"
SIGNBANK_VERSION_CODE = 'ASL'
URL = 'https://aslsignbank.haskins.yale.edu/'
ALLOWED_HOSTS = ['spinup-000691.yu.yale.edu','10.5.34.251','aslsignbank.haskins.yale.edu']

LANGUAGES = (
  ('en_US', 'American English'),
)

MODELTRANSLATION_LANGUAGES = ['en-us']

# Documented to be 'eng'. Use 'ame' to be unique in multilingual database.
LANGUAGES_LANGUAGE_CODE_3CHAR = (
    ('en-us', 'ame'),
)

LANGUAGE_CODE = "en-us"

DEFAULT_KEYWORDS_LANGUAGE = {'language_code_2char': 'en_US'}
DEFAULT_LANGUAGE_HEADER_COLUMN = {'English': 'name'}

SEPARATE_ENGLISH_IDGLOSS_FIELD = False

FIELDS = {}
FIELDS['main'] = ['semField']
FIELDS['phonology'] = ['handedness','locPrimLH','initial_secondary_loc','final_secondary_loc','domSF','domFlex',
                       'oriChAbd','oriChFlex','subhndsh','movSh']
FIELDS['semantics'] = ['wordClass','wordClass2','lexCatNotes','derivHist','iconType']
FIELDS['frequency'] = ['tokNo','tokNoSgnr']

MORPHEME_DISPLAY_FIELDS = []

HANDSHAPE_ETYMOLOGY_FIELDS = []
HANDEDNESS_ARTICULATION_FIELDS = []

ECV_FILE = ECV_FOLDER+'asl.ecv'
ECV_SETTINGS = {
    'CV_ID': 'ASL Signbank lexicon',
    'include_phonology_and_frequencies': False,
    # The order of languages matters as the first will
    # be treated as default by ELAN
    'languages': [
        {
            'id': 'eng',
            'description': 'ASL Signbank lexicon',
            'annotation_idgloss_fieldname': 'annotationidglosstranslation_en_US',
            'attributes': {
                'LANG_DEF': 'http://cdb.iso.org/lg/CDB-00138502-001',
                'LANG_ID': 'eng',
                'LANG_LABEL': 'English (eng)'
            }
        },
    ]

}

CROP_GLOSS_IMAGES = False
WSGI_FILE = 'signbank/wsgi.py'

SHOW_MORPHEME_SEARCH = False
SHOW_DATASET_INTERFACE_OPTIONS = False
USE_HANDSHAPE = False
USE_DERIVATIONHISTORY = True
SHOW_LETTER_NUMBER_PHONOLOGY = False
DEFAULT_DATASET = 'ASL'
DEFAULT_DATASET_ACRONYM = 'ASL'
DEFAULT_DATASET_PK = 2

EAF_FILES_LOCATION = ''
METADATA_LOCATION = ''

SHOW_ENGLISH_ONLY = True
SPEED_UP_RETRIEVING_ALL_SIGNS =	False

import datetime
RECENTLY_ADDED_SIGNS_PERIOD = datetime.timedelta(days=7)
