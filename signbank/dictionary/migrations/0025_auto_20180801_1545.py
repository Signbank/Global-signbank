# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-01 13:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0024_auto_20180618_1413'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='gloss',
            options={'ordering': ['lemma'], 'permissions': (('update_video', 'Can Update Video'), ('search_gloss', 'Can Search/View Full Gloss Details'), ('export_csv', 'Can export sign details as CSV'), ('export_ecv', 'Can create an ECV export file of Signbank'), ('can_publish', 'Can publish signs and definitions'), ('can_delete_unpublished', 'Can delete unpub signs or defs'), ('can_delete_published', 'Can delete pub signs and defs'), ('view_advanced_properties', 'Include all properties in sign detail view')), 'verbose_name_plural': 'Glosses'},
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='dataset',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='idgloss',
        ),
        migrations.AlterUniqueTogether(
            name='lemmaidglosstranslation',
            unique_together=set([('lemma', 'language')]),
        ),
    ]
