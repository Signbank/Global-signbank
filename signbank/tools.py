import guardian.shortcuts

import signbank.settings
from signbank.settings.base import WSGI_FILE, WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, LANGUAGE_CODE
import os
import shutil
import html
from zipfile import ZipFile
import json
import re
from urllib.parse import quote
import csv
import hashlib

from django.db.models import Q
from django.http import QueryDict

from django.utils.translation import override, gettext_lazy as _, activate

from django.http import HttpResponse, HttpResponseRedirect

from signbank.csv_interface import (sense_translations_for_language, update_senses_parse,
                                    update_sentences_parse, sense_examplesentences_for_language, get_sense_numbers,
                                    parse_sentence_row, get_senses_to_sentences, csv_sentence_tuples_list_compare,
                                    csv_header_row_glosslist, required_csv_columns, trim_columns_in_row,
                                    normalize_field_choice)
from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from django.utils.dateformat import format
from django.core.exceptions import ObjectDoesNotExist, EmptyResultSet
from django.db import OperationalError, ProgrammingError
from django.db.models import CharField, TextField, Value as V
from django.db.models.fields import BooleanField, BooleanField

from django.urls import reverse
from tagging.models import TaggedItem, Tag

from guardian.shortcuts import get_objects_for_user
from signbank.api_interface import api_fields
from django.views.decorators.csrf import csrf_exempt


def get_two_letter_dir(idgloss):
    foldername = idgloss[:2]

    if len(foldername) == 1:
        foldername += '-'

    return foldername


def save_media(source_folder, language_code_3char, goal_folder, gloss, extension):
        
    # Add a dot before the extension if needed
    if extension[0] != '.':
        extension = '.' + extension

    # Figure out some names
    annotation_id = ""
    try:
        language = Language.objects.get(language_code_3char=language_code_3char)
    except ObjectDoesNotExist:
        # no language exists for this folder
        return False, False
    annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
    if annotationidglosstranslations and len(annotationidglosstranslations) > 0:
        annotation_id = annotationidglosstranslations[0].text
    pk = str(gloss.pk)
    destination_folder = os.path.join(
        WRITABLE_FOLDER,
        goal_folder,
        gloss.lemma.dataset.acronym,
        get_two_letter_dir(gloss.idgloss)
    )

    # Create the necessary subfolder if needed
    if not os.path.isdir(destination_folder):
        os.mkdir(destination_folder)

    # Move the file
    source = source_folder+annotation_id+extension
    goal = os.path.join(destination_folder, annotation_id+'-'+pk+extension)

    if os.path.isfile(goal):
        overwritten = True
    else:
        overwritten = False

    try:
        shutil.copyfile(source,goal)
        was_allowed = True
    except IOError:
        was_allowed = False

    try:
        os.remove(source)
    except OSError:
        pass

    return overwritten, was_allowed


def unescape(string):

    return html.unescape(string)


