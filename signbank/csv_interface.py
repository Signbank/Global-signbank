
from signbank.dictionary.models import *
from signbank.dictionary.consistency_senses import check_consistency_senses
from django.utils.translation import override, gettext_lazy as _, activate
from signbank.settings.server_specific import LANGUAGES
from signbank.dictionary.update_senses_mapping import add_sense_to_revision_history


def create_empty_sense(gloss, order, erase=False):

    # make a new sense and translations for it
    translation_languages = gloss.lemma.dataset.translation_languages.all().order_by('id')
    sense_translations = dict()

    existing_senses = GlossSense.objects.filter(gloss=gloss, order=order)
    if existing_senses.count() > 1:
        print('create_empty_sense: multiple senses already exist: ', gloss, str(gloss.id), str(order), existing_senses)
        raise MultipleObjectsReturned
    if existing_senses:
        glosssense = existing_senses.first()
        sense_for_gloss = glosssense.sense
        for dataset_language in translation_languages:
            already_existing_sensetranslations = sense_for_gloss.senseTranslations.filter(language=dataset_language)
            if already_existing_sensetranslations.count() > 1:
                print('create_empty_sense: multiple sense translations exist for language: ', gloss, str(
                    gloss.id), str(order), glosssense, dataset_language, sense_for_gloss)
                raise MultipleObjectsReturned
            if already_existing_sensetranslations:
                existing_sensetranslation = already_existing_sensetranslations.first()
                if erase:
                    # force empty
                    for trans in existing_sensetranslation.translations.all():
                        existing_sensetranslation.translations.remove(trans)
                        trans.delete()
                sense_translations[dataset_language] = existing_sensetranslation
                continue
            glosssenselanguage = SenseTranslation(language=dataset_language)
            glosssenselanguage.save()
            sense_for_gloss.senseTranslations.add(glosssenselanguage)
            sense_translations[dataset_language] = glosssenselanguage
            continue
        return sense_for_gloss, sense_translations

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


def sense_examplesentences_for_language(gloss, language):
    # by the time this method is called, the consistency check has already been done on the Senses
    glosssenses = GlossSense.objects.filter(gloss=gloss).order_by('order')

    if not glosssenses:
        return ""
    gloss_senses = dict()
    for gs in glosssenses:
        order = gs.order
        sense = gs.sense
        if order in gloss_senses.keys():
            if settings.DEBUG_CSV:
                # if something is messed up with duplicate senses with the same number, just ignore
                print('ERROR: sense_examplesentences_for_language duplicate order: ', order)
                print(gloss, str(gloss.id), order, sense)
                continue
        gloss_senses[order] = sense

    activate(LANGUAGES[0][0])
    sentences_display_list = []
    for order in gloss_senses.keys():
        sense = gloss_senses[order]
        example_sentences = sense.exampleSentences.all()
        list_of_sentences = []
        for examplesentence in example_sentences:
            examplesentence_translations = examplesentence.examplesentencetranslation_set.filter(language=language)
            for sentence in examplesentence_translations:
                sentence_type_display = examplesentence.sentenceType.name if examplesentence.sentenceType else '-'
                sentence_tuple = (str(examplesentence.id), sentence_type_display, str(examplesentence.negative), sentence.text)
                list_of_sentences.append(sentence_tuple)
        if not list_of_sentences:
            continue
        sentences_display = []
        for (sid, stype, negative, text) in list_of_sentences:
            # does not use a comprehension because of possible nested parentheses in text fields
            tuple_reordered = '(' + str(order) + ', ' + sid + ', ' + stype + ', ' + negative + ', "' + text + '")'
            sentences_display.append(tuple_reordered)
        sorted_sentences_display = ' | '.join(sentences_display)
        sentences_display_list.append(sorted_sentences_display)
    if not sentences_display_list:
        return ""
    sentences_display = ' | '.join(sentences_display_list)
    return sentences_display


