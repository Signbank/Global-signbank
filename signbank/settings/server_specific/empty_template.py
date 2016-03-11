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
OTHER_VIDEOS_DIRECTORY = WRITABLE_FOLDER+'othervideos/'
WSGI_FILE = ROOT+'signbank/wsgi.py'