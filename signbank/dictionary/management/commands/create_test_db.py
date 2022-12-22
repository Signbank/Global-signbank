from django.core.management.base import BaseCommand, CommandError

from os.path import isfile
from sqlite3 import connect
from shutil import copyfile, move

def make_db_small(filename):
    conn = connect(filename,isolation_level=None)
    c = conn.cursor()

    for table in ['reversion_version', 'reversion_revision', 'django_session',
                  'dictionary_gloss', 'dictionary_translation',
                  'dictionary_annotationidglosstranslation', 'dictionary_keyword',
                  'dictionary_relation', 'dictionary_definition', 'dictionary_othermedia',
                  'dictionary_morphologydefinition', 'dictionary_morpheme',
                  'dictionary_simultaneousmorphologydefinition', 'dictionary_lemmaidgloss', 'dictionary_lemmaidglosstranslation',
                  'dictionary_speaker', 'dictionary_corpus', 'dictionary_document', 'dictionary_glossfrequency',
                  'video_glossvideo']:
        c.execute('DELETE FROM ' + table + ';')

    c.execute('VACUUM')
    conn.commit()
    conn.close()


class Command(BaseCommand):
    help = 'Creates a smaller faster database for unit tests'

    def handle(self, *args, **options):
        # find databases
        source_db = settings.DATABASES['default']['NAME']
        test_db_filename = settings.DATABASES['default']['TEST']['NAME']

        SMALL = True

        if isfile(test_db_filename):
            self.stdout.write('Making backup of old test database')
            move(test_db_filename, test_db_filename + '_save')

        self.stdout.write('Copying database file')
        copyfile(source_db, test_db_filename)

        if SMALL:
            self.stdout.write('Emptying tables, for faster tests')
            make_db_small(test_db_filename)
