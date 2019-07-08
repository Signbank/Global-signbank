from signbank.settings.server_specific.default import *

ADMINS = (('Wessel Stoop', 'w.stoop@let.ru.nl'))
LANGUAGE_NAME = 'Global'
COUNTRY_NAME = 'Netherlands'
SIGNBANK_VERSION_CODE = 'global'
URL = 'https://signbank.science.ru.nl/'
ALLOWED_HOSTS = ['signbank.science.ru.nl','signbank.cls.ru.nl','new.signbank.science.ru.nl']

EAF_FILES_LOCATION = 'corpus-ngt/eaf/'
METADATA_LOCATION = 'CNGT_MetadataEnglish_OtherResearchers.csv'

LANGUAGES = (
  ('en', gettext('English')),
  ('nl', gettext('Dutch')),
  ('zh-hans', gettext('Chinese'))
)

ECV_FILE = ECV_FOLDER+'ngt.ecv'
ECV_SETTINGS = {
    'include_phonology_and_frequencies': True,

    # The order of languages matters as the first will
    # be treated as default by ELAN
    'languages': [
        {
            'id': 'nld',
            'description': 'De glossen-CV voor het CNGT (RU)',
            'annotation_idgloss_fieldname': 'annotationidglosstranslation_nl',
            'attributes': {
                'LANG_DEF': 'http://cdb.iso.org/lg/CDB-00138580-001',
                'LANG_ID': 'nld',
                'LANG_LABEL': 'Dutch (nld)'
            }
        },
        {
            'id': 'eng',
            'description': 'The glosses CV for the CNGT (RU)',
            'annotation_idgloss_fieldname': 'annotationidglosstranslation_en',
            'attributes': {
                'LANG_DEF': 'http://cdb.iso.org/lg/CDB-00138502-001',
                'LANG_ID': 'eng',
                'LANG_LABEL': 'English (eng)'
            }
        },
    ]
}

DEFAULT_DATASET = 'Nederlandse Gebarentaal'
DEFAULT_DATASET_ACRONYM = 'NGT'
DEFAULT_DATASET_LANGUAGE_ID = 1
DEFAULT_DATASET_PK = 5