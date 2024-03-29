# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2023-01-25 11:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0055_auto_20221123_1437'),
        ('feedback', '0010_auto_20230123_1525'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='interpreterfeedback',
            name='user',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='althandshape',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='direction',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='handbodycontact',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='handform',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='handinteraction',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='handshape',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='location',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='movementtype',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='relativelocation',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='repetition',
        ),
        migrations.RemoveField(
            model_name='missingsignfeedback',
            name='smallmovement',
        ),
        migrations.AddField(
            model_name='missingsignfeedback',
            name='signlanguage',
            field=models.ForeignKey(help_text='Sign Language of the missing sign', null=True, on_delete=django.db.models.deletion.CASCADE, to='dictionary.SignLanguage', verbose_name='Sign Language'),
        ),
        migrations.DeleteModel(
            name='InterpreterFeedback',
        ),
    ]
