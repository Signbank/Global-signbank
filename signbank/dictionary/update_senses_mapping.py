from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import permission_required
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag

from signbank.dictionary.models import *
from signbank.dictionary.forms import *


def gloss_to_keywords_senses_groups(gloss, language):
    glossXsenses = dict()
    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    list_of_gloss_senses = [(gs.order, gs.sense) for gs in gloss_senses]
    senses_groups = dict()
    keywords_list = []
    for order, sense in list_of_gloss_senses:
        senses_groups[order] = []
        translations_for_language_for_sense = sense.senseTranslations.get(language=language)
        for trans in translations_for_language_for_sense.translations.all().order_by('index'):
            if trans.orderIndex != order:
                print(trans, ' has wrong order index: ', trans)
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

    dataset_languages = [str(lang.id) for lang
                         in gloss.lemma.dataset.translation_languages.all().order_by('id')]

    order_index_get = request.POST.get('order_index')
    order_index_list_str = json.loads(order_index_get)
    order_index = [int(s) for s in order_index_list_str]

    trans_id_get = request.POST.get('trans_id')
    trans_id_list_str = json.loads(trans_id_get)
    trans_id = [int(s) for s in trans_id_list_str]

    language = request.POST.get('language', '')

    translation_get = request.POST.get('translation')
    translation_list_str = json.loads(translation_get)
    translation = [s for s in translation_list_str]

    language_obj = Language.objects.get(id=int(language))

    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    order_sense_tuples = [(gs.order, gs.sense) for gs in gloss_senses]
    current_keywords = dict()
    for order, sense in order_sense_tuples:
        current_keywords[order] = []
        sense_trans = sense.senseTranslations.get(language=language_obj)
        for trans in sense_trans.translations.all():
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
                                         'language': str(language)})
            continue

        # new text is not in current keywords
        # fetch or create the text and update the translation object
        (keyword_object, created) = Keyword.objects.get_or_create(text=new_text)
        keyword_to_update.translation = keyword_object
        keyword_to_update.save()

    glossXsenses = gloss_to_keywords_senses_groups(gloss, language_obj)
    glossXsenses['regrouped_keywords'] = []
    glossXsenses['dataset_languages'] = dataset_languages
    glossXsenses['deleted_translations'] = deleted_translations
    glossXsenses['deleted_sense_numbers'] = []

    return glossXsenses


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


