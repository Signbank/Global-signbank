from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import permission_required
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag

from signbank.dictionary.models import *
from signbank.dictionary.forms import *


def add_sense_to_revision_history(request, gloss, sense_old_value, sense_new_value):
    # add update sense to revision history, indicated by both old and new values
    sense_label = 'Sense'
    revision = GlossRevision(old_value=sense_old_value,
                             new_value=sense_new_value,
                             field_name=sense_label,
                             gloss=gloss,
                             user=request.user,
                             time=datetime.now(tz=get_current_timezone()))
    revision.save()


def get_state_of_gloss_senses(gloss):
    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    gloss_sense_lookup = dict()
    for gs in gloss_senses:
        if str(gs.order) in gloss_sense_lookup.keys():
            continue
        gloss_sense_lookup[gs.order] = str(gs.sense)
    return gloss_sense_lookup


def gloss_senses_state_is_changed(request, gloss, original_senses_state_lookup, new_senses_state_lookup):
    print('gloss_senses_state_is_changed original: ', original_senses_state_lookup)
    print('gloss_senses_state_is_changed updated: ', new_senses_state_lookup)

    for snum in new_senses_state_lookup.keys():
        if snum not in original_senses_state_lookup.keys():
            add_sense_to_revision_history(request, gloss, "", new_senses_state_lookup[snum])
        elif new_senses_state_lookup[snum] != original_senses_state_lookup[snum]:
            add_sense_to_revision_history(request, gloss, original_senses_state_lookup[snum], new_senses_state_lookup[snum])
    for snum in original_senses_state_lookup.keys():
        if snum not in new_senses_state_lookup.keys():
            add_sense_to_revision_history(request, gloss, original_senses_state_lookup[snum], "")
    return


def create_empty_sense(gloss, order):

    # make a new sense and translations for it
    translation_languages = gloss.lemma.dataset.translation_languages.all().order_by('id')
    sense_translations = dict()
    sense_for_gloss = Sense()
    sense_for_gloss.save()
    glosssense = GlossSense(gloss=gloss, sense=sense_for_gloss, order=order)
    glosssense.save()
    for dataset_language in translation_languages:
        glosssenselanguage = SenseTranslation(language=dataset_language)
        glosssenselanguage.save()
        sense_for_gloss.senseTranslations.add(glosssenselanguage)
        sense_translations[dataset_language] = glosssenselanguage
    return sense_for_gloss, sense_translations


def gloss_to_keywords_senses_groups(gloss, language):
    glossXsenses = dict()
    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    list_of_gloss_senses = [(gs.order, gs.sense) for gs in gloss_senses]
    senses_groups = dict()
    keywords_list = []
    for order, sense in list_of_gloss_senses:
        senses_groups[order] = []
        translations_for_language_for_sense = sense.senseTranslations.filter(language=language).first()
        if not translations_for_language_for_sense:
            continue
        for trans in translations_for_language_for_sense.translations.all().order_by('index'):
            if trans.orderIndex != order:
                print('gloss_to_keywords_senses_groups')
                print('reset order index: ', gloss, order, trans.translation.text)
                if trans.gloss == gloss:
                    trans.orderIndex = order
                    trans.save()
                else:
                    print('trans gloss different than this gloss: ', trans.gloss)
            senses_groups[order].append((str(trans.id), trans.translation.text))
            keywords_list.append(trans.translation.text)
    glossXsenses['glossid'] = str(gloss.id)
    glossXsenses['language'] = str(language.id)
    glossXsenses['keywords'] = keywords_list
    glossXsenses['senses_groups'] = senses_groups
    return glossXsenses


