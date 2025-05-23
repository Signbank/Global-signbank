import datetime as DT
import ast
import json
import os

from django.db import models, DatabaseError, IntegrityError
from django.utils.translation import gettext_lazy as _, activate, gettext
from django.utils.timezone import get_current_timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.db.transaction import atomic, TransactionManagementError

from guardian.shortcuts import get_objects_for_user
from pympi.Elan import Eaf
from tempfile import NamedTemporaryFile

from signbank.settings.server_specific import (FIELDS, MODELTRANSLATION_LANGUAGES, DEBUG_API)
from signbank.dictionary.models import (Dataset, Gloss, Language, AnnotationIdglossTranslation, LemmaIdglossTranslation,
                                        Handshape, DerivationHistory, Keyword, SemanticField, GlossRevision,
                                        Sense, SenseTranslation, ExampleSentence, Translation, AnnotatedGloss,
                                        AnnotatedSentence, AnnotatedSentenceSource, AnnotatedSentenceTranslation,
                                        AnnotatedSentenceContext, FieldChoice, FieldChoiceForeignKey,
                                        CATEGORY_MODELS_MAPPING)
from signbank.video.models import GlossVideoDescription, GlossVideoNME, AnnotatedVideo, NME_PERSPECTIVE_CHOICES
from signbank.video.views import get_glosses_from_eaf
from signbank.tools import get_default_annotationidglosstranslation
from signbank.csv_interface import normalize_field_choice, normalize_boolean
from signbank.api_token import put_api_user_in_request
from signbank.abstract_machine import retrieve_language_code_from_header
from signbank.dictionary.batch_edit import add_gloss_update_to_revision_history

PERSPECTIVE_VIDEO_LABELS = {}
PERSPECTIVE_VIDEO_LABELS['center'] = ['center', 'centered', 'mid', 'default', 'file', 'video']
PERSPECTIVE_VIDEO_LABELS['left'] = ['left', 'l']
PERSPECTIVE_VIDEO_LABELS['right'] = ['right', 'r']


def names_of_update_gloss_fields(dataset, language_code):
    activate(language_code)

    dataset_languages = dataset.translation_languages.all()
    annotationidglosstranslation_fields = [gettext("Annotation ID Gloss") + " (" + language.name + ")"
                                           for language in dataset_languages]
    lemmaidglosstranslation_fields = [gettext("Lemma ID Gloss") + " (" + language.name + ")"
                                      for language in dataset_languages]

    language_fields = annotationidglosstranslation_fields + lemmaidglosstranslation_fields

    verbose_field_names = []
    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
    gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

    activate(language_code)
    for field in gloss_fields:
        verbose_field_names.append(field.verbose_name.title())

    return language_fields, verbose_field_names


def internal_language_fields(dataset, language_code):
    activate(language_code)

    dataset_languages = dataset.translation_languages.all()
    annotationidglosstranslation_fields = ['annotation_id_gloss_' + getattr(language, 'language_code_2char')
                                           for language in dataset_languages]
    lemmaidglosstranslation_fields = ['lemma_id_gloss_' + getattr(language, 'language_code_2char')
                                      for language in dataset_languages]

    language_fields = annotationidglosstranslation_fields + lemmaidglosstranslation_fields

    return language_fields


def update_gloss_columns_to_value_dict_keys(dataset, language_code):
    """
    Function to create mapping dictionaries for the different label representations
    Called from gloss_pre_update
    Representations:
    1. Human readable labels (multilingual, with language name in parentheses)
    2. JSON keys (multilingual, with colon before language name)
    3. Internal form field labels
       Gloss field names or labels for language fields
       Language fields are not Gloss fields. They are constructed,
       contain underscores and language code at the end.
    (1) and (3) are shared with CSV routines
    Mappings:
    human_readable_to_internal
       maps human readable labels to fields of Gloss (so attributes can be retrieved)
       or to language internal fields
    human_readable_to_json
       maps human readable language labels with parens to JSON keys with colons
       only used for language labels
    """
    human_readable_to_internal = dict()
    human_readable_to_json = dict()

    activate(language_code)

    dataset_languages = dataset.translation_languages.all()
    for language in dataset_languages:
        human_readable_annotation = gettext("Annotation ID Gloss") + " (" + language.name + ")"
        internal_annotation = 'annotation_id_gloss_' + getattr(language, 'language_code_2char')
        annotation_api_field_name = _("Annotation ID Gloss") + ": %s" % language.name

        human_readable_lemma = gettext("Lemma ID Gloss") + " (" + language.name + ")"
        internal_lemma = 'lemma_id_gloss_' + getattr(language, 'language_code_2char')
        lemma_api_field_name = _("Lemma ID Gloss") + ": %s" % language.name

        human_readable_to_internal[human_readable_annotation] = internal_annotation
        human_readable_to_internal[human_readable_lemma] = internal_lemma

        human_readable_to_json[human_readable_lemma] = lemma_api_field_name
        human_readable_to_json[human_readable_annotation] = annotation_api_field_name

    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
    gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

    for field in gloss_fields:
        human_readable_to_internal[field.verbose_name.title()] = field

    return human_readable_to_internal, human_readable_to_json


def get_gloss_update_human_readable_value_dict(request):
    post_data = json.loads(request.body.decode('utf-8'))

    value_dict = dict()
    for field in post_data.keys():
        value = post_data.get(field, '')
        value_dict[field] = value.strip() if isinstance(value, str) else value
    return value_dict