def create_gloss_from_valuedict(valuedict, dataset, row_nr, earlier_creation_same_csv,
                                earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss):

    errors_found = []
    new_gloss = []
    already_exists = []

    # Create an overview of all fields, sorted by their human name
    with override(LANGUAGE_CODE):
        empty_lemma_translation = False
        existing_glosses = {}
        existing_lemmas = {}
        existing_lemmas_list = []
        new_lemmas = {}
        lemmaidglosstranslations = {}
        annotationidglosstranslations = {}
        translation_languages = dataset.translation_languages.all()
        for language in translation_languages:

            lemmaidgloss_comumn_name = "Lemma ID Gloss (%s)" % (getattr(language,settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']))

            if lemmaidgloss_comumn_name in valuedict:
                lemmaidglosstranslation_text = valuedict[lemmaidgloss_comumn_name].strip()
                lemmaidglosstranslations[language.language_code_2char] = lemmaidglosstranslation_text

                lemmatranslation_for_this_text_language = LemmaIdglossTranslation.objects.filter(lemma__dataset=dataset,
                                                                                   language=language, text__exact=lemmaidglosstranslation_text)
                if lemmatranslation_for_this_text_language:
                    one_lemma = lemmatranslation_for_this_text_language.first().lemma
                    existing_lemmas[language.language_code_2char] = one_lemma
                    if one_lemma not in existing_lemmas_list:
                        existing_lemmas_list.append(one_lemma)
                elif not lemmaidglosstranslation_text:
                    empty_lemma_translation = True
                else:
                    new_lemmas[language.language_code_2char] = lemmaidglosstranslation_text

            column_name = "Annotation ID Gloss (%s)" % (getattr(language,settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']))
            if column_name in valuedict:
                annotationidglosstranslation_text = valuedict[column_name].strip()
                if annotationidglosstranslation_text:
                    annotationidglosstranslations[language.language_code_2char] = annotationidglosstranslation_text

                    # The annotation idgloss translation text for a language must be unique within a dataset.
                    glosses_with_same_text = Gloss.objects.filter(lemma__dataset=dataset,
                                                                  annotationidglosstranslation__text__exact=annotationidglosstranslation_text,
                                                                  annotationidglosstranslation__language=language)
                    if glosses_with_same_text.count() > 0:
                        existing_glosses[language.language_code_2char] = glosses_with_same_text
                else:
                    error_string = 'Row ' + str(row_nr + 1) + ' has an empty ' + column_name
                    errors_found += [error_string]
            else:
                print('column name not in value dict: ', column_name)

        if existing_glosses:
            existing_gloss_set = set()
            for language_code_2char,glosses in existing_glosses.items():
                for gloss in glosses:
                    if gloss not in existing_gloss_set:
                        gloss_dict = {
                             'gloss_pk': gloss.pk,
                             'dataset': gloss.dataset
                        }
                        annotationidglosstranslation_dict = {}
                        for lang in gloss.lemma.dataset.translation_languages.all():
                            language_name = getattr(language,settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                            annotationidglosstranslation_text = valuedict["Annotation ID Gloss (%s)" % language_name]
                            annotationidglosstranslation_dict[lang.language_code_2char] = annotationidglosstranslation_text
                        gloss_dict['annotationidglosstranslations'] = annotationidglosstranslation_dict

                        lemmaidglosstranslation_dict = {}
                        for lang in gloss.lemma.dataset.translation_languages.all():
                            language_name = getattr(language,settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                            lemmaidglosstranslation_text = valuedict["Lemma ID Gloss (%s)" % language_name]
                            lemmaidglosstranslation_dict[lang.language_code_2char] = lemmaidglosstranslation_text
                        gloss_dict['lemmaidglosstranslations'] = lemmaidglosstranslation_dict
                        already_exists.append(gloss_dict)
                        existing_gloss_set.add(gloss)
        else:
            gloss_dict = {'gloss_pk' : str(row_nr + 1), 'dataset': dataset }
            trans_languages = [ l for l in dataset.translation_languages.all() ]
            annotationidglosstranslation_dict = dict()
            for language in trans_languages:
                language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                annotationidglosstranslation_text = valuedict["Annotation ID Gloss (%s)" % language_name]
                annotationidglosstranslation_dict[language.language_code_2char] = annotationidglosstranslation_text
                if language.language_code_2char in earlier_creation_annotationidgloss.keys() and \
                        annotationidglosstranslation_text in earlier_creation_annotationidgloss[language.language_code_2char]:
                    error_string = 'Duplicate Annotation ID Gloss found for '+ language_name +': '+annotationidglosstranslation_text
                    errors_found += [error_string]

                if not earlier_creation_annotationidgloss or (
                        language.language_code_2char not in earlier_creation_annotationidgloss.keys()):
                    earlier_creation_annotationidgloss[language.language_code_2char] = [annotationidglosstranslation_text]
                else:
                    earlier_creation_annotationidgloss[language.language_code_2char].append(annotationidglosstranslation_text)
            gloss_dict['annotationidglosstranslations'] = annotationidglosstranslation_dict

            lemmaidglosstranslation_dict = {}
            for language in trans_languages:
                language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                lemmaidglosstranslation_text = valuedict["Lemma ID Gloss (%s)" % language_name]
                lemmaidglosstranslation_dict[language.language_code_2char] = lemmaidglosstranslation_text

            gloss_dict['lemmaidglosstranslations'] = lemmaidglosstranslation_dict
            new_gloss.append(gloss_dict)

        if len(existing_lemmas_list) > 0:

            if len(existing_lemmas_list) > 1:
                print('TOOLS more than one existing lemma in row ', str(row_nr+1))
            elif empty_lemma_translation:
                print('TOOLS exactly one lemma matches, but one of the translations in the csv is empty')
            if len(new_lemmas.keys()) and len(existing_lemmas.keys()):
                print('TOOLS existing and new lemmas in row ', str(row_nr+1))

        range_of_earlier_creation = [ v for (i,v) in earlier_creation_same_csv.items() ]
        if earlier_creation_same_csv and new_gloss in range_of_earlier_creation:
            error_string = 'Row ' + str(row_nr + 1) + ' is a duplicate gloss creation.'
            errors_found += [error_string]

    # save the parameters for the new gloss under the row number
    # make sure this gloss isn't being created twice
    if len(errors_found) == 0 and len(already_exists) == 0:
        earlier_creation_same_csv[str(row_nr+1)] = new_gloss
        earlier_creation_lemmaidgloss[str(row_nr+1)] = lemmaidglosstranslations

    return new_gloss, already_exists, errors_found, earlier_creation_same_csv, earlier_creation_annotationidgloss, \
        earlier_creation_lemmaidgloss


def compare_valuedict_to_gloss(valuedict, gloss_id, my_datasets, nl,
                               earlier_updates_same_csv, earlier_updates_lemmaidgloss,
                               notes_toggle, notes_assign_toggle, semfield_toggle, semfield_assign_toggle, tags_toggle):
    """Takes a dict of arbitrary key-value pairs, and compares them to a gloss"""
    # called by import_csv_update in views.py

    errors_found = []
    differences = []

    try:
        gloss = Gloss.objects.select_related().get(pk=gloss_id)
    except ObjectDoesNotExist:
        error_string = 'Could not find gloss for ID ' + str(gloss_id)
        errors_found.append(error_string)
        return differences, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss

    if gloss_id in earlier_updates_same_csv:
        e = 'Signbank ID (' + str(gloss_id) + ') found in multiple rows (Row ' + str(nl + 1) + ').'
        errors_found.append(e)
        return differences, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss
    else:
        earlier_updates_same_csv.append(gloss_id)
    column_name_error = False
    tag_name_error = False

    note_type_error = False
    note_tuple_error = False

    # Create an overview of all fields, sorted by their human name
    with override(LANGUAGE_CODE):

        default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

        # these are the same fields as for csv export
        # do not include frequency fields
        fieldnames = FIELDS['main']+FIELDS['phonology']+FIELDS['semantics']+['inWeb', 'isNew']

        glossfieldnames = [fname for fname in fieldnames
                           if fname in Gloss.get_field_names()]

        fields = dict()
        # this data structure is set up to reverse map column names to gloss fields
        for fieldname in glossfieldnames:
            field = Gloss.get_field(fieldname)
            fields[field.verbose_name] = field

        if gloss.lemma.dataset:
            current_dataset = gloss.lemma.dataset.acronym
        else:
            # because of legacy code, the current dataset might not have been set
            current_dataset = 'None'

        # Go through all values in the value dict, looking for differences with the gloss
        for human_key, new_human_value in valuedict.items():

            new_human_value = new_human_value.strip()

            # If these are not fields, but relations to other parts of the database, compare complex values
            if human_key == 'Signbank ID':
                continue

            annotation_idgloss_key_prefix = "Annotation ID Gloss ("
            if human_key.startswith(annotation_idgloss_key_prefix):
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = human_key[len(annotation_idgloss_key_prefix):-1]
                languages = Language.objects.filter(**{language_name_column: language_name})
                if languages:
                    language = languages.first()
                    annotation_idglosses = gloss.annotationidglosstranslation_set.filter(language=language)
                    if annotation_idglosses:
                        annotation_idgloss_string = annotation_idglosses.first().text

                        if annotation_idgloss_string != new_human_value and new_human_value not in ['None', '']:
                            glosses_with_same_annotation = Gloss.objects.filter(
                                annotationidglosstranslation__text__exact=new_human_value,
                                annotationidglosstranslation__language=language,
                                lemma__dataset=gloss.lemma.dataset).count()

                            if glosses_with_same_annotation:
                                error_string = 'ERROR: Signbank ID (' + str(gloss_id) \
                                               + ')  key value already exists: ' + human_key + ': ' + str(new_human_value)
                                errors_found += [error_string]

                            else:
                                differences.append({'pk': gloss_id,
                                                    'dataset': current_dataset,
                                                    'annotationidglosstranslation': default_annotationidglosstranslation,
                                                    'machine_key': human_key,
                                                    'human_key': human_key,
                                                    'original_machine_value': annotation_idgloss_string,
                                                    'original_human_value': annotation_idgloss_string,
                                                    'new_machine_value': new_human_value,
                                                    'new_human_value': new_human_value})
                continue

            lemma_idgloss_key_prefix = "Lemma ID Gloss ("
            if human_key.startswith(lemma_idgloss_key_prefix):
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = human_key[len(lemma_idgloss_key_prefix):-1]
                languages = Language.objects.filter(**{language_name_column:language_name})
                if languages:
                    language = languages[0]
                    lemma_idglosses = gloss.lemma.lemmaidglosstranslation_set.filter(language=language)
                    if lemma_idglosses:
                        lemma_idgloss_string = lemma_idglosses[0].text
                    else:
                        # lemma not set
                        lemma_idgloss_string = ''
                    if lemma_idgloss_string != new_human_value and new_human_value not in ['None', '']:
                        error_string = 'ERROR: Attempt to update Lemma translations: ' + human_key
                        errors_found += [error_string]
                continue

            keywords_key_prefix = "Senses ("
            if human_key.startswith(keywords_key_prefix):
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = human_key[len(keywords_key_prefix):-1]
                language = Language.objects.filter(**{language_name_column:language_name}).first()
                if not language:
                    current_keyword_string = ""
                    error_string = 'ERROR: Non-existent language specified for Senses column: ' + human_key
                    errors_found += [error_string]
                else:
                    current_keyword_string = sense_translations_for_language(gloss, language)
                    if current_keyword_string:
                        # update of existing senses currently not supported
                        pass
                    else:
                        okay = update_senses_parse(new_human_value)
                        if not okay:
                            print('current senses: ', current_keyword_string)
                            print('not okay new string: ', new_human_value)
                            error_string = 'ERROR Gloss ' + str(
                                gloss.id) + ': Error parsing value in Senses column ' + human_key + ': ' + new_human_value
                            errors_found += [error_string]

                if new_human_value not in ['None', ''] and not current_keyword_string:
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': current_keyword_string,
                                        'original_human_value': current_keyword_string,
                                        'new_machine_value': new_human_value,
                                        'new_human_value': new_human_value})
                continue

            example_sentences_key_prefix = "Example Sentences ("
            if human_key.startswith(example_sentences_key_prefix):
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = human_key[len(example_sentences_key_prefix):-1]
                language = Language.objects.filter(**{language_name_column:language_name}).first()
                sense_numbers = get_sense_numbers(gloss)
                sense_numbers_to_sentences = get_senses_to_sentences(gloss)
                if not language:
                    current_sentences_string = ""
                    error_string = 'ERROR: Non-existent language specified for Senses column: ' + human_key
                    errors_found += [error_string]
                else:
                    current_sentences_string = sense_examplesentences_for_language(gloss, language)
                    if current_sentences_string and settings.DEBUG_CSV:
                        print('Current sentences: ', current_sentences_string)
                    okay = update_sentences_parse(sense_numbers, sense_numbers_to_sentences, new_human_value)
                    if not okay:
                        print('current sentences: ', current_sentences_string)
                        print('not okay new sentences string: ', new_human_value)
                        error_string = 'ERROR Gloss ' + str(
                            gloss.id) + ': Error parsing value in Example Sentences column ' + human_key + ': ' + new_human_value
                        errors_found += [error_string]
                difference_org, difference, errors_found = csv_sentence_tuples_list_compare(str(gloss_id),
                                                                                            current_sentences_string,
                                                                                            new_human_value,
                                                                                            errors_found)

                if difference:
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': difference_org,
                                        'original_human_value': difference_org,
                                        'new_machine_value': difference,
                                        'new_human_value': difference})
                continue

            elif human_key == 'SignLanguages':

                if new_human_value in ['None', '']:
                    continue

                current_signlanguages_string = str(', '.join([str(lang.name) for lang in gloss.signlanguage.all()]))

                new_human_value_list = [v.strip() for v in new_human_value.split(',')]

                (found, not_found, errors) = check_existence_signlanguage(gloss, new_human_value_list)

                if len(errors):
                    errors_found += errors

                if current_signlanguages_string != new_human_value:
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': current_signlanguages_string,
                                        'original_human_value': current_signlanguages_string,
                                        'new_machine_value': new_human_value,
                                        'new_human_value': new_human_value})
                continue

            elif human_key == 'Dialects':
                if new_human_value in ['None', '', '-']:
                    continue

                current_dialects_string = str(', '.join([dia.signlanguage.name + '/' + str(dia.name)
                                                         for dia in gloss.dialect.all()]))

                new_human_value_list = [v.strip() for v in new_human_value.split(',')]

                (found, not_found, errors) = check_existence_dialect(gloss, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif current_dialects_string != new_human_value:
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': current_dialects_string,
                                        'original_human_value': current_dialects_string,
                                        'new_machine_value': new_human_value,
                                        'new_human_value': new_human_value})
                continue

            elif human_key == 'Dataset' or human_key == 'Glosses dataset':

                # cach legacy value
                if human_key == 'Glosses dataset':
                    human_key = 'Dataset'
                if new_human_value == 'None' or new_human_value == '':
                    # This check assumes that if the Dataset column is empty, it means no change
                    # Since we already know the id of the gloss, we keep the original dataset
                    # To be safe, confirm the original dataset is not empty, to catch legacy code
                    if not current_dataset or current_dataset == 'None' or current_dataset is None:
                        # Dataset must be non-empty to create a new gloss
                        error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(gloss_id) + '), Dataset must be non-empty. There is currently no dataset defined for this gloss.'

                        errors_found += [error_string]
                    continue

                # if we get to here, the user has specificed a new value for the dataset
                if new_human_value in my_datasets:
                    if current_dataset != new_human_value:
                        differences.append({'pk': gloss_id,
                                            'dataset': current_dataset,
                                            'annotationidglosstranslation': default_annotationidglosstranslation,
                                            'machine_key': human_key,
                                            'human_key': human_key,
                                            'original_machine_value': current_dataset,
                                            'original_human_value': current_dataset,
                                            'new_machine_value': new_human_value,
                                            'new_human_value': new_human_value})
                else:
                    error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                        gloss_id) + '), could not find ' + str(new_human_value) + ' for ' + human_key

                    errors_found += [error_string]

                continue

            elif human_key == 'Relations to other signs':
                if new_human_value in ['None', '']:
                    continue

                relations = [(relation.role, get_default_annotationidglosstranslation(relation.target))
                             for relation in gloss.relation_sources.filter(target__archived__exact=False,
                                                                           source__archived__exact=False)]

                # sort tuples on other gloss to allow comparison with imported values

                sorted_relations = sorted(relations, key=lambda tup: tup[1])

                relations_with_categories = []
                for rel_cat in sorted_relations:
                    relations_with_categories.append(':'.join(rel_cat))
                current_relations_string = ",".join(relations_with_categories)

                new_human_value_list = [v.strip() for v in new_human_value.split(',')]

                (checked_new_human_value, errors) = check_existence_relations(gloss, relations_with_categories, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif current_relations_string != checked_new_human_value:
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': current_relations_string,
                                        'original_human_value': current_relations_string,
                                        'new_machine_value': checked_new_human_value,
                                        'new_human_value': checked_new_human_value})
                continue

            elif human_key == 'Relations to foreign signs':

                relations = [(str(relation.loan), relation.other_lang, relation.other_lang_gloss)
                             for relation in gloss.relationtoforeignsign_set.all().order_by('other_lang_gloss')]
                if not relations and new_human_value in ['None', '', '-']:
                    continue

                relations_with_categories = []
                for rel_cat in relations:
                    relations_with_categories.append(':'.join(rel_cat))
                current_relations_foreign_string = ",".join(relations_with_categories)

                if new_human_value in ['None', '', '-']:
                    new_human_value_list = []
                else:
                    new_human_value_list = [v.strip() for v in new_human_value.split(',')]

                (checked_new_human_value, errors) = check_existence_foreign_relations(gloss, relations_with_categories, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif current_relations_foreign_string != checked_new_human_value:
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': current_relations_foreign_string,
                                        'original_human_value': current_relations_foreign_string,
                                        'new_machine_value': checked_new_human_value,
                                        'new_human_value': checked_new_human_value})
                continue

            elif human_key == 'Sequential Morphology':
                if new_human_value in ['None', '', '-']:
                    continue

                morphemes = [get_default_annotationidglosstranslation(morpheme.morpheme)
                             for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]
                morphemes_string = " + ".join(morphemes)

                (found, not_found, errors) = check_existence_sequential_morphology(gloss, new_human_value)

                if len(errors):
                    errors_found += errors

                elif morphemes_string != new_human_value:
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': morphemes_string,
                                        'original_human_value': morphemes_string,
                                        'new_machine_value': new_human_value,
                                        'new_human_value': new_human_value})
                continue

            elif human_key == 'Simultaneous Morphology':
                if new_human_value in ['None', '']:
                    continue

                morphemes = [(get_default_annotationidglosstranslation(m.morpheme), m.role)
                             for m in gloss.simultaneous_morphology.filter(parent_gloss__archived__exact=False)]
                sim_morphs = []
                for m in morphemes:
                    sim_morphs.append(':'.join(m))
                simultaneous_morphemes = ','.join(sim_morphs)

                new_human_value_list = [v.strip() for v in new_human_value.split(',')]

                (checked_new_human_value, errors) = check_existence_simultaneous_morphology(gloss, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif simultaneous_morphemes != checked_new_human_value:
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': simultaneous_morphemes,
                                        'original_human_value': simultaneous_morphemes,
                                        'new_machine_value': checked_new_human_value,
                                        'new_human_value': checked_new_human_value})
                continue

            elif human_key == 'Blend Morphology':
                if new_human_value in ['None', '']:
                    continue

                morphemes = [(get_default_annotationidglosstranslation(m.glosses), m.role)
                             for m in gloss.blend_morphology.filter(parent_gloss__archived__exact=False,
                                                                    glosses__archived__exact=False)]

                ble_morphs = []
                for m in morphemes:
                    ble_morphs.append(':'.join(m))
                blend_morphemes = ','.join(ble_morphs)

                new_human_value_list = [v.strip() for v in new_human_value.split(',')]

                (checked_new_human_value, errors) = check_existence_blend_morphology(gloss, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif blend_morphemes != checked_new_human_value:
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': blend_morphemes,
                                        'original_human_value': blend_morphemes,
                                        'new_machine_value': checked_new_human_value,
                                        'new_human_value': checked_new_human_value})
                continue

            elif human_key == 'Tags':
                if tags_toggle == 'keep' and (new_human_value == 'None' or new_human_value == ''):
                    continue

                (tag_names_string, sorted_tags_display) = get_tags_as_string(gloss_id)

                if new_human_value in ['None', '']:
                    (sorted_new_tags_display, sorted_new_tags, new_tag_errors, tag_name_error) = \
                        ("", [], [], tag_name_error)
                else:
                    new_human_value_list = [v.strip() for v in new_human_value.split(',')]

                    (sorted_new_tags_display, sorted_new_tags, new_tag_errors, tag_name_error) = \
                        check_existence_tags(gloss_id, new_human_value_list, tag_name_error,
                                             default_annotationidglosstranslation)

                if len(new_tag_errors):
                    errors_found += new_tag_errors
                elif sorted_tags_display != sorted_new_tags_display:

                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': sorted_tags_display,
                                        'original_human_value': sorted_tags_display,
                                        'new_machine_value': sorted_new_tags_display,
                                        'new_human_value': sorted_new_tags_display})
                continue

            elif human_key == 'Notes':

                if notes_toggle == 'keep' and (new_human_value == 'None' or new_human_value == ''):
                    continue

                notes_list, sorted_notes_display = get_notes_as_string(gloss)

                if new_human_value == 'None' or new_human_value == '':
                    (new_notes_display, sorted_new_notes_display, new_note_errors, note_type_error, note_tuple_error) = \
                        ([], "", [], note_type_error, note_tuple_error)
                else:
                    (new_notes_display, sorted_new_notes_display, new_note_errors, note_type_error, note_tuple_error) = \
                                check_existence_notes(gloss, new_human_value, note_type_error,
                                                      note_tuple_error, default_annotationidglosstranslation)

                if len(new_note_errors):
                    errors_found += new_note_errors
                elif new_notes_display != notes_list:
                    if notes_assign_toggle == 'update':
                        combined_notes = notes_list + new_notes_display
                        sorted_new_notes_display = ', '.join(combined_notes)
                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': sorted_notes_display,
                                        'original_human_value': sorted_notes_display,
                                        'new_machine_value': sorted_new_notes_display,
                                        'new_human_value': sorted_new_notes_display})
                continue

            elif human_key == 'Semantic Field':

                if new_human_value in ['', '0', ' ', None, 'None']:
                    new_human_value = '-'
                    new_human_value_list = []
                else:
                    new_human_value_list = [v.strip() for v in new_human_value.split(',')]

                if semfield_toggle == 'keep' and new_human_value == '-':
                    continue

                # make sure all fields exist
                new_values_sorted_lookup = lookup_semantic_fields(new_human_value_list)
                if new_values_sorted_lookup.count() != len(new_human_value_list):
                    error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                        gloss_id) + '), could not parse ' + new_human_value + ' for ' + human_key
                    errors_found += [error_string]
                    continue
                new_semfield_sorted_lookup_values = [str(sf.name) for sf in new_values_sorted_lookup]
                new_semanticfield_value = ', '.join(new_semfield_sorted_lookup_values)
                original_sorted_semfield_values = [str(sf.name) for sf in gloss.semField.all().order_by('machine_value')]
                original_semanticfield_value = ", ".join(original_sorted_semfield_values)
                if new_semanticfield_value != original_semanticfield_value:
                    if semfield_assign_toggle == 'update':
                        combined_semfield = original_sorted_semfield_values + new_semfield_sorted_lookup_values
                        compined_values_sorted_lookup = lookup_semantic_fields(combined_semfield)
                        new_semanticfield_value = ', '.join([str(sf.name) for sf in compined_values_sorted_lookup])

                    differences.append({'pk': gloss_id,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation': default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': original_semanticfield_value,
                                        'original_human_value': original_semanticfield_value,
                                        'new_machine_value': new_semanticfield_value,
                                        'new_human_value': new_semanticfield_value})
                continue

            elif human_key in ['Derivation history', 'Derivation History']:

                continue

            # If not, find the matching field in the gloss, and remember its 'real' name
            try:
                field = fields[human_key]
                gloss_field_name = field.name

            except KeyError:
                # Signbank ID is skipped, for this purpose it was popped from the fields to compare
                # Skip above fields with complex values: Keywords, Signlanguages, Dialects,
                # Relations to other signs, Relations to foreign signs, Morphology.

                error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                    gloss_id) + '), could not identify column name: ' + str(human_key)

                errors_found += [error_string]

                if not column_name_error:
                    error_string = 'HINT: Try exporting a CSV file to see what column names can be used.'
                    errors_found += [error_string]
                    column_name_error = True

                continue

            # Try to translate the value to machine values if needed
            if hasattr(field, 'field_choice_category'):
                if new_human_value in ['', '0', ' ', None, 'None']:
                    new_human_value = '-'

                try:
                    field_choice = FieldChoice.objects.get(name__iexact=new_human_value, field=field.field_choice_category)
                    new_machine_value = field_choice.machine_value
                except ObjectDoesNotExist:
                    normalised_choice = normalize_field_choice(new_human_value)
                    try:
                        field_choice = FieldChoice.objects.get(name__iexact=normalised_choice,
                                                               field=field.field_choice_category)
                        new_machine_value = field_choice.machine_value
                    except ObjectDoesNotExist:
                        error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                            gloss_id) + '), could not find option ' + new_human_value + ' for ' + human_key

                        errors_found += [error_string]
                        continue

            elif isinstance(field, models.ForeignKey) and field.related_model == Handshape:
                if new_human_value in ['', '0', ' ', None, 'None']:
                    new_human_value = '-'

                try:
                    handshape = Handshape.objects.get(name__iexact=new_human_value)
                    new_machine_value = handshape.machine_value
                except ObjectDoesNotExist:
                    error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                        gloss_id) + '), could not find option ' + new_human_value + ' for ' + human_key

                    errors_found += [error_string]
                    continue

            # Do something special for integers and booleans
            elif field.__class__.__name__ == 'IntegerField':

                try:
                    new_machine_value = int(new_human_value)
                except ValueError:
                    new_human_value = 'None'
                    new_machine_value = None
            elif field.__class__.__name__ == 'BooleanField':

                new_human_value_lower = new_human_value.lower()
                if new_human_value_lower == 'neutral' and (field.name in settings.HANDEDNESS_ARTICULATION_FIELDS):
                    new_machine_value = None
                elif new_human_value_lower in ['true', 'yes', '1']:
                    new_machine_value = True
                    new_human_value = 'True'
                elif new_human_value_lower == 'none':
                    new_machine_value = None
                elif new_human_value_lower in ['false', 'no', '0']:
                    new_machine_value = False
                    new_human_value = 'False'
                else:
                    # Boolean expected
                    error_string = ''
                    # If the new value is empty, don't count this as a type error, error_string is generated conditionally
                    if field.name in settings.HANDEDNESS_ARTICULATION_FIELDS:
                        if new_human_value is not None and new_human_value not in ['None', '']:
                            error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(gloss_id) + '), value ' + str(new_human_value) + ' for ' + human_key + ' should be a Boolean or Neutral.'
                    else:
                        if new_human_value is not None and new_human_value not in ['None', '']:
                            error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(gloss_id) + '), value ' + str(new_human_value) + ' for ' + human_key + ' is not a Boolean.'

                    if error_string:
                        errors_found += [error_string]
                    continue
            # If all the above does not apply, this is a None value or plain text
            else:
                if new_human_value == 'None':
                    new_machine_value = None
                else:
                    new_machine_value = new_human_value

            # Try to translate the key to machine keys if possible
            try:
                original_machine_value = getattr(gloss, gloss_field_name)
            except KeyError:
                error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                    gloss_id) + '), could not get original value for field: ' + gloss_field_name

                errors_found += [error_string]
                continue

            # Translate back the machine value from the gloss

            if hasattr(field, 'field_choice_category'):
                original_field_value = getattr(gloss, gloss_field_name)
                original_machine_value = original_field_value.machine_value if original_field_value else 0
                original_human_value = original_field_value.name if original_field_value else '-'

            elif isinstance(field, models.ForeignKey) and field.related_model == Handshape:
                original_field_value = getattr(gloss, gloss_field_name)
                original_machine_value = original_field_value.machine_value if original_field_value else 0
                original_human_value = original_field_value.name if original_field_value else '-'

            elif field.__class__.__name__ == 'BooleanField':
                if original_machine_value is None and (field.name in settings.HANDEDNESS_ARTICULATION_FIELDS):
                    original_human_value = 'Neutral'
                elif original_machine_value:
                    original_machine_value = True
                    original_human_value = 'True'
                else:
                    original_machine_value = False
                    original_human_value = 'False'
            # some legacy glosses have empty text fields of other formats
            elif (field.__class__.__name__ == 'CharField' or field.__class__.__name__ == 'TextField') \
                    and (original_machine_value is None or original_machine_value == '-'
                         or original_machine_value == '------' or original_machine_value == ' '):
                original_machine_value = ''
                original_human_value = ''
            else:
                value = getattr(gloss, field.name)
                original_human_value = value

            # Remove any weird char
            if not type(new_human_value) == str:
                # make sure passed parameter is a string
                coerced_string = str(new_human_value)
            else:
                coerced_string = new_human_value
            new_human_value = unescape(coerced_string)

            # test if blank value

            original_human_value = str(original_human_value)
            new_human_value = str(new_human_value)

            s1 = re.sub(' ', '', original_human_value)
            s2 = re.sub(' ', '', new_human_value)

            # If the original value is implicitly not set, and the new value is not set, ignore this change
            if (s1 in ['', 'None', 'False']) and s2 == '':
                pass
            # Check for change, and save your findings if there is one
            elif original_machine_value != new_machine_value and new_machine_value is not None:
                if (human_key == 'WD' or human_key == 'WP') and original_human_value == 'None':
                    original_human_value = 'Neutral'
                differences.append({'pk': gloss_id,
                                    'dataset': current_dataset,
                                    'annotationidglosstranslation': default_annotationidglosstranslation,
                                    'machine_key': gloss_field_name,
                                    'human_key': human_key,
                                    'original_machine_value': original_machine_value,
                                    'original_human_value': original_human_value,
                                    'new_machine_value': new_machine_value,
                                    'new_human_value': new_human_value})

    return differences, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss


