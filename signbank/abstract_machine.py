import json

from django.views.decorators.csrf import csrf_exempt

from signbank.dictionary.models import *
from tagging.models import Tag, TaggedItem
from signbank.dictionary.forms import *
from signbank.dictionary.consistency_senses import check_consistency_senses
from django.utils.translation import override, gettext_lazy as _, activate
from signbank.settings.server_specific import LANGUAGES, LEFT_DOUBLE_QUOTE_PATTERNS, RIGHT_DOUBLE_QUOTE_PATTERNS
from signbank.dictionary.update_senses_mapping import add_sense_to_revision_history
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from guardian.shortcuts import get_objects_for_user


def required_fields_create_gloss_columns(dataset):
    dataset_languages = dataset.translation_languages.all()
    lang_attr_name = 'name_' + DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
    annotationidglosstranslation_fields = ["Annotation ID Gloss" + " (" + getattr(language, lang_attr_name) + ")"
                                           for language in dataset_languages]
    lemmaidglosstranslation_fields = ["Lemma ID Gloss" + " (" + getattr(language, lang_attr_name) + ")"
                                      for language in dataset_languages]
    required_columns = ['Dataset'] + lemmaidglosstranslation_fields + annotationidglosstranslation_fields
    return required_columns


def required_fields_create_gloss_value_dict_keys(dataset):
    dataset_languages = dataset.translation_languages.all()
    annotationidglosstranslation_fields = ['annotation_id_gloss_' + getattr(language, 'language_code_2char')
                                           for language in dataset_languages]
    lemmaidglosstranslation_fields = ['lemma_id_gloss_' + getattr(language, 'language_code_2char')
                                      for language in dataset_languages]
    required_columns = ['dataset'] + annotationidglosstranslation_fields + lemmaidglosstranslation_fields
    return required_columns


def create_gloss_columns_to_value_dict_keys(dataset):
    required_columns = dict()
    required_columns['Dataset'] = 'dataset'
    dataset_languages = dataset.translation_languages.all()
    lang_attr_name = 'name_' + DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
    for language in dataset_languages:
        required_columns["Annotation ID Gloss" + " (" + getattr(language, lang_attr_name) + ")"] = (
                'annotation_id_gloss_' + getattr(language, 'language_code_2char'))
        required_columns["Lemma ID Gloss" + " (" + getattr(language, lang_attr_name) + ")"] = (
                'lemma_id_gloss_' + getattr(language, 'language_code_2char'))
    return required_columns


def create_gloss_value_dict_keys_to_columns(dataset):
    required_columns = dict()
    required_columns['dataset'] = 'Dataset'
    dataset_languages = dataset.translation_languages.all()
    lang_attr_name = 'name_' + DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
    for language in dataset_languages:
        required_columns['annotation_id_gloss_'
                         + getattr(language,
                                   'language_code_2char')] = ("Annotation ID Gloss"
                                                              + " (" + getattr(language, lang_attr_name) + ")")
        required_columns['lemma_id_gloss_'
                         + getattr(language,
                                   'language_code_2char')] = ("Lemma ID Gloss"
                                                              + " (" + getattr(language, lang_attr_name) + ")")
    return required_columns


def get_value_dict(request, dataset):
    required_fields = required_fields_create_gloss_value_dict_keys(dataset)
    value_dict = dict()
    for field in required_fields:
        if field in request.POST.keys():
            value = request.POST.get(field, '')
            value_dict[field] = value.strip()
    return value_dict


def get_human_readable_value_dict(request, dataset):
    required_fields = required_fields_create_gloss_columns(dataset)
    value_dict = dict()
    for field in required_fields:
        if field in request.POST.keys():
            value = request.POST.get(field, '')
            value_dict[field] = value.strip()
    return value_dict


def translate_human_readable_value_dict_to_keys(dataset, value_dict):
    translate_value_dict_lookup = create_gloss_columns_to_value_dict_keys(dataset)
    translated_value_dict = dict()
    for field, value in value_dict.items():
        value_dict_key = translate_value_dict_lookup[field]
        translated_value_dict[value_dict_key] = value
    return translated_value_dict


