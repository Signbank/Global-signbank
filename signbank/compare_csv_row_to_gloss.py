import re
import copy

from django.utils.translation import activate, gettext

from signbank.settings.server_specific import LANGUAGES, DEBUG_CSV, DEFAULT_LANGUAGE_HEADER_COLUMN
from signbank.dictionary.models import (Gloss, Morpheme, MorphologyDefinition, Relation, FieldChoice, SignLanguage, Dialect,
                                        Language, SemanticField)
from signbank.dictionary.update_csv import validate_and_resolve_gloss_relations
from signbank.csv_interface import (update_sentences_parse, sense_examplesentences_for_language, get_sense_numbers,
                                    get_senses_to_sentences, csv_sentence_tuples_list_compare, sense_translations_for_language,
                                    update_senses_parse)
from tagging.models import TaggedItem, Tag


def get_default_annotationidglosstranslation(gloss):
    if not gloss.lemma or not gloss.lemma.dataset:
        return str(gloss.id)
    dataset = gloss.lemma.dataset
    language = dataset.default_language
    if not language:
        language = dataset.translation_languages.first()

    annotationidglosstranslations = gloss.annotationidglosstranslation_set.all()

    if not annotationidglosstranslations:
        return str(gloss.id)

    if annotationidglosstranslations.filter(language=language):
        return annotationidglosstranslations.get(language=language).text

    return annotationidglosstranslations.first().text


def check_existence_simultaneous_morphology(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    tuples_list = []
    checked = ''

    # check syntax
    for new_value_tuple in values:
        try:
            (morpheme, role) = new_value_tuple.split(':')
            role = role.strip()
            morpheme = morpheme.strip()
            tuples_list.append((morpheme, role))
        except ValueError:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), formatting error in Simultaneous MorphMorphologyDefinitionology: {input}. Tuple morpheme:role expected.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), input=str(new_value_tuple))
            errors.append(error_string)

    for (morpheme, role) in tuples_list:

        filter_morphemes = Morpheme.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                                   annotationidglosstranslation__language=gloss.lemma.dataset.default_language,
                                                   annotationidglosstranslation__text__exact=morpheme).distinct()

        if not filter_morphemes:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), new Simultaneous Morphology morpheme '{morpheme}' not found.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), morpheme=str(morpheme))
            errors.append(error_string)
            continue
        elif filter_morphemes.count() > 1:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), multiple matches found for Simultaneous Morphology morpheme '{morpheme}'.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), morpheme=morpheme)
            errors.append(error_string)
            continue
        morpheme_gloss = filter_morphemes.first()
        if not morpheme_gloss or not morpheme_gloss.is_morpheme():
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), new Simultaneous Morphology morpheme '{morpheme}' is not a morpheme.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), morpheme=str(morpheme))
            errors.append(error_string)
            continue
        if checked:
            checked += ',' + ':'.join([morpheme, role])
        else:
            checked = ':'.join([morpheme, role])

    return checked, errors

def compare_simultaneous_morphology(gloss, new_human_value, human_key, errors_found, differences):
    if new_human_value in ['None', '', '-']:
        return errors_found, differences

    morphemes = [(get_default_annotationidglosstranslation(m.morpheme), m.role)
                 for m in gloss.simultaneous_morphology.filter(parent_gloss__archived__exact=False)]
    sim_morphs = []
    for m in morphemes:
        sim_morphs.append(':'.join(m))
    simultaneous_morphemes = ','.join(sim_morphs)

    new_human_value_list = new_human_value.split(',')

    (checked_new_human_value, errors) = check_existence_simultaneous_morphology(gloss, new_human_value_list)

    if len(errors):
        errors_found += errors
        return errors_found, differences

    elif simultaneous_morphemes == checked_new_human_value:
        return errors_found, differences

    differences.append({'pk': gloss.pk,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': simultaneous_morphemes,
                        'original_human_value': simultaneous_morphemes,
                        'new_machine_value': checked_new_human_value,
                        'new_human_value': checked_new_human_value,
                        'side_effects': {}})
    return errors_found, differences


