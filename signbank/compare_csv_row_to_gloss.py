
from django.utils.translation import override, activate, gettext, gettext_lazy as _

from signbank.settings.server_specific import DEBUG_CSV
from signbank.dictionary.models import Gloss, Morpheme, MorphologyDefinition, Relation
from signbank.dictionary.update_csv import validate_and_resolve_gloss_relations


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
        if not morpheme_gloss.is_morpheme():
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
    found = []
    not_found = []
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
                       for relation in Relation.objects.filter(source=gloss)]
    checked_relations = []
    for (role, target) in values_mapped_to_objects:
        if (gloss, role, target) in gloss_relations:
            continue
        # checked_relations contains tuples in the display format
        target_annotation = get_default_annotationidglosstranslation(target)
        checked_relations.append((role.name, target_annotation))
        if target_annotation not in side_effects.keys():
            side_effects[target_annotation] = []
        side_effects[target_annotation].append({'source_pk': target.pk,
                                                'role': role.reverse_relation_role(),
                                                'target': get_default_annotationidglosstranslation(gloss)})
    checked = ','.join([f'{role_name}:{target_annotation}'
                        for (role_name, target_annotation) in checked_relations])
    return checked, side_effects, errors


def compare_relations(gloss, new_human_value, human_key, errors_found, differences):
    relations = [(relation.role_fk.name, get_default_annotationidglosstranslation(relation.target))
                 for relation in gloss.get_relations()]
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


def check_existence_foreign_relations(gloss, relations, values):
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

    (checked_new_human_value, errors) = check_existence_foreign_relations(gloss, relations_with_categories,
                                                                          new_human_value_list)

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


