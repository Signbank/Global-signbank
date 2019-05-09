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
                  'dictionary_simultaneousmorphologydefinition', 'dictionary_lemmaidgloss', 'dictionary_lemmaidglosstranslation']:
        c.execute('DELETE FROM ' + table + ';')

    c.execute('VACUUM')
    conn.commit()
    conn.close()

if __name__ == '__main__':

    #Static settings
    WRITABLE_FOLDER = '/var/www/signbank/live/writable/database/'
    SOURCE_DB = WRITABLE_FOLDER+'signbank.db'
    TEST_DB_FILENAME = WRITABLE_FOLDER+'test-signbank.db'
    SMALL = True

    if isfile(TEST_DB_FILENAME):
        print('Making backup of old test database')
        move(TEST_DB_FILENAME,TEST_DB_FILENAME+'_save')

    print('Copying database file')
    copyfile(SOURCE_DB,TEST_DB_FILENAME)

    if SMALL:
        print('Emptying tables, for faster tests')
        make_db_small(TEST_DB_FILENAME)