def check_existence_sequential_morphology(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)
    new_values = values.split(' + ')
    errors = []
    found = []
    not_found = []
    for new_value in new_values:
        filter_morphemes = Gloss.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                                annotationidglosstranslation__language=gloss.lemma.dataset.default_language,
                                                annotationidglosstranslation__text__exact=new_value).distinct()
        if not filter_morphemes:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), new Sequential Morphology gloss '{value}' not found.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), value=new_value)
            errors.append(error_string)
            not_found += [new_value]
            continue
        elif filter_morphemes.count() > 1:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), multiple matches found for Sequential Morphology gloss '{value}'.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), value=new_value)
            errors.append(error_string)
            continue
        else:
            found += [new_value]

    if len(new_values) > 4:
        error_string = gettext(
            "For gloss '{annotation}' ({glossid}), too many Sequential Morphology components.").format(
            annotation=default_annotationidglosstranslation, glossid=str(gloss.pk))
        errors.append(error_string)

    return found, not_found, errors


def compare_sequential_morphology(gloss, new_human_value, human_key, errors_found, differences):
    if new_human_value in ['None', '', '-']:
        return errors_found, differences

    morphemes = [get_default_annotationidglosstranslation(morpheme.morpheme)
                 for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]
    morphemes_string = " + ".join(morphemes)

    (found, not_found, errors) = check_existence_sequential_morphology(gloss, new_human_value)

    if len(errors):
        errors_found += errors
        return errors_found, differences

    elif morphemes_string == new_human_value:
        return errors_found, differences

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': morphemes_string,
                        'original_human_value': morphemes_string,
                        'new_machine_value': new_human_value,
                        'new_human_value': new_human_value,
                        'side_effects': {}})
    return errors_found, differences


def check_existence_blend_morphology(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    tuples_list = []
    checked = ''

    # check syntax
    for new_value_tuple in values:
        try:
            (morpheme, role) = new_value_tuple.split(':')
            role = role.strip()
            morpheme = morpheme.strip()
            tuples_list.append((morpheme, role))
        except ValueError:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), formatting error in Blend Morphology: {input}. Tuple gloss:role expected.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), input=str(new_value_tuple))
            errors.append(error_string)

    for (morpheme, role) in tuples_list:

        filter_glosses = Gloss.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                              annotationidglosstranslation__text__exact=morpheme).distinct()

        if not filter_glosses:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), new Blend Morphology gloss '{morpheme}' not found.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), morpheme=morpheme)
            errors.append(error_string)
            continue
        elif filter_glosses.count() > 1:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), multiple matches found for Blend Morphology gloss '{morpheme}'.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), morpheme=morpheme)
            errors.append(error_string)
            continue
        if checked:
            checked += ',' + ':'.join([morpheme, role])
        else:
            checked = ':'.join([morpheme, role])

    return checked, errors


def compare_blend_morphology(gloss, new_human_value, human_key, errors_found, differences):
    if new_human_value in ['None', '', '-']:
        return errors_found, differences

    morphemes = [(get_default_annotationidglosstranslation(m.glosses), m.role)
                 for m in gloss.blend_morphology.filter(parent_gloss__archived__exact=False,
                                                        glosses__archived__exact=False)]

    ble_morphs = []
    for m in morphemes:
        ble_morphs.append(':'.join(m))
    blend_morphemes = ','.join(ble_morphs)

    new_human_value_list = [v.strip() for v in new_human_value.split(',')]

    (checked_new_human_value, errors) = check_existence_blend_morphology(gloss, new_human_value_list)

    if len(errors):
        errors_found += errors
        return errors_found, differences

    if blend_morphemes == checked_new_human_value:
        return errors_found, differences

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': blend_morphemes,
                        'original_human_value': blend_morphemes,
                        'new_machine_value': checked_new_human_value,
                        'new_human_value': checked_new_human_value,
                        'side_effects': {}})
    return errors_found, differences