def check_value_dict_create_gloss(request, dataset, value_dict):
    errors = []
    dataset_acronym = value_dict['dataset']

    if not dataset_acronym:
        e1 = 'Dataset is empty.'
        errors.append(e1)
    elif dataset_acronym != dataset.acronym:
        e2 = 'Dataset acronym does not match dataset ' + dataset.acronym + '.'
        errors.append(e2)

    lemmaidglosstranslations = {}
    for language in dataset.translation_languages.all():
        lemma_id_gloss = value_dict['lemma_id_gloss_' + language.language_code_2char]
        if lemma_id_gloss:
            lemmaidglosstranslations[language] = lemma_id_gloss
        else:
            e3 = 'Lemma translation for ' + language.name + ' is empty.'
            errors.append(e3)

    annotationidglosstranslations = {}
    for language in dataset.translation_languages.all():
        annotation_id_gloss = value_dict['annotation_id_gloss_' + language.language_code_2char]
        if annotation_id_gloss:
            annotationidglosstranslations[language] = annotation_id_gloss
        else:
            e4 = "Annotation translation for " + language.name + " is empty."
            errors.append(e4)

    if errors:
        return errors

    # check lemma translations
    lemmas_per_language_translation = dict()
    for language, lemmaidglosstranslation_text in lemmaidglosstranslations.items():
        lemmatranslation_for_this_text_language = LemmaIdglossTranslation.objects.filter(
            lemma__dataset=dataset, language=language, text__exact=lemmaidglosstranslation_text)
        lemmas_per_language_translation[language] = lemmatranslation_for_this_text_language

    existing_lemmas = []
    for language, lemmas in lemmas_per_language_translation.items():
        if lemmas.count():
            e5 = "Lemma translation for " + language.name + " already exists."
            errors.append(e5)
            if lemmas.first().lemma.pk not in existing_lemmas:
                existing_lemmas.append(lemmas.first().lemma.pk)
    if len(existing_lemmas) > 1:
        e6 = "Lemma translations refer to different already existing lemmas."
        errors.append(e6)

    # check annotation translations
    for language, annotationidglosstranslation_text in annotationidglosstranslations.items():
        annotationtranslation_for_this_text_language = AnnotationIdglossTranslation.objects.filter(
            gloss__lemma__dataset=dataset, language=language, text__exact=annotationidglosstranslation_text)

        if annotationtranslation_for_this_text_language.count():
            e7 = ('This annotation already exists for language '
                  + language.name + ': ' + annotationidglosstranslation_text)
            errors.append(e7)

    return errors


def create_gloss(request, dataset, value_dict):
    # assumes all guardian permissions have already been checked
    # the request argument is used to add the creator to the new gloss
    dataset_languages = dataset.translation_languages.all()
    results = dict()
    try:
        with atomic():
            lemma_for_gloss = LemmaIdgloss(dataset=dataset)
            lemma_for_gloss.save()
            for language in dataset_languages:
                lemma_id_gloss_text = value_dict['lemma_id_gloss_' + language.language_code_2char]
                new_lemmaidglosstranslation = LemmaIdglossTranslation(lemma=lemma_for_gloss,
                                                                      language=language, text=lemma_id_gloss_text)
                new_lemmaidglosstranslation.save()

            new_gloss = Gloss()
            new_gloss.lemma = lemma_for_gloss
            # Save the new gloss before updating it
            new_gloss.save()
            new_gloss.creationDate = DT.datetime.now()
            new_gloss.creator.add(request.user)
            new_gloss.save()

            for language in dataset_languages:
                annotationidgloss_text = value_dict['annotation_id_gloss_' + language.language_code_2char]
                annotationidglosstranslation = AnnotationIdglossTranslation()
                annotationidglosstranslation.language = language
                annotationidglosstranslation.gloss = new_gloss
                annotationidglosstranslation.text = annotationidgloss_text
                annotationidglosstranslation.save()
            results['glossid'] = str(new_gloss.pk)
            results['errors'] = []
            results['createstatus'] = "Success"
            return results
    except (DatabaseError, KeyError, TransactionManagementError):
        results['errors'] = ["Error creating new gloss."]
        results['createstatus'] = "Failed"
        results['glossid'] = ""
        return results


def csv_create_gloss(request, datasetid):
    if not request.user.is_authenticated:
        return JsonResponse({})

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset or not request.user.is_authenticated:
        return JsonResponse({})

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        return JsonResponse({})

    if not request.user.has_perm('dictionary.change_gloss'):
        return JsonResponse({})

    value_dict = get_value_dict(request, dataset)
    errors = check_value_dict_create_gloss(request, dataset, value_dict)
    if errors:
        results = dict()
        results['errors'] = errors
        results['createstatus'] = "Failed"
        results['glossid'] = ""
        return JsonResponse(results)

    creation_results = create_gloss(request, dataset, value_dict)

    results = dict()
    for key in creation_results:
        results[key] = creation_results[key]
    return JsonResponse(results)


@csrf_exempt
def api_create_gloss(request, datasetid):
    results = dict()

    if not request.user.is_staff:
        results['errors'] = "User is not Staff."
        return JsonResponse(results)

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        results['errors'] = "Dataset ID does not exist."
        return JsonResponse(results)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        results['errors'] = "No change permission for dataset."
        return JsonResponse(results)

    if not request.user.has_perm('dictionary.change_gloss'):
        results['errors'] = "No change gloss permission."
        return JsonResponse(results)

    human_readable_value_dict = get_human_readable_value_dict(request, dataset)
    value_dict = translate_human_readable_value_dict_to_keys(dataset, human_readable_value_dict)
    errors = check_value_dict_create_gloss(request, dataset, value_dict)
    if errors:
        results = dict()
        results['errors'] = errors
        results['createstatus'] = "Failed"
        results['glossid'] = ""
        return JsonResponse(results)

    creation_results = create_gloss(request, dataset, value_dict)

    return JsonResponse(creation_results)