def map_values_to_sentence_type(values, include_sentences=True):
    map_errors = False
    activate(LANGUAGES[0][0])
    sentencetype_role_choices = [st.name for st in FieldChoice.objects.filter(field__iexact='SentenceType',
                                                                              machine_value__gt=1)]
    import re
    pattern_mapped_sorted_note_names = []
    for note_name in sentencetype_role_choices:
        escaped_note_name = re.sub(r'([()])', r'\\\1', note_name)
        pattern_mapped_sorted_note_names.append(escaped_note_name)

    sentence_types = '|'.join(pattern_mapped_sorted_note_names)
    if sentence_types:
        pattern_sentence_types = '(\-|N\/A|' + sentence_types + ')'
    else:
        pattern_sentence_types = '(\-|N\/A)'
    mapped_values = values

    if include_sentences:
        regex_string = r"\s?\(([1-9]), ([1-9][0-9]*), %s, (True|False), \"([^\"]+)\"\)\s?" % pattern_sentence_types
    else:
        regex_string = r"\s?\(([1-9]), ([1-9][0-9]*), %s, (True|False)\)\s?" % pattern_sentence_types
    find_all = re.findall(regex_string, mapped_values)
    if not find_all:
        map_errors = True
    return find_all, map_errors


def get_sense_numbers(gloss):
    # by the time this method is called, the consistency check has already been done on the Senses
    glosssenses = GlossSense.objects.filter(gloss=gloss).order_by('order')

    if not glosssenses:
        return []
    gloss_senses = dict()
    for gs in glosssenses:
        order = gs.order
        sense = gs.sense
        if order in gloss_senses.keys():
            if settings.DEBUG_CSV:
                # if something is messed up with duplicate senses with the same number, just ignore
                print('ERROR: get_sense_numbers duplicate order: ', str(gloss.id), str(order))
                continue
        gloss_senses[order] = sense

    sense_numbers = [str(order) for order in gloss_senses.keys()]
    return sense_numbers


def get_senses_to_sentences(gloss):
    # by the time this method is called, the consistency check has already been done on the Senses
    glosssenses = GlossSense.objects.filter(gloss=gloss).order_by('order')

    if not glosssenses:
        return []
    gloss_senses = dict()
    gloss_senses_to_sentences_dict = dict()
    for gs in glosssenses:
        order = gs.order
        sense = gs.sense
        if order in gloss_senses.keys():
            if settings.DEBUG_CSV:
                # if something is messed up with duplicate senses with the same number, just ignore
                print('ERROR: get_sense_numbers duplicate order: ', str(gloss.id), str(order))
                continue
        gloss_senses[order] = sense
        sense_sentences = sense.exampleSentences.all()
        gloss_senses_to_sentences_dict[str(order)] = [str(sentence.id) for sentence in sense_sentences]

    return gloss_senses_to_sentences_dict


def parse_sentence_row(row_nr, sentence_dict):
    errors = []
    sentence_fields = '(' + sentence_dict['order'] + ', ' + sentence_dict['sentence_type'] + ', ' + sentence_dict['negative'] + ')'
    find_all, map_errors = map_values_to_sentence_type(sentence_fields, include_sentences=False)
    if map_errors:
        errors += ['Row '+row_nr + ': Error parsing sentence columns Sense Number, Sentence Type, Negative: '+sentence_fields]
    gloss_pk = sentence_dict['gloss_pk']
    try:
        dataset = Dataset.objects.get(acronym=sentence_dict['dataset'])
    except ObjectDoesNotExist:
        dataset = None
        errors += ['Row '+row_nr + ': Dataset '+sentence_dict['dataset']+' does not exist']
    try:
        gloss = Gloss.objects.get(pk=int(gloss_pk))
    except (ObjectDoesNotExist, ValueError, MultipleObjectsReturned):
        gloss = None
        errors += ['Row '+row_nr + ': Gloss ID '+gloss_pk+' does not exist.']
    if gloss and dataset and gloss.lemma and gloss.lemma.dataset != dataset:
        errors += ['Row '+row_nr + ': Gloss '+gloss_pk+' is not in dataset '+sentence_dict['dataset']+'.']
    if gloss:
        gloss_senses = get_sense_numbers(gloss)
        if sentence_dict['order'] not in gloss_senses:
            errors += ['Row '+row_nr + ': Gloss '+gloss_pk+' does not have a Sense Number '+sentence_dict['order']+'.']
    return errors


