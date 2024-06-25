from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import permission_required
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag

from signbank.dictionary.models import *
from signbank.dictionary.forms import *


def internal_batch_update_fields_for_gloss(gloss):

    languages = gloss.lemma.dataset.translation_languages.all()
    gloss_prefix = str(gloss.id) + '_'
    internal_batch_fields = []
    for language in languages:
        gloss_lemma_field_name = BatchEditForm.gloss_lemma_field_prefix + gloss_prefix + language.language_code_2char
        internal_batch_fields.append(gloss_lemma_field_name)

    for language in languages:
        gloss_annotation_field_name = BatchEditForm.gloss_annotation_field_prefix + gloss_prefix + language.language_code_2char
        internal_batch_fields.append(gloss_annotation_field_name)

    for language in languages:
        gloss_sense_field_name = BatchEditForm.gloss_sense_field_prefix + gloss_prefix + language.language_code_2char
        internal_batch_fields.append(gloss_sense_field_name)

    return internal_batch_fields


def get_value_dict(request, gloss):
    internal_language_fields = internal_batch_update_fields_for_gloss(gloss)
    value_dict = dict()
    for field in internal_language_fields:
        if field in request.POST.keys():
            value = request.POST.get(field, '')
            value_dict[field] = value.strip()
    return value_dict


def get_gloss_language_fields(gloss):
    gloss_prefix = str(gloss.id) + '_'
    dataset_languages = gloss.dataset.translation_languages.all()
    language_fields_dict = dict()
    for language in dataset_languages:
        lemmaidglosstranslations = gloss.lemma.lemmaidglosstranslation_set.filter(language=language)
        field_name = BatchEditForm.gloss_lemma_field_prefix + gloss_prefix + language.language_code_2char
        if lemmaidglosstranslations.count() > 0:
            language_fields_dict[field_name] = lemmaidglosstranslations.first().text
        else:
            language_fields_dict[field_name] = ''
    for language in dataset_languages:
        annotationidglosstranslation = gloss.annotationidglosstranslation_set.filter(language=language)
        field_name = BatchEditForm.gloss_annotation_field_prefix + gloss_prefix + language.language_code_2char
        if annotationidglosstranslation.count() > 0:
            language_fields_dict[field_name] = annotationidglosstranslation.first().text
        else:
            language_fields_dict[field_name] = ''
    return language_fields_dict


def get_sense_numbers(gloss):
    senses_mapping = dict()
    glosssenses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    languages = gloss.lemma.dataset.translation_languages.all()
    if not glosssenses:
        return []
    gloss_senses = dict()
    for gs in glosssenses:
        order = gs.order
        sense = gs.sense
        if order in gloss_senses.keys():
            continue
        gloss_senses[order] = sense
    for order, sense in gloss_senses.items():
        senses_mapping[order] = dict()
        for language in languages:
            sensetranslation = sense.senseTranslations.filter(language=language).first()
            translations = sensetranslation.translations.all().order_by('index') if sensetranslation else []
            keywords_list = [translation.translation.text for translation in translations]
            senses_mapping[order][language.language_code_2char] = ', '.join(keywords_list)
    return senses_mapping


def add_gloss_update_to_revision_history(user, gloss, field, oldvalue, newvalue):

    revision = GlossRevision(old_value=oldvalue,
                             new_value=newvalue,
                             field_name=field,
                             gloss=gloss,
                             user=user,
                             time=datetime.now(tz=get_current_timezone()))
    revision.save()


def update_lemma_translation(gloss, language_code_2char, new_value):
    language = Language.objects.get(language_code_2char=language_code_2char)
    try:
        lemma_idgloss_translation = LemmaIdglossTranslation.objects.get(lemma=gloss.lemma, language=language)
    except ObjectDoesNotExist:
        # create an empty translation for this gloss and language
        lemma_idgloss_translation = LemmaIdglossTranslation(lemma=gloss.lemma, language=language)

    try:
        lemma_idgloss_translation.text = new_value
        lemma_idgloss_translation.save()
    except (DatabaseError, ValidationError):
        pass


