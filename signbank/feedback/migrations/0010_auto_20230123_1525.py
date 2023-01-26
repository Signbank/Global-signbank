# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2023-01-23 14:25
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0055_auto_20221123_1437'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('feedback', '0009_auto_20210602_1417'),
    ]

    operations = [
        migrations.CreateModel(
            name='MorphemeFeedback',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('comment', models.TextField(blank=True, verbose_name='Comment or new keywords.')),
                ('status', models.CharField(choices=[('unread', 'unread'), ('read', 'read'), ('deleted', 'deleted')], default='unread', max_length=10)),
                ('morpheme', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dictionary.Morpheme')),
                ('translation', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='dictionary.Translation')),
                ('user', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
        migrations.RemoveField(
            model_name='signfeedback',
            name='correct',
        ),
        migrations.RemoveField(
            model_name='signfeedback',
            name='isAuslan',
        ),
        migrations.RemoveField(
            model_name='signfeedback',
            name='kwnotbelong',
        ),
        migrations.RemoveField(
            model_name='signfeedback',
            name='like',
        ),
        migrations.RemoveField(
            model_name='signfeedback',
            name='suggested',
        ),
        migrations.RemoveField(
            model_name='signfeedback',
            name='use',
        ),
        migrations.RemoveField(
            model_name='signfeedback',
            name='whereused',
        ),
        migrations.AddField(
            model_name='signfeedback',
            name='gloss',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dictionary.Gloss'),
        ),
    ]
