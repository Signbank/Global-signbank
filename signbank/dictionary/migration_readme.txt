NEW
------------------------------------------------------
1. Make backup of the old database
2. source /www/signbank/live/virtualenv/signbank/bin/activate
3.  python bin/develop.py schemamigration dictionary --auto

OLD
-------------------------------------------------------------

To change something to the models for signbank.science.ru.nl:
1. Clone a local copy (the production database is locked by Apache)
2. Clone the database
3. Change the settings file to know where this database can be found (base.py:23)

( 4. bin/development.py migrate --fake ) <-- no longer needed if you do 7

5. bin/development.py schemamigration dictionary --auto
6. bin/development.py migrate dictionary
7. Make sure the migrations are added to the repo

Note: when updating FieldChoice, make sure Gloss temporarily does not use it, otherwise you will get errors