def check_existence_relations(gloss, values):
    # used by Import CSV Update
    # values representing relations are checked and sorted as per the display method of the model
    # any new reverse relations are put into dict side_effects for display in the template
    checked = ''
    side_effects = dict()
    errors = []

    if values == [""]:
        return checked, side_effects, errors

    values_mapped_to_objects, errors = validate_and_resolve_gloss_relations(gloss, values)

    if errors:
        row_error = gettext(
            "For gloss '{annotation}' ({glossid}), errors found in column Relations to other signs.").format(
            annotation=get_default_annotationidglosstranslation(gloss), glossid=str(gloss.pk))
        errors = [row_error] + errors
        return checked, side_effects, errors

    gloss_relations = [(relation.source, relation.role_fk, relation.target)
                       for relation in Relation.objects.filter(source=gloss).order_by('role_fk__machine_value')]
    checked_relations = []
    for (role, target) in values_mapped_to_objects:
        if (gloss, role, target) in gloss_relations:
            # checked_relations contains tuples in the display format
            checked_relations.append((role.name, get_default_annotationidglosstranslation(target)))
            continue
        target_annotation = get_default_annotationidglosstranslation(target)
        if target_annotation not in side_effects.keys():
            side_effects[target_annotation] = []
        side_effects[target_annotation].append({'source_pk': target.pk,
                                                'role': role.reverse_relation_role(),
                                                'target': get_default_annotationidglosstranslation(gloss)})

    # remove duplicates and sort
    checked_relations = list(set(checked_relations))
    checked_relations = sorted(checked_relations, key=lambda tup: tup[1])

    checked = ','.join([f'{role_name}:{target_annotation}'
                        for (role_name, target_annotation) in checked_relations])
    return checked, side_effects, errors


def compare_relations(gloss, new_human_value, human_key, errors_found, differences):
    relations = [(relation.role_fk.name, get_default_annotationidglosstranslation(relation.target))
                 for relation in gloss.get_relations()]
    # remove duplicates and sort
    relations = list(set(relations))
    relations = sorted(relations, key=lambda tup: tup[1])
    current_relations_string = ','.join([f'{role}:{annotation}' for (role, annotation) in relations])

    if new_human_value in ['None', ''] and not relations:
        return errors_found, differences

    new_human_value_list = [v.strip() for v in new_human_value.split(',')]

    (checked_new_human_value, side_effects, errors) = check_existence_relations(gloss, new_human_value_list)

    if errors and DEBUG_CSV:
        print('subst check CSV import Relations errors: ', errors)

    if errors:
        errors_found += errors
        return errors_found, differences

    if current_relations_string == checked_new_human_value:
        return errors_found, differences

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': current_relations_string,
                        'original_human_value': current_relations_string,
                        'new_machine_value': checked_new_human_value,
                        'new_human_value': checked_new_human_value,
                        'side_effects': side_effects})
    return errors_found, differences


def check_existence_foreign_relations(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    output_string = ''
    sorted_values = []

    if not values:
        # this is a delete operation
        return output_string, errors

    for new_value_tuple in values:
        try:
            (loan_word, other_lang, other_lang_gloss) = new_value_tuple.split(':')
            sorted_values.append((loan_word, other_lang, other_lang_gloss))
        except ValueError:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), formatting error in Relations to foreign signs: '{input}'. Tuple 'bool:string:string' expected.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), input=str(new_value_tuple))
            errors.append(error_string)

    # remove duplicates
    sorted_values = list(set(sorted_values))
    sorted_values = sorted(sorted_values, key=lambda tup: tup[2])

    for (loan_word, other_lang, other_lang_gloss) in sorted_values:

        # check the syntax of the tuple of changes
        try:
            loan_word = loan_word.strip()
            if loan_word not in ['false', 'False', 'true', 'True']:
                raise ValueError
            other_lang = other_lang.strip()
            other_lang_gloss = other_lang_gloss.strip()
            if output_string:
                output_string += f',{loan_word}:{other_lang}:{other_lang_gloss}'
            else:
                output_string = f'{loan_word}:{other_lang}:{other_lang_gloss}'
        except ValueError:
            error_string = gettext(
                "For gloss {annotation} ({glossid}), formatting error in Relations to foreign signs: '{loan_word}:{other_lang}:{other_lang_gloss}'. Tuple 'bool:string:string' expected.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk),
                loan_word=loan_word, other_lang=other_lang, other_lang_gloss=other_lang_gloss)
            errors.append(error_string)

            pass

    return output_string, errors


def compare_relations_to_foreign_signs(gloss, new_human_value, human_key, errors_found, differences):

    relations = [(str(relation.loan), relation.other_lang, relation.other_lang_gloss)
                 for relation in gloss.relationtoforeignsign_set.all().order_by('other_lang_gloss')]
    if not relations and new_human_value in ['None', '', '-']:
        return errors_found, differences

    relations_with_categories = []
    for rel_cat in relations:
        relations_with_categories.append(':'.join(rel_cat))
    current_relations_foreign_string = ",".join(relations_with_categories)

    if new_human_value in ['None', '', '-']:
        new_human_value_list = []
    else:
        new_human_value_list = [v.strip() for v in new_human_value.split(',')]

    (checked_new_human_value, errors) = check_existence_foreign_relations(gloss, new_human_value_list)

    if len(errors):
        errors_found += errors
        return errors_found, differences

    if current_relations_foreign_string == checked_new_human_value:
        return errors_found, differences

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': current_relations_foreign_string,
                        'original_human_value': current_relations_foreign_string,
                        'new_machine_value': checked_new_human_value,
                        'new_human_value': checked_new_human_value,
                        'side_effects': {}})
    return errors_found, differences


