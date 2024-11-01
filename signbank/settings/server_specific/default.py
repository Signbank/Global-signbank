#Where the Signbank installation lives on your server
ROOT = '/var/www/'

#Where the code is (where you did git clone)
BASE_DIR = 'repo/'

#Where Signbank can store things like images and videos
WRITABLE_FOLDER = 'writable/'
GLOSS_VIDEO_DIRECTORY = 'glossvideo'
EXAMPLESENTENCE_VIDEO_DIRECTORY = 'sensevideo'
ANNOTATEDSENTENCE_VIDEO_DIRECTORY = 'annotatedvideo'
GLOSS_IMAGE_DIRECTORY = 'glossimage'
FEEDBANK_VIDEO_DIRECTORY = 'comments'
HANDSHAPE_IMAGE_DIRECTORY = 'handshapeimage'
OTHER_MEDIA_DIRECTORY = 'othermedia/'
IMAGES_TO_IMPORT_FOLDER = 'import_images/'
VIDEOS_TO_IMPORT_FOLDER = 'import_videos/'
OTHER_MEDIA_TO_IMPORT_FOLDER = 'import_other_media/'
SIGNBANK_PACKAGES_FOLDER = 'packages/'
EAF_FILES_LOCATION = 'eaf/'
DATASET_EAF_DIRECTORY = 'eafs'
DATASET_METADATA_DIRECTORY = 'metadata_eafs'
TEST_DATA_DIRECTORY = 'test_data'
BACKUP_VIDEOS_FOLDER = 'video_backups'

#Tmp folder to use
TMP_DIR = '/tmp'

#Database settings
DATABASES = {'default':
                {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': 'database/signbank.db',
                    'TEST': {
                        'NAME': 'database/test-signbank.db',
                    }
                }
            }

#Where to store various kinds of metadata not in a table
METADATA_LOCATION = 'metadata.csv'

#Video software to use to get the middle frame
FFMPEG_PROGRAM = "ffmpeg"

#List of tuples containing the name and the email address of the admins
ADMINS = [('Spongebob Squarepants','s.squarepants@gmail.com')]

#What do we call this Signbank (for example NGT Signank, Global Signbank, ASL Signbank)?
LANGUAGE_NAME = 'Global'
COUNTRY_NAME = 'Narnia'

#Influences which template and css folder are used
SIGNBANK_VERSION_CODE = 'mysignbank'

#Should include protocol and end with a slash
URL = 'https://example.com/'

#A list of hosts, without protocol or slash
ALLOWED_HOSTS = ['example.com']

# In case your Signbank lives in a subdirectory
PREFIX_URL = ''

#The interface languages supported by your installation
gettext = lambda s: s
LANGUAGES = (
    ('en', gettext('English')),
)

MODELTRANSLATION_LANGUAGES = ['en']

MODELTRANSLATION_FIELDCHOICE_LANGUAGES = ['en']

LANGUAGES_LANGUAGE_CODE_3CHAR = (
    ('en', 'eng'),
)

#Short (abbreviated) version of how language users call their language, to be used in the langauge picker
INTERFACE_LANGUAGE_SHORT_NAMES = ['EN']

#The main interface language
LANGUAGE_CODE = "en"

#The main language for keywords (translations), using the 2 character language code
DEFAULT_KEYWORDS_LANGUAGE = {'language_code_2char': 'en'}

#The language column on which to sort in the list view
DEFAULT_LANGUAGE_HEADER_COLUMN = {'English': 'name_en'}

# The default column prefix for the human readable FieldChoice name, used for display of Field Choices
FALLBACK_FIELDCHOICE_HUMAN_LANGUAGE = 'english'

#Hide other interface languages
SHOW_ENGLISH_ONLY = False
SEPARATE_ENGLISH_IDGLOSS_FIELD = True

# This is a short mapping between 2 and 3 letter language code
LANGUAGE_CODE_MAP = [
    {2: 'en', 3: 'eng'}
]

# Regex patterns for CSV double quote
# These are needed to avoid Spreadsheet modification of double quotes to pretty double quotes
# This may be dependent on local and spreadsheet software
LEFT_DOUBLE_QUOTE_PATTERNS = '[\"\u201c]'
RIGHT_DOUBLE_QUOTE_PATTERNS = '[\"\u201d]'
REGEX_SPECIAL_CHARACTERS = '[+]'
USE_REGULAR_EXPRESSIONS = False

#From all possible gloss fields available, display these
FIELDS = {}

FIELDS['main'] = ['useInstr','wordClass']