def compare_valuedict_to_lemma(valuedict, lemma_id, my_datasets, nl,
                                lemmaidglosstranslations, current_lemmaidglosstranslations,
                               earlier_updates_same_csv, earlier_updates_lemmaidgloss):
    """Takes a dict of key-value pairs, and compares them to a lemma"""

    errors_found = []
    differences = []

    try:
        lemma = LemmaIdgloss.objects.select_related().get(pk=lemma_id)
    except ObjectDoesNotExist as e:

        e = 'Could not find lemma for ID ' + str(lemma_id)
        errors_found.append(e)
        return differences, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss

    if lemma_id in earlier_updates_same_csv:
        e = 'Lemma ID (' + str(lemma_id) + ') found in multiple rows (Row ' + str(nl + 1) + ').'
        errors_found.append(e)
        return differences, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss
    else:
        earlier_updates_same_csv.append(lemma_id)

    count_new_nonempty_translations = 0
    count_existing_nonempty_translations = 0

    if lemmaidglosstranslations \
            and current_lemmaidglosstranslations != lemmaidglosstranslations:
        for key1 in lemmaidglosstranslations.keys():
            if lemmaidglosstranslations[key1]:
                count_new_nonempty_translations += 1
        for key2 in current_lemmaidglosstranslations.keys():
            if current_lemmaidglosstranslations[key2]:
                count_existing_nonempty_translations += 1
        pass
    else:
        return differences, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss

    if not count_new_nonempty_translations:
        # somebody has modified the lemma translations so as to delete alll of them:
        e = 'Row ' + str(nl + 1) + ': Lemma ID ' + str(lemma_id) + ' must have at least one translation.'
        errors_found.append(e)
        return differences, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss

    # Create an overview of all fields, sorted by their human name
    with override(LANGUAGE_CODE):

        if lemma.dataset:
            current_dataset = lemma.dataset.acronym
        else:
            # because of legacy code, the current dataset might not have been set
            current_dataset = 'None'

        # Go through all values in the value dict, looking for differences with the lemma
        for human_key, new_human_value in valuedict.items():

            new_human_value = new_human_value.strip()

            annotation_idgloss_key_prefix = "Annotation ID Gloss ("
            if human_key in ['Lemma ID', 'Dataset', 'Signbank ID'] or human_key.startswith(annotation_idgloss_key_prefix):
                # these fields can't be updated
                continue

            lemma_idgloss_key_prefix = "Lemma ID Gloss ("
            if human_key.startswith(lemma_idgloss_key_prefix):
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = human_key[len(lemma_idgloss_key_prefix):-1]
                languages = Language.objects.filter(**{language_name_column:language_name})
                if languages:
                    language = languages[0]
                    lemma_idglosses = lemma.lemmaidglosstranslation_set.filter(language=language)
                    if lemma_idglosses:
                        lemma_idgloss_string = lemma_idglosses[0].text
                    else:
                        # lemma not set
                        lemma_idgloss_string = ''
                    if lemma_idgloss_string != new_human_value:

                        differences.append({'pk': lemma_id,
                                            'dataset': current_dataset,
                                            'machine_key': human_key,
                                            'human_key': human_key,
                                            'original_machine_value': lemma_idgloss_string,
                                            'original_human_value': lemma_idgloss_string,
                                            'new_machine_value': new_human_value,
                                            'new_human_value': new_human_value})
                continue

            else:
                # this case should be impossible! It's included for completeness of else otherwise case
                print('Unknown lemma field encountered while comparing new to existing fields: ', human_key)

    return differences, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss


