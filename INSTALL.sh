bin/develop.py migrate
bin/develop.py createsuperuser

echo 'from django.contrib.contenttypes.models import ContentType; ContentType.objects.all().delete()' | bin/develop.py shell
echo 'from signbank.dictionary.models import FieldChoice; FieldChoice.objects.all().delete()' | bin/develop.py shell

bin/develop.py loaddata fixtures/content_types.json
bin/develop.py loaddata fixtures/permissions.json
bin/develop.py loaddata fixtures/groups.json
bin/develop.py loaddata fixtures/fieldchoices.json
bin/develop.py loaddata fixtures/pages.json

echo
echo "IMPORTANT: Add yourself to Dataset_Manager group in admin"