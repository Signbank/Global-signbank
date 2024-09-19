# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-10-31 13:24
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import signbank.dictionary.models


def get_translation_languages(language_model):
    languages = dict(settings.LANGUAGES)
    languages_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)

    translation_fields = ['name_'+language_2char for language_2char in languages.keys()]
    
    language_objects = []
    for language_2char, language_name in languages.items():
        fields_dict = {
            'language_code_2char': language_2char,
            'language_code_3char': languages_3char[language_2char],
            'name': language_name
        }
        language_object, created = language_model.objects.get_or_create(**fields_dict)
        language_objects.append(language_object)

    return language_objects


def copy_semanticfield_names_to_translations(apps, schema_editor):
    """
    Create translations for the name fields of SemanticField
    :param apps:
    :param schema_editor:
    """

    SemanticField = apps.get_model('dictionary', 'SemanticField')
    SemanticFieldTranslation = apps.get_model('dictionary', 'SemanticFieldTranslation')
    Language = apps.get_model('dictionary', 'Language')
    translation_languages = get_translation_languages(Language)
    semanticfields = SemanticField.objects.filter(machine_value__gt=1)

    for language in translation_languages:
        for semfield in semanticfields:
            translations_for_semfield = [sft.language for sft in
                                         SemanticFieldTranslation.objects.filter(semField=semfield)]
            semfield_translation = getattr(semfield, 'name_'+language.language_code_2char)
            if semfield_translation and language not in translations_for_semfield:
                SemanticFieldTranslation.objects.get_or_create(
                    semField=semfield,
                    language=language,
                    name=semfield_translation)


def copy_derivationhistory_names_to_translations(apps, schema_editor):
    """
    Create translations for the name fields of DerivationHistory
    :param apps:
    :param schema_editor:
    """

    DerivationHistory = apps.get_model('dictionary', 'DerivationHistory')
    DerivationHistoryTranslation = apps.get_model('dictionary', 'DerivationHistoryTranslation')
    Language = apps.get_model('dictionary', 'Language')
    translation_languages = get_translation_languages(Language)
    derivationhistories = DerivationHistory.objects.all()

    for language in translation_languages:
        for derivhist in derivationhistories:
            translations_for_derivhist = [dht.language for dht
                                          in DerivationHistoryTranslation.objects.filter(derivHist=derivhist)]
        derivhist_translation = getattr(derivhist, 'name_'+language.language_code_2char.replace('-', '_'))
        if derivhist and language not in translations_for_derivhist:
            DerivationHistoryTranslation.objects.get_or_create(
                derivHist=derivhist,
                language=language,
                name=derivhist.name_en)

class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0052_auto_20221024_1633'),
    ]

    operations = [
        migrations.RunPython(copy_semanticfield_names_to_translations),
        migrations.RunPython(copy_derivationhistory_names_to_translations),
    ]