def check_existence_dialect(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    found = []
    not_found = []
    for new_value in values:
        dialect_signlanguage_str, dialect_name_str = new_value.split('/')
        dialect_signlanguage = dialect_signlanguage_str.strip()
        dialect_name = dialect_name_str.strip()
        if Dialect.objects.filter(name=dialect_name, signlanguage__name=dialect_signlanguage):
            if new_value not in found:
                found += [new_value]
        else:
            error_string = ('ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk)
                            + '), new Dialect value ' + str(new_value) + ' not found.')
            errors.append(error_string)
            not_found += [new_value]
        continue

    return found, not_found, errors


def check_existence_signlanguage(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    found = []
    not_found = []

    for new_value in values:
        if SignLanguage.objects.filter(name__iexact=new_value):
            if new_value in found:
                error_string = 'WARNING: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Sign Language value ' + str(new_value) + ' is duplicate.'
                errors.append(error_string)
            else:
                found += [new_value]
        else:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) + '), new Sign Language value ' + str(new_value) + ' not found.'

            errors.append(error_string)
            not_found += [new_value]
        continue

    return found, not_found, errors


def check_existence_notes(gloss, values, note_type_error, note_tuple_error, default_annotationidglosstranslation):
    # convert new Notes csv value to proper format
    # values is not empty

    activate(LANGUAGES[0][0])
    # The following need to be ordered reversely because note name 'Project Note' contains 'Note'
    note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType',
                                                   machine_value__gt=1).order_by('-name')
    all_notes_names = [str(n.machine_value) for n in note_role_choices]
    all_notes_display = ', '.join(all_notes_names)

    new_human_values = []
    new_note_errors = []

    # first replace the note names with their machine value
    # this is needed in order to parse the input, since some notes have parentheses and numbers, etc.
    mapped_values, map_errors = map_values_to_notes_id(values)

    if map_errors:
        note_tuple_error = True
        note_type_error = False
        # error in processing new notes
        error_string1 = 'For ' + default_annotationidglosstranslation + ' (' + str(
            gloss.pk) + '), could not parse note: ' + values
        error_string2 = "Note values must be a comma-separated list of tagged tuples: 'Type:(Boolean,Index,Text)'"
        new_note_errors.append(error_string1)
        new_note_errors.append(error_string2)
        # it doesn't work to use the translation here because it's a proxy
        # new_note_errors.append(_('A non-existent note type was found.'))

        return values, values, new_note_errors, note_type_error, note_tuple_error

    # the space is required in order to identify multiple notes in the input
    split_human_values = re.split(r', ([0-9]+: ?)', mapped_values)

    # this doesn't split cleanly, because the "split" is also shown in the result
    # e.g., ['NNN: (...,...,...)', "NNN: ', '(...,...,...)']
    # an index variable is used in order to obtain the correct item from the list of splits
    # consecutive elements must be concatenated after the first element, as shown above
    splits_combined = []
    list_index = 0
    # find the patterns of the different notes in the input
    for split_value in split_human_values:
        if re.match(r'[0-9]+: ?(.+,.+,.+)', split_value):
            # there is a match to the pattern <machine_value>:(<published>,<index>,<text>) possibly with spaces
            splits_combined.append(split_value)
        elif re.match(r'[0-9]+: ?', split_value):
            next_value = split_human_values[list_index+1]
            splits_combined.append(split_value+next_value)
        # else skip over this one, it was combined with the previous
        list_index += 1

    for split_value in splits_combined:
        take_apart = re.match(r'([0-9]+): ?[(](False|True),([0-9]+),(.+)[)]', split_value)
        if take_apart:
            (field, name, count, text) = take_apart.groups()

            if field not in all_notes_names:
                error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), a non-existent note type was found: ' + field + '.'

                new_note_errors += [error_string]
                if not note_type_error:
                    error_string = 'Current note types are: ' + all_notes_display + '.'
                    new_note_errors += [error_string]
                    note_type_error = True
            else:
                new_tuple = (field, name, count, text.strip())
                new_human_values.append(new_tuple)
        else:
            # error in processing new notes
            error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), could not parse note: ' + split_value

            if not note_tuple_error:
                new_note_errors += [error_string]
                error_string1 = "Note values must be a comma-separated list of tagged tuples: 'Type:(Boolean,Index,Text)'"
                new_note_errors += [error_string1]
                error_string2 = 'Try exporting a CSV for glosses with Notes to check the format.'
                new_note_errors += [error_string2]
                note_tuple_error = True
            else:
                new_note_errors += [error_string]

    note_translations = {}
    for nrc in note_role_choices:
        note_translations[str(nrc.machine_value)] = nrc.name

    new_notes_mapped = []
    for (machine_value, published, count, text) in new_human_values:
        role = note_translations[machine_value]
        new_notes_mapped.append((role, published, count, text))

    sorted_new_human_values = sorted(new_notes_mapped, key=lambda x: (x[0], x[1], x[2], x[3]))

    new_notes_display = []
    for (role, published, count, text) in sorted_new_human_values:
        new_note = role + ': (' + published + ',' + count + ',' + text + ')'
        new_notes_display.append(new_note)
    sorted_new_notes_display = ', '.join(new_notes_display)
    return new_notes_display, sorted_new_notes_display, new_note_errors, note_type_error, note_tuple_error