def mapping_edit_keywords(request, glossid):
    """Edit the keywords"""
    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    gloss = get_object_or_404(Gloss, id=glossid)

    original_gloss_senses = get_state_of_gloss_senses(gloss)

    dataset_languages = [str(lang.id) for lang
                         in gloss.lemma.dataset.translation_languages.all().order_by('id')]

    order_index_get = request.POST.get('order_index')
    order_index_list_str = json.loads(order_index_get)
    order_index = [int(s) for s in order_index_list_str]

    trans_id_get = request.POST.get('trans_id')
    trans_id_list_str = json.loads(trans_id_get)
    trans_id = [int(s) for s in trans_id_list_str]

    changed_language_id = request.POST.get('language', '')

    translation_get = request.POST.get('translation')
    translation_list_str = json.loads(translation_get)
    translation = [s.strip() for s in translation_list_str]

    # this one is set if this is the first keyword and first sense
    new_translation_get = request.POST.get('new_translation')
    new_translation_list_str = json.loads(new_translation_get)
    new_translation = [s.strip() for s in new_translation_list_str]

    language_obj = Language.objects.get(id=int(changed_language_id))

    gloss_senses = GlossSense.objects.filter(gloss=gloss).count()

    if not gloss_senses:
        create_empty_sense(gloss, 1)

    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')

    order_sense_tuples = [(gs.order, gs.sense) for gs in gloss_senses]
    current_keywords = dict()
    for order, sense in order_sense_tuples:
        current_keywords[order] = []
        sense_trans = sense.senseTranslations.filter(language=language_obj).first()
        if not sense_trans:
            # there is currently to SenseTranslation object for this language
            # this can happen if a sense was created in GlossDetailView
            sense_trans = SenseTranslation(language=language_obj)
            sense_trans.save()
            sense.senseTranslations.add(sense_trans)
        for trans in sense_trans.translations.all():
            if trans.orderIndex != order:
                trans.orderIndex = order
                trans.save()
            current_keywords[order].append(trans.translation.text)

    order_sense_dict = dict()
    for glosssense in gloss_senses:
        order_sense_dict[glosssense.order] = glosssense.sense.senseTranslations.filter(language=language_obj).first()

    deleted_translations = []
    # update the new keywords
    for inx, new_text in enumerate(translation):
        input_order_index = order_index[inx]
        index_to_update = trans_id[inx]
        # fetch the keyword's translation object and change its keyword
        keyword_to_update = Translation.objects.get(pk=index_to_update)
        keyword_order = keyword_to_update.orderIndex

        keywords_for_sense_number = current_keywords[input_order_index] if input_order_index in current_keywords.keys() else []
        if new_text != '' and new_text in keywords_for_sense_number:
            # already appears in sense numer
            continue

        if new_text == '':
            # this looks a bit weird, but somehow the order index of a translation
            # may not match the sense it is stored in
            if keyword_order in order_sense_dict.keys():
                original_sense_translations = order_sense_dict[keyword_order]
            elif input_order_index in order_sense_dict.keys():
                original_sense_translations = order_sense_dict[input_order_index]
            else:
                original_sense_translations = None
            if original_sense_translations:
                original_sense_translations.translations.remove(keyword_to_update)
            keyword_to_update.delete()
            deleted_translations.append({'inputEltIndex': inx,
                                         'orderIndex': str(keyword_order),
                                         'trans_id': str(index_to_update),
                                         'language': changed_language_id})
            continue

        # new text is not in current keywords
        # fetch or create the text and update the translation object
        (keyword_object, created) = Keyword.objects.get_or_create(text=new_text)
        keyword_to_update.translation = keyword_object
        keyword_to_update.orderIndex = input_order_index
        keyword_to_update.save()

    new_translations = []
    new_sense_number = 1
    new_index = 1
    # the following is only executed if the gloss currently has no keywords for this language
    for inx, new_text in enumerate(new_translation):
        if new_text == '':
            continue
        (keyword_object, created) = Keyword.objects.get_or_create(text=new_text)

        saved_translation = []

        # make a new translation using new sense number and new index numer
        try:
            trans = Translation(gloss=gloss, translation=keyword_object, index=new_index,
                                language=language_obj, orderIndex=new_sense_number)
            trans.save()
            saved_translation.append(trans)
            new_index += 1
        except (IntegrityError, DatabaseError, TransactionManagementError):
            print('error creating translation: ', gloss, new_text, language_obj, ' order ', new_sense_number)
            new_index += 1
            continue
        new_trans = saved_translation[0]
        new_translations.append({'new_text': new_text,
                                 'new_trans_id': str(new_trans.id),
                                 'new_order_index': str(new_sense_number),
                                 'new_language': changed_language_id})
        sense_language = order_sense_dict[new_sense_number]
        sense_language.translations.add(new_trans)

    glossXsenses = gloss_to_keywords_senses_groups(gloss, language_obj)

    updated_gloss_senses = get_state_of_gloss_senses(gloss)
    gloss_senses_state_is_changed(request, gloss, original_gloss_senses, updated_gloss_senses)

    glossXsenses['regrouped_keywords'] = []
    glossXsenses['dataset_languages'] = dataset_languages
    glossXsenses['deleted_translations'] = deleted_translations
    glossXsenses['deleted_sense_numbers'] = []
    glossXsenses['new_translations'] = new_translations

    return glossXsenses