def check_fields_can_be_updated(gloss, value_dict, dataset, language_code):
    activate(language_code)
    language_fields, gloss_fields = names_of_update_gloss_fields(dataset, language_code)
    available_fields = language_fields + gloss_fields
    errors = dict()
    for field in value_dict.keys():
        if field in ["Senses", "Betekenissen"]:
            if ExampleSentence.objects.filter(senses__glosses=gloss).exists():
                errors[field] = gettext(
                    'API UPDATE NOT AVAILABLE: The gloss has senses with example sentences.')
            elif isinstance(value_dict[field], str):
                new_senses, formatting_error_senses = convert_string_to_dict_of_list_of_lists(value_dict[field])
                if formatting_error_senses:
                    errors[field] = formatting_error_senses
            continue
        elif field in gloss_fields or field in language_fields:
            continue
        errors[field] = _("Field name not found in fields that can be updated.")
    if errors:
        errors["Available Fields"] = ", ".join(available_fields)
    return errors


def remove_duplicates_preserve_order(translation_list):
    unique_list = []
    seen = set()
    for item in translation_list:
        if item not in seen:
            unique_list.append(item)
            seen.add(item)
    return unique_list


def convert_string_to_dict_of_list_of_lists(input_string):
    """
    Convert a string to a dictionary of lists of lists.
    """
    try:
        dict_of_lists = ast.literal_eval(input_string)
    except (ValueError, SyntaxError):
        return {}, "Sense input is not in the expected format. \nTry: '{\"en\":[[\"sense 1 keyword1\", \"sense 1 keyword2\"],[\"sense 2 keyword1\"]], \"nl\":[[\"sense 1 keyword1\"],[\"sense 2 keyword1\", \"sense 2 keyword2\"]]}'"

    # Verify if the result is a dictionary
    if isinstance(dict_of_lists, dict):
        lengths = set()
        for key, value in dict_of_lists.items():
            if not isinstance(value, list):
                return {}, f"The value associated with key '{key}' is not a list."
            lengths.add(len(value))
            for item in value:
                if not isinstance(item, list):
                    return {}, f"The value associated with key '{key}' contains a non-list element."
        if len(lengths) > 1:
            return {}, "Lists within the dictionary have different lengths."
        return dict_of_lists, None
    else:
        return {}, "Input is not a dictionary."


def collect_revision_history_for_senses(gloss):
    # this collects the senses in pretty-printed in human-readable form
    senses_display_list = []
    gloss_senses = gloss.senses.all()
    for sense in gloss_senses:
        senses_display_list.append(str(sense))
    return ' ||| '.join(senses_display_list)


def update_senses(gloss, new_value): 
    """"
    new_value is a string of comma separated senses, where each sense is a string of comma separated translations
    """
    # new_senses, _ = convert_string_to_dict_of_list_of_lists(new_value)
    new_senses = new_value
    dataset = gloss.lemma.dataset
    dataset_languages = dataset.translation_languages.all()

    # First remove the senses from the gloss
    old_senses = gloss.senses.all()
    for old_sense in old_senses:
        for sense_translation in old_sense.senseTranslations.all():
            # iterate over a list because the objects will be removed
            for translation in sense_translation.translations.all():
                sense_translation.translations.remove(translation)
                translation.delete()
            old_sense.senseTranslations.remove(sense_translation)
            sense_translation.delete()
        gloss.senses.remove(old_sense)
        old_sense.delete()

    old_translations = [trans.pk for trans in Translation.objects.filter(gloss=gloss)]
    for old_trans in old_translations:
        # remove the old translation objects
        retrieved = Translation.objects.get(pk=old_trans)
        retrieved.delete()

    new_senses_dict = dict()
    number_of_senses_to_create = dict()
    for key in new_senses.keys():
        number_of_senses_to_create[key] = len(new_senses[key])
    num_senses_per_language = [number_of_senses_to_create[key] for key in new_senses.keys()]
    flatten_total = list(set(num_senses_per_language))
    if len(flatten_total) != 1:
        # fail the lists don't match
        return
    num_senses = flatten_total[0]
    new_senses_per_language_dict = dict()
    for i in range(1, num_senses+1):
        sense_i = Sense.objects.create()
        new_senses_dict[i] = sense_i
    for i in range(1, num_senses+1):
        sense_i = new_senses_dict[i]
        new_senses_per_language_dict[i] = dict()
        for dataset_language in dataset_languages:
            language_code = dataset_language.language_code_2char
            sensetranslation = SenseTranslation.objects.create(language=dataset_language)
            sense_i.senseTranslations.add(sensetranslation)
            new_senses_per_language_dict[i][language_code] = sensetranslation
    for dataset_language in dataset_languages:
        language_code = dataset_language.language_code_2char
        if language_code in new_senses:
            for new_sense_i, new_sense in enumerate(new_senses[language_code], 1):
                # sense = new_senses_dict[new_sense_i]
                sense_translations = new_senses_per_language_dict[new_sense_i][language_code]
                new_sense_translations = remove_duplicates_preserve_order(new_sense)
                for inx, kw in enumerate(new_sense_translations, 1):
                    # this is a new sense so it has no translations yet
                    # the combination with gloss, language, orderIndex does not exist yet
                    # the index is the order the keyword was entered by the user
                    if not kw:
                        continue
                    keyword = Keyword.objects.get_or_create(text=kw)[0]
                    translation = Translation(translation=keyword,
                                              language=dataset_language,
                                              gloss=gloss,
                                              orderIndex=new_sense_i,
                                              index=inx)
                    try:
                        translation.save()
                        sense_translations.translations.add(translation)
                    except (TransactionManagementError, IntegrityError):
                        print('constraint violation: ', inx, kw)
                        continue
    for i in range(1, num_senses+1):
        sense_i = new_senses_dict[i]
        gloss.senses.add(sense_i)

    gloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    gloss.save()
    

def update_semantic_field(gloss, new_values, language_code):
    new_semanticfields_to_save = []

    activate(language_code)

    new_human_value_list = [v.strip() for v in new_values.split(',')]

    for value in new_human_value_list:
        field_value = SemanticField.objects.get(name__iexact=value)
        new_semanticfields_to_save.append(field_value)

    gloss.semField.clear()
    for sf in new_semanticfields_to_save:
        gloss.semField.add(sf)
    gloss.save()


