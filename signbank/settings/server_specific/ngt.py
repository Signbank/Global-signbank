import socket
hostname = socket.gethostname()

if hostname == 'spitfire':
    ROOT = '/var/www2/signbank/live/'
else:
    ROOT = '/www/signbank/live/'

BASE_DIR = ROOT+'repo/signbank/'
WRITABLE_FOLDER = ROOT+'writable/'

DATABASES = {'default':
                {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': WRITABLE_FOLDER+'database/signbank.db',
                }
            }

ADMINS = (('Wessel Stoop', 'w.stoop@let.ru.nl'))

#Influences which template and css folder are used
SIGNBANK_VERSION_CODE = 'NGT'
URL = 'https://signbank.science.ru.nl/'

LANGUAGES = (
  ('en', 'English'),
  ('nl', 'Dutch'),
  ('cn', 'Chinese')
)
LANGUAGE_CODE = "en"

SEPARATE_ENGLISH_IDGLOSS_FIELD = True

FIELDS = {}

FIELDS['main'] = ['useInstr','wordClass']

FIELDS['phonology'] = ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim','locVirtObj',
          'relOriMov','relOriLoc','oriCh','contType','movSh','movDir','repeat','altern','phonOth', 'mouthG',
          'mouthing', 'phonetVar',]

FIELDS['semantics'] = ['iconImg','namEnt','semField','valence']

FIELDS['frequency'] = ['tokNo','tokNoSgnr','tokNoA','tokNoSgnrA','tokNoV','tokNoSgnrV','tokNoR','tokNoSgnrR','tokNoGe','tokNoSgnrGe',
                       'tokNoGr','tokNoSgnrGr','tokNoO','tokNoSgnrO']

ECV_FILE = WRITABLE_FOLDER+'ecv/ngt.ecv'
ECV_SETTINGS = {
    'CV_ID': 'CNGT_RU-lexicon',
    'include_phonology_and_frequencies': True,

    # The order of languages matters as the first will
    # be treated as default by ELAN
    'languages': [
        {
            'id': 'nld',
            'description': 'De glossen-CV voor het CNGT (RU)',
            'annotation_idgloss_fieldname': 'annotation_idgloss',
            'attributes': {
                'LANG_DEF': 'http://cdb.iso.org/lg/CDB-00138580-001',
                'LANG_ID': 'nld',
                'LANG_LABEL': 'Dutch (nld)'
            }
        },
        {
            'id': 'eng',
            'description': 'The glosses CV for the CNGT (RU)',
            'annotation_idgloss_fieldname': 'annotation_idgloss_en',
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
CROP_GLOSS_IMAGES = True
OTHER_MEDIA_DIRECTORY = WRITABLE_FOLDER+'othermedia/'
WSGI_FILE = ROOT+'virtualenv/signbank/lib/python2.7/site-packages/signbank/wsgi.py'
IMAGES_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_images/'
VIDEOS_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_videos/'
OTHER_MEDIA_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_other_media/'
SIGNBANK_PACKAGES_FOLDER = WRITABLE_FOLDER+'packages/'

CNGT_EAF_FILES_LOCATION = WRITABLE_FOLDER+'corpus-ngt/eaf/'
CNGT_METADATA_LOCATION = ROOT+'virtualenv/signbank/CNGT_MetadataEnglish_OtherResearchers.csv'

FFMPEG_PROGRAM = "avconv"
TMP_DIR = "/tmp"