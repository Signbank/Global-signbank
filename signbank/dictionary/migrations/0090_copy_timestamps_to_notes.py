import datetime as DT
from django.db import migrations


def copy_timestamps_from_glosses(apps, schema_editor):
    Definition = apps.get_model('dictionary', 'Definition')
    for defn in Definition.objects.all():
        if defn.creationDate > DT.datetime(2015, 1, 1, 0, 0).date():
            continue
        creation_date = defn.gloss.creationDate
        last_updated = defn.gloss.lastUpdated
        defn.creationDate = creation_date
        defn.lastUpdated = last_updated
        defn.save()


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0089_definition_creationdate_definition_creator_and_more'),
    ]

    operations = [
        migrations.RunPython(copy_timestamps_from_glosses),
    ]

