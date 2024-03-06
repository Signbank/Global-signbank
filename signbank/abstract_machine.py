from signbank.dictionary.models import *
from tagging.models import Tag, TaggedItem
from signbank.dictionary.forms import *
from signbank.dictionary.consistency_senses import check_consistency_senses
from django.utils.translation import override, gettext_lazy as _, activate
from signbank.settings.server_specific import LANGUAGES, LEFT_DOUBLE_QUOTE_PATTERNS, RIGHT_DOUBLE_QUOTE_PATTERNS
from signbank.dictionary.update_senses_mapping import add_sense_to_revision_history


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
        if field in request.POST:
            value_dict[field] = request.POST.get(field, '')

    return value_dict


def check_value_dict_create_gloss(request, dataset, value_dict):
    errors = []
    dataset_acronym = value_dict['dataset']

    try:
        dataset_object = Dataset.objects.get(acronym=dataset_acronym)
    except ObjectDoesNotExist:
        e1 = 'Dataset not found: ' + dataset
        errors.append(e1)
    if dataset_acronym != dataset.acronym:
        e2 = 'Dataset does not match'
        errors.append(e2)

    lemmaidglosstranslations = {}
    for language in dataset.translation_languages.all():
        lemma_id_gloss = value_dict['lemma_id_gloss_' + language.language_code_2char]
        if lemma_id_gloss:
            lemmaidglosstranslations[language] = lemma_id_gloss

    # REWRITE THIS, COPIED FROM CSV CREATE GLOSSES CHECKS
    existing_lemmas = {}
    existing_lemmas_list = []
    new_lemmas = {}
    empty_lemma_translation = False
    # check lemma translations
    for language, lemmaidglosstranslation_text in lemmaidglosstranslations.items():
        lemmatranslation_for_this_text_language = LemmaIdglossTranslation.objects.filter(
            lemma__dataset=dataset, language=language, text__exact=lemmaidglosstranslation_text)
        if lemmatranslation_for_this_text_language:
            one_lemma = lemmatranslation_for_this_text_language.first().lemma
            existing_lemmas[language.language_code_2char] = one_lemma
            if not one_lemma in existing_lemmas_list:
                existing_lemmas_list.append(one_lemma)
                help = 'Existing Lemma ID Gloss (' + language.name + '): ' + lemmaidglosstranslation_text
                errors.append(help)
        elif not lemmaidglosstranslation_text:
            # lemma translation is empty, determine if existing lemma is also empty for this language
            if existing_lemmas_list:
                lemmatranslation_for_this_text_language = LemmaIdglossTranslation.objects.filter(
                    lemma__dataset=dataset, lemma=existing_lemmas_list[0],
                    language=language)
                if lemmatranslation_for_this_text_language:
                    help = 'Lemma ID Gloss (' + language.name + ') is empty'
                    errors.append(help)
                    empty_lemma_translation = True
            else:
                empty_lemma_translation = True
        else:
            new_lemmas[language.language_code_2char] = lemmaidglosstranslation_text
            help = 'New Lemma ID Gloss (' + language.name + '): ' + lemmaidglosstranslation_text
            errors.append(help)

    if len(existing_lemmas_list) > 0:
        if len(existing_lemmas_list) > 1:
            e1 = 'The Lemma translations refer to different lemmas.'
            errors.append(e1)
        elif empty_lemma_translation:
            e1 = 'Exactly one lemma matches, but one of the translations in the csv is empty.'
            errors.append(e1)
        if len(new_lemmas.keys()) and len(existing_lemmas.keys()):
            e1 = 'Combination of existing and new lemma translations.'
            errors.append(e1)
    elif not len(new_lemmas.keys()):
        e1 = 'No lemma translations provided.'
        errors.append(e1)

    annotationidglosstranslations = {}
    for language in dataset.translation_languages.all():
        annotation_id_gloss = value_dict['annotation_id_gloss_' + language.language_code_2char]
        if annotation_id_gloss:
            annotationidglosstranslations[language] = annotation_id_gloss

    # check annotation translations
    for language, annotationidglosstranslation_text in annotationidglosstranslations.items():
        annotationtranslation_for_this_text_language = AnnotationIdglossTranslation.objects.filter(
            gloss__lemma__dataset=dataset, language=language, text__exact=annotationidglosstranslation_text)

        if annotationtranslation_for_this_text_language:
            error_string = ('This annotation already exists for language '
                            + language.name + ': ' + annotationidglosstranslation_text)
            errors.append(error_string)

    return errors

