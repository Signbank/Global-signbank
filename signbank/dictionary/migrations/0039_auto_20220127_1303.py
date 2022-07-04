# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-01-27 12:03

from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0038_auto_20201028_1533'),
    ]

    operations = [
        migrations.CreateModel(
            name='SemanticField',
            fields=[
                ('machine_value', models.IntegerField(primary_key=True, serialize=False, verbose_name='Machine value')),
                ('name', models.CharField(max_length=20, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SemanticFieldTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dictionary.Language')),
                ('semField', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dictionary.SemanticField')),
            ],
        ),
        migrations.AddField(
            model_name='gloss',
            name='semFieldShadow',
            field=models.ManyToManyField(to='dictionary.SemanticField'),
        ),
        migrations.AlterUniqueTogether(
            name='semanticfieldtranslation',
            unique_together=set([('semField', 'language', 'name')]),
        ),
    ]
