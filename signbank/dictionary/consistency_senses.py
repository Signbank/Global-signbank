from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import permission_required
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from signbank.dictionary.models import *


def consistent_senses(gloss, include_translations=False, allow_empty_language=False):
    # this method is unambiguous in its coding
    # it explicitly codes everything it checks
    translation_languages = gloss.lemma.dataset.translation_languages.all()
    glosssenses = GlossSense.objects.filter(gloss=gloss)
    gloss_senses_lookup = dict()
    for gs in glosssenses:
        if gs.order in gloss_senses_lookup.keys():
            print('sense order appears twice')
            return False
        gloss_senses_lookup[gs.order] = gs.sense
    for order, sense in gloss_senses_lookup.items():
        for language in translation_languages:
            sense_translations = sense.senseTranslations.filter(language=language)
            if sense_translations.count() > 1:
                print('more than one sense translation object for language ', language)
                return False
            sense_translation = sense_translations.first()
            if not sense_translation and not allow_empty_language:
                print('no sense translation object for ', language)
                return False
            if not include_translations:
                continue
            if allow_empty_language and not sense_translation:
                continue
            translations = sense_translation.translations.all()
            if settings.DEBUG_SENSES:
                for t in translations:
                    print("'gloss': ", str(gloss.id), ", 'sense': ", str(order),
                          ", 'orderIndex': ", str(t.orderIndex), ", 'language': ", str(t.language),
                          ", 'index': ", str(t.index), ", 'translation_id': ", str(t.id),
                          ", 'translation.text': ", t.translation.text)
                print('-------')
            for trans in translations:
                if trans.language != language:
                    print('translation object language does not match')
                    return False
                if trans.orderIndex != order:
                    print('translation order index does not match')
                    return False
                if trans.gloss != gloss:
                    print('gloss does not match')
                    return False
    return True


def check_consistency_senses(gloss, delete_empty=False):

    glosssenses = GlossSense.objects.filter(gloss=gloss)
    gloss_sense_orders = [gs.order for gs in glosssenses]
    # use a list to store potential duplicates with no translations
    duplicates_with_empty_senses = []
    for gs in glosssenses:
        if gloss_sense_orders.count(gs.order) > 1:
            # duplicates found with same order
            gs_sense_translations = gs.sense.senseTranslations.all()
            is_empty = True
            for st in gs_sense_translations:
                if st.translations.all():
                    is_empty = False
            if is_empty:
                duplicates_with_empty_senses.append(gs)
    if duplicates_with_empty_senses:
        print('duplicate senses with no translations: ', duplicates_with_empty_senses)
        if delete_empty:
            # delete senses with no translations
            for gs in duplicates_with_empty_senses:
                sense = gs.sense
                sense_translations = sense.senseTranslations.all()
                for st in sense_translations:
                    sense.senseTranslations.remove(st)
                    st.delete()
                gs.delete()
                sense.delete()


def reorder_translations(gloss_sense, order):

    gloss = gloss_sense.gloss
    consistent = consistent_senses(gloss, include_translations=False)
    if not consistent:
        print('inconsistent senses: ', gloss, str(gloss.id))
        return
    sense = gloss_sense.sense
    for sensetranslation in sense.senseTranslations.all():
        inconsistent_translations = []
        wrong_gloss_translations = []
        wrong_language_translations = []
        wrong_order_index_translations = []
        for trans in sensetranslation.translations.all():
            this_trans_okay = True
            if trans.gloss != gloss:
                # trans.gloss does not match this gloss
                wrong_gloss_translations.append(trans)
                this_trans_okay = False
            if trans.orderIndex != order:
                # trans.orderIndex does not match order of sense
                wrong_order_index_translations.append(trans)
                this_trans_okay = False
            if trans.language != sensetranslation.language:
                # trans.language does not match order of sense
                wrong_language_translations.append(trans)
                this_trans_okay = False
            if not this_trans_okay:
                inconsistent_translations.append(trans)

        if wrong_order_index_translations:
            # these are being updated or removed if not possible
            for trans in wrong_order_index_translations:
                try:
                    trans.orderIndex = order
                    trans.save()
                    inconsistent_translations.remove(trans)
                except (DatabaseError, IntegrityError, TransactionManagementError):
                    sensetranslation.translations.remove(trans)
                    inconsistent_translations.remove(trans)
                    trans.delete()
        if wrong_language_translations:
            print('wrong language: ', wrong_language_translations)
            for trans in wrong_language_translations:
                try:
                    trans.language = sensetranslation.language
                    trans.save()
                    inconsistent_translations.remove(trans)
                except (DatabaseError, IntegrityError, TransactionManagementError):
                    sensetranslation.translations.remove(trans)
                    inconsistent_translations.remove(trans)
                    trans.delete()
        if wrong_gloss_translations:
            print('wrong gloss: ', wrong_gloss_translations)
            for trans in wrong_gloss_translations:
                try:
                    trans.gloss = gloss
                    trans.save()
                    inconsistent_translations.remove(trans)
                except (DatabaseError, IntegrityError, TransactionManagementError):
                    sensetranslation.translations.remove(trans)
                    inconsistent_translations.remove(trans)
                    trans.delete()

        # these are translations for one language
        all_translations = [tr for tr in sensetranslation.translations.all().order_by('index')]
        for index, trans in enumerate(all_translations, 1):
            # this does not violate any constraint
            trans.index = index
            trans.save()