def map_values_to_notes_id(values):

    map_errors = False
    activate(LANGUAGES[0][0])
    note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType', machine_value__gt=1).order_by('-name')

    # this needs to be done twice in order to reverse map to escaped names
    # some of the names include parentheses
    note_reverse_translation = {}
    for nrc in note_role_choices:
        note_reverse_translation[nrc.name] = str(nrc.machine_value)

    import re
    sorted_note_names = note_reverse_translation.keys()
    pattern_mapped_sorted_note_names = []
    escaped_note_reverse_translation = {}
    for note_name in sorted_note_names:
        escaped_note_name = re.sub(r'([()])', r'\\\1', note_name)
        pattern_mapped_sorted_note_names.append(escaped_note_name)
        escaped_note_reverse_translation[escaped_note_name] = note_reverse_translation[note_name]

    mapped_values = values

    for note_name in pattern_mapped_sorted_note_names:
        regex_string = r"%s" % note_name + r": "
        m = re.search(regex_string, mapped_values)
        if m:
            regex = re.compile(note_name)
            mapped_values = regex.sub(escaped_note_reverse_translation[note_name], mapped_values)
    # see if any note names have not been reverse mapped
    find_all = re.findall(r'\D+: ?[(]', mapped_values)
    if find_all:
        map_errors = True
    return mapped_values, map_errors


def get_notes_as_string(gloss):
    activate(LANGUAGES[0][0])
    notes_of_gloss = gloss.definition_set.all()

    notes_list = []
    for note in notes_of_gloss:
        notes_list += [note.note_tuple()]
    sorted_notes_list = sorted(notes_list, key=lambda x: (x[0], x[1], x[2], x[3]))

    notes_display = []
    for (role, published, count, text) in sorted_notes_list:
        # does not use a comprehension because of nested parentheses in role and text fields
        tuple_reordered = role + ': (' + published + ',' + count + ',' + text + ')'
        notes_display.append(tuple_reordered)
    sorted_notes_display = ', '.join(notes_display)
    return notes_display, sorted_notes_display


def get_tags_as_string(gloss_id):
    activate(LANGUAGES[0][0])

    tags_of_gloss = TaggedItem.objects.filter(object_id=gloss_id)
    tag_names_of_gloss = []
    for t_obj in tags_of_gloss:
        tag_id = t_obj.tag_id
        tag_name = Tag.objects.get(id=tag_id)
        tag_names_of_gloss += [str(tag_name)]
    tag_names_of_gloss = sorted(tag_names_of_gloss)

    tag_names_string = ", ".join(tag_names_of_gloss)

    tag_names_display = [t.replace('_', ' ') for t in tag_names_of_gloss]
    tag_names_display = ', '.join(tag_names_display)

    return tag_names_string, tag_names_display


def check_existence_tags(gloss_id, new_human_value_list, tag_name_error, default_annotationidglosstranslation):
    # convert new Tags csv value to proper format
    # values is not empty

    tags_objects = Tag.objects.all()
    refreshed_tags = []
    for tag in tags_objects:
        tag.refresh_from_db()
        refreshed_tags.append(tag)
    all_tags = [t.name for t in refreshed_tags]

    all_tags_display = ', '.join([t.replace('_',' ') for t in all_tags])

    new_tag_errors = []

    new_human_value_list = [v.replace(' ', '_') for v in new_human_value_list]

    new_human_value_list_no_dups = list(set(new_human_value_list))
    sorted_new_tags = sorted(new_human_value_list_no_dups)

    # check for non-existent tags
    for t in sorted_new_tags:
        if t not in all_tags:
            error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                gloss_id) + '), a new Tag name was found: ' + t.replace('_', ' ') + '.'

            new_tag_errors += [error_string]
            if not tag_name_error:
                error_string = 'Current tag names are: ' + all_tags_display + '.'
                new_tag_errors += [error_string]
                tag_name_error = True

    new_tag_names_display = [t.replace('_', ' ') for t in sorted_new_tags]
    new_tag_names_display = ', '.join(new_tag_names_display)

    sorted_new_tags = ", ".join(sorted_new_tags)

    return new_tag_names_display, sorted_new_tags, new_tag_errors, tag_name_error


def check_existence_sequential_morphology(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)
    new_values = values.split(' + ')
    errors = []
    found = []
    not_found = []
    for new_value in new_values:
        filter_morphemes = Gloss.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                                annotationidglosstranslation__text__exact=new_value).distinct()
        if not filter_morphemes:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), new Sequential Morphology gloss ' + new_value + ' not found.'
            errors.append(error_string)
            not_found += [new_value]
            continue
        elif filter_morphemes.count() > 1:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), multiple matches found for Sequential Morphology gloss ' + new_value + '.'
            errors.append(error_string)
            continue
        else:
            found += [new_value]

    if len(new_values) > 4:
        error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
            gloss.pk) + ', too many Sequential Morphology components.'
        errors.append(error_string)

    return found, not_found, errors


def check_existence_simultaneous_morphology(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    tuples_list = []
    checked = ''

    # check syntax
    for new_value_tuple in values:
        try:
            (morpheme, role) = new_value_tuple.split(':')
            role = role.strip()
            morpheme = morpheme.strip()
            tuples_list.append((morpheme, role))
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Simultaneous Morphology: ' + str(new_value_tuple) + '. Tuple morpheme:role expected.'
            errors.append(error_string)

    for (morpheme, role) in tuples_list:

        filter_morphemes = Morpheme.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                                   annotationidglosstranslation__text__exact=morpheme).distinct()

        if not filter_morphemes:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), new Simultaneous Morphology gloss ' + str(morpheme) + ' not found.'
            errors.append(error_string)
            continue
        elif filter_morphemes.count() > 1:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), multiple matches found for Simultaneous Morphology gloss ' + morpheme + '.'
            errors.append(error_string)
            continue
        morpheme_gloss = filter_morphemes.first()
        if not morpheme_gloss.is_morpheme():
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), new Simultaneous Morphology gloss ' + str(morpheme) + ' is not a morpheme.'
            errors.append(error_string)
            continue
        if checked:
            checked += ',' + ':'.join([morpheme, role])
        else:
            checked = ':'.join([morpheme, role])

    return checked, errors


def check_existence_blend_morphology(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    found = []
    not_found = []
    tuples_list = []
    checked = ''

    # check syntax
    for new_value_tuple in values:
        try:
            (morpheme, role) = new_value_tuple.split(':')
            role = role.strip()
            morpheme = morpheme.strip()
            tuples_list.append((morpheme, role))
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Blend Morphology: ' + str(new_value_tuple) + '. Tuple gloss:role expected.'
            errors.append(error_string)

    for (morpheme, role) in tuples_list:

        filter_glosses = Gloss.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                              annotationidglosstranslation__text__exact=morpheme).distinct()

        if not filter_glosses:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), new Blend Morphology gloss ' + morpheme + '  not found.'
            errors.append(error_string)
            continue
        elif filter_glosses.count() > 1:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), multiple matches found for Blend Morphology gloss ' + morpheme + '.'
            errors.append(error_string)
            continue
        if checked:
            checked += ',' + ':'.join([morpheme, role])
        else:
            checked = ':'.join([morpheme, role])

    return checked, errors


RELATION_ROLES = ['homonym', 'Homonym', 'synonym', 'Synonym', 'variant', 'Variant', 'paradigm', 'Handshape Paradigm',
                         'antonym', 'Antonym', 'hyponym', 'Hyponym', 'hypernym', 'Hypernym', 'seealso', 'See Also']

