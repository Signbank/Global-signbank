# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-03-20 11:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0031_auto_20190320_1236'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='exclude_choices',
            field=models.ManyToManyField(blank=True, help_text='Exclude these field choices', null=True, to='dictionary.FieldChoice'),
        )
    ]
