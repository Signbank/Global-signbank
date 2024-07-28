
from django.utils.translation import gettext_lazy as _, activate, gettext
from signbank.dictionary.models import *
from signbank.tools import get_default_annotationidglosstranslation
from django.db.transaction import atomic
from django.utils.timezone import get_current_timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from guardian.shortcuts import get_objects_for_user
from signbank.tools import get_interface_language_and_default_language_codes
from signbank.csv_interface import normalize_field_choice
from signbank.api_token import put_api_user_in_request
import datetime as DT

import ast


def api_update_gloss_fields(dataset, language_code='en'):
    activate(language_code)

    dataset_languages = dataset.translation_languages.all()
    annotationidglosstranslation_fields = [gettext("Annotation ID Gloss") + " (" + language.name + ")"
                                           for language in dataset_languages]
    lemmaidglosstranslation_fields = [gettext("Lemma ID Gloss") + " (" + language.name + ")"
                                      for language in dataset_languages]

    language_fields = annotationidglosstranslation_fields + lemmaidglosstranslation_fields

    api_fields_2024 = []
    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv', 'senses']
    gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

    # TO DO
    extra_columns = ['Sign Languages', 'Dialects',
                     'Relations to other signs', 'Relations to foreign signs', 'Tags', 'Notes']

    for field in gloss_fields:
        api_fields_2024.append(field.verbose_name.title())

    return language_fields, api_fields_2024


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
    Called from gloss_update
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

    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv', 'senses']
    gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

    for field in gloss_fields:
        human_readable_to_internal[field.verbose_name.title()] = field

    return human_readable_to_internal, human_readable_to_json


@csrf_exempt
def get_gloss_update_human_readable_value_dict(request):
    post_data = json.loads(request.body.decode('utf-8'))

    value_dict = dict()
    for field in post_data.keys():
        value = post_data.get(field, '')
        value_dict[field] = value.strip()
    return value_dict


def check_fields_can_be_updated(value_dict, dataset, language_code):
    language_fields, api_fields_2024 = api_update_gloss_fields(dataset, language_code)
    errors = dict()
    for field in value_dict.keys():
        if field not in api_fields_2024 and field not in language_fields:
            errors[field] = _("Field update not available")
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
    new_senses, _ = convert_string_to_dict_of_list_of_lists(new_value)

    dataset = gloss.lemma.dataset
    dataset_languages = dataset.translation_languages.all()

    # First remove the senses from the gloss
    old_senses = gloss.senses.all()
    for old_sense in old_senses:
        gloss.senses.remove(old_sense)

        # if this sense is part of another gloss, don't delete it
        other_glosses_for_sense = GlossSense.objects.filter(sense=old_sense).exclude(gloss=gloss).count()
        if not other_glosses_for_sense:
            # If this is this only gloss this sense was in, delete the sense
            for sense_translation in old_sense.senseTranslations.all():
                # iterate over a list because the objects will be removed
                for translation in sense_translation.translations.all():
                    sense_translation.translations.remove(translation)
                    translation.delete()
                old_sense.senseTranslations.remove(sense_translation)
                sense_translation.delete()
            # also remove its examplesentences if they are not in another sense
            example_sentences = old_sense.exampleSentences.all()
            for example_sentence in example_sentences:
                old_sense.exampleSentences.remove(example_sentence)
                if Sense.objects.filter(exampleSentences=example_sentence).count() == 0:
                    example_sentence.delete()
            old_sense.delete()

    # Then add the new senses
    for dataset_language in dataset_languages:
        if dataset_language.language_code_2char in new_senses:
            for new_sense_i, new_sense in enumerate(new_senses[dataset_language.language_code_2char], 1):
                # Make a new sense object or get the existing one
                if gloss.senses.count() < new_sense_i:
                    sense = Sense.objects.create()
                    gloss.senses.add(sense, through_defaults={'order':new_sense_i})
                else:
                    sense = gloss.senses.get(glosssense__order=new_sense_i)

                try:
                    sensetranslation = sense.senseTranslations.get(language=dataset_language)
                except ObjectDoesNotExist:
                    # there should only be one per language
                    sensetranslation = SenseTranslation.objects.create(language=dataset_language)
                    sense.senseTranslations.add(sensetranslation)
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
                    translation.save()
                    sensetranslation.translations.add(translation)
                sensetranslation.save()
                sense.save()
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