RELATION_ROLES_DISPLAY = 'homonym, synonym, variant, paradigm, antonym, hyponym, hypernym, seealso'


def check_existence_relations(gloss, relations, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    checked = ''
    sorted_values = []

    # check syntax
    for new_value_tuple in values:
        try:
            (role, other_gloss) = new_value_tuple.split(':')
            role = role.strip()

            role = role.replace(' ', '')
            role = role.lower()
            other_gloss = other_gloss.strip()
            sorted_values.append((role,other_gloss))
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Relations to other signs: ' + str(new_value_tuple) + '. Tuple role:gloss expected.'
            errors.append(error_string)

    # remove duplicates
    sorted_values = list(set(sorted_values))

    sorted_values = sorted(sorted_values, key=lambda tup: tup[1])

    # check roles
    for (role, other_gloss) in sorted_values:

        try:
            if role not in RELATION_ROLES:
                raise ValueError
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), column Relations to other signs: ' + role + ':' + other_gloss + '. Role ' + role + ' not found.' \
                    + ' Role should be one of: ' + RELATION_ROLES_DISPLAY + '.'
            errors.append(error_string)

    # check other glosses
    for (role, other_gloss) in sorted_values:

        filter_target = Gloss.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                             annotationidglosstranslation__text__exact=other_gloss).distinct()

        if not filter_target:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), column Relations to other signs: ' + role + ':' + other_gloss + '. Other gloss ' \
                           + other_gloss + ' not found.'
            errors.append(error_string)
        elif filter_target.count() > 1:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), column Relations to other signs: ' + role + ':' + other_gloss + \
                           '. Multiple matches found for other gloss ' + other_gloss + '.'
            errors.append(error_string)
            continue

        if checked:
            checked += ',' + ':'.join([role, other_gloss])
        else:
            checked = ':'.join([role, other_gloss])

    return checked, errors


def check_existence_foreign_relations(gloss, relations, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    checked = ''
    sorted_values = []

    if not values:
        # this is a delete
        return checked, errors

    for new_value_tuple in values:
        try:
            (loan_word, other_lang, other_lang_gloss) = new_value_tuple.split(':')
            sorted_values.append((loan_word,other_lang,other_lang_gloss))
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Relations to foreign signs: ' + str(new_value_tuple) \
                           + '. Tuple bool:string:string expected.'
            errors.append(error_string)

    # remove duplicates
    sorted_values = list(set(sorted_values))

    sorted_values = sorted(sorted_values, key=lambda tup: tup[2])

    for (loan_word, other_lang, other_lang_gloss) in sorted_values:

        # check the syntax of the tuple of changes
        try:
            loan_word = loan_word.strip()
            if loan_word not in ['false', 'False', 'true', 'True']:
                raise ValueError
            other_lang = other_lang.strip()
            other_lang_gloss = other_lang_gloss.strip()
            if checked:
                checked += ',' + ':'.join([loan_word, other_lang, other_lang_gloss])
            else:
                checked = ':'.join([loan_word,other_lang,other_lang_gloss])
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Relations to foreign signs: ' \
                           + loan_word + ':' + other_lang + ':' + other_lang_gloss \
                           + '. Tuple bool:string:string expected.'
            errors.append(error_string)

            pass

    return checked, errors


@csrf_exempt
def set_dark_mode(request):
    # this is the toggle button in the menu bar
    from django.http import JsonResponse
    if 'dark_mode' not in request.session.keys():
        # first time button is used
        request.session['dark_mode'] = "True"
    elif request.session['dark_mode'] == "True":
        request.session['dark_mode'] = "False"
    elif request.session['dark_mode'] == "False":
        request.session['dark_mode'] = "True"
    request.session.modified = True
    return JsonResponse({})


def lookup_semantic_fields(values):
    # case insensitive lookup of values for semantic fields
    semantic_fields_machine_values = []
    for value in values:
        semfields = SemanticField.objects.filter(name__iexact=value)
        if not semfields or semfields.count() > 1:
            continue
        semantic_fields_machine_values.append(semfields.first().machine_value)
    semantic_fields = SemanticField.objects.filter(machine_value__in=semantic_fields_machine_values).order_by('machine_value')
    return semantic_fields


def reload_signbank(request=None):
    """Functions to clear the cache of Apache, also works as view"""

    # Refresh the wsgi script
    os.utime(WSGI_FILE, None)

    # If this is an HTTP request, give an HTTP response
    if request is not None:

        from django.shortcuts import render
        return render(request, 'reload_signbank.html')


def get_gloss_data(since_timestamp=0, language_code='en', dataset=None, inWebSet=False, extended_fields=False):

    if not dataset:
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)

    if inWebSet:
        glosses = Gloss.objects.filter(lemma__dataset=dataset, inWeb=True, archived=False)
    else:
        glosses = Gloss.objects.filter(lemma__dataset=dataset, archived=False)

    # settings.API_FIELDS
    api_fields_2023 = api_fields(dataset, language_code, extended_fields)

    gloss_data = {}
    for gloss in glosses:
        if int(format(gloss.lastUpdated, 'U')) > since_timestamp:
            data = gloss.get_fields_dict(api_fields_2023, language_code)
            gloss_data[str(gloss.pk)] = data

    return gloss_data


def create_zip_with_json_files(data_per_file, output_path):

    """Creates a zip file filled with the output of the functions supplied.

    Data should either be a json string or a list, which will be transformed to json."""

    INDENTATION_CHARS = 4

    zip = ZipFile(output_path, 'w')

    for filename, data in data_per_file.items():
        if isinstance(data, list) or isinstance(data, dict):
            try:
                output = json.dumps(data, indent=INDENTATION_CHARS, ensure_ascii=False).encode('utf8')
            except TypeError:
                print('problem processing json.dumps on ', filename)
                output = ''
            zip.writestr(filename+'.json', output)
    zip.close()


def get_deleted_gloss_or_media_data(item_type, since_timestamp):

    result = []
    from datetime import datetime, date
    deletion_date_range = [datetime.fromtimestamp(since_timestamp), date.today()]

    for deleted_gloss_or_media in DeletedGlossOrMedia.objects.filter(deletion_date__range=deletion_date_range,
                                                                     item_type=item_type):
        if item_type == 'gloss':
            result.append((str(deleted_gloss_or_media.old_pk), deleted_gloss_or_media.idgloss))
        else:
            result.append(str(deleted_gloss_or_media.old_pk))

    return result


def generate_still_image(video):
    try:
        from CNGT_scripts.python.extractMiddleFrame import MiddleFrameExtracter
        # local copy for debugging purposes
        # from signbank.video.extractMiddleFrame import MiddleFrameExtracter
        from signbank.settings.server_specific import FFMPEG_PROGRAM, TMP_DIR
        from signbank.settings.base import GLOSS_IMAGE_DIRECTORY

        # Extract frames (incl. middle)
        extracter = MiddleFrameExtracter([os.path.join(WRITABLE_FOLDER, str(video.videofile))],
                                         os.path.join(TMP_DIR, "signbank-ExtractMiddleFrame"), FFMPEG_PROGRAM, True)
        output_dirs = extracter.run()

        # Copy video still to the correct location
        vfile_name = os.path.basename(str(video.videofile))
        still_goal_location = os.path.join(WRITABLE_FOLDER,
                                           str(video.videofile).replace(GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY, 1))
        destination = os.path.dirname(still_goal_location)
        for dir in output_dirs:
            for filename in os.listdir(dir):
                if filename.replace('.png', '') == os.path.splitext(vfile_name)[0]:
                    if not os.path.isdir(destination):
                        os.makedirs(destination, 0o770)
                    shutil.copy(os.path.join(dir, filename), destination)
            shutil.rmtree(dir)
        print("Generating still images succes!")
    except ImportError as i:
        print("Error resizing video: ", i)
    except IOError as io:
        print("IOError: ", io)


def get_datasets_with_public_glosses():

    # Make sure a non-empty set is returned, for anonymous users when no datasets are public
    # the first query fetches glosses that are public, then obtains those glosses' dataset ids
    datasets_of_public_glosses = Gloss.objects.filter(inWeb=True, archived=False).values('lemma__dataset__id').distinct()
    datasets_with_public_glosses = Dataset.objects.filter(id__in=datasets_of_public_glosses)
    return datasets_with_public_glosses


def get_selected_datasets_for_user(user):
    if user.is_authenticated:
        user_profile = UserProfile.objects.get(user=user)
        selected_datasets = user_profile.selected_datasets.all()
        return selected_datasets
    else:
        # Make sure a non-empty set is returned, for anonymous users when no datasets are public
        selected_datasets = Dataset.objects.filter(acronym=settings.DEFAULT_DATASET_ACRONYM)
        return selected_datasets


def get_dataset_languages(datasets):
    """
    Return Language queryset containing languages for given datasets
    :param datasets: 
    :return: dataset_languages: Language queryset: 
    """
    try:
        dataset_languages = Language.objects.filter(dataset__in=datasets).distinct()
    except EmptyResultSet:
        dataset_languages = Language.objects.none()
    return dataset_languages


def get_users_without_dataset():

    users_with_no_dataset = []

    for user in User.objects.all():
        if user.is_active and len(get_objects_for_user(user, ['view_dataset'], Dataset, any_perm=True)) == 0:
            users_with_no_dataset.append(user)

    return users_with_no_dataset

def gloss_from_identifier(value):
    """Given an id of the form "idgloss (pk)" return the
    relevant gloss or None if none is found
    BUT: first check if a unique hit can be found by the string alone (if it is not empty)
    """

    match = re.match(r'(.*) \((\d+)\)', value)
    if match:
        print("MATCH: ", match)
        annotation_idgloss = match.group(1)
        pk = match.group(2)
        print("INFO: ", annotation_idgloss, pk)

        target = Gloss.objects.get(pk=int(pk))
        print("TARGET: ", target)
        return target
    elif value:
        annotation_idgloss = value
        target = Gloss.objects.get(annotation_idgloss=annotation_idgloss)
        return target
    else:
        return None


