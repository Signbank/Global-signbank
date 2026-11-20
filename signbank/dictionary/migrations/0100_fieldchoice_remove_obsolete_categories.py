# -*- coding: utf-8 -*-

from django.db import migrations


def remove_obsolete_fieldchoices(apps, schema_editor):
    """
    FieldChoice obsolete categories Handshape, Derivation History, and Semantic Field
    :param apps:
    :param schema_editor:
    :return:
    """
    FieldChoice = apps.get_model('dictionary', 'FieldChoice')

    for category in ['Handshape', 'derivHist', 'semField']:
        field_choices_for_category = FieldChoice.objects.filter(field__exact=category)

        if not field_choices_for_category.exists():
            continue

        for fc in field_choices_for_category.iterator():
            print("Remove obsolete FieldChoice object with field category='", category, "', machine_value=", fc.machine_value, ", name=", fc.name)
            fc.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0100_alter_annotationidglosstranslation_text_and_more'),
    ]

    operations = [
        migrations.RunPython(remove_obsolete_fieldchoices),
    ]
