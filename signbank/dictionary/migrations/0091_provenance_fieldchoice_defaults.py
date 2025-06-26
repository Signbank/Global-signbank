from django.db import migrations, models
from signbank.settings.server_specific import MODELTRANSLATION_LANGUAGES

def add_default_provenance(apps, schema_editor):
    """
    Add 0 and 1 choices to every FieldChoice category
    :param apps:
    :param schema_editor:
    :return:
    """
    FieldChoice = apps.get_model('dictionary', 'FieldChoice')
    new_field_choice_0, created = FieldChoice.objects.get_or_create(field='Provenance', machine_value=0)
    new_field_choice_1, created = FieldChoice.objects.get_or_create(field='Provenance', machine_value=1)
    for language in MODELTRANSLATION_LANGUAGES:
        field_name = 'name_' + language.replace('-', '_')
        setattr(new_field_choice_0, field_name, '-')
        setattr(new_field_choice_1, field_name, 'N/A')
    new_field_choice_0.save()
    new_field_choice_1.save()

class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0090_dataset_use_provenance_alter_fieldchoice_field_and_more'),
    ]

    operations = [
        migrations.RunPython(add_default_provenance),
    ]