def reorder_sensetranslations(gloss, sensetranslation, order, reset=False, force_reset=False):
    inconsistent_translations = []
    inconsistent_translation_ids = []
    wrong_gloss_translations = []
    wrong_language_translations = []
    wrong_order_index_translations = []
    for trans in sensetranslation.translations.all():
        this_trans_okay = True
        if trans.gloss != gloss:
            # trans.gloss does not match this gloss
            wrong_gloss_translations.append(trans)
            this_trans_okay = False
        if trans.orderIndex != order:
            # trans.orderIndex does not match order of sense
            wrong_order_index_translations.append(trans)
            this_trans_okay = False
        if trans.language != sensetranslation.language:
            # trans.language does not match order of sense
            wrong_language_translations.append(trans)
            this_trans_okay = False
        if not this_trans_okay:
            inconsistent_translations.append(trans)
            inconsistent_translation_ids.append(trans.id)
    if not reset:
        return inconsistent_translations

    # reset is true
    if force_reset and wrong_order_index_translations:
        for trans in wrong_order_index_translations:
            try:
                trans.orderIndex = order
                trans.save()
                inconsistent_translations.remove(trans)
            except (DatabaseError, IntegrityError, TransactionManagementError):
                sensetranslation.translations.remove(trans)
                inconsistent_translations.remove(trans)
                trans.delete()
    if force_reset and wrong_language_translations:
        for trans in wrong_language_translations:
            try:
                trans.language = sensetranslation.language
                trans.save()
                inconsistent_translations.remove(trans)
            except (DatabaseError, IntegrityError, TransactionManagementError):
                sensetranslation.translations.remove(trans)
                inconsistent_translations.remove(trans)
                trans.delete()
    if force_reset and wrong_gloss_translations:
        for trans in wrong_gloss_translations:
            try:
                trans.gloss = gloss
                trans.save()
                inconsistent_translations.remove(trans)
            except (DatabaseError, IntegrityError, TransactionManagementError):
                sensetranslation.translations.remove(trans)
                inconsistent_translations.remove(trans)
                trans.delete()

    all_translations = [tr for tr in sensetranslation.translations.all().order_by('index')]
    for index, trans in enumerate(all_translations, 1):
        # this does not violate any constraint
        trans.index = index
        trans.save()
    return inconsistent_translations


def reorder_senses(gloss):

    glosssenses = GlossSense.objects.filter(gloss=gloss)
    gloss_sense_orders = [gs.order for gs in glosssenses]
    gloss_senses_with_order = dict()
    for order in gloss_sense_orders:
        gloss_senses_with_order[order] = [gs for gs in glosssenses.filter(order=order)]

    # use a list to store potential duplicates with no translations
    duplicates_with_empty_senses = []
    for gs in glosssenses:
        if gloss_sense_orders.count(gs.order) > 1:
            # duplicates found with same order
            gs_sense_translations = gs.sense.senseTranslations.all()
            is_empty = True
            for st in gs_sense_translations:
                if st.translations.all():
                    is_empty = False
            if is_empty:
                duplicates_with_empty_senses.append(gs)
    if duplicates_with_empty_senses:
        # delete senses with no translations
        for gs in duplicates_with_empty_senses:
            sense = gs.sense
            sense_translations = sense.senseTranslations.all()
            for st in sense_translations:
                sense.senseTranslations.remove(st)
                st.delete()
            if gs in gloss_senses_with_order[gs.order]:
                gloss_senses_with_order[gs.order].remove(gs)
            gs.delete()
            sense.delete()
    # reorder after deleting empty objects
    gloss.reorder_senses()