def update_derivation_history_field(gloss, new_values, language_code):
    new_derivationhistory_to_save = []

    activate(language_code)

    new_human_value_list = [v.strip() for v in new_values.split(',')]

    for value in new_human_value_list:
        field_value = DerivationHistory.objects.get(name__iexact=value)
        new_derivationhistory_to_save.append(field_value)

    gloss.derivHist.clear()
    for dh in new_derivationhistory_to_save:
        gloss.derivHist.add(dh)
    gloss.save()


def type_check_multiselect(category, new_values, language_code):
    activate(language_code)

    if category not in CATEGORY_MODELS_MAPPING.keys():
        return True

    multiselect_model = CATEGORY_MODELS_MAPPING[category]

    new_human_value_list = [v.strip() for v in new_values.split(',')]

    for value in new_human_value_list:
        try:
            field_value = multiselect_model.objects.get(name__iexact=value)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            return False
    return True


def detect_type_related_problems_for_gloss_update(gloss, changes, dataset, language_code):

    language_fields = internal_language_fields(dataset, language_code)
    errors = dict()
    # in the following loop, field is either a language field as described above
    # or a field of model Gloss, not a string
    for field, (original_value, new_value) in changes.items():
        if not new_value:
            continue
        if field in language_fields:
            continue
        if isinstance(field, FieldChoiceForeignKey):
            field_choice_category = field.field_choice_category
            try:
                fieldchoice = FieldChoice.objects.get(field=field_choice_category, name__iexact=new_value)
                continue
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                normalised_choice = normalize_field_choice(new_value)
                try:
                    fieldchoice = FieldChoice.objects.get(field=field_choice_category, name__iexact=normalised_choice)
                    continue
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    errors[field.verbose_name.title()] = gettext('Incorrect value')
                    continue
        if isinstance(field, models.ForeignKey) and field.related_model == Handshape:
            try:
                handshape = Handshape.objects.get(name__iexact=new_value)
                continue
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                errors[field.verbose_name.title()] = gettext('Incorrect value')
                continue
        if field.__class__.__name__ == 'BooleanField':
            if field.name in ['weakdrop', 'weakprop']:
                if new_value not in ['True', 'False', 'None']:
                    errors[field.verbose_name.title()] = gettext('Incorrect value')
            else:
                if new_value not in ['True', 'False']:
                    errors[field.verbose_name.title()] = gettext('Incorrect value')
        elif field.name == 'semField':
            type_check = type_check_multiselect('SemField', new_value, language_code)
            if not type_check:
                errors[field.verbose_name.title()] = gettext('Incorrect value')
        elif field.name == 'derivHist':
            type_check = type_check_multiselect('derivHist', new_value, language_code)
            if not type_check:
                errors[field.verbose_name.title()] = gettext('Incorrect value')
    return errors


def check_constraints_on_gloss_language_fields(gloss, language_code, value_dict):
    activate(language_code)
    errors = []

    dataset = gloss.lemma.dataset
    lemmaidglosstranslations = {}
    for language in dataset.translation_languages.all():
        lemma_key = 'lemma_id_gloss_' + language.language_code_2char
        if lemma_key in value_dict.keys():
            lemmaidglosstranslations[language] = value_dict[lemma_key][1]

    if lemmaidglosstranslations:
        # the lemma translations are being updated
        lemma_group_glossset = Gloss.objects.filter(lemma=gloss.lemma)
        if lemma_group_glossset.count() > 1:
            more_than_one_gloss_in_lemma_group = gettext("More than one gloss in lemma group.")
            errors.append(more_than_one_gloss_in_lemma_group)

    if errors:
        return errors

    annotationidglosstranslations = {}
    for language in dataset.translation_languages.all():
        annotation_key = 'annotation_id_gloss_' + language.language_code_2char
        if annotation_key in value_dict.keys():
            annotationidglosstranslations[language] = value_dict[annotation_key][1]

    # check lemma translations
    lemmas_per_language_translation = dict()
    for language, lemmaidglosstranslation_text in lemmaidglosstranslations.items():
        lemmatranslation_for_this_text_language = LemmaIdglossTranslation.objects.filter(
            lemma__dataset=dataset, language=language, text__iexact=lemmaidglosstranslation_text)
        lemmas_per_language_translation[language] = lemmatranslation_for_this_text_language

    existing_lemmas = []
    for language, lemmas in lemmas_per_language_translation.items():
        if lemmas.count():
            e5 = gettext("Lemma ID Gloss") + " (" + language.name + ") " + gettext("already exists.")
            errors.append(e5)
            if lemmas.first().lemma.pk not in existing_lemmas:
                existing_lemmas.append(lemmas.first().lemma.pk)
    if len(existing_lemmas) > 1:
        e6 = gettext("Lemma translations refer to different already existing lemmas.")
        errors.append(e6)

    # check annotation translations
    annotations_per_language_translation = dict()
    for language, annotationidglosstranslation_text in annotationidglosstranslations.items():
        annotationtranslation_for_this_text_language = AnnotationIdglossTranslation.objects.filter(
            gloss__lemma__dataset=dataset, language=language, text__iexact=annotationidglosstranslation_text)
        annotations_per_language_translation[language] = annotationtranslation_for_this_text_language

    existing_glosses = []
    for language, annotations in annotations_per_language_translation.items():
        if annotations.count():
            this_annotation = annotations.first()
            if this_annotation.id not in existing_glosses and this_annotation.id != gloss.id:
                existing_glosses.append(this_annotation.id)
                e7 = gettext('Annotation ID Gloss') + " (" + language.name + ') ' + gettext(
                    'already exists.')
                errors.append(e7)
    if len(existing_glosses) > 1:
        e6 = gettext("Annotation translations refer to different already existing glosses.")
        errors.append(e6)

    return errors


