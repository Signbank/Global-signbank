import json
import ast

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
from signbank.api_token import hash_token, put_api_user_in_request


def get_interface_language_api(request, user):

    user_profile = UserProfile.objects.get(user=user)
    last_used_language = getattr(user_profile, 'last_used_language')

    if 'LANGUAGE_CODE' in request and request.LANGUAGE_CODE in dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR).keys():
        interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[request.LANGUAGE_CODE]
    elif last_used_language:
        interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[last_used_language]
    else:
        interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[settings.LANGUAGE_CODE]

    interface_language = Language.objects.get(language_code_3char=interface_language_3char)
    interface_language_code = interface_language.language_code_2char

    return interface_language_code


def convert_string_to_list_of_lists(input_string):
    """
    Convert a string to a list of lists.
    """
    try:
        list_of_lists = ast.literal_eval(input_string)
    except (ValueError, SyntaxError):
        return [], "Sense input if not in the expected format. \nTry: '[[\"sense 1 keyword1\", \"sense 1 keyword2\"],[\"sense 2 keyword1\", \"sense 2 keyword2\"],[\"sense 3 keyword1\", \"sense 3 keyword2\"]]'"
        
    # Verify if the result is a list of lists
    if isinstance(list_of_lists, list):
        for item in list_of_lists:
            if not isinstance(item, list):
                return [], 'Input is not a list of lists.'
        return list_of_lists, None
    else:
        return [], 'Input is not a list of lists.'


def required_fields_create_gloss_columns(dataset, language_code):
    activate(language_code)
    dataset_languages = dataset.translation_languages.all()
    annotationidglosstranslation_fields = [gettext("Annotation ID Gloss") + " (" + language.name + ")"
                                           for language in dataset_languages]
    lemmaidglosstranslation_fields = [gettext("Lemma ID Gloss") + " (" + language.name + ")"
                                      for language in dataset_languages]
    sensestranslation_fields = [gettext("Senses") + " (" + language.name + ")"
                                for language in dataset_languages]
    required_columns = ['Dataset'] + lemmaidglosstranslation_fields + annotationidglosstranslation_fields + sensestranslation_fields
    return required_columns


def required_fields_create_gloss_value_dict_keys(dataset):
    dataset_languages = dataset.translation_languages.all()
    annotationidglosstranslation_fields = ['annotation_id_gloss_' + getattr(language, 'language_code_2char')
                                           for language in dataset_languages]
    lemmaidglosstranslation_fields = ['lemma_id_gloss_' + getattr(language, 'language_code_2char')
                                      for language in dataset_languages]
    sensetranslation_fields = ['sense_' + getattr(language, 'language_code_2char')
                               for language in dataset_languages]
    required_columns = ['dataset'] + annotationidglosstranslation_fields + lemmaidglosstranslation_fields + sensetranslation_fields
    return required_columns


def create_gloss_columns_to_value_dict_keys(dataset, language_code):
    activate(language_code)
    required_columns = dict()
    required_columns['Dataset'] = 'dataset'
    dataset_languages = dataset.translation_languages.all()
    for language in dataset_languages:
        required_columns[gettext("Annotation ID Gloss") + " (" + language.name + ")"] = (
                'annotation_id_gloss_' + getattr(language, 'language_code_2char'))
        required_columns[gettext("Lemma ID Gloss") + " (" + language.name + ")"] = (
                'lemma_id_gloss_' + getattr(language, 'language_code_2char'))
        required_columns[gettext("Senses") + " (" + language.name + ")"] = (
                'sense_' + getattr(language, 'language_code_2char'))
    return required_columns


def create_gloss_value_dict_keys_to_columns(dataset, language_code):
    activate(language_code)
    required_columns = dict()
    required_columns['dataset'] = 'Dataset'
    dataset_languages = dataset.translation_languages.all()

    for language in dataset_languages:
        required_columns['annotation_id_gloss_'
                         + getattr(language,
                                   'language_code_2char')] = gettext("Annotation ID Gloss") + " (" + language.name + ")"
        required_columns['lemma_id_gloss_'
                         + getattr(language,
                                   'language_code_2char')] = gettext("Lemma ID Gloss") + " (" + language.name + ")"
        required_columns['sense_'
                         + getattr(language,
                                   'language_code_2char')] = gettext("Senses") + " (" + language.name + ")"
    return required_columns