def delete_empty_senses(gloss):

    translation_languages = gloss.lemma.dataset.translation_languages.all().order_by('id')
    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    order_sense_dict = dict()
    for glosssense in gloss_senses:
        if glosssense.order not in order_sense_dict.keys():
            # first time seen, initialise structure for this order
            order_sense_dict[glosssense.order] = dict()
            for dataset_language in translation_languages:
                # keep a list of SenseTranslation objects
                order_sense_dict[glosssense.order][dataset_language] = []
        for dataset_language in translation_languages:
            senseTranslations = glosssense.sense.senseTranslations.filter(language=dataset_language)
            for st in senseTranslations:
                order_sense_dict[glosssense.order][dataset_language].append(st)

    senses_to_delete = []
    for order in order_sense_dict.keys():
        count_keywords = 0
        for lang in order_sense_dict[order].keys():
            senseTranslations = order_sense_dict[order][lang]
            for st in senseTranslations:
                count_keywords += st.translations.exclude(translation__text='').count()
        if count_keywords == 0:
            senses_to_delete.append(order)

    deleted_sense_numbers = []
    for order in senses_to_delete:
        glosssenses = GlossSense.objects.filter(gloss=gloss, order=order)
        if not glosssenses:
            continue
        for gs in glosssenses:
            sense = gs.sense
            sense_translations = sense.senseTranslations.all()
            for sensetranslation in sense_translations:
                for trans in sensetranslation.translations.all():
                    sensetranslation.translations.remove(trans)
                    trans.delete()
                sense.senseTranslations.remove(sensetranslation)
                sensetranslation.delete()
            gs.delete()
            sense.delete()
            deleted_sense_numbers.append(str(order))
    return deleted_sense_numbers