def get_tags_as_string(gloss_id):
    activate(LANGUAGES[0][0])

    tags_of_gloss = TaggedItem.objects.filter(object_id=gloss_id)
    tag_names_of_gloss = []
    for t_obj in tags_of_gloss:
        tag_id = t_obj.tag_id
        tag_name = Tag.objects.get(id=tag_id)
        tag_names_of_gloss += [str(tag_name)]
    tag_names_of_gloss = sorted(tag_names_of_gloss)

    tag_names_string = ", ".join(tag_names_of_gloss)

    tag_names_display = [t.replace('_', ' ') for t in tag_names_of_gloss]
    tag_names_display = ', '.join(tag_names_display)

    return tag_names_string, tag_names_display


def check_existence_tags(gloss_id, new_human_value_list, tag_name_error, default_annotationidglosstranslation):
    # convert new Tags csv value to proper format
    # values is not empty

    tags_objects = Tag.objects.all()
    refreshed_tags = []
    for tag in tags_objects:
        tag.refresh_from_db()
        refreshed_tags.append(tag)
    all_tags = [t.name for t in refreshed_tags]

    new_tag_errors = []

    new_human_value_list = [v.replace(' ', '_') for v in new_human_value_list]

    new_human_value_list_no_dups = list(set(new_human_value_list))
    sorted_new_tags = sorted(new_human_value_list_no_dups)

    # check for non-existent tags
    for t in sorted_new_tags:
        if t not in all_tags:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), an unknown Tag name was encountered: '{tag}'.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss_id), tag=t.replace('_', ' '))
            new_tag_errors += [error_string]
            if not tag_name_error:
                error_string = gettext("See the available Tags in the table on the Import CSV Update Glosses page.")
                new_tag_errors += [error_string]
                tag_name_error = True

    new_tag_names_display = [t.replace('_', ' ') for t in sorted_new_tags]
    new_tag_names_display = ', '.join(new_tag_names_display)

    sorted_new_tags = ", ".join(sorted_new_tags)

    return new_tag_names_display, sorted_new_tags, new_tag_errors, tag_name_error


def compare_tags(gloss, new_human_value, human_key, errors_found, differences, tag_name_error):
    (tag_names_string, sorted_tags_display) = get_tags_as_string(gloss.id)

    if new_human_value in ['None', '']:
        (sorted_new_tags_display, sorted_new_tags, new_tag_errors, tag_name_error) = \
            ("", [], [], tag_name_error)
    else:
        new_human_value_list = [v.strip() for v in new_human_value.split(',')]

        (sorted_new_tags_display, sorted_new_tags, new_tag_errors, tag_name_error) = \
            check_existence_tags(gloss.id, new_human_value_list, tag_name_error,
                                 get_default_annotationidglosstranslation(gloss))

    if len(new_tag_errors):
        errors_found += new_tag_errors
        return errors_found, differences, tag_name_error

    if sorted_tags_display == sorted_new_tags_display:
        return errors_found, differences, tag_name_error

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': sorted_tags_display,
                        'original_human_value': sorted_tags_display,
                        'new_machine_value': sorted_new_tags_display,
                        'new_human_value': sorted_new_tags_display,
                        'side_effects': {}})
    return errors_found, differences, tag_name_error


