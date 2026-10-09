import os
import shutil
from zipfile import ZipFile
import json
import hashlib
import re
import codecs
from lxml import etree
import datetime as DT
from datetime import date
from dateutil.parser import parse

from django.db import models
from django.db.models.fields import BooleanField
from django.utils.translation import override, activate, gettext, gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateformat import format
from django.utils.timezone import get_current_timezone
from django.core.exceptions import ObjectDoesNotExist, EmptyResultSet
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template

from urllib.parse import urlencode
from guardian.shortcuts import get_objects_for_user

from signbank.settings.server_specific import (FIELDS, DEFAULT_LANGUAGE_HEADER_COLUMN, WRITABLE_FOLDER, LANGUAGE_CODE,
                                               WSGI_FILE,
                                               DEFAULT_DATASET_PK, TMP_DIR, FFMPEG_PROGRAM, GLOSS_VIDEO_DIRECTORY,
                                               GLOSS_IMAGE_DIRECTORY, DEFAULT_DATASET_ACRONYM, DEFAULT_KEYWORDS_LANGUAGE,
                                               ECV_SETTINGS, ECV_FOLDER_ABSOLUTE_PATH, URL, PREFIX_URL,
                                               LANGUAGES_LANGUAGE_CODE_3CHAR)
from signbank.dictionary.models import (Dataset, Gloss, Morpheme, Language, FieldChoice,
                                        DeletedGlossOrMedia, UserProfile, get_default_language_id,
                                        Handshape, LemmaIdgloss, FieldChoiceForeignKey, Definition,
                                        LemmaIdglossTranslation, MorphologyDefinition, AnnotatedSentenceTranslation,
                                        ExampleSentence, OtherMedia, Relation, GlossRevision)
from signbank.csv_interface import (parse_sentence_row,
                                    required_csv_columns, trim_columns_in_row)
from signbank.compare_csv_row_to_gloss import (get_default_annotationidglosstranslation,
                                               compare_simultaneous_morphology,
                                               compare_sequential_morphology, compare_blend_morphology,
                                               compare_relations,
                                               compare_relations_to_foreign_signs, compare_tags, compare_notes,
                                               compare_dataset,
                                               compare_signlanguages, compare_dialects, compare_example_sentences,
                                               compare_semantic_fields, compare_senses, compare_choice_field,
                                               compare_handshape, compare_booleans, compare_text, compare_annotations)
from signbank.dictionary.field_choices import fields_to_fieldcategory_dict

from signbank.video.extract_middle_frame import MiddleFrameExtracter


def get_two_letter_dir(idgloss):
    foldername = idgloss[:2]

    if len(foldername) == 1:
        foldername += '-'

    return foldername


def api_fields(dataset, language_code='en', advanced=False):
    activate(language_code)
    api_fields_2023 = []
    if not dataset:
        dataset = Dataset.objects.get(acronym=DEFAULT_DATASET_ACRONYM)
    if advanced:
        for language in dataset.translation_languages.all():
            language_field = gettext("Lemma ID Gloss") + ": %s" % language.name
            api_fields_2023.append(language_field)
    for language in dataset.translation_languages.all():
        language_field = gettext("Annotation ID Gloss") + ": %s" % language.name
        api_fields_2023.append(language_field)
    for language in dataset.translation_languages.all():
        language_field = gettext("Senses") + ": %s" % language.name
        api_fields_2023.append(language_field)

    if not advanced:
        api_fields_2023.append(gettext("Handedness"))
        api_fields_2023.append(gettext("Strong Hand"))
        api_fields_2023.append(gettext("Weak Hand"))
        api_fields_2023.append(gettext("Location"))
        api_fields_2023.append(gettext("Semantic Field"))
        api_fields_2023.append(gettext("Word Class"))
        api_fields_2023.append(gettext("Named Entity"))
        api_fields_2023.append(gettext("Link"))
        api_fields_2023.append(gettext("Video"))
        api_fields_2023.append(gettext("Perspective Videos"))
    else:
        api_fields_2023.append(gettext("Link"))
        api_fields_2023.append(gettext("Video"))
        api_fields_2023.append(gettext("Perspective Videos"))
        api_fields_2023.append(gettext("Tags"))
        api_fields_2023.append(gettext("Notes"))
        api_fields_2023.append(gettext("Affiliation"))
        api_fields_2023.append(gettext("Sequential Morphology"))
        api_fields_2023.append(gettext("Simultaneous Morphology"))
        api_fields_2023.append(gettext("Blend Morphology"))

        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
        gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

        # TO DO
        extra_columns = ['Sign Languages', 'Dialects',
                         'Relations to other signs', 'Relations to foreign signs', 'Notes']

        # show advanced properties
        for field in gloss_fields:
            api_fields_2023.append(field.verbose_name.title())

        api_fields_2023.append(gettext("NME Videos"))

    return api_fields_2023


