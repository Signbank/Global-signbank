from os import environ

ROOT = 'd:/data files/TG/'

# BASE_DIR = ROOT+'repo/signbank/'
BASE_DIR = 'D:\\Data Files\\VS2010\\Projects\\NGT\\signbank\\'
WRITABLE_FOLDER = ROOT+'writable\\'

DATABASES = {'default':
                {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': WRITABLE_FOLDER+'database\\signbank.db',
                }
            }

ADMINS = (('Erwin Komen', 'e.komen@let.ru.nl'))

#Influences which template and css folder are used
SIGNBANK_VERSION_CODE = 'NGT'
# Running it locally is possible -- but then the static/js files are not present:
# URL = 'http://localhost:'+environ.get('SERVER_PORT', '5555')+'/'
URL = ''
# Therefore: run it on science:
# URL = 'http://signbank.science.ru.nl/'

LANGUAGES = (
  ('en', 'English'),
  ('nl', 'Dutch'),
  ('cn', 'Chinese')
)
LANGUAGE_CODE = "en"

SEPARATE_ENGLISH_IDGLOSS_FIELD = True

FIELDS = {}

FIELDS['phonology'] = ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim','locVirtObj',
          'relOriMov','relOriLoc','oriCh','contType','movSh','movDir','repeat','altern','phonOth', 'mouthG',
          'mouthing', 'phonetVar',]

FIELDS['semantics'] = ['iconImg','namEnt','semField']

FIELDS['frequency'] = ['tokNo','tokNoSgnr','tokNoA','tokNoSgnrA','tokNoV','tokNoSgnrV','tokNoR','tokNoSgnrR','tokNoGe','tokNoSgnrGe',
                       'tokNoGr','tokNoSgnrGr','tokNoO','tokNoSgnrO']

ECV_FILE = WRITABLE_FOLDER+'ecv\\ngt.ecv'
GLOSS_VIDEO_DIRECTORY = 'glossvideo'
GLOSS_IMAGE_DIRECTORY = 'glossimage'
OTHER_MEDIA_DIRECTORY = WRITABLE_FOLDER+'othermedia\\'
WSGI_FILE = BASE_DIR+'signbank\\wsgi.py'
VIDEOS_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_videos\\'
OTHER_MEDIA_TO_IMPORT_FOLDER = WRITABLE_FOLDER+'import_other_media\\'