def mapping_group_keywords(request, glossid):
    """Update the keyword field"""

    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    gloss = get_object_or_404(Gloss, id=glossid)

    original_gloss_senses = get_state_of_gloss_senses(gloss)

    dataset_languages = [str(lang.id)
                         for lang in gloss.lemma.dataset.translation_languages.all().order_by('id')]
    translation_languages = gloss.lemma.dataset.translation_languages.all().order_by('id')

    trans_id_get = request.POST.get('trans_id')
    trans_id_list_str = json.loads(trans_id_get) if trans_id_get else []
    trans_id = [int(s) for s in trans_id_list_str]

    language = request.POST.get('language', '')

    regroup_get = request.POST.get('regroup')
    regroup_list_str = json.loads(regroup_get) if regroup_get else []
    regroup = [int(s) for s in regroup_list_str]

    changed_language = Language.objects.get(id=int(language))

    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    order_sense_dict = dict()
    for glosssense in gloss_senses:
        order_sense_dict[glosssense.order] = dict()
        sense = glosssense.sense
        for dataset_language in translation_languages:
            sense_trans = sense.senseTranslations.filter(language=dataset_language).first()
            if not sense_trans:
                # there is currently to SenseTranslation object for this language
                # this can happen if a sense was created in GlossDetailView
                sense_trans = SenseTranslation(language=dataset_language)
                sense_trans.save()
                sense.senseTranslations.add(sense_trans)
            order_sense_dict[glosssense.order][dataset_language] = sense_trans

    current_senses = [gs.order for gs in gloss_senses]
    for inx, regroup_sense_number in enumerate(regroup):
        if regroup_sense_number not in current_senses:
            # create a new sense and put it in the data structure for targets
            regroup_sense, regroup_sense_translations = create_empty_sense(gloss, regroup_sense_number)
            order_sense_dict[regroup_sense_number] = regroup_sense_translations
            current_senses.append(regroup_sense_number)

    keywords_per_sense = dict()
    for order in order_sense_dict.keys():
        keywords_per_sense[order] = dict()
        for lang in order_sense_dict[order].keys():
            keywords_per_sense[order][lang.id] = []
            sense_trans = order_sense_dict[order][lang]
            for trans in sense_trans.translations.all().order_by('index'):
                keywords_per_sense[order][lang.id].append(trans.translation.text)

    regrouped_keywords = []
    for inx, transid in enumerate(trans_id):
        target_sense_group = regroup[inx]
        try:
            trans = Translation.objects.get(id=transid)
        except ObjectDoesNotExist:
            print('regroup keyword translation not found: ', transid, ' target group ', target_sense_group)
            continue
        original_order_index = trans.orderIndex

        if target_sense_group == original_order_index:
            continue
        if trans.language != changed_language:
            continue
        if trans.translation.text in keywords_per_sense[target_sense_group][changed_language.id]:
            # keyword already exists in target sense for language
            continue

        original_sense = order_sense_dict[original_order_index][changed_language]
        target_sense = order_sense_dict[target_sense_group][changed_language]
        try:
            original_sense.translations.remove(trans)
            trans.orderIndex = target_sense_group
            trans.save()
            target_sense.translations.add(trans)

            regrouped_keywords.append({'inputEltIndex': inx,
                                       'originalIndex': str(original_order_index),
                                       'orderIndex': str(target_sense_group),
                                       'language': str(changed_language.id),
                                       'trans_id': str(trans.id)})
        except (IntegrityError, DatabaseError, TransactionManagementError):
            print('regroup error saving translation object: ', gloss, trans, target_sense_group)
            continue

    deleted_sense_numbers = []
    deleted_translations = []
    new_translations = []
    glossXsenses = gloss_to_keywords_senses_groups(gloss, changed_language)

    updated_gloss_senses = get_state_of_gloss_senses(gloss)
    gloss_senses_state_is_changed(request, gloss, original_gloss_senses, updated_gloss_senses)

    glossXsenses['regrouped_keywords'] = regrouped_keywords
    glossXsenses['dataset_languages'] = dataset_languages
    glossXsenses['deleted_sense_numbers'] = deleted_sense_numbers
    glossXsenses['deleted_translations'] = deleted_translations
    glossXsenses['new_translations'] = new_translations

    return glossXsenses


def gloss_to_keywords_senses_groups_matrix(gloss):
    glossXsenses = dict()
    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    list_of_gloss_senses = [(gs.order, gs.sense) for gs in gloss_senses]
    sense_numbers = [gs.order for gs in gloss_senses]
    senses_groups = dict()
    keywords_translations = dict()
    translation_languages = gloss.lemma.dataset.translation_languages.all().order_by('id')
    for language in translation_languages:
        senses_groups[str(language.id)] = dict()
        keywords_translations[str(language.id)] = []
        for sense_index in sense_numbers:
            senses_groups[str(language.id)][str(sense_index)] = []
    for order, sense in list_of_gloss_senses:
        for language in translation_languages:
            translations_for_language_for_sense = sense.senseTranslations.get(language=language)
            for trans in translations_for_language_for_sense.translations.all().order_by('index'):
                keywords_translations[str(language.id)].append(trans.translation.text)
                senses_groups[str(language.id)][str(order)].append((str(trans.id), trans.translation.text))
    glossXsenses['glossid'] = str(gloss.id)
    glossXsenses['keywords'] = keywords_translations
    glossXsenses['senses_groups'] = senses_groups
    return glossXsenses