def save_media(source_folder, language_code_3char, goal_folder, gloss, extension):
        
    # Add a dot before the extension if needed
    if extension[0] != '.':
        extension = '.' + extension

    # Figure out some names
    try:
        language = Language.objects.get(language_code_3char=language_code_3char)
    except ObjectDoesNotExist:
        # no language exists for this folder
        return False, False
    annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
    if annotationidglosstranslations.count() > 0:
        annotation_text = annotationidglosstranslations.first().text
    else:
        annotation_text = ""

    destination_folder = f'{WRITABLE_FOLDER}/{goal_folder}/{gloss.lemma.dataset.acronym}/{get_two_letter_dir(gloss.idgloss)}'

    # Create the necessary subfolder if needed
    if not os.path.isdir(destination_folder):
        os.mkdir(destination_folder)

    # Move the file
    source = source_folder+annotation_text+extension
    destination_file = f'{annotation_text}-{gloss.pk}{extension}'
    goal = os.path.join(destination_folder, destination_file)

    if os.path.isfile(goal):
        overwritten = True
    else:
        overwritten = False

    try:
        shutil.copyfile(source, goal)
        was_allowed = True
    except IOError:
        was_allowed = False

    try:
        os.remove(source)
    except OSError:
        pass

    return overwritten, was_allowed


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

            lemmaidgloss_comumn_name = "Lemma ID Gloss (%s)" % (getattr(language, DEFAULT_LANGUAGE_HEADER_COLUMN['English']))

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

            column_name = "Annotation ID Gloss (%s)" % (getattr(language, DEFAULT_LANGUAGE_HEADER_COLUMN['English']))
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
                    error_string = gettext("Row {row} has an empty {column_name}").format(row=str(row_nr+1), column_name=column_name)
                    errors_found += [error_string]
            else:
                print('column name not in value dict: ', column_name)

        if existing_glosses:
            existing_gloss_set = set()
            for language_code_2char, glosses in existing_glosses.items():
                for gloss in glosses:
                    if gloss not in existing_gloss_set:
                        gloss_dict = {
                             'gloss_pk': gloss.pk,
                             'dataset': gloss.dataset
                        }
                        annotationidglosstranslation_dict = {}
                        for lang in gloss.lemma.dataset.translation_languages.all():
                            language_name = getattr(language, DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                            annotationidglosstranslation_text = valuedict["Annotation ID Gloss (%s)" % language_name]
                            annotationidglosstranslation_dict[lang.language_code_2char] = annotationidglosstranslation_text
                        gloss_dict['annotationidglosstranslations'] = annotationidglosstranslation_dict

                        lemmaidglosstranslation_dict = {}
                        for lang in gloss.lemma.dataset.translation_languages.all():
                            language_name = getattr(language, DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                            lemmaidglosstranslation_text = valuedict["Lemma ID Gloss (%s)" % language_name]
                            lemmaidglosstranslation_dict[lang.language_code_2char] = lemmaidglosstranslation_text
                        gloss_dict['lemmaidglosstranslations'] = lemmaidglosstranslation_dict
                        already_exists.append(gloss_dict)
                        existing_gloss_set.add(gloss)
        else:
            gloss_dict = {'gloss_pk': str(row_nr + 1), 'dataset': dataset}
            trans_languages = [l for l in dataset.translation_languages.all()]
            annotationidglosstranslation_dict = dict()
            for language in trans_languages:
                language_name = getattr(language, DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                annotationidglosstranslation_text = valuedict["Annotation ID Gloss (%s)" % language_name]
                annotationidglosstranslation_dict[language.language_code_2char] = annotationidglosstranslation_text
                if language.language_code_2char in earlier_creation_annotationidgloss.keys() and \
                        annotationidglosstranslation_text in earlier_creation_annotationidgloss[language.language_code_2char]:
                    error_string = gettext("Duplicate Annotation ID Gloss found for {language}: {annotation}").format(language=language_name, annotation=annotationidglosstranslation_text)
                    errors_found += [error_string]

                if not earlier_creation_annotationidgloss or (
                        language.language_code_2char not in earlier_creation_annotationidgloss.keys()):
                    earlier_creation_annotationidgloss[language.language_code_2char] = [annotationidglosstranslation_text]
                else:
                    earlier_creation_annotationidgloss[language.language_code_2char].append(annotationidglosstranslation_text)
            gloss_dict['annotationidglosstranslations'] = annotationidglosstranslation_dict

            lemmaidglosstranslation_dict = {}
            for language in trans_languages:
                language_name = getattr(language, DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
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

        range_of_earlier_creation = [v for (i, v) in earlier_creation_same_csv.items()]
        if earlier_creation_same_csv and new_gloss in range_of_earlier_creation:
            error_string = gettext("Row {row} is a duplicate gloss creation.").format(row=str(row_nr+1))
            errors_found += [error_string]

    # save the parameters for the new gloss under the row number
    # make sure this gloss isn't being created twice
    if len(errors_found) == 0 and len(already_exists) == 0:
        earlier_creation_same_csv[str(row_nr+1)] = new_gloss
        earlier_creation_lemmaidgloss[str(row_nr+1)] = lemmaidglosstranslations

    return new_gloss, already_exists, errors_found, earlier_creation_same_csv, earlier_creation_annotationidgloss, \
        earlier_creation_lemmaidgloss


def compare_valuedict_to_gloss(valuedict, gloss, my_datasets, nl,
                               notes_toggle, notes_assign_toggle, semfield_toggle, semfield_assign_toggle, tags_toggle):
    """Takes a dict of arbitrary key-value pairs, and compares them to a gloss"""
    # called by import_csv_update in views.py

    errors_found = []
    differences = []

    column_name_error = False
    tag_name_error = False

    note_type_error = False
    note_tuple_error = False

    # Create an overview of all fields, sorted by their human name
    with override(LANGUAGE_CODE):

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

        # Go through all values in the value dict, looking for differences with the gloss
        for human_key, new_human_value in valuedict.items():

            new_human_value = new_human_value.strip()

            if human_key == 'Signbank ID':
                continue

            annotation_idgloss_key_prefix = "Annotation ID Gloss ("
            if human_key.startswith(annotation_idgloss_key_prefix):

                errors_found, differences = compare_annotations(gloss, new_human_value, human_key, errors_found, differences)
                continue

            lemma_idgloss_key_prefix = "Lemma ID Gloss ("
            if human_key.startswith(lemma_idgloss_key_prefix):
                # Any attempts to change the lemma translations are handled in the outer scope
                continue

            keywords_key_prefix = "Senses ("
            if human_key.startswith(keywords_key_prefix):

                errors_found, differences = compare_senses(gloss, new_human_value, human_key, errors_found, differences)
                continue

            example_sentences_key_prefix = "Example Sentences ("
            if human_key.startswith(example_sentences_key_prefix):

                errors_found, differences = compare_example_sentences(gloss, new_human_value, human_key, errors_found, differences)
                continue

            elif human_key == 'SignLanguages':

                errors_found, differences = compare_signlanguages(gloss, new_human_value, human_key, errors_found, differences)
                continue

            elif human_key == 'Dialects':

                errors_found, differences = compare_dialects(gloss, new_human_value, human_key, errors_found, differences)
                continue

            elif human_key == 'Dataset':

                errors_found, differences = compare_dataset(gloss, new_human_value, human_key, errors_found, differences, my_datasets)
                continue

            elif human_key == 'Relations to other signs':

                errors_found, differences = compare_relations(gloss, new_human_value, human_key, errors_found, differences)
                continue

            elif human_key == 'Relations to foreign signs':

                errors_found, differences = compare_relations_to_foreign_signs(gloss, new_human_value, human_key, errors_found, differences)
                continue

            elif human_key == 'Sequential Morphology':

                errors_found, differences = compare_sequential_morphology(gloss, new_human_value, human_key, errors_found, differences)
                continue

            elif human_key == 'Simultaneous Morphology':

                errors_found, differences = compare_simultaneous_morphology(gloss, new_human_value, human_key, errors_found, differences)
                continue

            elif human_key == 'Blend Morphology':

                errors_found, differences = compare_blend_morphology(gloss, new_human_value, human_key, errors_found, differences)
                continue

            elif human_key == 'Tags':

                if tags_toggle == 'keep' and new_human_value in ['None', '']:
                    continue

                errors_found, differences, tag_name_error = compare_tags(gloss, new_human_value, human_key, errors_found, differences, tag_name_error)
                continue

            elif human_key == 'Notes':

                if notes_toggle == 'keep' and new_human_value in ['None', '']:
                    continue

                errors_found, differences, note_type_error, note_tuple_error = compare_notes(gloss, new_human_value, human_key, notes_assign_toggle, errors_found, differences, note_type_error, note_tuple_error)
                continue

            elif human_key == 'Semantic Field':

                if semfield_toggle == 'keep' and new_human_value == '-':
                    continue

                errors_found, differences = compare_semantic_fields(gloss, new_human_value, human_key, errors_found, differences, semfield_assign_toggle)
                continue

            elif human_key in ['Derivation history', 'Derivation History']:

                continue

            # Before obtaining the Gloss field associated with the human key (column header) in the next step, make sure it is a field verbose name
            if human_key not in fields.keys():
                error_string = gettext("For gloss '{annotation}' ({glossid}), could not identify column name: '{column}'.").format(
                    annotation=get_default_annotationidglosstranslation(gloss), glossid=str(gloss.id), column=human_key)
                errors_found += [error_string]

                if not column_name_error:
                    # a setting is used to avoid repeating this feedback message
                    error_string = gettext("HINT: Try exporting a CSV file to see what column names can be used.")
                    errors_found += [error_string]
                    column_name_error = True
                continue

            # What follows is processing for the Gloss model fields that are not complex related models
            field = fields[human_key]

            if hasattr(field, 'field_choice_category'):
                errors_found, differences = compare_choice_field(gloss, field, new_human_value, human_key, errors_found, differences)

                continue

            if isinstance(field, models.ForeignKey) and field.related_model == Handshape:
                errors_found, differences = compare_handshape(gloss, field, new_human_value, human_key, errors_found, differences)

                continue

            if field.__class__.__name__ == 'BooleanField':
                errors_found, differences = compare_booleans(gloss, field, new_human_value, human_key, errors_found, differences)

                continue
            if field.__class__.__name__ == 'CharField' or field.__class__.__name__ == 'TextField':
                errors_found, differences = compare_text(gloss, field, new_human_value, human_key, errors_found, differences)

                continue

    return differences, errors_found


def compare_valuedict_to_lemma(valuedict, lemma_id, my_datasets, nl,
                                lemmaidglosstranslations, current_lemmaidglosstranslations,
                               earlier_updates_same_csv, earlier_updates_lemmaidgloss):
    """Takes a dict of key-value pairs, and compares them to a lemma"""

    errors_found = []
    differences = []

    try:
        lemma = LemmaIdgloss.objects.select_related().get(pk=lemma_id)
    except ObjectDoesNotExist as e:
        e = gettext("Could not find lemma for ID {lemmaid}.").format(lemmaid=str(lemma_id))
        errors_found.append(e)
        return differences, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss

    if lemma_id in earlier_updates_same_csv:
        e = gettext("Lemma ID {lemmaid} found in multiple rows (Row {row}).").format(lemmaid=str(lemma_id), row=str(nl+1))
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
        # somebody has modified the lemma translations to delete all of them:
        e = gettext("Row {row}: Lemma ID {lemmaid} must have at least one translation.").format(row=str(nl+1), lemmaid=str(lemma_id))
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
                language_name_column = DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = human_key[len(lemma_idgloss_key_prefix):-1]
                languages = Language.objects.filter(**{language_name_column: language_name})
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


@csrf_exempt
def set_dark_mode(request):
    # this is the toggle button in the menu bar
    if 'dark_mode' not in request.session.keys():
        # first time button is used
        request.session['dark_mode'] = "True"
    elif request.session['dark_mode'] == "True":
        request.session['dark_mode'] = "False"
    elif request.session['dark_mode'] == "False":
        request.session['dark_mode'] = "True"
    request.session.modified = True
    return JsonResponse({})


def reload_signbank(request=None):
    """Functions to clear the cache of Apache, also works as view"""

    # Refresh the wsgi script
    os.utime(WSGI_FILE, None)

    # If this is an HTTP request, give an HTTP response
    if request is not None:

        return render(request, 'reload_signbank.html')


def get_gloss_data(since_timestamp=0, language_code='en', dataset=None, inWebSet=False, extended_fields=False):

    if not dataset:
        dataset = Dataset.objects.get(id=DEFAULT_DATASET_PK)

    if inWebSet:
        glosses = Gloss.objects.filter(lemma__dataset=dataset, inWeb=True, archived=False)
    else:
        glosses = Gloss.objects.filter(lemma__dataset=dataset, archived=False)

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
    deletion_date_range = [DT.datetime.fromtimestamp(since_timestamp), date.today()]

    for deleted_gloss_or_media in DeletedGlossOrMedia.objects.filter(deletion_date__range=deletion_date_range,
                                                                     item_type=item_type):
        if item_type == 'gloss':
            result.append((str(deleted_gloss_or_media.old_pk), deleted_gloss_or_media.idgloss))
        else:
            result.append(str(deleted_gloss_or_media.old_pk))

    return result


def generate_still_image(video):
    try:
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
        selected_datasets = Dataset.objects.filter(acronym=DEFAULT_DATASET_ACRONYM)
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


def get_gloss_handshape_fields():
    # returns a list of fields that are Handshape ForeignKeys
    fields_list = []

    for gloss_fieldname in Gloss.get_field_names():
        gloss_field = Gloss.get_field(gloss_fieldname)
        if isinstance(gloss_field, models.ForeignKey) and gloss_field.related_model == Handshape:
            fields_list.append(gloss_field.name)
    return fields_list


def get_fields_with_choices_glosses():
    # return a dict that maps the field choice categories to the fields of Gloss that have the category

    fields_dict = {}

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

def get_fields_with_choices_handshapes():
    # return a dict that maps the field choice categories to the fields of Handshape that have the category

    fields_dict = {}

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

def get_fields_with_choices_examplesentences():
    # return a dict that maps the field choice categories to the fields of Handshape that have the category

    fields_dict = {}

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

def get_fields_with_choices_definition():
    # return a dict that maps the field choice categories to the fields of Definition that have the category

    fields_dict = {}

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

def get_fields_with_choices_morphology_definition():
    # return a dict that maps the field choice categories to the fields of MorphologyDefinition that have the category

    fields_dict = {}

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

def get_fields_with_choices_other_media_type():
    # return a dict that maps the field choice categories to the fields of OtherMediaType that have the category

    fields_dict = {}

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

def get_fields_with_choices_morpheme_type():
    # return a dict that maps the field choice categories to the fields of MorphemeType that have the category

    fields_dict = {}

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


def get_fields_with_choices_relation():
    # return a dict that maps the field choice categories to the fields of Definition that have the category

    fields_dict = {}

    for fieldname in Relation.get_field_names():
        field = Relation.get_field(fieldname)
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
        lang_attr_name = DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
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
    ecv_template = get_template('dictionary/ecv.xml')
    xmlstr = ecv_template.render(context)
    ecv_file = os.path.join(ECV_FOLDER_ABSOLUTE_PATH, dataset_name.lower().replace(" ", "_") + ".ecv")
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
                sentence_words = sentence.text.split() if sentence and sentence.text else []
                sentence_prefix = ' '.join(sentence_words[:5]) if sentence else ''
                data_label = f'{item.gloss.idgloss} ({item.annotatedsentence.id}. {sentence_prefix}...)'
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
            data_label = f'({item.sense})'
            items.append(dict(id=str(item.gloss.id), data_label=data_label, href_type='gloss'))
    return items


def searchform_panels(searchform, searchfields):
    search_by_fields = []
    for field in searchfields:
        form_field_parameters = (field, searchform.fields[field].label, searchform[field])
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
    if request.LANGUAGE_CODE in dict(LANGUAGES_LANGUAGE_CODE_3CHAR).keys():
        interface_language_3char = dict(LANGUAGES_LANGUAGE_CODE_3CHAR)[request.LANGUAGE_CODE]
    else:
        interface_language_3char = dict(LANGUAGES_LANGUAGE_CODE_3CHAR)[default_language_code]
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
            language_name = getattr(language, DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
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

    BYTES_PER_CHUNK = 8192 #"8 KB is a common practice to efficiently handle large files without consuming too much memory"

    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5()
            while chunk := f.read(BYTES_PER_CHUNK):
                file_hash.update(chunk)
            return file_hash.hexdigest()
    except FileNotFoundError:
        return None


def get_eaf_creation_time(fname):
    """
    Extracts the creation time from an EAF file.
    EAF = ELAN Annotation File - https://archive.mpi.nl/tla/elan/
    """
    with open(fname, encoding="utf-8") as eaf:
        try:
            xml = etree.parse(eaf)
            # root node is ANNOTATION_DOCUMENT
            root = xml.getroot()
            creation_date = root.attrib['DATE']
            date_time_obj = parse(creation_date)
        except:
            date_time_obj = DT.datetime.now(tz=get_current_timezone())

        return date_time_obj


def get_multiselect_fieldnames():
    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew'] + ['dialect', 'signlanguage']
    fields_with_choices = fields_to_fieldcategory_dict(fieldnames)
    multiple_select_gloss_fields = [fieldname for fieldname in fieldnames if fieldname in fields_with_choices.keys()]
    return multiple_select_gloss_fields


def filter_page_values(vals):
    values = [v for v in vals if re.match(r"[1-9]\d*$", v)]
    return values


def get_available_url_parameters_for_template(search_form):
    search_form_fields = list(search_form.fields.keys())
    multiselect_fields = get_multiselect_fieldnames()

    multiselect_fields_of_form = [f'{field}[]' for field in multiselect_fields if field in search_form_fields]
    multiselect_fields_missing_brackets = [field for field in multiselect_fields if field in search_form_fields]
    non_multiselect_fields = [field for field in search_form_fields if field not in multiselect_fields_missing_brackets]

    return multiselect_fields_of_form + non_multiselect_fields


def get_page_parameters_for_listview(search_form, request_get_parameters, query_parameters):
    page_params_list = []
    okay_parameters = get_available_url_parameters_for_template(search_form)
    if 'query' not in request_get_parameters:
        for key, value in query_parameters.items():
            # process explicitly saved query parameters first
            if isinstance(value, list):
                page_params_list.extend((key, x) for x in value)
            else:
                page_params_list.append((key, value))
    for key, value in request_get_parameters.items():
        # add other url parameters and ignore if processed above, this allows processing of multi-select parameters
        if key in query_parameters.keys() or key not in okay_parameters:
            continue
        if isinstance(value, list):
            page_params_list.extend((key, x) for x in value)
        else:
            page_params_list.append((key, value))
    return f'&{urlencode(page_params_list)}' if page_params_list else ""


def get_lemma_translation_violations(dataset):
    # for use in a command to check all the lemma's of a dataset for constraint violations
    # the "none" case is legacy data, so not necessarily a constraint violation, but they cannot be empty if updated
    results = {dataset: {}}
    dataset_lemmas = dataset.lemmaidgloss_set.all()
    for language in dataset.translation_languages.all():
        results[dataset][language] = {
            'none': [],
            'multiple': [],
            'empty': []
        }
    for lemma in dataset_lemmas:
        lemma_translation_objects = lemma.lemmaidglosstranslation_set.all()
        for language in dataset.translation_languages.all():
            if lemma_translation_objects.filter(language=language).count() > 1:
                results[dataset][language]['multiple'].append(lemma)
            elif lemma_translation_objects.filter(language=language).count() == 0:
                results[dataset][language]['none'].append(lemma)
            elif lemma_translation_objects.filter(language=language, text='').count() > 0:
                results[dataset][language]['empty'].append(lemma)
    return results


def copy_missing_lemmaidglosstranslation_from_annotationidglosstranslation(lemma):

    duplicatelemmas = find_duplicate_lemmas(lemma)
    if duplicatelemmas:
        return
    lemma_group_glossset = Gloss.objects.filter(lemma=lemma)
    if lemma_group_glossset.count() != 1:
        return
    dataset_languages = lemma.dataset.translation_languages.all()
    lemma_translation_objects = lemma.lemmaidglosstranslation_set.all()
    if dataset_languages.count() == lemma_translation_objects.count():
        return
    gloss_translations = lemma_group_glossset.first().annotationidglosstranslation_set.all()
    for language in dataset_languages:
        lemma_translation_for_language = lemma_translation_objects.filter(language=language).first()
        if lemma_translation_for_language:
            # the lemma already has a translation for this language
            continue
        gloss_translation_for_language = gloss_translations.filter(language=language).first()
        if not gloss_translation_for_language:
            # there is no translation for this language from the (unique) gloss of this lemma
            continue
        # copy the lemma translation for this language from the (unique) gloss of this lemma
        new_lemma_translation = LemmaIdglossTranslation(lemma=lemma, language=language,
                                                        text=gloss_translation_for_language.text)
        new_lemma_translation.save()
    return


def find_duplicate_lemmas(lemma):
    # this finds other lemmas in the same dataset with duplicates of the translations of this lemma
    # it returns a list of unique lemma ids.
    if lemma.dataset is None:
        return []
    duplicate_to_me = []
    for translation in lemma.lemmaidglosstranslation_set.all():

        duplicate_translations = LemmaIdglossTranslation.objects.filter(language=translation.language,
                                                                        text__iexact=translation.text,
                                                                        lemma__dataset=lemma.dataset).exclude(
            lemma=lemma)
        for duplicate_translation in duplicate_translations:
            duplicate_to_me.append(duplicate_translation.lemma.id)
    duplicate_lemma = list(set(duplicate_to_me))
    return duplicate_lemma


def generate_tabbed_text_response(values):
    """ Used by update methods to format a list of return values into a tabbed string.
    The tabbed strings are used in the editable templates where the updates are shown by javascript.
    """
    str_values = map(str, values)
    content = '\t'.join(str_values)
    return HttpResponse(content, content_type='text/plain')

def add_gloss_update_to_revision_history(user, gloss, field, oldvalue, newvalue):

    assert user is not None, "user parameter must not be None"
    assert gloss is not None, "gloss parameter must not be None"
    assert field is not None, "field parameter must not be None"

    if oldvalue == newvalue:
        return

    revision = GlossRevision(old_value=oldvalue,
                             new_value=newvalue,
                             field_name=field,
                             gloss=gloss,
                             user=user,
                             time=DT.datetime.now(tz=get_current_timezone()))
    revision.save()

def add_relations_to_revision_history(user, gloss, original_glosses_display):

    new_relations_display = gloss.get_relation_display()
    original_relations_display = original_glosses_display[gloss]
    if new_relations_display != original_relations_display:
        add_gloss_update_to_revision_history(user, gloss, 'relation', original_relations_display,
                                             new_relations_display)

    for target, original_target_display in original_glosses_display.items():
        if target == gloss:
            continue
        new_target_display = target.get_relation_display()
        if new_target_display == original_target_display:
            continue
        add_gloss_update_to_revision_history(user, target, 'relation', original_target_display,
                                             new_target_display)


def update_boolean_checkbox(user, gloss, field, value):
    assert isinstance(gloss, Gloss), "Not a Gloss object"
    assert isinstance(Gloss.get_field(field), BooleanField), "Not a BooleanField"

    if field in FIELDS['phonology']:
        category_value = 'phonology'
    elif field in ['inWeb', 'isNew', 'excludeFromEcv']:
        category_value = 'publication'
    else:
        category_value = ''

    original_value = getattr(gloss, field)

    boolean_value = value.lower() in [_('Yes').lower(), 'true', 'True', True, 1]

    gloss.__setattr__(field, boolean_value)
    gloss.save()

    display_value = _('Yes') if boolean_value else _('No')

    add_gloss_update_to_revision_history(user, gloss, field, str(original_value), str(boolean_value))

    # results = {'boolean_value': boolean_value,
    #            'display_value': display_value,
    #            'category_value': category_value}
    # return JsonResponse(results)
    return HttpResponse(f'{boolean_value}\t{display_value}\t{category_value}', content_type='text/plain')