def check_existence_notes(gloss, values, note_type_error, note_tuple_error, default_annotationidglosstranslation):
    # convert new Notes csv value to proper format
    # values is not empty

    activate(LANGUAGES[0][0])
    # The following need to be ordered reversely because note name 'Project Note' contains 'Note'
    note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType',
                                                   machine_value__gte=0).order_by('-name')

    new_human_values = []
    new_note_errors = []

    # first replace the note names with their machine value
    # this is needed in order to parse the input, since some notes have parentheses and numbers, etc.
    mapped_values, map_errors = map_values_to_notes_id(values)

    if map_errors:
        note_tuple_error = True
        # error in processing new notes
        error_string1 = gettext(
            "For gloss '{annotation}' ({glossid}), unknown type for Notes: '{values}'").format(
            annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), values=values)
        new_note_errors.append(error_string1)
        if not note_type_error:
            error_string2 = gettext("See the available Notes types in the table on the Import CSV Update Glosses page.")
            new_note_errors.append(error_string2)
            note_type_error = True
        # it doesn't work to use the translation here because it's a proxy
        # new_note_errors.append(_('A non-existent note type was found.'))
        return values, values, new_note_errors, note_type_error, note_tuple_error

    # the space is required in order to identify multiple notes in the input
    split_human_values = re.split(r', ([0-9]+: ?)', mapped_values)

    # this doesn't split cleanly, because the "split" is also shown in the result
    # e.g., ['NNN: (...,...,...)', "NNN: ', '(...,...,...)']
    # an index variable is used in order to obtain the correct item from the list of splits
    # consecutive elements must be concatenated after the first element, as shown above
    splits_combined = []
    list_index = 0
    # find the patterns of the different notes in the input
    for split_value in split_human_values:
        if re.match(r'[0-9]+: ?(.+,.+,.+)', split_value):
            # there is a match to the pattern <machine_value>:(<published>,<index>,<text>) possibly with spaces
            splits_combined.append(split_value)
        elif re.match(r'[0-9]+: ?', split_value):
            next_value = split_human_values[list_index+1]
            splits_combined.append(split_value+next_value)
        # else skip over this one, it was combined with the previous
        list_index += 1

    for split_value in splits_combined:
        take_apart = re.match(r'([0-9]+): ?[(](False|True),\s?(-?[0-9]+),\s?(.+)[)]', split_value)
        if take_apart:
            (field, name, count, text) = take_apart.groups()
            new_tuple = (field, name, count, text.strip())
            new_human_values.append(new_tuple)
        else:
            # error in processing new notes
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), could not parse Notes: '{values}'.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), values=values)

            if not note_tuple_error:
                new_note_errors += [error_string]
                error_string1 = gettext("Notes values must be a comma-separated list of tagged tuples: 'Type:(Boolean,Index,Text)'")
                new_note_errors += [error_string1]
                error_string2 = gettext("Try exporting a CSV for glosses with Notes to check the format.")
                new_note_errors += [error_string2]
                note_tuple_error = True
            else:
                new_note_errors += [error_string]

    note_translations = {}
    for nrc in note_role_choices:
        note_translations[str(nrc.machine_value)] = nrc.name

    new_notes_mapped = []
    for (machine_value, published, count, text) in new_human_values:
        role = note_translations[machine_value]
        new_notes_mapped.append((role, published, count, text))

    sorted_new_human_values = sorted(new_notes_mapped, key=lambda x: (x[0], x[1], x[2], x[3]))

    new_notes_display = []
    for (role, published, count, text) in sorted_new_human_values:
        new_note = f'{role}: ({published},{count},{text})'
        new_notes_display.append(new_note)
    sorted_new_notes_display = ', '.join(new_notes_display)
    return new_notes_display, sorted_new_notes_display, new_note_errors, note_type_error, note_tuple_error


def map_values_to_notes_id(input_values):

    values = copy.deepcopy(input_values)
    map_errors = False
    activate(LANGUAGES[0][0])
    note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType', machine_value__gte=0).order_by('-name')

    # this needs to be done twice in order to reverse map to escaped names
    # some of the names include parentheses
    note_reverse_translation = {}
    for nrc in note_role_choices:
        note_reverse_translation[nrc.name] = str(nrc.machine_value)

    sorted_note_names = note_reverse_translation.keys()
    pattern_mapped_sorted_note_names = []
    escaped_note_reverse_translation = {}
    for note_name in sorted_note_names:
        escaped_note_name = re.sub(r'([()])', r'\\\1', note_name)
        pattern_mapped_sorted_note_names.append(escaped_note_name)
        escaped_note_reverse_translation[escaped_note_name] = note_reverse_translation[note_name]

    mapped_values = values
    for note_name in pattern_mapped_sorted_note_names:
        regex_string = r"%s: \(" % note_name
        m = re.search(regex_string, mapped_values)
        if m:
            regex = re.compile(note_name+": \\(")
            mapped_values = regex.sub(escaped_note_reverse_translation[note_name]+': (', mapped_values)
    # see if any note names have not been reverse mapped
    find_all = re.findall(r'\D+: ?[(]', mapped_values)
    if find_all:
        map_errors = True
    return mapped_values, map_errors