def update_sentences_parse(sense_numbers, sense_numbers_to_sentences, new_sentences_string):
    """CSV Import Update check the parsing of the senses field"""

    if not new_sentences_string:
        # do nothing
        return True

    new_sentences = [k for k in new_sentences_string.split(' | ')]

    new_sentence_tuples = []
    for sentence_tuple in new_sentences:
        find_all, map_errors = map_values_to_sentence_type(sentence_tuple)
        if map_errors or not find_all:
            # examine errors
            continue
        new_sentence_tuples.append(find_all[0])

    if settings.DEBUG_CSV:
        print('Parsed sentence tuples: ', new_sentence_tuples)

    sentence_ids = []
    for order, sentence_id, sentence_type, negative, sentence_text in new_sentence_tuples:
        if order not in sense_numbers:
            return False
        if order not in sense_numbers_to_sentences.keys():
            return False
        if sentence_id not in sense_numbers_to_sentences[order]:
            return False
        sentence_ids.append(sentence_id)
    if len(sentence_ids) != len(list(set(sentence_ids))):
        # updates to same sentence in two different tuples
        return False

    return True


def sentence_tuple_list_to_string(sentence_tuple_string):
    tuple_list_of_strings = []

    if not sentence_tuple_string:
        return tuple_list_of_strings
    print(sentence_tuple_string, type(sentence_tuple_string))
    sentences = [k for k in sentence_tuple_string.split(' | ')]

    for sentence_tuple in sentences:
        find_all, map_errors = map_values_to_sentence_type(sentence_tuple)
        if map_errors or not find_all:
            # skip any non-parsing tuples, this was already checked so should not happen
            continue
        tuple_list_of_strings.append(find_all[0])

    return tuple_list_of_strings


def csv_sentence_tuples_list_compare(gloss_id, sentence_string_old, sentence_string_new, errors_found):
    # convert input to list of tuples (order, sentence_id, sentence_type, negative, sentence_text)
    sentence_tuples_old = sentence_tuple_list_to_string(sentence_string_old)
    sentence_tuples_new = sentence_tuple_list_to_string(sentence_string_new)

    different_org = []
    different_new = []
    errors = errors_found
    original_sentences_lookup = {sid: (so, styp, sn, stxt)
                                 for (so, sid, styp, sn, stxt) in sentence_tuples_old}
    for (order, sentence_id, sentence_type, negative, sentence_text) in sentence_tuples_new:
        if (order, sentence_type, negative, sentence_text) != original_sentences_lookup[sentence_id]:
            (sord, styp, sneg, stxt) = original_sentences_lookup[sentence_id]
            if sord != order:
                errors += ['ERROR Gloss ' + gloss_id + ': The Sense Number cannot be modified in CSV Update.']
            if styp != sentence_type:
                errors += ['ERROR Gloss ' + gloss_id + ': The Sentence Type cannot be modified in CSV Update.']
            if sneg != negative:
                errors += ['ERROR Gloss ' + gloss_id + ': The Sentence Negative cannot be modified in CSV Update.']
            if errors:
                continue
            tuple_string_new = '(' + order + ', ' + sentence_id + ', ' + sentence_type \
                               + ', ' + negative + ', "' + sentence_text + '")'
            different_new.append(tuple_string_new)
            tuple_string_org = '(' + sord + ', ' + sentence_id + ', ' + styp \
                               + ', ' + sneg + ', "' + stxt + '")'
            different_org.append(tuple_string_org)
    difference_new = ' | '.join(different_new)
    difference_org = ' | '.join(different_org)
    return difference_org, difference_new, errors


