# Generated by Django 4.1.7 on 2023-06-16 14:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0071_translation_orderindex_alter_translation_language'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='translation',
            unique_together={('gloss', 'language', 'translation', 'orderIndex')},
        ),
    ]