def get_default_annotationidglosstranslation(gloss):
    if not gloss.lemma or not gloss.lemma.dataset:
        return str(gloss.id)
    dataset = gloss.lemma.dataset
    language = dataset.default_language
    if not language:
        language = dataset.translation_languages.first()

    annotationidglosstranslations = gloss.annotationidglosstranslation_set.all()

    if not annotationidglosstranslations:
        return str(gloss.id)

    if annotationidglosstranslations.filter(language=language):
        return annotationidglosstranslations.get(language=language).text

    return annotationidglosstranslations.first().text


from signbank.settings.base import ECV_FILE,EARLIEST_GLOSS_CREATION_DATE, FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD, LANGUAGE_CODE, ECV_SETTINGS, URL, LANGUAGE_CODE_MAP
from signbank.settings import server_specific
from signbank.settings.server_specific import *
import re
import datetime as DT


def gloss_handshape_fields():
    # returns a list of fields that are Handshape ForeignKeys
    fields_list = []

    from signbank.dictionary.models import Gloss
    for gloss_fieldname in Gloss.get_field_names():
        gloss_field = Gloss.get_field(gloss_fieldname)
        if isinstance(gloss_field, models.ForeignKey) and gloss_field.related_model == Handshape:
            fields_list.append(gloss_field.name)
    return fields_list


def fields_with_choices_glosses():
    # return a dict that maps the field choice categories to the fields of Gloss that have the category

    fields_dict = {}

    from signbank.dictionary.models import Gloss
    for fieldname in Gloss.get_field_names():
        field = Gloss.get_field(fieldname)
        if hasattr(field, 'field_choice_category') and isinstance(field, FieldChoiceForeignKey):
            # field has choices
            field_category = field.field_choice_category
            if field_category in fields_dict.keys():
                fields_dict[field_category].append(field.name)
            else:
                fields_dict[field_category] = [field.name]
    return fields_dict

def fields_with_choices_handshapes():
    # return a dict that maps the field choice categories to the fields of Handshape that have the category

    fields_dict = {}

    from signbank.dictionary.models import Handshape
    for fieldname in Handshape.get_field_names():
        field = Handshape.get_field(fieldname)
        if hasattr(field, 'field_choice_category') and isinstance(field, FieldChoiceForeignKey):
            # field has choices
            field_category = field.field_choice_category
            if field_category in fields_dict.keys():
                fields_dict[field_category].append(field.name)
            else:
                fields_dict[field_category] = [field.name]
    return fields_dict

def fields_with_choices_examplesentences():
    # return a dict that maps the field choice categories to the fields of Handshape that have the category

    fields_dict = {}

    from signbank.dictionary.models import ExampleSentence
    for fieldname in ExampleSentence.get_field_names():
        field = ExampleSentence.get_field(fieldname)
        if hasattr(field, 'field_choice_category') and isinstance(field, FieldChoiceForeignKey):
            # field has choices
            field_category = field.field_choice_category
            if field_category in fields_dict.keys():
                fields_dict[field_category].append(field.name)
            else:
                fields_dict[field_category] = [field.name]
    return fields_dict

def fields_with_choices_definition():
    # return a dict that maps the field choice categories to the fields of Definition that have the category

    fields_dict = {}

    from signbank.dictionary.models import Definition
    for fieldname in Definition.get_field_names():
        field = Definition.get_field(fieldname)
        if hasattr(field, 'field_choice_category') and isinstance(field, FieldChoiceForeignKey):
            # field has choices
            field_category = field.field_choice_category
            if field_category in fields_dict.keys():
                fields_dict[field_category].append(field.name)
            else:
                fields_dict[field_category] = [field.name]
    return fields_dict

def fields_with_choices_morphology_definition():
    # return a dict that maps the field choice categories to the fields of MorphologyDefinition that have the category

    fields_dict = {}

    from signbank.dictionary.models import MorphologyDefinition
    for fieldname in MorphologyDefinition.get_field_names():
        field = MorphologyDefinition.get_field(fieldname)
        if hasattr(field, 'field_choice_category') and isinstance(field, FieldChoiceForeignKey):
            # field has choices
            field_category = field.field_choice_category
            if field_category in fields_dict.keys():
                fields_dict[field_category].append(field.name)
            else:
                fields_dict[field_category] = [field.name]
    return fields_dict

def fields_with_choices_other_media_type():
    # return a dict that maps the field choice categories to the fields of OtherMediaType that have the category

    fields_dict = {}

    from signbank.dictionary.models import OtherMedia
    for fieldname in OtherMedia.get_field_names():
        field = OtherMedia.get_field(fieldname)
        if hasattr(field, 'field_choice_category') and isinstance(field, FieldChoiceForeignKey):
            # field has choices
            field_category = field.field_choice_category
            if field_category in fields_dict.keys():
                fields_dict[field_category].append(field.name)
            else:
                fields_dict[field_category] = [field.name]
    return fields_dict

def fields_with_choices_morpheme_type():
    # return a dict that maps the field choice categories to the fields of MorphemeType that have the category

    fields_dict = {}

    from signbank.dictionary.models import Morpheme
    for fieldname in Morpheme.get_field_names():
        if fieldname in Gloss.get_field_names():
            # skip fields that are also in superclass Gloss
            continue
        field = Morpheme.get_field(fieldname)
        if hasattr(field, 'field_choice_category') and isinstance(field, FieldChoiceForeignKey):
            # field has choices
            field_category = field.field_choice_category
            if field_category in fields_dict.keys():
                fields_dict[field_category].append(field.name)
            else:
                fields_dict[field_category] = [field.name]
    return fields_dict


def write_ecv_files_for_all_datasets():

    all_dataset_objects = Dataset.objects.all()

    for ds in all_dataset_objects:
        success, ecv_filename = write_ecv_file_for_dataset(ds.acronym)
        if success:
            print('Saved ECV for Dataset ', ds.name, ' to file: ', ecv_filename)
        else:
            print('Error saving ECV for Dataset ', ds.name, ' to filename: ', ecv_filename)

    return True


def write_ecv_file_for_dataset(dataset_name):
    dataset_id = Dataset.objects.get(acronym=dataset_name)

    query_dataset = Gloss.none_morpheme_objects().filter(excludeFromEcv=False).filter(lemma__dataset=dataset_id)
    if not query_dataset:
        return ''

    sOrder = 'annotationidglosstranslation__text'
    if dataset_id.default_language:
        lang_attr_name = dataset_id.default_language.language_code_2char
    else:
        lang_attr_name = settings.DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
    sort_language = 'annotationidglosstranslation__language__language_code_2char'
    qs_empty = query_dataset.filter(**{sOrder + '__isnull': True})
    qs_letters = query_dataset.filter(**{sOrder + '__regex': r'^[a-zA-Z]', sort_language: lang_attr_name})
    qs_special = query_dataset.filter(**{sOrder + '__regex': r'^[^a-zA-Z]', sort_language: lang_attr_name})

    ordered = list(qs_letters.order_by(sOrder))
    ordered += list(qs_special.order_by(sOrder))
    ordered += list(qs_empty)

    context = {
        'CV_ID': ECV_SETTINGS['CV_ID'] if 'CV_ID' in ECV_SETTINGS else "",
        'date': str(DT.date.today()) + 'T' + str(DT.datetime.now().time()),
        'glosses': ordered,
        'dataset': dataset_id,
        'languages': dataset_id.translation_languages.all(),
        'resource_url': URL + PREFIX_URL + '/dictionary/gloss/'
    }
    from django.template.loader import get_template
    ecv_template = get_template('dictionary/ecv.xml')
    xmlstr = ecv_template.render(context)
    ecv_file = os.path.join(ECV_FOLDER_ABSOLUTE_PATH, dataset_name.lower().replace(" ","_") + ".ecv")
    import codecs
    try:
        f = codecs.open(ecv_file, "w", "utf-8")
        f.write(xmlstr)
        return True, ecv_file
    except PermissionError:
        return False, ecv_file


def get_ecv_description_for_gloss(gloss, lang, include_phonology_and_frequencies=False):
    activate(lang)

    desc = ""
    if include_phonology_and_frequencies:

        for f in ECV_SETTINGS['description_fields']:
            gloss_field = getattr(gloss, f)
            if isinstance(gloss_field, FieldChoice) or isinstance(gloss_field, Handshape):
                value = getattr(gloss, f).name
            else:
                value = get_value_for_ecv(gloss, f)

            # potential error: this pretty printing assumes a particular ordering of the fields
            # parens might not match if sorted otherwise
            # these fields seem to be hard coded
            if f == 'handedness':
                desc = value
            elif f == 'domhndsh':
                desc = desc + ', (' + value
            elif f == 'subhndsh':
                desc = desc + ',' + value
            elif f == 'handCh':
                desc = desc + '; ' + value + ')'
            elif f == 'tokNo':
                desc = desc + ' [' + value
            elif f == 'tokNoSgnr':
                desc = desc + '/' + value + ']'
            else:
                desc = desc + ', ' + value

    if desc and include_phonology_and_frequencies:
        desc += ", "

    lang = Language.objects.get(language_code_2char=lang)
    trans = []
    for sense in gloss.senses.all():
        for st in sense.senseTranslations.filter(language=lang).order_by('sense'):
            if str(st) != "":
                trans.append(str(st))
    desc += ", ".join(
        # The next line was adapted from an older version of this code,
        # that happened to do nothing. I left this for future usage.
        # map(lambda t: str(t.encode('ascii','xmlcharrefreplace')) if isinstance(t, unicode) else t, trans)
        trans
    )

    return desc


