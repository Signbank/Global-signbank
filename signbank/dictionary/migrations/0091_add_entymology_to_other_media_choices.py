from __future__ import unicode_literals

from django.db import migrations

def add_entymology_choice(apps, schema_editor):

    FieldChoice = apps.get_model('dictionary', 'FieldChoice')
    used_machine_values = [h.machine_value for h in FieldChoice.objects.filter(field='OtherMediaType',
                                                                               machine_value__gt=1)]
    max_used_machine_value = max(used_machine_values)
    new_field_choice, created = FieldChoice.objects.get_or_create(field='OtherMediaType', name='Etymology',
                                                                  machine_value=max_used_machine_value+1)
    new_field_choice.name_en = 'Etymology'
    new_field_choice.name_nl = 'Etymologie'
    new_field_choice.name_zh_hans = 'Etymology'
    new_field_choice.name_ar = 'Etymology'
    new_field_choice.name_he = 'Etymology'
    new_field_choice.save()
    return

class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0090_dataset_prominent_media_othermedia_description'),
    ]

    operations = [
        migrations.RunPython(add_entymology_choice),
    ]
