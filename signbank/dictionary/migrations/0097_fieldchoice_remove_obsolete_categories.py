# -*- coding: utf-8 -*-

from django.db import migrations


def remove_obsolete_fieldchoices(apps, schema_editor):
    """
    Add 0 and 1 choices to every FieldChoice category
    :param apps:
    :param schema_editor:
    :return:
    """
    FieldChoice = apps.get_model('dictionary', 'FieldChoice')

    for category in ['Handshape', 'derivHist', 'semField']:
        field_choices_for_category = FieldChoice.objects.filter(field__exact=category)

        if not field_choices_for_category.exists():
            print('No objects found matching category ', category)
            continue

        for fc in field_choices_for_category.iterator():
            print("Remove FieldChoice object with field='", category, "', machine_value=", fc.machine_value, ", name=", fc.name)
            fc.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0096_fieldchoice_reverse_populate'),
    ]

    operations = [
        migrations.RunPython(remove_obsolete_fieldchoices),
    ]
