from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import permission_required
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag

from signbank.dictionary.models import *
from signbank.dictionary.forms import *


def internal_batch_update_fields_for_gloss(gloss):

    languages = gloss.lemma.dataset.translation_languages
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


def batch_edit_update_gloss(request, glossid):
    """Update the gloss fields"""
    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    gloss = get_object_or_404(Gloss, id=glossid)