def update_language_field(gloss, language_field, new_value):
    if language_field.startswith('lemma_id_gloss_'):
        language_code_2char = language_field[-2:]
        language = Language.objects.filter(language_code_2char=language_code_2char).first()
        try:
            lemma_idgloss_translation = LemmaIdglossTranslation.objects.get(lemma=gloss.lemma, language=language)
        except ObjectDoesNotExist:
            # create an empty annotation for this gloss and language
            lemma_idgloss_translation = LemmaIdglossTranslation(lemma=gloss.lemma, language=language)

        try:
            lemma_idgloss_translation.text = new_value
            lemma_idgloss_translation.save()
        except (DatabaseError, ValidationError):
            pass
    elif language_field.startswith('annotation_id_gloss_'):
        language_code_2char = language_field[-2:]
        language = Language.objects.filter(language_code_2char=language_code_2char).first()
        try:
            annotation_idgloss_translation = AnnotationIdglossTranslation.objects.get(gloss=gloss, language=language)
        except ObjectDoesNotExist:
            # create an empty annotation for this gloss and language
            annotation_idgloss_translation = AnnotationIdglossTranslation(gloss=gloss, language=language)

        try:
            annotation_idgloss_translation.text = new_value
            annotation_idgloss_translation.save()
        except (DatabaseError, ValidationError):
            pass
    gloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    gloss.save()


def gloss_update_do_changes(user, gloss, changes, language_code):
    dataset = gloss.lemma.dataset
    language_fields = internal_language_fields(dataset, language_code)
    changes_done = []
    activate(language_code)
    with atomic():
        for field, (original_value, new_value) in changes.items():
            if field in language_fields:
                update_language_field(gloss, field, new_value)
                changes_done.append((field, original_value, new_value))
            elif isinstance(field, FieldChoiceForeignKey):
                field_choice_category = field.field_choice_category
                normalised_choice = normalize_field_choice(new_value)
                fieldchoice = FieldChoice.objects.get(field=field_choice_category, name__iexact=normalised_choice)
                setattr(gloss, field.name, fieldchoice)
                changes_done.append((field.name, original_value, new_value))
            elif field.__class__.__name__ == 'BooleanField':
                # the new value is a string, do not use a coercion because we want
                # to store None as a value
                if new_value in ['true', 'True', 'TRUE']:
                    boolean_value = True
                elif new_value in ['false', 'False', 'FALSE']:
                    boolean_value = False
                elif new_value == 'None' or new_value == 'Neutral':
                    boolean_value = None
                else:
                    boolean_value = False
                setattr(gloss, field.name, boolean_value)
                changes_done.append((field.name, original_value, new_value))
            elif isinstance(field, models.ForeignKey) and field.related_model == Handshape:
                handshape = Handshape.objects.get(name__iexact=new_value)
                setattr(gloss, field.name, handshape)
                changes_done.append((field.name, original_value, new_value))
            elif field.name in ["senses"]:
                original_senses = collect_revision_history_for_senses(gloss)
                update_senses(gloss, new_value)
                new_senses = collect_revision_history_for_senses(gloss)
                changes_done.append((field, original_senses, new_senses))
            elif field.name == 'semField':
                update_semantic_field(gloss, new_value, language_code)
                changes_done.append((field.name, original_value, new_value))
            elif field.name == 'derivHist':
                update_derivation_history_field(gloss, new_value, language_code)
                changes_done.append((field.name, original_value, new_value))
            else:
                # text field
                setattr(gloss, field.name, new_value)
                changes_done.append((field.name, original_value, new_value))
        gloss.save()
        for field, original_human_value, glossrevision_newvalue in changes_done:
            revision = GlossRevision(old_value=original_human_value,
                                     new_value=glossrevision_newvalue,
                                     field_name=field,
                                     gloss=gloss,
                                     user=user,
                                     time=DT.datetime.now(tz=get_current_timezone()))
            revision.save()


def get_original_senses_value(gloss):
    senses_dict = dict()
    for language in gloss.dataset.translation_languages.all():
        senses_dict[language.language_code_2char] = []
    for sense in gloss.senses.all():
        for language in gloss.dataset.translation_languages.all():
            if sense.senseTranslations.filter(language=language).exists():
                sensetranslation = sense.senseTranslations.get(language=language)
                translations = sensetranslation.translations.all().order_by('index')
                if translations:
                    keywords_list = [str(trans.translation.text) for trans in translations if
                                     trans.translation.text != '']
                    if keywords_list:
                        senses_dict[language.language_code_2char].append(keywords_list)
    return senses_dict