def detect_type_related_problems_for_gloss_update(changes, dataset, language_code):

    language_fields = internal_language_fields(dataset, language_code)
    errors = dict()
    for field, (original_value, new_value) in changes.items():
        if not new_value:
            continue
        if field in language_fields:
            continue
        if isinstance(field, FieldChoiceForeignKey):
            field_choice_category = field.field_choice_category
            try:
                fieldchoice = FieldChoice.objects.get(field=field_choice_category, name__iexact=new_value)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                normalised_choice = normalize_field_choice(new_value)
                try:
                    fieldchoice = FieldChoice.objects.get(field=field_choice_category, name__iexact=normalised_choice)
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
        elif isinstance(field, models.ForeignKey) and field.related_model == Handshape:
            try:
                handshape = Handshape.objects.get(name__iexact=new_value)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
        elif field.__class__.__name__ == 'BooleanField':
            if new_value not in ['true', 'True', 'TRUE', 'false', 'False', 'FALSE', 'Neutral', 'None']:
                errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
        elif field.name == 'semField':
            type_check = type_check_multiselect('SemField', new_value, language_code)
            if not type_check:
                errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
        elif field.name == 'derivHist':
            type_check = type_check_multiselect('derivHist', new_value, language_code)
            if not type_check:
                errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
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


@csrf_exempt
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
                if new_value in ['true', 'True', 'TRUE']:
                    new_value = True
                elif new_value in ['false', 'False', 'FALSE']:
                    new_value = False
                elif new_value == 'None' or new_value == 'Neutral':
                    new_value = None
                else:
                    new_value = False
                setattr(gloss, field.name, new_value)
                changes_done.append((field.name, original_value, new_value))
            elif isinstance(field, models.ForeignKey) and field.related_model == Handshape:
                handshape = Handshape.objects.get(name__iexact=new_value)
                setattr(gloss, field.name, handshape)
                changes_done.append((field.name, original_value, new_value))
            elif field.name == 'semField':
                update_semantic_field(gloss, new_value, language_code)
                changes_done.append((field.name, original_value, new_value))
            elif field.name == 'derivHist':
                update_derivation_history_field(gloss, new_value, language_code)
                changes_done.append((field.name, original_value, new_value))
            elif field.name == "senses" and isinstance(field, models.ManyToManyField):
                original_senses = collect_revision_history_for_senses(gloss)
                update_senses(gloss, new_value)
                new_senses = collect_revision_history_for_senses(gloss)
                changes_done.append((field.name, original_senses, new_senses))
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
                                     time=datetime.now(tz=get_current_timezone()))
            revision.save()


def gloss_update(gloss, update_fields_dict, language_code):

    dataset = gloss.lemma.dataset
    language_fields, api_fields_2024 = api_update_gloss_fields(dataset, language_code)
    human_readable_to_internal, human_readable_to_json = update_gloss_columns_to_value_dict_keys(dataset, language_code)

    combined_fields = api_fields_2024
    for language_field in language_fields:
        gloss_dict_language_field = human_readable_to_json[language_field]
        combined_fields.append(gloss_dict_language_field)

    gloss_data_dict = gloss.get_fields_dict(combined_fields, language_code)

    fields_to_update = dict()
    for human_readable_field, new_field_value in update_fields_dict.items():
        if not new_field_value:
            continue
        if human_readable_field in language_fields:
            gloss_language_field = human_readable_to_json[human_readable_field]
            original_value = gloss_data_dict[gloss_language_field]
            gloss_field = human_readable_to_internal[human_readable_field]
            fields_to_update[gloss_field] = (original_value, new_field_value)
            continue
        elif human_readable_field not in gloss_data_dict.keys():
            # new value
            original_value = ''
            gloss_field = human_readable_to_internal[human_readable_field]
            fields_to_update[gloss_field] = (original_value, new_field_value)
            continue
        if human_readable_field in human_readable_to_internal.keys():
            original_value = gloss_data_dict[human_readable_field]
            if original_value in ['False'] and new_field_value in ['', 'False']:
                # treat empty as False
                continue
            if new_field_value == original_value:
                continue
            gloss_field = human_readable_to_internal[human_readable_field]
            fields_to_update[gloss_field] = (original_value, new_field_value)
    return fields_to_update


