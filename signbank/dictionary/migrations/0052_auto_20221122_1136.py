# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-11-22 10:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import signbank.dictionary.models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0051_auto_20221121_1414'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoA',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoGe',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoGr',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoO',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoR',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoSgnrA',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoSgnrGe',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoSgnrGr',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoSgnrO',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoSgnrR',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoSgnrV',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='tokNoV',
        ),
    ]