def get_value_dict(request, dataset):
    required_fields = required_fields_create_gloss_value_dict_keys(dataset)
    value_dict = dict()
    for field in required_fields:
        if field in request.POST.keys():
            value = request.POST.get(field, '')
            value_dict[field] = value.strip()
    return value_dict


@csrf_exempt
def get_human_readable_value_dict(request, dataset, language_code):
    post_data = json.loads(request.body.decode('utf-8'))

    required_fields = required_fields_create_gloss_columns(dataset, language_code)
    value_dict = dict()
    for field in required_fields:
        if field in post_data.keys():
            value = post_data.get(field, '')
            value_dict[field] = value.strip()
    return value_dict


def translate_human_readable_value_dict_to_keys(dataset, language_code, value_dict):
    translate_value_dict_lookup = create_gloss_columns_to_value_dict_keys(dataset, language_code)
    translated_value_dict = dict()
    for field, value in value_dict.items():
        value_dict_key = translate_value_dict_lookup[field]
        translated_value_dict[value_dict_key] = value
    return translated_value_dict


def check_value_dict_create_gloss(dataset, language_code, value_dict):
    activate(language_code)
    errors = []
    if 'dataset' not in value_dict.keys():
        available_keys = list(value_dict.keys())
        e0 = ', '.join(available_keys)
        e00 = dataset.acronym
        errors.append(gettext('Key dataset missing: ') + e0 + ' ' + e00)
        return errors

    dataset_acronym = value_dict['dataset']

    if not dataset_acronym:
        e1 = gettext('Dataset is empty.')
        errors.append(e1)
    elif dataset_acronym != dataset.acronym:
        e2 = gettext('Dataset acronym does not match dataset ') + dataset.acronym + '.'
        errors.append(e2)

    lemmaidglosstranslations = {}
    for language in dataset.translation_languages.all():
        lemma_id_gloss = value_dict['lemma_id_gloss_' + language.language_code_2char]
        if lemma_id_gloss:
            lemmaidglosstranslations[language] = lemma_id_gloss
        else:
            e3 = gettext('Lemma ID Gloss') + " (" + language.name + ")" + gettext(' is empty.')
            errors.append(e3)

    annotationidglosstranslations = {}
    for language in dataset.translation_languages.all():
        annotation_id_gloss = value_dict['annotation_id_gloss_' + language.language_code_2char]
        if annotation_id_gloss:
            annotationidglosstranslations[language] = annotation_id_gloss
        else:
            e4 = gettext("Annotation ID Gloss") + " (" + language.name + ")" + gettext(" is empty.")
            errors.append(e4)

    senses = {}
    for language in dataset.translation_languages.all():
        senses_one_lang = value_dict['sense_' + language.language_code_2char]
        if senses_one_lang:
            senses[language], sense_error = convert_string_to_list_of_lists(senses_one_lang)
            if sense_error:
                errors.append(sense_error)

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
            e5 = gettext("Lemma ID Gloss") + " (" + language.name + ") " + gettext("already exists.")
            errors.append(e5)
            if lemmas.first().lemma.pk not in existing_lemmas:
                existing_lemmas.append(lemmas.first().lemma.pk)
    if len(existing_lemmas) > 1:
        e6 = gettext("Lemma translations refer to different already existing lemmas.")
        errors.append(e6)

    # check annotation translations
    for language, annotationidglosstranslation_text in annotationidglosstranslations.items():
        annotationtranslation_for_this_text_language = AnnotationIdglossTranslation.objects.filter(
            gloss__lemma__dataset=dataset, language=language, text__exact=annotationidglosstranslation_text)

        if annotationtranslation_for_this_text_language.count():
            e7 = gettext('Annotation ID Gloss') + " (" + language.name + ') ' + gettext('already exists') + ': ' + annotationidglosstranslation_text
            errors.append(e7)

    # check if lengths of senses is same in every language
    # senses can be left empty
    if len(senses.keys()) > 1:
        nr_senses = 0
        for language_i, language in enumerate(senses.keys()):
            if language_i == 0:
                nr_senses = len(senses[language])
            else:
                if nr_senses != len(senses[language]):
                    e8 = gettext("Sense arrays are not the same length.")
                    errors.append(e8)

    return errors


