ROOT = ''
BASE_DIR = ROOT+''
WRITABLE_FOLDER = ROOT+'writable/'

DATABASES = {'default':
                {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': '/path/to/database',
                }
            }

ADMINS = (('name', 'name@example.com'))

#Influences which template and css folder are used
SIGNBANK_VERSION_CODE = ''
URL = ''

LANGUAGES = (
  ('en', 'English'),
)
LANGUAGE_CODE = "en"

SEPARATE_ENGLISH_IDGLOSS_FIELD = False

FIELDS = {}

FIELDS['phonology'] = ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim','locVirtObj',
          'relOriMov','relOriLoc','oriCh','contType','movSh','movDir','repeat','altern','phonOth', 'mouthG',
          'mouthing', 'phonetVar',]

FIELDS['semantics'] = ['iconImg','namEnt','semField']

FIELDS['frequency'] = ['tokNo','tokNoSgnr','tokNoA','tokNoSgnrA','tokNoV','tokNoSgnrV','tokNoR','tokNoSgnrR','tokNoGe','tokNoSgnrGe',
                       'tokNoGr','tokNoSgnrGr','tokNoO','tokNoSgnrO']

ECV_FILE = WRITABLE_FOLDER+'ecv/ngt.ecv'
GLOSS_VIDEO_DIRECTORY = 'glossvideo'
GLOSS_IMAGE_DIRECTORY = 'glossimage'
CROP_GLOSS_IMAGES = True
OTHER_MEDIA_DIRECTORY = WRITABLE_FOLDER+'othermedia/'
WSGI_FILE = ROOT+'signbank/wsgi.py'
VIDEOS_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_videos/'
IMAGES_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_images/'
OTHER_MEDIA_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_other_media/'
SIGNBANK_PACKAGES_FOLDER = WRITABLE_FOLDER+'packages/'

CNGT_EAF_FILES_LOCATION = ''
CNGT_METADATA_LOCATION = ''