def gloss_pre_update(gloss, input_fields_dict, language_code):

    # this returns a dictionary mapping internal Gloss fields to tuples of original and new values
    # for fields of Gloss, this is the internal model field
    # for language fields, which are relations, this is an encoding of the field used in many interfaces
    # of the templates and the methods
    dataset = gloss.lemma.dataset
    language_fields, gloss_fields = names_of_update_gloss_fields(dataset, language_code)
    human_readable_to_internal, human_readable_to_json = update_gloss_columns_to_value_dict_keys(dataset, language_code)
    # initial value of fields is put in combined_fields variable
    combined_fields = gloss_fields
    for language_field in language_fields:
        package_gloss_language_field = human_readable_to_json[language_field]
        combined_fields.append(package_gloss_language_field)
    # retrieve what the current values for the fields, using the same string representation as package uses
    gloss_package_data_dict = gloss.get_fields_dict(combined_fields, language_code)
    fields_to_update = dict()
    for human_readable_field, new_field_value in input_fields_dict.items():
        if not new_field_value:
            continue
        if human_readable_field in language_fields:
            package_gloss_language_field = human_readable_to_json[human_readable_field]
            original_value = gloss_package_data_dict[package_gloss_language_field]
            if original_value == new_field_value:
                continue
            gloss_field = human_readable_to_internal[human_readable_field]
            fields_to_update[gloss_field] = (original_value, new_field_value)
            continue
        if human_readable_field in ["Senses", "Betekenissen"]:
            original_value = get_original_senses_value(gloss)
            new_senses = new_field_value
            if isinstance(new_senses, str):
                new_senses, errors = convert_string_to_dict_of_list_of_lists(new_field_value)
                if errors:
                    # already checked at a previous step
                    continue
            if DEBUG_API:
                print('gloss_pre_update: ', human_readable_field, original_value, new_senses)
            if original_value != new_senses:
                internal_field = Gloss.get_field('senses')
                fields_to_update[internal_field] = (original_value, new_senses)
            continue
        if human_readable_field not in human_readable_to_internal.keys():
            if DEBUG_API:
                print('gloss_pre_update: json field not found in Gloss fields: ', human_readable_field)
            continue
        internal_field = human_readable_to_internal[human_readable_field]
        original_internal_value = getattr(gloss, internal_field.name)
        if original_internal_value is None and internal_field.name in ['weakdrop', 'weakprop']:
            original_value = 'Neutral'
        elif isinstance(original_internal_value, bool):
            original_value = str(original_internal_value)
        elif isinstance(internal_field, FieldChoiceForeignKey):
            original_value = original_internal_value.name if original_internal_value else '-'
        elif internal_field.name in ['domhndsh', 'subhndsh',
                                     'semField', 'derivHist', 'dialect', 'signlanguage']:
            display_method = 'get_'+internal_field.name+'_display'
            original_value = getattr(gloss, display_method)()
        else:
            # value is a string
            original_value = original_internal_value
        if new_field_value == original_value:
            continue
        if internal_field.__class__.__name__ == 'BooleanField':
            # normalise if this is a Boolean and compare again
            normalised_new_boolean = normalize_boolean(internal_field, new_field_value, original_value)
            if original_value == normalised_new_boolean:
                continue
            fields_to_update[internal_field] = (original_value, normalised_new_boolean)
        else:
            fields_to_update[internal_field] = (original_value, new_field_value)
    # return the dictionary of input fields that differ from stored values
    return fields_to_update