def get_value_for_ecv(gloss, fieldname):
    value = None
    annotationidglosstranslation_prefix = "annotationidglosstranslation_"
    if fieldname.startswith(annotationidglosstranslation_prefix):
        language_code_2char = fieldname[len(annotationidglosstranslation_prefix):]
        annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(
            language__language_code_2char=language_code_2char)
        if annotationidglosstranslations and len(annotationidglosstranslations) > 0:
            value = annotationidglosstranslations[0].text
    else:
        try:
            value = getattr(gloss, 'get_' + fieldname + '_display')()

        except AttributeError:
            value = getattr(gloss, fieldname)

    # This was disabled with the move to python 3... might not be needed anymore
    # if isinstance(value,unicode):
    #     value = str(value.encode('ascii','xmlcharrefreplace'))

    if value is None:
        value = " "
    elif not isinstance(value, str):
        value = str(value)

    if value == '-':
        value = ' '
    return value


def construct_scrollbar(qs, search_type, language_code):
    items = []
    if search_type in ['sign', 'sign_or_morpheme', 'morpheme', 'sign_handshape', 'annotatedsentence']:
        for item in qs:
            if item.is_morpheme():
                href_type = 'morpheme'
            elif item.is_annotatedgloss():
                sentence = AnnotatedSentenceTranslation.objects.filter(annotatedsentence=item.annotatedsentence).first()
                sentence_words = sentence.text.split()
                sentence_prefix = ' '.join(sentence_words[:5]) if sentence else ''
                data_label = str(item.gloss.idgloss) + ' (' + str(item.annotatedsentence.id) + '. ' + sentence_prefix + '...)'
                items.append(dict(id=str(item.annotatedsentence.id), glossid=str(item.gloss.id),
                                  data_label=data_label, gloss_label=str(item.gloss.idgloss),
                                  href_type='annotatedsentence'))
                continue
            else:
                href_type = 'gloss'
            annotationidglosstranslations = item.annotationidglosstranslation_set.filter(
                language__language_code_2char__exact=language_code
            )
            if annotationidglosstranslations and len(annotationidglosstranslations) > 0:
                gloss_text = annotationidglosstranslations.first().text
                if not gloss_text:
                    gloss_text = item.idgloss
                items.append(dict(id=str(item.id), data_label=gloss_text, href_type=href_type))
            else:
                # no annotations found for gloss
                # idgloss defaults to the id if nothing is found
                items.append(dict(id=str(item.id), data_label=item.idgloss, href_type=href_type))

    elif search_type in ['handshape']:
        for item in qs:
            data_label = item.name
            items.append(dict(id=str(item.machine_value), data_label=data_label, href_type='handshape'))

    elif search_type in ['lemma']:
        # there is no lemma details, so the href goes to lemma/update
        for item in qs:
            lemmaidglosstranslations = item.lemmaidglosstranslation_set.all()
            if lemmaidglosstranslations:
                if len(lemmaidglosstranslations) == 1:
                    # there are lemma's with only one translation, make sure they can be printed in the scroll bar
                    lemma_text = lemmaidglosstranslations.first().text
                else:
                    lemma_text = str(item.id)
                    for tr in lemmaidglosstranslations:
                        if tr.language.language_code_2char == language_code:
                            lemma_text = tr.text
                items.append(dict(id=str(item.id), data_label=lemma_text, href_type='lemma/update'))
            else:
                # no translations found for lemma
                items.append(dict(id=str(item.id), data_label=str(item.id), href_type='lemma/update'))

    elif search_type in ['sense']:
        for item in qs:
            data_label = '(' + str(item.sense) + ')'
            items.append(dict(id=str(item.gloss.id), data_label=data_label, href_type='gloss'))
    return items


def searchform_panels(searchform, searchfields):
    search_by_fields = []
    for field in searchfields:
        form_field_parameters = (field,searchform.fields[field].label,searchform[field])
        search_by_fields.append(form_field_parameters)
    return search_by_fields


def map_search_results_to_gloss_list(search_results):

    if not search_results:
        return [], []
    gloss_ids = []
    for search_result in search_results:
        if search_result['href_type'] == 'annotatedsentence':
            gloss_ids.append(search_result['glossid'])
        else:
            gloss_ids.append(search_result['id'])
    return gloss_ids, Gloss.objects.filter(id__in=gloss_ids)


def get_interface_language_and_default_language_codes(request):
    default_language = Language.objects.get(id=get_default_language_id())
    default_language_code = default_language.language_code_2char
    if request.LANGUAGE_CODE in dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR).keys():
        interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[request.LANGUAGE_CODE]
    else:
        interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[default_language_code]
    interface_language = Language.objects.get(language_code_3char=interface_language_3char)
    interface_language_code = interface_language.language_code_2char

    return interface_language, interface_language_code, default_language, default_language_code


def detect_delimiter(csv_lines):

    csv_lines_buffer = csv_lines

    delimiter_okay = True
    found_delimiter = ''

    for delimiter in ['\t', ',', ';']:
        while not found_delimiter:
            # keep searching for the header row
            # Apple Keynote stores an extra row above the header row when exported to CSV
            first_csv_line, rest_csv_lines = csv_lines_buffer[0], csv_lines_buffer[1:]

            row = first_csv_line.strip().split(delimiter)
            row = trim_columns_in_row(row)
            if first_csv_line and len(row) < 2:
                # the row has not been split into columns
                delimiter_okay = False
                break
            delimiter_okay = True
            found_delimiter = delimiter

        if found_delimiter:
            # break out of the for loop
            break
    return delimiter_okay, found_delimiter


def split_csv_lines_header_body(dataset_languages, csv_lines, delimiter, create_or_update):

    required_columns, language_fields, optional_columns = required_csv_columns(dataset_languages, create_or_update)
    csv_lines_buffer = csv_lines
    keys_found = False
    extra_keys = []
    delimiter_okay = True
    missing_keys = []
    csv_header = []
    csv_body = []
    count_check_rows = 0
    while not keys_found and csv_lines_buffer:
        # keep searching for the header row
        # Apple Keynote stores an extra row above the header row when exported to CSV
        first_csv_line, rest_csv_lines = csv_lines_buffer[0], csv_lines_buffer[1:]

        row = first_csv_line.strip().split(delimiter)
        row = trim_columns_in_row(row)
        if first_csv_line and len(row) < 2:
            # the row has not been split into columns
            delimiter_okay = False
            break
        all_keys_present = True
        for key in required_columns:
            if key not in row:
                if key == 'Lemma ID':
                    # create_or_update == 'update_lemma'
                    if 'Signbank ID' not in row:
                        # check for one or the other, Lemma ID or Signbank ID
                        all_keys_present = False
                        if key not in missing_keys:
                            missing_keys.append(key)
                else:
                    all_keys_present = False
                    if key not in missing_keys:
                        missing_keys.append(key)
        for col in row:
            if col in required_columns or col in language_fields or col in optional_columns:
                continue
            if col not in extra_keys:
                extra_keys.append(col)
        if all_keys_present:
            keys_found = True
            csv_header = row
            csv_body = rest_csv_lines
            # reset these since keys were found in the second row
            missing_keys = []
            extra_keys = []
        elif count_check_rows > 1 and (missing_keys or extra_keys):
            break
        else:
            # set up for next row
            # only record extra keys if this is a header row
            csv_lines_buffer = rest_csv_lines
            count_check_rows += 1
    return delimiter_okay, keys_found, missing_keys, extra_keys, csv_header, csv_body


def split_csv_lines_sentences_header_body(dataset_languages, csv_lines, delimiter):

    required_columns, language_fields, optional_columns = required_csv_columns(dataset_languages, 'create_sentences')

    csv_lines_buffer = csv_lines

    keys_found = False
    missing_keys = []
    extra_keys = []
    csv_header = []
    csv_body = []
    count_check_rows = 0
    while not keys_found and csv_lines_buffer:
        # keep searching for the header row
        # Apple Keynote stores an extra row above the header row when exported to CSV
        first_csv_line, rest_csv_lines = csv_lines_buffer[0], csv_lines_buffer[1:]

        row = first_csv_line.strip().split(delimiter)
        row = trim_columns_in_row(row)
        all_keys_present = True
        for key in required_columns:
            if key not in row:
                all_keys_present = False
                if key not in missing_keys:
                    missing_keys.append(key)
        for col in row:
            if col in required_columns:
                continue
            if col not in extra_keys:
                extra_keys.append(col)
        if all_keys_present:
            keys_found = True
            csv_header = row
            csv_body = rest_csv_lines
            # reset these since keys were found in the second row
            missing_keys = []
            extra_keys = []
        elif count_check_rows > 1 and (missing_keys or extra_keys):
            break
        else:
            # set up for next row
            # only record extra keys if this is a header row
            csv_lines_buffer = rest_csv_lines
            count_check_rows += 1
    return keys_found, missing_keys, extra_keys, csv_header, csv_body


def create_sentence_from_valuedict(valuedict, dataset, row_nr, earlier_creation_same_csv,
                                   earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss):

    errors_found = []
    new_sentence = []
    already_exists = []

    # Create an overview of all fields, sorted by their human name
    with override(LANGUAGE_CODE):

        translation_languages = dataset.translation_languages.all()

        sentence_translations = dict()
        # check sentence translations
        for language in translation_languages:
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            column_name = "Example Sentences (%s)" % language_name
            sentence_text = valuedict[column_name].strip()
            # also stores empty values
            sentence_translations[language] = sentence_text

        sentence_dict = {'row_nr': str(row_nr + 2), 'gloss_pk': valuedict["Signbank ID"], 'dataset': valuedict["Dataset"],
                         'order': valuedict["Sense Number"], 'sentence_type': valuedict["Sentence Type"],
                         'negative': valuedict["Negative"], 'translations': sentence_translations}
        errors_found = parse_sentence_row(str(row_nr + 2), sentence_dict)
        new_sentence.append(sentence_dict)
    return new_sentence, already_exists, errors_found, earlier_creation_same_csv, earlier_creation_annotationidgloss, \
        earlier_creation_lemmaidgloss

def get_checksum_for_path(file_path):

    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
            return file_hash.hexdigest()
    except FileNotFoundError:
        return None   