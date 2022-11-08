# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-10-24 14:33
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.models import F

from signbank.dictionary.models import SemanticField, DerivationHistory

def add_default_choices(apps, schema_editor):
    """
    Add 0 and 1 choices to SemanticField and DerivationHistory
    :param apps: 
    :param schema_editor: 
    :return: 
    """
    SemanticField = apps.get_model('dictionary', 'SemanticField')
    DerivationHistory = apps.get_model('dictionary', 'DerivationHistory')

    new_field_choice_0, created = SemanticField.objects.get_or_create(name='-',
                                                                      machine_value=0)
    new_field_choice_0.name_en = '-'
    new_field_choice_0.name_nl = '-'
    new_field_choice_0.name_zh_hans = '-'
    new_field_choice_0.save()

    new_field_choice_1, created = SemanticField.objects.get_or_create(name='N/A',
                                                                      machine_value=1)
    new_field_choice_1.name_en = 'N/A'
    new_field_choice_1.name_nl = 'N/A'
    new_field_choice_1.name_zh_hans = 'N/A'
    new_field_choice_1.save()

    new_field_choice_2, created = DerivationHistory.objects.get_or_create(name='-',
                                                                          machine_value=0)
    new_field_choice_2.name_en = '-'
    new_field_choice_2.name_nl = '-'
    new_field_choice_2.name_zh_hans = '-'
    new_field_choice_2.save()

    new_field_choice_3, created = DerivationHistory.objects.get_or_create(name='N/A',
                                                                          machine_value=1)
    new_field_choice_3.name_en = 'N/A'
    new_field_choice_3.name_nl = 'N/A'
    new_field_choice_3.name_zh_hans = 'N/A'
    new_field_choice_3.save()


def copy_fieldchoice_names(apps, schema_editor):
    """
    Copy the name fields based on the machine_value for the SemanticField and DerivationHistory models
    :param apps: 
    :param schema_editor:
    """

    FieldChoice = apps.get_model('dictionary', 'FieldChoice')

    semanticfields = SemanticField.objects.all()
    for obj in semanticfields:
        try:
            field_choice = FieldChoice.objects.get(field='SemField', machine_value=obj.machine_value)
        except Exception as e:
            print("INFO: SemField fieldchoice not found", e)
            continue

        obj.name_nl = field_choice.name_nl
        obj.name_zh_hans = field_choice.name_zh_hans
        obj.save()

    derivationhistories = DerivationHistory.objects.all()
    for obj in derivationhistories:
        try:
            field_choice = FieldChoice.objects.get(field='derivHist', machine_value=obj.machine_value)
        except Exception as e:
            print("INFO: derivHist fieldchoice not found", e)
            continue

        obj.name_nl = field_choice.name_nl
        obj.name_zh_hans = field_choice.name_zh_hans
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0051_auto_20221021_1433'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fieldchoice',
            name='chinese_name',
            field=models.CharField(blank=True, help_text='Field from Global Signbank before multilingual model translation.', max_length=50),
        ),
        migrations.AlterField(
            model_name='fieldchoice',
            name='dutch_name',
            field=models.CharField(help_text='Field from the original NGT Signbank.', max_length=50),
        ),
        migrations.AlterField(
            model_name='fieldchoice',
            name='field',
            field=models.CharField(choices=[('AbsOriFing', 'AbsOriFing'), ('AbsOriPalm', 'AbsOriPalm'), ('Aperture', 'Aperture'), ('ContactType', 'ContactType'), ('derivHist', 'derivHist'), ('DominantHandFlexion', 'DominantHandFlexion'), ('DominantHandSelectedFingers', 'DominantHandSelectedFingers'), ('FingerSelection', 'FingerSelection'), ('Handedness', 'Handedness'), ('Handshape', 'Handshape'), ('iconicity', 'iconicity'), ('HandshapeChange', 'HandshapeChange'), ('JointConfiguration', 'JointConfiguration'), ('Location', 'Location'), ('MinorLocation', 'MinorLocation'), ('MorphemeType', 'MorphemeType'), ('MorphologyType', 'MorphologyType'), ('MovementDir', 'MovementDir'), ('MovementMan', 'MovementMan'), ('MovementShape', 'MovementShape'), ('NamedEntity', 'NamedEntity'), ('NoteType', 'NoteType'), ('OriChange', 'OriChange'), ('OtherMediaType', 'OtherMediaType'), ('PathOnPath', 'PathOnPath'), ('Quantity', 'Quantity'), ('RelOriLoc', 'RelOriLoc'), ('RelOriMov', 'RelOriMov'), ('RelatArtic', 'RelatArtic'), ('SemField', 'SemField'), ('Spreading', 'Spreading'), ('Thumb', 'Thumb'), ('Valence', 'Valence'), ('WordClass', 'WordClass')], max_length=50),
        ),
        migrations.AlterField(
            model_name='relation',
            name='role',
            field=models.CharField(choices=[('homonym', 'Homonym'), ('synonym', 'Synonym'), ('variant', 'Variant'), ('antonym', 'Antonym'), ('hyponym', 'Hyponym'), ('hypernym', 'Hypernym'), ('seealso', 'See Also'), ('paradigm', 'Handshape Paradigm')], max_length=20),
        ),
        migrations.AlterField(
            model_name='speaker',
            name='gender',
            field=models.CharField(blank=True, choices=[('Male', 'm'), ('Female', 'f'), ('Other', 'o')], max_length=1),
        ),
	    migrations.RunPython(add_default_choices),
        migrations.RunPython(copy_fieldchoice_names),
    ]
