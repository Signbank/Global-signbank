# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-06-02 09:47
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0046_auto_20210106_1425'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gloss',
            name='domhndsh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='domhndsh_handshapefk',
            new_name='domhndsh',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='subhndsh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='subhndsh_handshapefk',
            new_name='subhndsh',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='final_domhndsh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='final_domhndsh_handshapefk',
            new_name='final_domhndsh',
        ),
        migrations.RemoveField(
            model_name='gloss',
            name='final_subhndsh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='final_subhndsh_handshapefk',
            new_name='final_subhndsh',
        ),
    ]
