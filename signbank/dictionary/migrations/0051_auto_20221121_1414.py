# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-11-21 13:14
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import signbank.dictionary.models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0050_auto_20210602_1417'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gloss',
            name='derivHist',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='derivHistShadow',
            new_name='derivHist',
        ),
        migrations.AlterField(
            model_name='gloss',
            name='derivHist',
            field=models.ManyToManyField(to='dictionary.DerivationHistory', verbose_name='Derivation history'),
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='semField',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='semFieldShadow',
            new_name='semField',
        ),
        migrations.AlterField(
            model_name='gloss',
            name='semField',
            field=models.ManyToManyField(to='dictionary.SemanticField', verbose_name='Semantic Field'),
        ),
    ]