def get_notes_as_string(gloss):
    activate(LANGUAGES[0][0])
    notes_of_gloss = gloss.definition_set.all()

    notes_list = []
    for note in notes_of_gloss:
        notes_list += [note.note_tuple()]
    sorted_notes_list = sorted(notes_list, key=lambda x: (x[0], x[1], x[2], x[3]))

    notes_display = []
    for (role, published, count, text) in sorted_notes_list:
        # does not use a comprehension because of nested parentheses in role and text fields
        tuple_reordered = f'{role}: ({published},{count},{text})'
        notes_display.append(tuple_reordered)
    sorted_notes_display = ', '.join(notes_display)
    return notes_display, sorted_notes_display


def compare_notes(gloss, new_human_value, human_key, notes_assign_toggle, errors_found, differences, note_type_error, note_tuple_error):

    notes_list, sorted_notes_display = get_notes_as_string(gloss)

    if new_human_value == 'None' or new_human_value == '':
        (new_notes_display, sorted_new_notes_display, new_note_errors, note_type_error, note_tuple_error) = \
            ([], "", [], note_type_error, note_tuple_error)
    else:
        (new_notes_display, sorted_new_notes_display, new_note_errors, note_type_error, note_tuple_error) = \
            check_existence_notes(gloss, new_human_value, note_type_error,
                                  note_tuple_error, get_default_annotationidglosstranslation(gloss))

    if len(new_note_errors):
        errors_found += new_note_errors
        return errors_found, differences, note_type_error, note_tuple_error

    if new_notes_display == notes_list:
        return errors_found, differences, note_type_error, note_tuple_error

    if notes_assign_toggle == 'update':
        combined_notes = notes_list + new_notes_display
        sorted_new_notes_display = ', '.join(combined_notes)

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': sorted_notes_display,
                        'original_human_value': sorted_notes_display,
                        'new_machine_value': sorted_new_notes_display,
                        'new_human_value': sorted_new_notes_display,
                        'side_effects': {}})

    return errors_found, differences, note_type_error, note_tuple_error


def compare_dataset(gloss, new_human_value, human_key, errors_found, differences, my_datasets):
    current_dataset = gloss.lemma.dataset.acronym

    if new_human_value == 'None' or new_human_value == '':
        # This check assumes that if the Dataset column is empty, it means no change
        # Since we already know the id of the gloss, we keep the original dataset
        # To be safe, confirm the original dataset is not empty, to catch legacy code
        if not current_dataset or current_dataset == 'None' or current_dataset is None:
            # Dataset must be non-empty to create a new gloss
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), Dataset must be non-empty. There is currently no dataset defined for this gloss.").format(
                annotation=get_default_annotationidglosstranslation(gloss), glossid=str(gloss.id))
            errors_found += [error_string]
            return errors_found, differences

    # if we get to here, the user has specified a new value for the dataset
    # This allows a user to move glosses from a temporary dataset to another dataset, making use of a CSV file
    if new_human_value not in my_datasets:
        error_string = gettext(
            "For gloss '{annotation}' ({glossid}), could not find '{value}' for '{column}'.").format(
            annotation=get_default_annotationidglosstranslation(gloss), glossid=str(gloss.id), value=new_human_value,
            column=human_key)
        errors_found += [error_string]
        return errors_found, differences

    if current_dataset == new_human_value:
        return errors_found, differences

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': current_dataset,
                        'original_human_value': current_dataset,
                        'new_machine_value': new_human_value,
                        'new_human_value': new_human_value,
                        'side_effects': {}})
    return errors_found, differences


def check_existence_signlanguage(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    found = []
    not_found = []

    for new_value in values:
        if SignLanguage.objects.filter(name__iexact=new_value):
            if new_value in found:
                error_string = gettext(
                    "For gloss '{annotation}' ({glossid}), Sign Language value '{value}' is a duplicate.").format(
                    annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), value=str(new_value))
                errors.append(error_string)
            else:
                found += [new_value]
        else:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), an unknown Sign Language value was encountered: '{value}'.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), value=str(new_value))
            errors.append(error_string)
            not_found += [new_value]
        continue

    return found, not_found, errors