def update_annotation_translation(gloss, language_code_2char, new_value):
    language = Language.objects.get(language_code_2char=language_code_2char)
    try:
        annotation_idgloss_translation = AnnotationIdglossTranslation.objects.get(gloss=gloss, language=language)
    except ObjectDoesNotExist:
        # create an empty translation for this gloss and language
        annotation_idgloss_translation = AnnotationIdglossTranslation(gloss=gloss, language=language)

    try:
        annotation_idgloss_translation.text = new_value
        annotation_idgloss_translation.save()
    except (DatabaseError, ValidationError):
        pass


def check_constraints_on_gloss_language_fields(gloss, value_dict):
    gloss_prefix = str(gloss.id) + '_'

    errors = []

    dataset = gloss.lemma.dataset
    lemmaidglosstranslations = {}
    for language in dataset.translation_languages.all():
        lemma_key = 'lemma_' + gloss_prefix + language.language_code_2char
        if lemma_key in value_dict.keys():
            lemmaidglosstranslations[language] = value_dict[lemma_key]

    if lemmaidglosstranslations:
        # the lemma translations are being updated
        lemma_group_glossset = Gloss.objects.filter(lemma=gloss.lemma)
        if lemma_group_glossset.count() > 1:
            more_than_one_gloss_in_lemma_group = gettext("More than one gloss in lemma group.")
            errors.append(more_than_one_gloss_in_lemma_group)

    annotationidglosstranslations = {}
    for language in dataset.translation_languages.all():
        annotation_key = 'annotation__' + gloss_prefix + language.language_code_2char
        if annotation_key in value_dict.keys():
            annotationidglosstranslations[language] = value_dict[annotation_key]

    # check lemma translations
    lemmas_per_language_translation = dict()
    for language, lemmaidglosstranslation_text in lemmaidglosstranslations.items():
        lemmatranslation_for_this_text_language = LemmaIdglossTranslation.objects.filter(
            lemma__dataset=dataset, language=language,
            text__iexact=lemmaidglosstranslation_text).exclude(lemma=gloss.lemma)
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
            gloss__lemma__dataset=dataset, language=language,
            text__iexact=annotationidglosstranslation_text).exclude(gloss=gloss)
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


def batch_edit_update_gloss(request, glossid):
    """Update the gloss fields"""
    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    result = dict()

    gloss = get_object_or_404(Gloss, id=glossid)

    value_dict = get_value_dict(request, gloss)
    language_fields_dict = get_gloss_language_fields(gloss)
    fields_to_update = dict()
    for key in value_dict.keys():
        if value_dict[key] != language_fields_dict[key]:
            fields_to_update[key] = value_dict[key]

    if not fields_to_update:
        print('nothing to do')
        saved_text = gettext("No changes were found.")
        result['glossid'] = glossid
        result['errors'] = []
        result['updatestatus'] = saved_text
        return result

    errors = check_constraints_on_gloss_language_fields(gloss, fields_to_update)
    if errors:
        result['glossid'] = glossid
        result['errors'] = errors
        result['updatestatus'] = "&#10060;"
        return result

    for key in fields_to_update.keys():
        original_value = language_fields_dict[key]
        newvalue = fields_to_update[key]
        language = key[-2:]
        if key.startswith('lemma'):
            update_lemma_translation(gloss, key[-2:], newvalue)
            add_gloss_update_to_revision_history(request.user, gloss, 'lemma_'+language, original_value, newvalue)
        elif key.startswith('annotation'):
            update_annotation_translation(gloss, key[-2:], newvalue)
            add_gloss_update_to_revision_history(request.user, gloss, 'annotation_'+language, original_value, newvalue)
    gloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    gloss.save()

    saved_text = gettext("Gloss saved to dataset")
    result['glossid'] = glossid
    result['errors'] = []
    result['updatestatus'] = saved_text + " &#x2713;"

    return result