def csv_update_sentences(gloss, language, new_sentences_string, update=False):
    """CSV Import Update the senses field"""
    # this function assumes the new_senses_string is correctly parsed
    # the function update_senses_parse tests this
    # the sense numbers in the new_senses_string are unique numbers between 1 and 9
    if settings.DEBUG_CSV:
        print('call to csv_update_sentences: ', gloss, str(gloss.id), language, new_sentences_string)
    if not new_sentences_string:
        return

    new_sentences = [k for k in new_sentences_string.split(' | ')]

    glosssenses = GlossSense.objects.filter(gloss=gloss).order_by('order')

    if not glosssenses:
        return ""
    gloss_senses = dict()
    for gs in glosssenses:
        order = gs.order
        sense = gs.sense
        if order in gloss_senses.keys():
            print('ERROR: csv_update_sentences: duplicate order: ', order)
            print(gloss, str(gloss.id), order, sense)
        gloss_senses[order] = sense

    current_sentences_string = sense_examplesentences_for_language(gloss, language)
    if settings.DEBUG_CSV:
        print('Existing sentences: ', current_sentences_string)

    new_sentence_tuples = []
    for sentence_tuple in new_sentences:
        find_all, map_errors = map_values_to_sentence_type(sentence_tuple)
        if map_errors or not find_all:
            # examine errors
            if settings.DEBUG_CSV:
                print('ERROR: Parsing error sentence tuple: ', sentence_tuple)
            continue
        new_sentence_tuples.append(find_all[0])

    activate(LANGUAGES[0][0])
    sentencetype_roles_to_type = {st.name: st
                                  for st in FieldChoice.objects.filter(field__iexact='SentenceType')}

    new_sentences_list = []
    for order, sentence_id, sentence_type, negative, sentence_text in new_sentence_tuples:
        new_sentence_dict = dict()
        new_sentence_dict['order'] = int(order)
        new_sentence_dict['sentence_id'] = int(sentence_id)
        new_sentence_dict['sentence_type'] = sentencetype_roles_to_type[sentence_type]
        new_sentence_dict['negative'] = negative == 'True'
        new_sentence_dict['sentence_text'] = sentence_text
        new_sentences_list.append(new_sentence_dict)

    if settings.DEBUG_CSV:
        print('Sentences to update: ', new_sentences_list)

    if not update:
        if settings.DEBUG_CSV:
            print('Sentences to update: update set to False')
        return

    for sentence_dict in new_sentences_list:
        sense = gloss_senses[sentence_dict['order']]

        sentence_id = sentence_dict['sentence_id']
        try:
            examplesentence = ExampleSentence.objects.get(id=sentence_id)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            continue

        examplesentence.negative = sentence_dict['negative']
        examplesentence.sentenceType = sentence_dict['sentence_type']
        examplesentence.save()

        try:
            sentence_translation = ExampleSentenceTranslation.objects.get(language=language,
                                                                          examplesentence=examplesentence)
        except ObjectDoesNotExist:
            sentence_translation = ExampleSentenceTranslation(language=language,
                                                              examplesentence=examplesentence)
        sentence_translation.text = sentence_dict['sentence_text']
        sentence_translation.save()


def csv_create_sentence(gloss, dataset_languages, sentence_to_create, create=False):
    """CSV Import Update the senses field"""
    if settings.DEBUG_CSV:
        print('call to csv_create_sentence: ', gloss, str(gloss.id), sentence_to_create)

    glosssenses = GlossSense.objects.filter(gloss=gloss).order_by('order')

    if not glosssenses:
        return ""
    gloss_senses = dict()
    for gs in glosssenses:
        order = gs.order
        sense = gs.sense
        if order in gloss_senses.keys():
            print('ERROR: csv_update_sentences: duplicate order: ', order)
            print(gloss, str(gloss.id), order, sense)
        gloss_senses[order] = sense

    activate(LANGUAGES[0][0])
    sentencetype_roles_to_type = {st.name: st
                                  for st in FieldChoice.objects.filter(field__iexact='SentenceType')}

    new_sentence_dict = dict()
    new_sentence_dict['order'] = int(sentence_to_create['order'])
    new_sentence_dict['sentence_type'] = sentencetype_roles_to_type[sentence_to_create['sentence_type']]
    new_sentence_dict['negative'] = sentence_to_create['negative'] == 'True'

    if not create:
        if settings.DEBUG_CSV:
            print('New sentences to create: create set to False')
        return

    sense = gloss_senses[new_sentence_dict['order']]

    examplesentence = ExampleSentence(negative=new_sentence_dict['negative'],
                                      sentenceType=new_sentence_dict['sentence_type'])
    examplesentence.save()
    sense.exampleSentences.add(examplesentence)

    for language in dataset_languages:
        sentence_text = sentence_to_create['sentence_text_'+language.language_code_2char]
        sentence_translation = ExampleSentenceTranslation(language=language,
                                                          examplesentence=examplesentence,
                                                          text=sentence_text)
        sentence_translation.save()


