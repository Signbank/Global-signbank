bin/develop.py migrate
bin/develop.py createsuperuser

echo 'from django.contrib.contenttypes.models import ContentType; ContentType.objects.all().delete()' | bin/develop.py shell
echo 'from signbank.dictionary.models import FieldChoice; FieldChoice.objects.all().delete()' | bin/develop.py shell

bin/develop.py loaddata content_types.json
bin/develop.py loaddata permissions.json
bin/develop.py loaddata groups.json
bin/develop.py loaddata fieldchoices.json
bin/develop.py loaddata pages.json

# Add yourself to Dataset_Manager group in admin