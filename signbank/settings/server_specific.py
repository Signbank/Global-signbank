import os
import socket

hostname = socket.gethostname()

#This should be cleaned up
if hostname == 'spitfire':
    ROOT = '/var/www2/signbank/live/'
    BASE_DIR = ROOT+'repo/signbank/'
    WRITABLE_FOLDER = ROOT+'writable/'
elif hostname == 'applejack':
    ROOT = '/scratch2/www/ASL-signbank/'
    BASE_DIR = ROOT+'repo/NGT-signbank/'
    WRITABLE_FOLDER = ROOT+'writable/'
else:
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

#Influences which template and css folder are used
SIGNBANK_VERSION_CODE = '' #'ASL'

URL = '' #'/asl-signbank'

FIELDS = {}

FIELDS['phonology'] = ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim','locVirtObj',
          'relOriMov','relOriLoc','oriCh','contType','movSh','movDir','repeat','altern','phonOth', 'mouthG',
          'mouthing', 'phonetVar',]

FIELDS['semantics'] = ['iconImg','namEnt','semField']

FIELDS['frequency'] = ['tokNo','tokNoSgnr','tokNoA','tokNoSgnrA','tokNoV','tokNoSgnrV','tokNoR','tokNoSgnrR','tokNoGe','tokNoSgnrGe',
                       'tokNoGr','tokNoSgnrGr','tokNoO','tokNoSgnrO']