def delete_empty_senses(gloss):

    translation_languages = gloss.lemma.dataset.translation_languages.all().order_by('id')
    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    order_sense_dict = dict()
    for glosssense in gloss_senses:
        order_sense_dict[glosssense.order] = dict()
        for dataset_language in translation_languages:
            order_sense_dict[glosssense.order][dataset_language] = glosssense.sense.senseTranslations.get(language=dataset_language)

    senses_to_delete = []
    for order in order_sense_dict.keys():
        if order == 1:
            # don't delete first sense
            continue
        count_keywords = 0
        for lang in order_sense_dict[order].keys():
            sense_trans = order_sense_dict[order][lang]
            count_keywords += sense_trans.translations.all().count()
        if count_keywords == 0:
            senses_to_delete.append(order)

    deleted_sense_numbers = []
    for order in senses_to_delete:
        gloss_sense = GlossSense.objects.filter(gloss=gloss, order=order).first()
        if not gloss_sense:
            continue
        sense = gloss_sense.sense
        for sensetranslation in sense.senseTranslations.all():
            # there are no translation objects for this sense
            sense.senseTranslations.remove(sensetranslation)
            sensetranslation.delete()
        gloss_sense.delete()
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
        for dataset_language in translation_languages:
            order_sense_dict[glosssense.order][dataset_language] = glosssense.sense.senseTranslations.get(language=dataset_language)

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
    glossXsenses = gloss_to_keywords_senses_groups(gloss, changed_language)
    glossXsenses['regrouped_keywords'] = regrouped_keywords
    glossXsenses['dataset_languages'] = dataset_languages
    glossXsenses['deleted_sense_numbers'] = deleted_sense_numbers
    glossXsenses['deleted_translations'] = deleted_translations

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
            senses_groups[str(language.id)][sense_index] = []
    for order, sense in list_of_gloss_senses:
        for language in translation_languages:
            translations_for_language_for_sense = sense.senseTranslations.get(language=language)
            for trans in translations_for_language_for_sense.translations.all().order_by('index'):
                keywords_translations[str(language.id)].append(trans.translation.text)
                senses_groups[str(language.id)][order].append((str(trans.id), trans.translation.text))
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
    new_sense_keywords = [s for s in translation_list_str]

    languages_get = request.POST.get('languages')
    languages_list = json.loads(languages_get) if languages_get else []
    keywords_languages = [int(s) for s in languages_list]

    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    order_sense_tuples = [(gs.order, gs.sense) for gs in gloss_senses]
    current_senses = [gs.order for gs in gloss_senses]

    sense_keywords = dict()
    for order, sense in order_sense_tuples:
        sense_keywords[order] = []
        for dataset_language in translation_languages:
            sense_trans = sense.senseTranslations.get(language=dataset_language)
            for trans in sense_trans.translations.all():
                if trans.translation.text:
                    if trans.orderIndex != order:
                        print('different order index: ', gloss, sense, trans, order)
                    sense_keywords[order].append(trans)

    # the indices just computed could differ if there are translations with keyword ''
    gloss_translation_indices = [trans.index for trans in gloss.translation_set.all()]
    # the following is used to obtain translations for the gloss with the empty string keyword
    current_trans = gloss.translation_set.all()
    current_keywords_gloss = dict()
    for dataset_language in translation_languages:
        current_keywords_gloss[dataset_language.id] = [t.translation.text for t in current_trans.filter(language=dataset_language)]

    empty_translations_for_gloss = dict()
    for dataset_language in translation_languages:
        empty_translations_for_gloss[dataset_language.id] = []
        # get an empty string translation for this gloss for this language if it exists
        empty_translations = current_trans.filter(language=dataset_language, translation__text='')
        if empty_translations.count():
            empty_translations_for_gloss[dataset_language.id].append(empty_translations.first())

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

        # check if there are any '' translations for this gloss
        saved_translation = []
        if '' in current_keywords_gloss[target_language_id] and empty_translations_for_gloss[target_language_id]:
            # fetch the empty keyword's translation object and change its keyword if possible
            # legacy code added empty translations
            translation_to_update = empty_translations_for_gloss[target_language_id][0]
            try:
                translation_to_update.translation = keyword_object
                translation_to_update.orderIndex = new_sense
                translation_to_update.index = new_index
                translation_to_update.language = target_language
                translation_to_update.save()
                saved_translation.append(translation_to_update)
                new_index += 1
                # remove the reused empty keyword and empty translation from temporary storage
                empty_translations_for_gloss[target_language_id].pop(0)
                current_keywords_gloss[target_language_id].remove('')
            except (ObjectDoesNotExist, KeyError, IntegrityError, TransactionManagementError):
                # make a new translation if it didn't work to update
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
        else:
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
        translations_row[str(target_language)] = {'new_text': new_text,
                                                  'new_trans_id': str(new_trans.id)}

        sense_language = sense_translations[target_language]
        sense_language.translations.add(new_trans)

    glossXsenses = gloss_to_keywords_senses_groups_matrix(gloss)
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
    translation_languages = gloss.lemma.dataset.translation_languages.all().order_by('id')
    dataset_languages = [str(lang.id) for lang in translation_languages.order_by('id')]
    gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
    order_sense_dict = {gs.order: gs.sense for gs in gloss_senses}
    current_senses = [gs.order for gs in gloss_senses]
    translation_ids = []
    current_trans = []
    current_indices = []
    for order in order_sense_dict.keys():
        sense = order_sense_dict[order]
        for dataset_language in translation_languages:
            sense_trans = sense.senseTranslations.get(language=dataset_language)
            for trans in sense_trans.translations.all().order_by('index'):
                current_indices.append(trans.index)
                current_trans.append(trans)
                translation_ids.append(trans.id)

    current_keywords = dict()
    for order in current_senses:
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
    new_translation = [s for s in new_translation_list]

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
    translation = [s for s in translation_list_str]

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

        if trans.language != language_obj:
            print('update text of translation ', trans, ' (', transid, ') language does not match ', language_obj)
            # something is wrong with the form
            # this can occur if the dataset translation languages are not all sorted per id
            continue
        if trans.translation.text == target_text and trans.orderIndex == target_sense_number:
            # nothing changed
            continue

        if target_text != "" and target_text in current_keywords[target_sense_number][target_language]:
            # attempt to put duplicate keyword in same sense number
            continue

        if target_text == "":
            original_sense = order_sense_dict[target_sense_number]
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
        if target_sense_number not in current_senses:
            # ignore this case, this should not happen
            continue

        original_sense = order_sense_dict[target_sense_number]
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
    newvalue = [tag.name.replace('_',' ') for tag in  Tag.objects.filter(id__in=new_tag_ids)]
    result['tags_list'] = newvalue

    return result