def compare_signlanguages(gloss, new_human_value, human_key, errors_found, differences):
    if new_human_value in ['None', '']:
        return errors_found, differences

    current_signlanguages_string = str(', '.join([str(lang.name) for lang in gloss.signlanguage.all()]))

    new_human_value_list = [v.strip() for v in new_human_value.split(',')]

    (found, not_found, errors) = check_existence_signlanguage(gloss, new_human_value_list)

    if len(errors):
        errors_found += errors
        return errors_found, differences

    if current_signlanguages_string == new_human_value:
        return errors_found, differences

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': current_signlanguages_string,
                        'original_human_value': current_signlanguages_string,
                        'new_machine_value': new_human_value,
                        'new_human_value': new_human_value,
                        'side_effects': {}})
    return errors_found, differences


def check_existence_dialect(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    found = []
    not_found = []
    for new_value in values:
        dialect_signlanguage_str, dialect_name_str = new_value.split('/')
        dialect_signlanguage = dialect_signlanguage_str.strip()
        dialect_name = dialect_name_str.strip()
        if Dialect.objects.filter(name=dialect_name, signlanguage__name=dialect_signlanguage):
            if new_value not in found:
                found += [new_value]
        else:
            error_string = gettext(
                "For gloss '{annotation}' ({glossid}), new Dialect value '{value}' not found.").format(
                annotation=default_annotationidglosstranslation, glossid=str(gloss.pk), value=str(new_value))
            errors.append(error_string)
            not_found += [new_value]
        continue

    return found, not_found, errors


def compare_dialects(gloss, new_human_value, human_key, errors_found, differences):
    if new_human_value in ['None', '', '-']:
        return errors_found, differences

    current_dialects_string = str(', '.join([f'{dia.signlanguage.name}/{dia.name}'
                                             for dia in gloss.dialect.all()]))

    new_human_value_list = [v.strip() for v in new_human_value.split(',')]

    (found, not_found, errors) = check_existence_dialect(gloss, new_human_value_list)

    if len(errors):
        errors_found += errors
        return errors_found, differences

    elif current_dialects_string == new_human_value:
        return errors_found, differences

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': current_dialects_string,
                        'original_human_value': current_dialects_string,
                        'new_machine_value': new_human_value,
                        'new_human_value': new_human_value,
                        'side_effects': {}})
    return errors_found, differences


def compare_example_sentences(gloss, new_human_value, human_key, errors_found, differences):
    if new_human_value in ['None', '']:
        return errors_found, differences

    example_sentences_key_prefix = "Example Sentences ("
    language_name_column = DEFAULT_LANGUAGE_HEADER_COLUMN['English']
    language_name = human_key[len(example_sentences_key_prefix):-1]
    language = Language.objects.filter(**{language_name_column: language_name}).first()
    if not language:
        error_string = gettext("Non-existent language specified for column: {column}").format(column=human_key)
        errors_found += [error_string]
        return errors_found, differences

    sense_numbers_to_sentences = get_senses_to_sentences(gloss)
    if not sense_numbers_to_sentences:
        error_string = gettext("For gloss '{annotation}' ({glossid}), creation of new sentences not available: {column}. Only update is available, but the gloss has no sentences.").format(annotation=get_default_annotationidglosstranslation(gloss), glossid=gloss.id, column=human_key)
        errors_found += [error_string]
        return errors_found, differences

    sense_numbers = get_sense_numbers(gloss)
    okay = update_sentences_parse(sense_numbers, sense_numbers_to_sentences, new_human_value)
    if not okay:
        error_string = gettext(
            "For gloss {glossid}: Error parsing value in column {column}: {value}").format(
            glossid=str(gloss.id), column=human_key, value=new_human_value)
        errors_found += [error_string]
        return errors_found, differences

    current_sentences_string = sense_examplesentences_for_language(gloss, language)
    difference_org, difference, parse_errors = csv_sentence_tuples_list_compare(gloss,
                                                                                current_sentences_string,
                                                                                new_human_value)
    if parse_errors:
        error_string = gettext(
            "For gloss {glossid}: Error parsing value in column {column}: {value}").format(
            glossid=str(gloss.id), column=human_key, value=new_human_value)
        errors_found += [error_string]
        errors_found += parse_errors
        return errors_found, differences

    if difference:
        differences.append({'pk': gloss.id,
                            'dataset': gloss.lemma.dataset,
                            'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                            'machine_key': human_key,
                            'human_key': human_key,
                            'original_machine_value': difference_org,
                            'original_human_value': difference_org,
                            'new_machine_value': difference,
                            'new_human_value': difference,
                            'side_effects': {}})
    return errors_found, differences


