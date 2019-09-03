#Where the Signbank installation lives on your server
ROOT = '/var/www/signbank/live/'

#Where the code is (where you did git clone)
BASE_DIR = 'repo/'

#Where Signbank can store things like images and videos
WRITABLE_FOLDER = 'writable/'
GLOSS_VIDEO_DIRECTORY = 'glossvideo'
GLOSS_IMAGE_DIRECTORY = 'glossimage'
FEEDBANK_VIDEO_DIRECTORY = 'comments'
HANDSHAPE_IMAGE_DIRECTORY = 'handshapeimage'
OTHER_MEDIA_DIRECTORY = 'othermedia/'
IMAGES_TO_IMPORT_FOLDER = 'import_images/'
VIDEOS_TO_IMPORT_FOLDER = 'import_videos/'
OTHER_MEDIA_TO_IMPORT_FOLDER = 'import_other_media/'
SIGNBANK_PACKAGES_FOLDER = 'packages/'
EAF_FILES_LOCATION = 'eaf/'

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
FFMPEG_PROGRAM = "avconv"

#List of tuples containing the name and the email address of the admins
ADMINS = (('Spongebob Squarepants','s.squarepants@gmail.com'))

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
LANGUAGES = [('en', gettext('English'))]

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
# This needs more complete solution (perhaps a library),
# but then the code cn for Chinese should changed to zh.
LANGUAGE_CODE_MAP = [
    {2:'nl',3:'nld'},
    {2:'en',3:'eng'},
    {2:'zh-hans',3:'chi'}
]

#From all possible gloss fields available, display these
FIELDS = {}

FIELDS['main'] = ['useInstr','wordClass']

FIELDS['phonology'] = ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim','locVirtObj','relOriMov',
                       'relOriLoc','oriCh','contType','movSh','movDir','repeat','altern','phonOth', 'mouthG',
                       'mouthing', 'phonetVar','domhndsh_letter','domhndsh_number','subhndsh_letter','subhndsh_number',
                       'weakdrop','weakprop']

FIELDS['semantics'] = ['iconImg','namEnt','semField','valence','concConcSet']

FIELDS['frequency'] = ['tokNo','tokNoSgnr','tokNoA','tokNoSgnrA','tokNoV','tokNoSgnrV','tokNoR','tokNoSgnrR','tokNoGe',
                       'tokNoSgnrGe','tokNoGr','tokNoSgnrGr','tokNoO','tokNoSgnrO']

FIELDS['handshape'] = ['hsNumSel','hsFingSel','hsFingSel2','hsFingConf','hsFingConf2','hsAperture','hsSpread',
                       'hsFingUnsel','fsT','fsI','fsM','fsR','fsP','fs2T','fs2I','fs2M','fs2R','fs2P','ufT','ufI','ufM',
                       'ufR','ufP']

#Use these fields to figure out which glosses are minimal pairs
MINIMAL_PAIRS_FIELDS = ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim','relOriMov','relOriLoc',
                        'oriCh','contType','movSh','movDir','repeat','altern']

#Display these fields als columns in the list view
GLOSS_LIST_DISPLAY_FIELDS = ['handedness','domhndsh','subhndsh','locprim']

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

#Whether the dataset functionality should be present in the interface
SHOW_DATASET_INTERFACE_OPTIONS = True

#Settings for the default dataset
DEFAULT_DATASET = 'Your Dataset'
DEFAULT_DATASET_ACRONYM = 'YDS'
DEFAULT_DATASET_LANGUAGE_ID = 1
DEFAULT_DATASET_PK = 1

#Gloss fields used in the API
API_FIELDS = ['idgloss']

#How long will new glosses be considered new?
import datetime
RECENTLY_ADDED_SIGNS_PERIOD = datetime.timedelta(days=90)

#Experimental feature to make the list view faster
SPEED_UP_RETRIEVING_ALL_SIGNS =	True

#Delete the video and image files when a GlossVideo instance is deleted
DELETE_FILES_ON_GLOSSVIDEO_DELETE = False
