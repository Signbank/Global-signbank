# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-06-23 10:50
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import F
from django.core.exceptions import FieldDoesNotExist


def copy_dutch_and_chinese_name_fields(apps, schema_editor):
    FieldChoice = apps.get_model('dictionary', 'FieldChoice')
    try:
        FieldChoice.objects.all().update(name_en=F('name'))
        print("Copied FieldChoice name to name_en")
    except FieldDoesNotExist:
        pass
    try:
        FieldChoice.objects.all().update(name_nl=F('dutch_name'))
        print("Copied FieldChoice dutch_name to name_nl")
    except FieldDoesNotExist:
        pass
    try:
        FieldChoice.objects.all().update(name_zh_hans=F('chinese_name'))
        print("Copied FieldChoice chinese_name to name_zh_hans")
    except FieldDoesNotExist:
        pass
    
    Handshape = apps.get_model('dictionary', 'Handshape')
    try:
        Handshape.objects.all().update(name_en=F('name'))
        print("Copied Handshape name to name_en")
    except FieldDoesNotExist:
        pass
    try:
        Handshape.objects.all().update(name_nl=F('dutch_name'))
        print("Copied Handshape dutch_name to name_nl")
    except FieldDoesNotExist:
        pass
    try:
        Handshape.objects.all().update(name_zh_hans=F('chinese_name'))
        print("Copied Handshape chinese_name to name_zh_hans")
    except FieldDoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0042_auto_20200623_1245'),
    ]

    operations = [
        migrations.RunPython(copy_dutch_and_chinese_name_fields),
    ]