@csrf_exempt
def create_gloss(user, dataset, value_dict):
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
            new_gloss.creator.add(user)
            new_gloss.save()
            user_affiliations = AffiliatedUser.objects.filter(user=user)
            if user_affiliations.count() > 0:
                for ua in user_affiliations:
                    new_affiliation, created = AffiliatedGloss.objects.get_or_create(affiliation=ua.affiliation,
                                                                                     gloss=new_gloss)

            for language in dataset_languages:
                annotationidgloss_text = value_dict['annotation_id_gloss_' + language.language_code_2char]
                annotationidglosstranslation = AnnotationIdglossTranslation()
                annotationidglosstranslation.language = language
                annotationidglosstranslation.gloss = new_gloss
                annotationidglosstranslation.text = annotationidgloss_text
                annotationidglosstranslation.save()
            
            # Find the number of senses in the gloss
            nr_senses = 0
            for language in dataset_languages:
                sensetranslations, _ = convert_string_to_list_of_lists(value_dict['sense_' + language.language_code_2char])
                nr_senses_in_lang = len(sensetranslations)
                if nr_senses_in_lang > nr_senses:
                    nr_senses = nr_senses_in_lang

            if nr_senses > 0:
                # Make new sense objects and add them to the new gloss
                for sense_n in range(nr_senses):
                    new_sense = Sense.objects.create()
                    new_gloss.senses.add(new_sense, through_defaults={'order':sense_n+1})
                    for language in dataset_languages:
                        if value_dict['sense_' + language.language_code_2char] == '':
                            continue
                        sensetranslations, _ = convert_string_to_list_of_lists(value_dict['sense_' + language.language_code_2char])
                        if sensetranslations[sense_n]:
                            sensetranslation = SenseTranslation.objects.create(language=language)
                            new_sense.senseTranslations.add(sensetranslation)
                            for inx, kw in enumerate(sensetranslations[sense_n], 1):
                                # this is a new sense so it has no translations yet
                                # the combination with gloss, language, orderIndex does not exist yet
                                # the index is the order the keyword was entered by the user
                                if not kw:
                                    continue
                                keyword = Keyword.objects.get_or_create(text=kw)[0]
                                translation = Translation(translation=keyword,
                                                        language=language,
                                                        gloss=new_gloss,
                                                        orderIndex=sense_n+1,
                                                        index=inx)
                                translation.save()
                                sensetranslation.translations.add(translation)

                # add create sense to revision history, indicated by empty old_value
                sense_new_value = str(new_sense)
                sense_label = 'Sense'
                revision = GlossRevision(old_value="",
                                         new_value=sense_new_value,
                                         field_name=sense_label,
                                         gloss=new_gloss,
                                         user=user,
                                         time=datetime.now(tz=get_current_timezone()))
                revision.save()

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
    errors = check_value_dict_create_gloss(dataset, language_code, value_dict)
    if errors:
        results = dict()
        results['errors'] = errors
        results['createstatus'] = "Failed"
        results['glossid'] = ""
        return JsonResponse(results)

    creation_results = create_gloss(request.user, dataset, value_dict)

    results = dict()
    for key in creation_results:
        results[key] = creation_results[key]
    return JsonResponse(results)


@csrf_exempt
@put_api_user_in_request
def api_create_gloss(request, datasetid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        results['errors'] = [gettext("Dataset ID does not exist.")]
        return JsonResponse(results)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        results['errors'] = [gettext("No change permission for dataset for user ") + str(request.user)]
        return JsonResponse(results)

    if not request.user.has_perm('dictionary.change_gloss'):
        results['errors'] = [gettext("No change gloss permission.")]
        return JsonResponse(results)

    activate(interface_language_code)

    human_readable_value_dict = get_human_readable_value_dict(request, dataset, interface_language_code)
    value_dict = translate_human_readable_value_dict_to_keys(dataset, interface_language_code, human_readable_value_dict)
    errors = check_value_dict_create_gloss(dataset, interface_language_code, value_dict)
    if errors:
        results = dict()
        results['errors'] = errors
        results['createstatus'] = "Failed"
        results['glossid'] = ""
        return JsonResponse(results)

    creation_results = create_gloss(request.user, dataset, value_dict)

    return JsonResponse(creation_results)