def lookup_semantic_fields(values):
    # case insensitive lookup of values for semantic fields
    semantic_fields_machine_values = []
    for value in values:
        semfields = SemanticField.objects.filter(name__iexact=value)
        if not semfields or semfields.count() > 1:
            continue
        semantic_fields_machine_values.append(semfields.first().machine_value)
    semantic_fields = SemanticField.objects.filter(machine_value__in=semantic_fields_machine_values).order_by('machine_value')
    return semantic_fields


def compare_semantic_fields(gloss, new_human_value, human_key, errors_found, differences, semfield_assign_toggle):
    if new_human_value in ['', '0', ' ', None, 'None']:
        new_human_value = '-'
        new_human_value_list = []
    else:
        new_human_value_list = [v.strip() for v in new_human_value.split(',')]

    # make sure all fields exist
    new_values_sorted_lookup = lookup_semantic_fields(new_human_value_list)
    if new_values_sorted_lookup.count() != len(new_human_value_list):
        error_string = gettext(
            "For gloss '{annotation}' ({glossid}), could not parse '{value}' for '{column}'.").format(
            annotation=get_default_annotationidglosstranslation(gloss), glossid=str(gloss.id), value=new_human_value,
            column=human_key)
        errors_found += [error_string]
        return errors_found, differences

    new_semfield_sorted_lookup_values = [str(sf.name) for sf in new_values_sorted_lookup]
    new_semanticfield_value = ', '.join(new_semfield_sorted_lookup_values)
    original_sorted_semfield_values = [str(sf.name) for sf in gloss.semField.all().order_by('machine_value')]
    original_semanticfield_value = ", ".join(original_sorted_semfield_values)
    if new_semanticfield_value == original_semanticfield_value:
        return errors_found, differences

    if semfield_assign_toggle == 'update':
        combined_semfield = original_sorted_semfield_values + new_semfield_sorted_lookup_values
        compined_values_sorted_lookup = lookup_semantic_fields(combined_semfield)
        new_semanticfield_value = ', '.join([str(sf.name) for sf in compined_values_sorted_lookup])

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': original_semanticfield_value,
                        'original_human_value': original_semanticfield_value,
                        'new_machine_value': new_semanticfield_value,
                        'new_human_value': new_semanticfield_value,
                        'side_effects': {}})
    return errors_found, differences


def compare_senses(gloss, new_human_value, human_key, errors_found, differences):
    if new_human_value in ['None', '']:
        return errors_found, differences

    keywords_key_prefix = "Senses ("
    language_name_column = DEFAULT_LANGUAGE_HEADER_COLUMN['English']
    language_name = human_key[len(keywords_key_prefix):-1]
    language = Language.objects.filter(**{language_name_column: language_name}).first()
    if not language:
        error_string = gettext("Non-existent language specified for Senses column: '{column}'").format(column=human_key)
        errors_found += [error_string]
        return errors_found, differences

    current_keyword_string = sense_translations_for_language(gloss, language)

    if current_keyword_string == new_human_value:
        return errors_found, differences

    if current_keyword_string:
        error_string = gettext("For gloss '{annotation}' ({glossid}), update of senses not available: {column}: {value}.").format(annotation=get_default_annotationidglosstranslation(gloss), glossid=gloss.id, column=human_key, value=new_human_value)
        errors_found += [error_string]
        return errors_found, differences

    okay = update_senses_parse(new_human_value)
    if not okay:
        error_string = gettext(
            "For gloss {glossid}: Error parsing value in Senses column '{column}': {value}").format(
            glossid=str(gloss.id), column=human_key, value=new_human_value)
        errors_found += [error_string]
        return errors_found, differences

    differences.append({'pk': gloss.id,
                        'dataset': gloss.lemma.dataset,
                        'annotationidglosstranslation': get_default_annotationidglosstranslation(gloss),
                        'machine_key': human_key,
                        'human_key': human_key,
                        'original_machine_value': current_keyword_string,
                        'original_human_value': current_keyword_string,
                        'new_machine_value': new_human_value,
                        'new_human_value': new_human_value,
                        'side_effects': {}})
    return errors_found, differences
