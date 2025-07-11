from __future__ import unicode_literals

from django.db import migrations
from signbank.settings.server_specific import MODELTRANSLATION_LANGUAGES


def add_entymology_choice(apps, schema_editor):

    FieldChoice = apps.get_model('dictionary', 'FieldChoice')
    used_machine_values = [h.machine_value for h in FieldChoice.objects.filter(field='OtherMediaType',
                                                                               machine_value__gt=1)]
    max_used_machine_value = max(used_machine_values)
    new_field_choice, created = FieldChoice.objects.get_or_create(field='OtherMediaType', name='Etymology',
                                                                  machine_value=max_used_machine_value+1)
    for language in MODELTRANSLATION_LANGUAGES:
        field_name = 'name_' + language.replace('-', '_')
        if field_name == 'name_nl':
            setattr(new_field_choice, field_name, 'Etymologie')
        else:
            setattr(new_field_choice, field_name, 'Etymology')
    new_field_choice.save()
    return

class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0092_dataset_prominent_media_othermedia_description'),
    ]

    operations = [
        migrations.RunPython(add_entymology_choice),
    ]
