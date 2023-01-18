from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from os.path import isfile
from sqlite3 import connect
from shutil import copyfile, move

def make_db_small(filename):
    conn = connect(filename,isolation_level=None)
    c = conn.cursor()

    # Select all tables in dataset
    sql_query = """SELECT name FROM sqlite_master WHERE type='table';"""
    c.execute(sql_query)

    # Set which tables should not be emptied
    keep_tables = ['auth_group', 'auth_permissions', 
        'dictionary_corpus', 'dictionary_dataset', 'dictionary_dataset_translation_languages', 
        'dictionary_derivationhistory', 'dictionary_derivationhistorytranslation', 'dictionary_dialect', 
        'dictionary_fieldchoice', 'dictionary_handshape', 'dictionary_language', 
        'dictionary_semanticfield', 'dictionary_semanticfieldtranslation', 
        'dictionary_signlanguage', 'dictionary_content_type', 
        'django_migrations', 
        'pages_page', 'south_migrationhistory', 'tagging_tag']
    
    # Empty all other tables
    for table in c.fetchall():
        if table[0] not in keep_tables:
            c.execute('DELETE FROM ' + table[0] + ';')

    c.execute('VACUUM')
    conn.commit()
    conn.close()


class Command(BaseCommand):
    help = 'Creates a smaller faster database for unit tests'

    def handle(self, *args, **options):

        # Static settings
        WRITABLE_FOLDER = '/var/www/writable/database/'
        SOURCE_DB = WRITABLE_FOLDER + 'signbank.db'
        TEST_DB_FILENAME = WRITABLE_FOLDER + 'test-signbank.db'
        SMALL = True

        if isfile(TEST_DB_FILENAME):
            self.stdout.write('Making backup of old test database')
            move(TEST_DB_FILENAME, TEST_DB_FILENAME + '_save')

        self.stdout.write('Copying database file')
        copyfile(SOURCE_DB, TEST_DB_FILENAME)

        if SMALL:
            self.stdout.write('Emptying tables, for faster tests')
            make_db_small(TEST_DB_FILENAME)