@csrf_exempt
@put_api_user_in_request
def api_update_gloss(request, datasetid, glossid, language_code='en'):

    interface_language_code = retrieve_language_code_from_header(language_code,
                                                                 request.headers.get('Accept-Language', ''),
                                                                 request.META.get('HTTP_ACCEPT_LANGUAGE', None))
    activate(interface_language_code)

    results = dict()

    results['glossid'] = glossid

    errors = dict()

    try:
        dataset_id = int(datasetid)
    except TypeError:
        errors[gettext("Dataset")] = gettext("Dataset ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No permission to change dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    gloss = Gloss.objects.filter(id=gloss_id, archived=False).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No permission to change glosses.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    value_dict = get_gloss_update_human_readable_value_dict(request)
    if DEBUG_API:
        print('api_update_gloss ', glossid, ' input value_dict: ', value_dict)
    errors = check_fields_can_be_updated(gloss, value_dict, dataset, interface_language_code)
    if errors:
        # "Field name not found in fields that can be updated."
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(errors, status=400)

    fields_to_update = gloss_pre_update(gloss, value_dict, interface_language_code)
    errors = detect_type_related_problems_for_gloss_update(gloss, fields_to_update, dataset, interface_language_code)
    if errors:
        # "New value has wrong type."
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    errors = check_constraints_on_gloss_language_fields(gloss, interface_language_code, fields_to_update)
    if errors:
        # "Constraint violation on language fields."
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    if DEBUG_API:
        # now we are ready to do the update, save the intended update fields to the log
        print('api_update_gloss ', glossid, ' fields_to_update: ', fields_to_update)

    try:
        gloss_update_do_changes(request.user, gloss, fields_to_update, interface_language_code)
    except (TransactionManagementError, ValueError, IntegrityError):
        errors = dict()
        errors[gettext('Exception')] = gettext("Transaction management error.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    results['errors'] = {}
    results['updatestatus'] = "Gloss successfully updated."

    return JsonResponse(results, status=201)


def check_confirmed(value_dict):

    errors = dict()
    for field in value_dict.keys():
        if field not in ['confirmed', 'Confirmed'] or value_dict[field] not in ['true', 'True', 'TRUE']:
            errors[field] = _("Gloss operation not confirmed")
    return errors


def gloss_archival_delete(user, gloss, annotation):

    gloss.archived = True
    gloss.save(update_fields=['archived'])

    revision = GlossRevision(old_value=annotation,
                             new_value=annotation,
                             field_name='archived',
                             gloss=gloss,
                             user=user,
                             time=DT.datetime.now(tz=get_current_timezone()))
    revision.save()


def gloss_archival_restore(user, gloss, annotation):

    gloss.archived = False
    gloss.save(update_fields=['archived'])

    revision = GlossRevision(old_value=annotation,
                             new_value=annotation,
                             field_name='restored',
                             gloss=gloss,
                             user=user,
                             time=DT.datetime.now(tz=get_current_timezone()))
    revision.save()


@csrf_exempt
@put_api_user_in_request
def api_delete_gloss(request, datasetid, glossid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    results['glossid'] = glossid

    errors = dict()

    try:
        dataset_id = int(datasetid)
    except TypeError:
        errors[gettext("Dataset")] = gettext("Dataset ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No permission to change dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    gloss = Gloss.objects.filter(id=gloss_id, archived=False).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No permission to change glosses.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    value_dict = get_gloss_update_human_readable_value_dict(request)
    errors = check_confirmed(value_dict)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    annotation = get_default_annotationidglosstranslation(gloss)
    gloss_archival_delete(request.user, gloss, annotation)

    results['errors'] = {}
    results['updatestatus'] = "Success"

    return JsonResponse(results, safe=False, status=200)


@csrf_exempt
@put_api_user_in_request
def api_restore_gloss(request, datasetid, glossid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    results['glossid'] = glossid

    errors = dict()

    try:
        dataset_id = int(datasetid)
    except TypeError:
        errors[gettext("Dataset")] = gettext("Dataset ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No permission to change dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    gloss = Gloss.objects.filter(id=gloss_id, archived=True).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found in archive.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, status=400)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No permission to change glosses.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    value_dict = get_gloss_update_human_readable_value_dict(request)
    errors = check_confirmed(value_dict)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    annotation = get_default_annotationidglosstranslation(gloss)
    gloss_archival_restore(request.user, gloss, annotation)

    results['errors'] = {}
    results['updatestatus'] = "Success"

    return JsonResponse(results, safe=False, status=200)


def gloss_update_nmevideo(gloss, update_fields_dict, nmevideo, language_code, create=False):

    dataset = gloss.lemma.dataset

    activate(language_code)
    offset = gettext("Index")
    perspective = gettext("Perspective")
    dataset_languages = dataset.translation_languages.all()
    description_fields = [gettext("Description") + " (%s)" % language.name
                          for language in dataset_languages] + [offset, perspective]
    description_field_to_internal = dict()
    json_field_to_human_readable = dict()

    for language in dataset_languages:
        human_readable = gettext("Description") + " (%s)" % language.name
        description_field_to_internal[human_readable] = ('description_' + language.language_code_2char)
        description_api_field_name = gettext("Description") + ": %s" % language.name
        json_field_to_human_readable[description_api_field_name] = human_readable

    description_field_to_internal[offset] = 'offset'
    json_field_to_human_readable[offset] = offset

    description_field_to_internal[perspective] = 'perspective'
    json_field_to_human_readable[perspective] = perspective

    nme_videos_key = gettext("NME Videos")
    nme_videos_field = [nme_videos_key]
    gloss_data_dict = dict()

    if not create:
        gloss_data_nme_videos = gloss.get_fields_dict(nme_videos_field, language_code)
        gloss_data_nme_videos_list = gloss_data_nme_videos[nme_videos_key]

        for nme_dict in gloss_data_nme_videos_list:
            if nme_dict['ID'] != str(nmevideo.id):
                continue

            for gloss_json_field in nme_dict.keys():
                if gloss_json_field not in json_field_to_human_readable.keys():
                    continue

                human_readable = json_field_to_human_readable[gloss_json_field]
                gloss_data_dict[human_readable] = nme_dict[gloss_json_field]
    else:
        gloss_data_dict['ID'] = str(nmevideo.id)
        gloss_data_dict[offset] = str(nmevideo.offset)

    fields_to_update = dict()
    for human_readable_field, new_field_value in update_fields_dict.items():
        if not new_field_value:
            continue

        if human_readable_field not in gloss_data_dict.keys():
            if human_readable_field not in description_fields:
                continue

            internal_field = description_field_to_internal[human_readable_field]
            fields_to_update[internal_field] = '', new_field_value
            continue

        if human_readable_field in description_fields:
            original_value = gloss_data_dict[human_readable_field]
            internal_field = description_field_to_internal[human_readable_field]

            if internal_field in ['offset','perspective'] and gloss_data_dict[human_readable_field] == new_field_value:
                continue

            fields_to_update[internal_field] = original_value, new_field_value
    
    return fields_to_update

def gloss_nmevideo_do_changes(user, gloss, nmevideo, changes, language_code, create=True):
    changes_done = []
    activate(language_code)
    original_filename = '' if create else os.path.basename(nmevideo.videofile.name)

    for field, (original_value, new_value) in changes.items():

        if field.startswith('description_'):
            language_code_2char = field[len('description_'):]
            language = Language.objects.filter(language_code_2char=language_code_2char).first()
            value = new_value.strip()
            description, _ = GlossVideoDescription.objects.get_or_create(nmevideo=nmevideo, language=language)
            description.text = value
            description.save()
            changes_done.append((field, original_value, value))

        elif field == 'offset':
            # this changes the filename and moves the file
            nmevideo.offset = int(new_value)
            nmevideo.save(update_fields=['offset']) 

        elif field == 'perspective':
            nmevideo.perspective = new_value
            nmevideo.save(update_fields=['perspective'])

    operation = 'nmevideo_create' if create else 'nmevideo_update'
    filename = os.path.basename(nmevideo.videofile.name)
    revision = GlossRevision(old_value=original_filename,
                             new_value=filename,
                             field_name=operation,
                             gloss=gloss,
                             user=user,
                             time=DT.datetime.now(tz=get_current_timezone()))
    revision.save()

    for field, original_human_value, glossrevision_newvalue in changes_done:
        revision = GlossRevision(old_value=original_human_value,
                                 new_value=glossrevision_newvalue,
                                 field_name=field,
                                 gloss=gloss,
                                 user=user,
                                 time=DT.datetime.now(tz=get_current_timezone()))
        revision.save()


@csrf_exempt
@put_api_user_in_request
def api_update_gloss_nmevideo(request, datasetid, glossid, videoid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    results['glossid'] = glossid

    errors = dict()

    try:
        dataset_id = int(datasetid)
    except TypeError:
        errors[gettext("Dataset")] = gettext("Dataset ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No permission to change dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    gloss = Gloss.objects.filter(id=gloss_id, archived=False).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No permission to change glosses.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    try:
        video_id = int(videoid)
    except TypeError:
        # the videoid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("NME Video ID")] = gettext("Video ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    nmevideo = GlossVideoNME.objects.filter(id=video_id, gloss=gloss).first()

    if not nmevideo:
        errors[gettext("NME Video ID")] = gettext("NME Video not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    # pass create=False: ignore the File field if present, this is an update
    # we already have an nme video object
    value_dict = get_gloss_nmevideo_value_dict(request, gloss, interface_language_code, create=False)
    fields_to_update = gloss_update_nmevideo(gloss, value_dict, nmevideo, interface_language_code)
    gloss_nmevideo_do_changes(request.user, gloss, nmevideo, fields_to_update, interface_language_code, create=False)

    results['errors'] = errors
    results['updatestatus'] = "Success"

    return JsonResponse(results, safe=False, status=200)


def get_gloss_nmevideo_value_dict(request, gloss, language_code, create=True):

    value_dict = dict()

    index_key = gettext("Index")
    if index_key in request.POST.keys():
        index_str = request.POST.get(index_key)
        index = int(index_str)
    else:
        index = 1
    value_dict[index_key] = index

    if create:
        #Figure out the perspective from the file label
        for request_key in request.FILES.keys():
            for perspective, _ in NME_PERSPECTIVE_CHOICES:
                if request_key.lower() not in PERSPECTIVE_VIDEO_LABELS[perspective]:
                    continue

                value_dict['File'] = gloss.add_nme_video(request.user, request.FILES.get(request_key, None), index, 'False', perspective=perspective)
                value_dict['perspective'] = perspective
                break           
    else:
        perspective_key = gettext("Perspective")
        if perspective_key in request.POST.keys():
            value_dict[perspective_key] = request.POST.get(perspective_key)

    dataset = gloss.lemma.dataset
    activate(language_code)
    dataset_languages = dataset.translation_languages.all()
    description_fields = [gettext("Description") + " (%s)" % language.name
                          for language in dataset_languages]

    for field in description_fields:
        value = request.POST.get(field, '')
        value_dict[field] = value.strip()

    return value_dict


@csrf_exempt
@put_api_user_in_request
def api_create_gloss_nmevideo(request, datasetid, glossid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    results['glossid'] = glossid
    results['videoid'] = ''

    errors = dict()

    try:
        dataset_id = int(datasetid)
    except TypeError:
        errors[gettext("Dataset")] = gettext("Dataset ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No permission to change dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    gloss = Gloss.objects.filter(id=gloss_id, archived=False).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No permission to change glosses.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    value_dict = get_gloss_nmevideo_value_dict(request, gloss, interface_language_code)

    if 'File' not in value_dict.keys():
        errors['File'] = gettext("Missing video file, using label center, left or right.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    new_nme_video = value_dict['File']
    fields_to_update = gloss_update_nmevideo(gloss, value_dict, new_nme_video, interface_language_code, create=True)
    gloss_nmevideo_do_changes(request.user, gloss, new_nme_video, fields_to_update, interface_language_code)

    results['errors'] = errors
    results['updatestatus'] = "Success"
    results['videoid'] = str(new_nme_video.id)

    return JsonResponse(results, safe=False, status=200)


@csrf_exempt
@put_api_user_in_request
def api_delete_gloss_nmevideo(request, datasetid, glossid, videoid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    results['glossid'] = glossid

    errors = dict()

    try:
        dataset_id = int(datasetid)
    except TypeError:
        errors[gettext("Dataset")] = gettext("Dataset ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No permission to change dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    gloss = Gloss.objects.filter(id=gloss_id, archived=False).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No permission to change glosses.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    try:
        video_id = int(videoid)
    except TypeError:
        # the videoid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("NME Video ID")] = gettext("Video ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    nmevideo = GlossVideoNME.objects.filter(id=video_id, gloss=gloss).first()

    if not nmevideo:
        errors[gettext("NME Video ID")] = gettext("NME Video not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False, status=400)

    original_nme_file = os.path.basename(nmevideo.videofile.name)
    nmevideo.delete()

    add_gloss_update_to_revision_history(request.user, gloss, 'nmevideo_delete', original_nme_file, '')

    results['errors'] = errors
    results['updatestatus'] = "Success"

    return JsonResponse(results, safe=False, status=200)


@csrf_exempt
@put_api_user_in_request
def api_create_annotated_sentence(request, datasetid):

    if not request.method == 'POST': 
        return JsonResponse({"error": "POST method required."}, status=400)

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return JsonResponse({"error": gettext("Dataset ID must be a number.")}, safe=False, status=400)

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        return JsonResponse({"error": gettext("Dataset with given id does not exist.")}, status=400)

    dataset_acronym = request.POST.get('Dataset')
    dataset_by_acronym = Dataset.objects.filter(acronym=dataset_acronym).first()
    if not dataset_by_acronym:
        return JsonResponse({"error": gettext("Dataset with given acronym does not exist.")}, status=400)

    if dataset.acronym != dataset_by_acronym.acronym:
        return JsonResponse({"error": gettext("Dataset acronym does not match.")}, status=400)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        return JsonResponse({"error": gettext("No permission to change dataset.")}, status=400)

    if not request.user.has_perm('dictionary.change_gloss'):
        return JsonResponse({"error": gettext("No permission to change glosses.")}, status=400)
    
    source = request.POST.get('Source')
    url = request.POST.get('Url')
    video_file = request.FILES.get('Video_file')
    eaf_file = request.FILES.get('Eaf_file')

    if eaf_file.name.split('.')[-1] != 'eaf':
        return JsonResponse({"error": gettext("Eaf file must be in .eaf format.")}, status=400)
    if video_file.name.split('.')[-1] not in ['mp4', 'webm', 'mov']:
        return JsonResponse({"error": gettext("Video file must be in .mp4, .webm, or .mov format.")}, status=400)

    # Process the files and fields as needed
    if not (video_file and eaf_file):
        return JsonResponse({"error": gettext("Missing a required field.")}, status=400)

    # Create a temporary file
    with NamedTemporaryFile(delete=False, suffix='.eaf') as tmp_eaf_file:
        for chunk in eaf_file.chunks():
            tmp_eaf_file.write(chunk)
    tmp_eaf_file_path = tmp_eaf_file.name

    # Read the eaf file
    eaf = Eaf(tmp_eaf_file_path)
    os.remove(tmp_eaf_file_path)

    # Create an AnnotatedSentence object
    annotated_sentence = AnnotatedSentence.objects.create()

    # Get glosses and sentences from the eaf file
    annotations, labels_not_found, sentence_dict = get_glosses_from_eaf(eaf, dataset.acronym)
    if len(annotations) == 0:
        return JsonResponse({"error": gettext("No annotations found in EAF file.")}, status=400)

    # pick a random gloss from dataset, this is only used to -in add_annotations- retrieve the right dataset
    gloss = Gloss.objects.filter(lemma__dataset=dataset).first()
    annotated_sentence.add_annotations(annotations, gloss)

    if sentence_dict != {}:
        annotated_sentence.add_translations(sentence_dict)
    
    source_obj = AnnotatedSentenceSource.objects.filter(name=source).first()
    if source_obj is None and source != '':
        return JsonResponse({"error": gettext("Annotated sentence source received but not found.")}, status=400)
    
    # Add the video to the AnnotatedSentence object
    annotated_video = annotated_sentence.add_video(request.user, video_file, eaf_file, source_obj, url)

    if not annotated_video:
        return JsonResponse({"error": gettext("Annotated video not found.")}, status=400)

    if len(labels_not_found) > 0:
        return JsonResponse({"success": "Sentence was added successfully. However, some labels were not found in Signbank: " + ', '.join(labels_not_found)}, status=201)
    return JsonResponse({"success": gettext("Sentence was added successfully.")}, status=201)


@csrf_exempt
@put_api_user_in_request
def api_update_annotated_sentence(request, datasetid, annotatedsentenceid):

    post_data = json.loads(request.body.decode('utf-8'))

    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return JsonResponse({"error": gettext("Dataset ID must be a number.")}, safe=False, status=400)

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        return JsonResponse({"error": gettext("Dataset with given id does not exist")}, status=400)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        return JsonResponse({"error": gettext("No permission to change dataset.")}, status=401)

    annotated_sentence = AnnotatedSentence.objects.filter(
        id=annotatedsentenceid,
        annotated_glosses__gloss__lemma__dataset=dataset
    ).first()
    if not annotated_sentence:
        return JsonResponse({"error": gettext("Annotated sentence not found.")}, status=404)
    
    dataset_languages = dataset.translation_languages.all()
    translations, contexts = dict(), dict()
    for language in dataset_languages:
        translations[language.language_code_3char] = post_data[gettext("Translation") + " (" + language.name + ")"]
        contexts[language.language_code_3char] = post_data[gettext("Context") + " (" + language.name + ")"]

    if any(translations.values()):
        AnnotatedSentenceTranslation.objects.filter(annotatedsentence=annotated_sentence).delete()
        annotated_sentence.add_translations(translations)
    if any(contexts.values()):  
        AnnotatedSentenceContext.objects.filter(annotatedsentence=annotated_sentence).delete()
        annotated_sentence.add_contexts(contexts)

    source = post_data['Source']
    url = post_data['Url']

    source_obj = AnnotatedSentenceSource.objects.filter(name=source).first()
    if source_obj is None and source != '':
        return JsonResponse({"error": gettext("Annotated sentence source received but not found.")}, status=400)
    
    annotated_sentence_video = annotated_sentence.annotatedvideo
    if not annotated_sentence_video:
        return JsonResponse({"error": gettext("Annotated video not found.")}, status=404)
    else:
        annotated_sentence_video.source = source_obj
        annotated_sentence_video.url = url

    annotated_sentence_video.save()

    representative_glosses_ids = post_data['Representative glosses']
    representative_glosses = AnnotatedGloss.objects.filter(gloss__id__in=representative_glosses_ids, annotatedsentence=annotated_sentence)
    if len(representative_glosses) == 0:
        return JsonResponse({"error": gettext("No valid representative gloss id's given.")}, status=404)
    for annotated_gloss in annotated_sentence.annotated_glosses.all():
        annotated_gloss.isRepresentative = False
        annotated_gloss.save()
    for representative_gloss in representative_glosses:
        representative_gloss.isRepresentative = True
        representative_gloss.save()

    return JsonResponse({"success": gettext("Sentence was updated successfully.")}, status=200)


@csrf_exempt
@put_api_user_in_request
def api_delete_annotated_sentence(request, datasetid, annotatedsentenceid):

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return JsonResponse({"error": gettext("Dataset ID must be a number.")}, safe=False, status=400)

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        return JsonResponse({"error": "Dataset with given id does not exist."}, status=400)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        return JsonResponse({"error": gettext("No permission to change dataset.")}, status=401)

    annotated_sentence = AnnotatedSentence.objects.get(id=annotatedsentenceid)
    if not annotated_sentence:
        return JsonResponse({"error": gettext("Annotated sentence not found.")}, status=404)
    
    if annotated_sentence.get_dataset() != dataset:
        return JsonResponse({"error": gettext("Annotated sentence not found in dataset.")}, status=404)
    
    annotated_videos = AnnotatedVideo.objects.filter(annotatedsentence=annotated_sentence)
    for annotated_video in annotated_videos:
        annotated_video.delete_files()
        annotated_video.delete()
    annotated_sentence.delete()

    return JsonResponse({"success": gettext("Sentence was deleted successfully.")}, status=200)
