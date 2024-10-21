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
        'pages_page', 'south_migrationhistory', 'tagging_tag',
                   'auth_group_permissions',
                   'auth_user_groups',
                   'auth_user_user_permissions',
                   'auth_permission',
                   'auth_user',
                   'registration_registrationprofile',
                   'registration_userprofile',
                   'pages_page_group_required',
                   'django_site',
                   'guardian_groupobjectpermission',
                   'guardian_userobjectpermission',
                   'dictionary_userprofile',
                   'django_content_type',
                   'sqlite_sequence'
                   ]
    
    # Empty all other tables
    for table in c.fetchall():
        if table[0] not in keep_tables:
            print('Delete contents from table: ', table[0])
            c.execute('DELETE FROM ' + table[0] + ';')

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