def mapping_add_keyword(request, glossid):
    """Add keywords"""
    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    gloss = get_object_or_404(Gloss, id=glossid)

    dataset_languages = [str(lang.id)
                         for lang in gloss.lemma.dataset.translation_languages.all().order_by('id')]
    translation_languages = gloss.lemma.dataset.translation_languages.all().order_by('id')

    keywords = request.POST.get('keywords')
    translation_list_str = json.loads(keywords)
    new_sense_keywords = [s.strip() for s in translation_list_str]

    languages_get = request.POST.get('languages')
    languages_list = json.loads(languages_get) if languages_get else []
    keywords_languages = [int(s) for s in languages_list]

    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    order_sense_tuples = [(gs.order, gs.sense) for gs in gloss_senses]
    current_senses = [gs.order for gs in gloss_senses]

    check_non_empty = list(set(new_sense_keywords))

    if len(check_non_empty) == 1 and check_non_empty[0] == '':
        # no text was filled in
        return {}

    sense_keywords = dict()
    for order, sense in order_sense_tuples:
        sense_keywords[order] = []
        for dataset_language in translation_languages:
            sense_trans = sense.senseTranslations.filter(language=dataset_language).first()
            if not sense_trans:
                # there is currently to SenseTranslation object for this language
                # this can happen if a sense was created in GlossDetailView
                sense_trans = SenseTranslation(language=dataset_language)
                sense_trans.save()
                sense.senseTranslations.add(sense_trans)
            for trans in sense_trans.translations.all():
                if trans.translation.text:
                    if trans.orderIndex != order:
                        print('mapping_add_keyword')
                        print('reset order index: ', gloss, order, trans.translation.text)
                        if trans.gloss == gloss:
                            trans.orderIndex = order
                            trans.save()
                        else:
                            print('trans gloss different than this gloss: ', trans.gloss)
                    sense_keywords[order].append(trans)

    # the indices just computed could differ if there are translations with keyword ''
    gloss_translation_indices = [trans.index for trans in gloss.translation_set.all()]

    if not current_senses:
        new_sense = 1
    else:
        new_sense = max(current_senses) + 1

    if not gloss_translation_indices:
        new_index = 1
    else:
        new_index = max(gloss_translation_indices) + 1
        if len(gloss_translation_indices) <= new_index:
            new_index += 1
        else:
            new_index = len(gloss_translation_indices) + 1

    # make a new sense and translations for it
    sense, sense_translations = create_empty_sense(gloss, new_sense)

    new_translations = []
    translations_row = dict()
    for inx, new_text in enumerate(new_sense_keywords):

        target_language_id = keywords_languages[inx]
        target_language = Language.objects.get(id=target_language_id)

        if not new_text:
            # these will set up an empty cell in the matrix
            new_translations.append({'new_text': '',
                                     'new_trans_id': '',
                                     'new_language': str(target_language_id)})
            translations_row[str(target_language_id)] = {'new_text': '',
                                                         'new_trans_id': ''}
            continue

        (keyword_object, created) = Keyword.objects.get_or_create(text=new_text)

        saved_translation = []
        # make a new translation using new sense number and new index numer
        try:
            trans = Translation(gloss=gloss, translation=keyword_object, index=new_index,
                                language=target_language, orderIndex=new_sense)
            trans.save()
            saved_translation.append(trans)
            new_index += 1
        except (IntegrityError, DatabaseError, TransactionManagementError):
            print('error creating translation: ', gloss, keyword_object.text, target_language, ' order ', new_sense)
            new_index += 1
            continue
        new_trans = saved_translation[0]
        new_translations.append({'new_text': new_text,
                                 'new_trans_id': str(new_trans.id),
                                 'new_language': str(target_language_id)})
        translations_row[str(target_language_id)] = {'new_text': new_text,
                                                     'new_trans_id': str(new_trans.id)}

        sense_language = sense_translations[target_language]
        sense_language.translations.add(new_trans)

    glossXsenses = gloss_to_keywords_senses_groups_matrix(gloss)

    # the newly created sense is updated indirectly in the above code
    # this retrieves its new translations as a string that includes both languages
    new_sense_string = str(sense)
    add_sense_to_revision_history(request, gloss, "", new_sense_string)

    # creating a new sense sends back extra info
    glossXsenses['new_translations'] = new_translations
    glossXsenses['translations_row'] = translations_row
    glossXsenses['new_sense'] = str(new_sense)
    glossXsenses['dataset_languages'] = dataset_languages

    return glossXsenses