def sense_translations_for_language(gloss, language):
    # This finds the sense translations for one language
    # It is used for export of CSV
    # It is used again for import CSV update
    # The exact same function is used in order to identify whether a cell has been modified
    # The code is flattened out, avoiding usage of 'join' on empty lists
    # The 'join' on empty lists causes problems with spaces not matching
    # The SenseTranslation get_translations method causes problems with spaces not matching

    check_consistency_senses(gloss, delete_empty=True)
    glosssenses = GlossSense.objects.filter(gloss=gloss).order_by('order')

    if not glosssenses:
        return ""
    gloss_senses = dict()
    for gs in glosssenses:
        order = gs.order
        sense = gs.sense
        if order in gloss_senses.keys():
            print('ERROR: duplicate order: ', order)
            print(gloss, str(gloss.id), order, sense)
        gloss_senses[order] = sense

    translations_per_language = []
    for order, sense in gloss_senses.items():
        sensetranslations = sense.senseTranslations.filter(language=language)
        if not sensetranslations.count():
            if settings.DEBUG_CSV:
                print('No sensetranslation object for ', gloss, ' ( ', str(gloss.id), ') ', language)
            continue
        elif sensetranslations.count() > 1:
            if settings.DEBUG_CSV:
                print('Multiple sensetranslation objects for ', gloss, ' ( ', str(gloss.id), ') ', sensetranslations)
        sensetranslation = sensetranslations.first()
        keywords_list = []
        translations = sensetranslation.translations.all().order_by('index')
        for translation in translations:
            keywords_list.append(translation.translation.text)
        if keywords_list:
            keywords = ', '.join(keywords_list)
            sense_translations = str(order) + '. ' + keywords
            translations_per_language.append(sense_translations)
    if translations_per_language:
        sense_translations = ' | '.join(translations_per_language)
    else:
        sense_translations = ""
    if settings.DEBUG_CSV:
        print(gloss, str(gloss.id), language, sense_translations)
    return sense_translations


def update_senses_parse(new_senses_string):
    """CSV Import Update check the parsing of the senses field"""

    if not new_senses_string:
        # do nothing
        return True

    new_senses = [k for k in new_senses_string.split(' | ')]
    order_list = []
    for ns in new_senses:
        try:
            order_string, keywords_string = ns.split('. ')
        except ValueError:
            # incorrect separator between sense number and keywords
            if settings.DEBUG_CSV:
                print('first error: ', ns)
            return False
        try:
            order = int(order_string)
        except ValueError:
            # sense is not a number
            if settings.DEBUG_CSV:
                print('second error: ', ns, order_string, keywords_string)
            return False
        if order not in range(1, 9):
            # sense out of range
            if settings.DEBUG_CSV:
                print('third error: ', ns, order, keywords_string)
            return False
        if order in order_list:
            # duplicate sense number found
            if settings.DEBUG_CSV:
                print('fourth error: ', ns, order, keywords_string)
            return False
        order_list.append(order)
        if not keywords_string:
            if settings.DEBUG_CSV:
                # no keywords specified
                print('fifth error: ', ns)
                return False
        try:
            keywords_list = keywords_string.split(', ')
        except ValueError:
            if settings.DEBUG_CSV:
                print('sixth error: ', ns, order, keywords_string)
            return False
        if len(keywords_list) != len(list(set(keywords_list))):
            # duplicates in same sense
            if settings.DEBUG_CSV:
                print('seventh error: ', ns, order, keywords_list)
            return False

    return True