# fields are ordered per kind: Field Choice Lists, Text, Boolean
# followed by etymology and articulation
FIELDS['phonology'] = ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim',
                       'contType', 'movSh', 'movDir',
                       'repeat', 'altern',
                       'relOriMov', 'relOriLoc', 'oriCh',
                       'locVirtObj', 'phonOth', 'mouthG', 'mouthing', 'phonetVar',
                       'domhndsh_letter', 'domhndsh_number', 'subhndsh_letter', 'subhndsh_number',
                       'weakdrop', 'weakprop']

FIELDS['semantics'] = ['semField', 'derivHist', 'namEnt','valence','iconImg','concConcSet']

FIELDS['frequency'] = ['tokNo','tokNoSgnr']

FIELDS['handshape'] = ['hsNumSel','hsFingSel','hsFingSel2','hsFingConf','hsFingConf2','hsAperture','hsSpread',
                       'hsFingUnsel','fsT','fsI','fsM','fsR','fsP','fs2T','fs2I','fs2M','fs2R','fs2P','ufT','ufI','ufM',
                       'ufR','ufP']

FIELDS['publication'] = ['inWeb', 'isNew']

FIELDS['properties'] = ['hasvideo', 'hasothermedia', 'hasmultiplesenses',
                        'definitionRole', 'definitionContains', 'defspublished',
                        'createdBy', 'createdAfter', 'createdBefore',
                        'tags', 'excludeFromEcv']
FIELDS['relations'] = ['relation', 'hasRelation', 'relationToForeignSign', 'hasRelationToForeignSign']
FIELDS['morpheme'] = ['morpheme', 'isablend', 'ispartofablend']
FIELDS['morpheme_properties'] = ['hasvideo',
                                 'definitionRole', 'definitionContains', 'defspublished',
                                 'createdBy', 'createdAfter', 'createdBefore',
                                 'tags']

GLOSS_CHOICE_FIELDS = ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim',
                       'relOriMov',
                       'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', 'wordClass',
                       'semField', 'derivHist', 'namEnt', 'valence',
                       'definitionRole', 'hasComponentOfType', 'mrpType', 'hasRelation']

GLOSSSENSE_CHOICE_FIELDS = ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim',
                            'relOriMov',
                            'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', 'wordClass',
                            'semField', 'derivHist', 'namEnt', 'valence',
                            'definitionRole', 'hasComponentOfType']

# these are the multiple select fields for Morpheme Search, the field definitionRole is a search form field,
# the field mrpType appears in Morpheme, the rest are also in Gloss
MORPHEME_CHOICE_FIELDS = ['handedness', 'handCh', 'relatArtic', 'locprim', 'relOriMov',
                          'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', 'mrpType', 'wordClass',
                          'semField', 'derivHist', 'namEnt', 'valence', 'definitionRole']

# Use these fields in the server specific settings to specify frequency fields, if available
FREQUENCY_CATEGORIES = []
FREQUENCY_REGIONS = []
FREQUENCY_FIELDS = {}

# the following are used to avoid using fieldnames in the code
# although these are all Boolean fields
# it's not sufficient to identify per type because repeat and altern are also Booleans
HANDSHAPE_ETYMOLOGY_FIELDS = ['domhndsh_letter','domhndsh_number','subhndsh_letter','subhndsh_number']
HANDEDNESS_ARTICULATION_FIELDS = ['weakdrop','weakprop']

#Use these fields to figure out which glosses are minimal pairs
MINIMAL_PAIRS_FIELDS = ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim','relOriMov','relOriLoc',
                        'oriCh','contType','movSh','movDir','repeat','altern']
MINIMAL_PAIRS_SEARCH_FIELDS = MINIMAL_PAIRS_FIELDS + ['namEnt','semField','valence']
MINIMAL_PAIRS_CHOICE_FIELDS = ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim', 'relOriMov',
                               'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', 'namEnt', 'semField', 'valence']

#Display these fields as columns in the list view
GLOSS_LIST_DISPLAY_FIELDS = ['handedness','domhndsh','subhndsh','locprim']

# These are fields in the Search forms by panel
SEARCH_BY = {}
# the ordering of the list of publication fields is important for the Gloss Search template
SEARCH_BY['publication'] = FIELDS['publication'] + FIELDS['properties']
SEARCH_BY['morpheme_publication'] = FIELDS['publication'] + FIELDS['morpheme_properties']
SEARCH_BY['relations'] = FIELDS['relations']
SEARCH_BY['morpheme'] = ['morpheme', 'hasComponentOfType', 'mrpType', 'isablend', 'ispartofablend']