def mapping_edit_senses_matrix(request, glossid):
    """Edit the keywords"""
    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    gloss = get_object_or_404(Gloss, id=glossid)

    original_gloss_senses = get_state_of_gloss_senses(gloss)

    # for some reason these assignments need to be done in the same way in all functions
    dataset_languages = [str(lang.id)
                         for lang in gloss.lemma.dataset.translation_languages.all().order_by('id')]
    translation_languages = gloss.lemma.dataset.translation_languages.all().order_by('id')

    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    order_sense_lookup = dict()
    for gs in gloss_senses:
        if gs.order in order_sense_lookup.keys():
            print('multiple senses with same sense number for gloss: ', gloss, gs.sense)
        else:
            order_sense_lookup[gs.order] = gs.sense
    current_sense_numbers = [gs.order for gs in gloss_senses]
    current_trans = []
    current_indices = []
    for order in order_sense_lookup.keys():
        sense = order_sense_lookup[order]
        for dataset_language in translation_languages:
            try:
                sense_trans = sense.senseTranslations.get(language=dataset_language)
            except ObjectDoesNotExist:
                # there should only be one
                sense_trans = SenseTranslation(language=dataset_language)
                sense_trans.save()
                sense.senseTranslations.add(sense_trans)
                # the new sense translation object is empty
                continue
            for trans in sense_trans.translations.all().order_by('index'):
                current_indices.append(trans.index)
                current_trans.append(trans)

    current_keywords = dict()
    for order in current_sense_numbers:
        current_keywords[order] = dict()
        for dataset_language in translation_languages:
            current_keywords[order][dataset_language.id] = [t.translation.text for t in current_trans
                                                            if t.orderIndex == order and t.language == dataset_language]

    if len(current_indices) < 1:
        new_index = 1
    else:
        new_index = max(current_indices) + 1
        if len(current_indices) <= new_index:
            new_index += 1
        else:
            new_index = len(current_indices) + 1

    new_translation_get = request.POST.get('new_translation')
    new_translation_list = json.loads(new_translation_get) if new_translation_get else []
    new_translation = [s.strip() for s in new_translation_list]

    new_language_get = request.POST.get('new_language')
    new_language_list = json.loads(new_language_get) if new_language_get else []
    new_language = [int(s) for s in new_language_list]

    new_order_index_get = request.POST.get('new_order_index')
    new_order_index_list = json.loads(new_order_index_get) if new_order_index_get else []
    new_order_index = [int(s) for s in new_order_index_list]

    language_get = request.POST.get('language')
    language_list = json.loads(language_get) if language_get else []
    language = [int(s) for s in language_list]

    trans_id_get = request.POST.get('trans_id')
    trans_id_list = json.loads(trans_id_get) if trans_id_get else []
    trans_id = [int(s) for s in trans_id_list]

    order_index_get = request.POST.get('order_index')
    order_index_list = json.loads(order_index_get) if order_index_get else []
    order_index = [int(s) for s in order_index_list]

    translation_get = request.POST.get('translation')
    translation_list_str = json.loads(translation_get) if translation_get else []
    translation = [s.strip() for s in translation_list_str]

    updated_translations = []
    deleted_translations = []
    # update the text fields
    for inx, transid in enumerate(trans_id):
        target_language = language[inx]
        target_sense_number = order_index[inx]
        target_text = translation[inx]
        language_obj = Language.objects.get(id=target_language)
        try:
            trans = Translation.objects.get(pk=transid)
        except ObjectDoesNotExist:
            print('update matrix translation does not exist: ', gloss, language_obj, ' id=', transid)
            continue

        if trans.translation.text == target_text and trans.orderIndex == target_sense_number:
            # nothing changed
            continue

        if target_text != "" and target_text in current_keywords[target_sense_number][target_language]:
            # attempt to put duplicate keyword in same sense number
            continue

        if target_text == "":
            original_sense = order_sense_lookup[target_sense_number]
            original_sense_translations = original_sense.senseTranslations.get(language=language_obj)
            original_sense_translations.translations.remove(trans)
            trans.delete()
            deleted_translations.append({ 'inputEltIndex': inx,
                                          'orderIndex': str(target_sense_number),
                                          'trans_id': str(transid),
                                          'language': str(target_language)})
        else:
            (keyword_object, created) = Keyword.objects.get_or_create(text=target_text)
            # the sense number should already be the same
            trans.orderIndex = target_sense_number
            trans.translation = keyword_object
            trans.save()
            updated_translations.append({ 'inputEltIndex': inx,
                                          'orderIndex': str(target_sense_number),
                                          'trans_id': str(trans.id),
                                          'language': str(target_language),
                                          'text': target_text })

    new_translations = []
    for inx, new_trans in enumerate(new_translation):
        if new_trans == '':
            continue
        target_language = new_language[inx]
        target_sense_number = new_order_index[inx]
        language_obj = Language.objects.get(id=target_language)

        if new_trans in current_keywords[target_sense_number][target_language]:
            # attempt to put duplicate keyword in same sense number
            continue
        if target_sense_number not in current_sense_numbers:
            # ignore this case, this should not happen
            continue

        original_sense = order_sense_lookup[target_sense_number]
        # above it was ensured that there is a SenseTranslation object for each language
        original_sense_translations = original_sense.senseTranslations.get(language=language_obj)

        (keyword_object, created) = Keyword.objects.get_or_create(text=new_trans)
        try:
            trans = Translation(gloss=gloss, translation=keyword_object,
                                language=language_obj, orderIndex=target_sense_number, index=new_index)
            trans.save()
            original_sense_translations.translations.add(trans)
        except (DatabaseError, IntegrityError, TransactionManagementError):
            print('edit_senses_matrix: Error saving new translation (gloss, keyword, language, order, index): ',
                        gloss, keyword_object, language_obj, target_sense_number, new_index)
            new_index = new_index + 1
            continue

        new_index = new_index + 1
        new_translations.append({ 'inputEltIndex': inx,
                                  'orderIndex': str(target_sense_number),
                                  'trans_id': str(trans.id),
                                  'language': str(target_language),
                                  'text': new_trans })

    deleted_sense_numbers = delete_empty_senses(gloss)

    glossXsenses = gloss_to_keywords_senses_groups_matrix(gloss)

    updated_gloss_senses = get_state_of_gloss_senses(gloss)
    gloss_senses_state_is_changed(request, gloss, original_gloss_senses, updated_gloss_senses)

    glossXsenses['new_translations'] = new_translations
    glossXsenses['updated_translations'] = updated_translations
    glossXsenses['deleted_translations'] = deleted_translations
    glossXsenses['deleted_sense_numbers'] = deleted_sense_numbers
    glossXsenses['translation_languages'] = dataset_languages

    return glossXsenses


@permission_required('dictionary.change_gloss')
def mapping_toggle_sense_tag(request, glossid):

    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    gloss = get_object_or_404(Gloss, id=glossid)

    current_tags = [ tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    change_sense_tag = Tag.objects.get_or_create(name='check_senses')
    (sense_tag, created) = change_sense_tag

    if sense_tag.id not in current_tags:
        Tag.objects.add_tag(gloss, 'check_senses')
    else:
        # delete tag from object
        tagged_obj = TaggedItem.objects.get(object_id=gloss.id,tag_id=sense_tag.id)
        tagged_obj.delete()

    new_tag_ids = [tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    result = dict()
    result['glossid'] = str(gloss.id)
    newvalue = [tag.name.replace('_',' ') for tag in Tag.objects.filter(id__in=new_tag_ids)]
    result['tags_list'] = newvalue

    return result