def sense_translations_for_language_mapping(gloss, language):

    sense_keywords_mapping = dict()
    glosssenses = GlossSense.objects.all().prefetch_related('sense').filter(gloss=gloss).order_by('order')
    if not glosssenses:
        return sense_keywords_mapping

    gloss_senses = dict()
    for gs in glosssenses:
        gloss_senses[gs.order] = gs.sense
    for order, sense in gloss_senses.items():
        sensetranslations = sense.senseTranslations.filter(language=language)
        if not sensetranslations.count():
            if settings.DEBUG_CSV:
                print('No sensetranslation object for ', gloss, ' ( ', str(gloss.id), ') ', language)
            continue
        elif sensetranslations.count() > 1:
            if settings.DEBUG_CSV:
                print('Multiple sensetranslation objects for ', gloss, ' ( ', str(gloss.id), ') ', sensetranslations)
        sensetranslation = sensetranslations.first()
        keywords_list = []
        translations = sensetranslation.translations.all().order_by('index')
        for translation in translations:
            keywords_list.append(translation.translation.text)
        if keywords_list:
            sense_keywords_mapping[order] = keywords_list
    if settings.DEBUG_CSV:
        print('sense_translations_for_language_mapping: ', gloss, str(gloss.id), language, sense_keywords_mapping)
    return sense_keywords_mapping


def csv_create_senses(request, gloss, language, new_senses_string, create=False):
    """CSV Import Update the senses field"""
    # this function assumes the new_senses_string is correctly parsed
    # the function update_senses_parse tests this
    # the sense numbers in the new_senses_string are unique numbers between 1 and 9
    # the request argument is needed to save the user sense creation in the Gloss Revision History
    if settings.DEBUG_CSV:
        print('call to csv_create_senses: ', gloss, str(gloss.id), language, '"', new_senses_string, '"')
    if not new_senses_string:
        return

    current_senses_string = sense_translations_for_language(gloss, language)
    if current_senses_string:
        # update of senses is not done by this method
        return

    new_senses = [k.strip() for k in new_senses_string.split(' | ')]

    new_senses_dict = dict()
    for ns in new_senses:
        order_string, keywords_string = ns.split('. ')
        keywords_list_split = keywords_string.split(', ')
        keywords_list = [kw.strip() for kw in keywords_list_split]
        new_senses_dict[int(order_string)] = keywords_list

    if settings.DEBUG_CSV:
        print('new senses to create: ', new_senses_dict)
    gloss_senses = GlossSense.objects.filter(gloss=gloss)

    if not gloss_senses:
        # there are currently no senses for this gloss, create an empty 1st one
        # in case the user has started numbering at something other than 1, get this
        new_senses_orders = sorted(ns for ns in new_senses_dict.keys())
        if settings.DEBUG_CSV:
            print('new sense orders: ', new_senses_orders)
        if create:
            if settings.DEBUG_CSV:
                print('csv_create_senses create: ', gloss, new_senses_string, new_senses_orders)
            # there are currently no senses for this gloss
            create_empty_sense(gloss, new_senses_orders[0], erase=True)

    if not create:
        return

    revisions = []
    for order, keywords in new_senses_dict.items():
        sense, sense_translations = create_empty_sense(gloss, order, erase=False)
        gloss_sense_translation = sense_translations[language]
        for inx, keyword in enumerate(keywords, 1):
            (keyword_object, created) = Keyword.objects.get_or_create(text=keyword)
            translation = Translation.objects.create(gloss=gloss,
                                                     language=language,
                                                     orderIndex=order,
                                                     translation=keyword_object,
                                                     index=inx)
            translation.save()
            gloss_sense_translation.translations.add(translation)
        sense_new_value = str(sense)
        revisions.append(('', sense_new_value))

    for sense_old_value, sense_new_value in revisions:
        add_sense_to_revision_history(request, gloss, sense_old_value, sense_new_value)
