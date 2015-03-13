To change something to the models for signbank.science.ru.nl:
1. Clone a local copy (the production database is locked by Apache)
2. Clone the database
3. Change the settings file to know where this database can be found (base.py:23)
4. bin/development.py migrate --fake
5. bin/development.py schemamigration dictionary --auto
6. bin/development.py migrate dictionary