@csrf_exempt
@put_api_user_in_request
def api_update_gloss(request, datasetid, glossid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    results['glossid'] = glossid

    errors = dict()

    if not request.user.is_authenticated:
        errors[gettext("User")] = gettext("You must be logged in to use this functionality.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No change permission for dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    gloss = Gloss.objects.filter(id=gloss_id, archived=False).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No change gloss permission.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    value_dict = get_gloss_update_human_readable_value_dict(request)
    errors = check_fields_can_be_updated(value_dict, dataset, interface_language_code)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    fields_to_update = gloss_update(gloss, value_dict, interface_language_code)
    errors = detect_type_related_problems_for_gloss_update(fields_to_update, dataset, interface_language_code)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    errors = check_constraints_on_gloss_language_fields(gloss, interface_language_code, fields_to_update)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if 'Senses' in value_dict:
        _, errors = convert_string_to_dict_of_list_of_lists(value_dict['Senses'])
        if errors:
            results['errors'] = [errors]
            results['updatestatus'] = "Failed"
            return JsonResponse(results)

    gloss_update_do_changes(request.user, gloss, fields_to_update, interface_language_code)

    results['errors'] = {}
    results['updatestatus'] = "Success"

    return JsonResponse(results)


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
                             time=datetime.now(tz=get_current_timezone()))
    revision.save()


def gloss_archival_restore(user, gloss, annotation):

    gloss.archived = False
    gloss.save()

    revision = GlossRevision(old_value=annotation,
                             new_value=annotation,
                             field_name='restored',
                             gloss=gloss,
                             user=user,
                             time=datetime.now(tz=get_current_timezone()))
    revision.save()


@csrf_exempt
@put_api_user_in_request
def api_delete_gloss(request, datasetid, glossid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    results['glossid'] = glossid

    errors = dict()

    if not request.user.is_authenticated:
        errors[gettext("User")] = gettext("You must be logged in to use this functionality.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No change permission for dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    gloss = Gloss.objects.filter(id=gloss_id, archived=False).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No change gloss permission.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    value_dict = get_gloss_update_human_readable_value_dict(request)
    errors = check_confirmed(value_dict)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    annotation = get_default_annotationidglosstranslation(gloss)
    gloss_archival_delete(request.user, gloss, annotation)

    results['errors'] = {}
    results['updatestatus'] = "Success"

    return JsonResponse(results)


@csrf_exempt
@put_api_user_in_request
def api_restore_gloss(request, datasetid, glossid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    results['glossid'] = glossid

    errors = dict()

    if not request.user.is_authenticated:
        errors[gettext("User")] = gettext("You must be logged in to use this functionality.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No change permission for dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    gloss = Gloss.objects.filter(id=gloss_id, archived=True).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found in archive.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No change gloss permission.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    value_dict = get_gloss_update_human_readable_value_dict(request)
    errors = check_confirmed(value_dict)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    annotation = get_default_annotationidglosstranslation(gloss)
    gloss_archival_restore(request.user, gloss, annotation)

    results['errors'] = {}
    results['updatestatus'] = "Success"

    return JsonResponse(results)
