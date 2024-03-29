# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-06-30 14:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0003_auto_20170601_1010'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='content_arabic',
            field=models.TextField(blank=True, verbose_name='Arabic content'),
        ),
        migrations.AddField(
            model_name='page',
            name='content_hebrew',
            field=models.TextField(blank=True, verbose_name='Hebrew content'),
        ),
        migrations.AddField(
            model_name='page',
            name='title_arabic',
            field=models.CharField(blank=True, max_length=200, verbose_name='Arabic title'),
        ),
        migrations.AddField(
            model_name='page',
            name='title_hebrew',
            field=models.CharField(blank=True, max_length=200, verbose_name='Hebrew title'),
        ),
    ]