QUERY_DISPLAY_FIELDS = MINIMAL_PAIRS_SEARCH_FIELDS
SHOW_QUERY_PARAMETERS_AS_BUTTON = True

# fields are ordered per kind: Field Choice Lists, Text, Boolean
MORPHEME_DISPLAY_FIELDS = ['handedness','handCh','relatArtic','locprim','relOriMov',
                       'relOriLoc','oriCh','contType','movSh','movDir', 'locVirtObj','phonOth','repeat','altern']

#Where the ECV files are
ECV_FOLDER = 'ecv/'
ECV_FILE = 'myecv.ecv'

#What do you want to include in the ECV file?
ECV_SETTINGS = {
    'include_phonology_and_frequencies': True,

    'description_fields' : ['handedness', 'tokNo'],

    # The order of languages matters as the first will
    # be treated as default by ELAN
    'languages': [
        {
            'id': 'eng',
            'description': 'My description',
            'annotation_idgloss_fieldname': 'annotationidglosstranslation_en',
            'attributes': {
                'LANG_DEF': 'http://cdb.iso.org/lg/CDB-00138502-001',
                'LANG_ID': 'eng',
                'LANG_LABEL': 'English (eng)'
            }
        },
    ]
}

#Make a smaller version of uploaded images, for storage reasons?
CROP_GLOSS_IMAGES = True

#Where the WSGI files lives
WSGI_FILE = 'lib/python2.7/site-packages/signbank/wsgi.py'

#Whether the morpheme functionality should be present in the interface
SHOW_MORPHEME_SEARCH = True

#Whether the letter number phonology should be present in the interface
SHOW_LETTER_NUMBER_PHONOLOGY = True

#Whether colors can be set for field choices
SHOW_FIELD_CHOICE_COLORS = True

#Whether the dataset functionality should be present in the interface
SHOW_DATASET_INTERFACE_OPTIONS = True

# Used in Toggle View to hide
SHOW_NAMED_ENTITY = False

#Settings for the default dataset
DEFAULT_DATASET = 'Your Dataset'
DEFAULT_DATASET_ACRONYM = 'YDS'
DEFAULT_DATASET_LANGUAGE_ID = 1
DEFAULT_DATASET_PK = 1
TEST_DATASET_ACRONYM = 'TESTDB'

#whether the Handshape functionality should be present in the interface
USE_HANDSHAPE = True

#whether the Derivation History functionality should be present in the interface
USE_DERIVATIONHISTORY = True

# Only set this to true after the foreign key field choices have replaced the machine value field choices in the migration
USE_FIELD_CHOICE_FOREIGN_KEY = True

#Gloss fields used in the API
API_FIELDS = ['idgloss']

#How long will new glosses be considered new?
import datetime
RECENTLY_ADDED_SIGNS_PERIOD = datetime.timedelta(days=90)
# The following is the ISO 8601 format
DATE_FORMAT = "%Y-%m-%d"

#Experimental feature to make the list view faster
SPEED_UP_RETRIEVING_ALL_SIGNS = True

#Delete the video and image files when a GlossVideo instance is deleted
DELETE_FILES_ON_GLOSSVIDEO_DELETE = False

#Whether the non ASCII characters in the path and filename of an uploaded video should be escaped
ESCAPE_UPLOADED_VIDEO_FILE_PATH = False

#Enables plugin such that images/videos only appear to logged in users
USE_X_SENDFILE = False

# this keeps the browser from crashing
MAX_SCROLL_BAR = 500

#Print to debug registration / access emails
DEBUG_EMAILS_ON = False

# default url to admin page, specify a hidden one in server_specific to override this
ADMIN_URL = 'admin'

# Redirect to homepage after logout
LOGOUT_REDIRECT_URL = '/'

FILESYSTEM_SIGNBANK_GROUPS = ['signbank', 'www-data', 'signbank-writable', 'wwwsignbank']

SHARE_SENSES = False

DEBUG_CSV = False

DEBUG_SENSES = False

DEBUG_VIDEOS = False

# Set this to True to avoid deleting glosses that are in relations with other glosses
GUARDED_GLOSS_DELETE = False

GUARDED_MORPHEME_DELETE = True

FILE_UPLOAD_HANDLERS = ['django.core.files.uploadhandler.TemporaryFileUploadHandler',]

FILE_UPLOAD_MAX_MEMORY_SIZE = 15728640 # 15 MB