import signbank.settings
from signbank.settings.base import WSGI_FILE, WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, LANGUAGE_CODE
import os
import shutil
from html.parser import HTMLParser
from zipfile import ZipFile
import json
import re
from urllib.parse import quote

from django.utils.translation import override

from signbank.dictionary.models import *
from django.utils.dateformat import format
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from tagging.models import TaggedItem, Tag

from guardian.shortcuts import get_objects_for_user

def save_media(source_folder,language_code_3char,goal_folder,gloss,extension):
        
    #Add a dot before the extension if needed
    if extension[0] != '.':
        extension = '.' + extension

    #Figure out some names
    annotation_id = ""
    language = Language.objects.get(language_code_3char=language_code_3char)
    if not language:
        raise ObjectDoesNotExist
    annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
    if annotationidglosstranslations and len(annotationidglosstranslations) > 0:
        annotation_id = annotationidglosstranslations[0].text
    pk = str(gloss.pk)
    destination_folder = goal_folder+annotation_id[:2]+'/'

    #Create the necessary subfolder if needed
    if not os.path.isdir(destination_folder):
        os.mkdir(destination_folder)

    #Move the file
    source = source_folder+annotation_id+extension
    goal = destination_folder+annotation_id+'-'+pk+extension

    if os.path.isfile(goal):
        overwritten = True
    else:
        overwritten = False

    try:
        shutil.copyfile(source,goal)
        was_allowed = True
    except IOError:
        was_allowed = False

    os.remove(source)

    return overwritten,was_allowed

def unescape(string):

    return HTMLParser().unescape(string)

class MachineValueNotFoundError(Exception):
    pass

def create_gloss_from_valuedict(valuedict,datasets,row_nr):

    errors_found = []
    new_gloss = []
    already_exists = []

    #Create an overview of all fields, sorted by their human name
    with override(LANGUAGE_CODE):

        # initialise
        dataset_name = valuedict['Dataset'].strip()
        # python sets undefined items in dictionary to 'None'

        dataset = Dataset.objects.get(name=dataset_name)
        if not dataset:
            error_string = 'Row ' + str(row_nr + 1) + ': Dataset ' + dataset_name + ' not found.'

            errors_found += [error_string]

        existing_glosses = {}

        annotationidglosstranslations = {}
        for language in dataset.translation_languages.all():
            column_name = "Annotation ID Gloss (%s)" % language.name_en
            if column_name in valuedict:
                annotationidglosstranslation_text = valuedict[column_name].strip()
                annotationidglosstranslations[language.language_code_2char] = annotationidglosstranslation_text

                # The annotation idgloss translation text for a language must be unique within a dataset.
                glosses_with_same_text = dataset.gloss_set.filter(
                    annotationidglosstranslation__text__exact=annotationidglosstranslation_text,
                    annotationidglosstranslation__language=language)
                if len(glosses_with_same_text) > 0:
                    existing_glosses[language.language_code_2char] = glosses_with_same_text

        if existing_glosses:
            existing_gloss_set = set()
            for language_code_2char,glosses in existing_glosses.items():
                for gloss in glosses:
                    if gloss not in existing_gloss_set:
                        gloss_dict = {
                             'gloss_pk': gloss.pk,
                             'dataset': gloss.dataset
                        }
                        annotationidglosstranslation_dict = {}
                        for lang in gloss.dataset.translation_languages.all():
                            annotationidglosstranslation_text = valuedict["Annotation ID Gloss (%s)" % lang.name_en]
                            annotationidglosstranslation_dict[lang.language_code_2char] = annotationidglosstranslation_text
                        gloss_dict['annotationidglosstranslations'] = annotationidglosstranslation_dict

                        lemmaidglosstranslation_dict = {}
                        for lang in gloss.dataset.translation_languages.all():
                            lemmaidglosstranslation_text = valuedict["Lemma ID Gloss (%s)" % lang.name_en]
                            lemmaidglosstranslation_dict[lang.language_code_2char] = lemmaidglosstranslation_text
                        gloss_dict['lemmaidglosstranslations'] = lemmaidglosstranslation_dict

                        already_exists.append(gloss_dict)
                        existing_gloss_set.add(gloss)

        else:
            # for the new gloss, we don't know the id yet so save the row number in this field
            gloss_dict = {'gloss_pk': str(row_nr),
                                'dataset': dataset_name}
            dataset = Dataset.objects.get(name=dataset_name)
            trans_languages = [ l for l in dataset.translation_languages.all() ]
            # print('translation languages for dataset: ', trans_languages)
            annotationidglosstranslation_dict = {}
            for language in trans_languages:
                annotationidglosstranslation_text = valuedict["Annotation ID Gloss (%s)" % language.name_en]
                # print('tools create gloss, language: ', language, ' annotation ID gloss: ', annotationidglosstranslation_text)
                annotationidglosstranslation_dict[language.language_code_2char] = annotationidglosstranslation_text
            gloss_dict['annotationidglosstranslations'] = annotationidglosstranslation_dict

            lemmaidglosstranslation_dict = {}
            for language in trans_languages:
                lemmaidglosstranslation_text = valuedict["Lemma ID Gloss (%s)" % language.name_en]
                lemmaidglosstranslation_dict[language.language_code_2char] = lemmaidglosstranslation_text
            gloss_dict['lemmaidglosstranslations'] = lemmaidglosstranslation_dict

            new_gloss.append(gloss_dict)

        # print('create gloss field ', lemma_id_gloss, ' with annotation ', annotation_id_gloss, ' english: ', annotation_id_gloss_en)

        # print('create new gloss: ', new_gloss, ' already exists: ', already_exists, ' errors: ', errors_found)

    return (new_gloss, already_exists, errors_found)

def compare_valuedict_to_gloss(valuedict,gloss,my_datasets):
    """Takes a dict of arbitrary key-value pairs, and compares them to a gloss"""

    errors_found = []
    column_name_error = False
    tag_name_error = False
    all_tags = [t.name for t in Tag.objects.all()]
    all_tags_display = ', '.join([t.replace('_',' ') for t in all_tags])

    #Create an overview of all fields, sorted by their human name
    with override(LANGUAGE_CODE):

        default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

        # There are too many to show the user!
        # allowed_column_names = [ str(f.verbose_name) for f in Gloss._meta.fields ]
        # allowed_columns = ', '.join(allowed_column_names)

        fields = {field.verbose_name: field for field in Gloss._meta.fields}

        differences = []

        if gloss.dataset:
            current_dataset = gloss.dataset.name
        else:
            # because of legacy code, the current dataset might not have been set
            current_dataset = 'None'

        #Go through all values in the value dict, looking for differences with the gloss
        for human_key, new_human_value in valuedict.items():

            new_human_value_list = []

            if new_human_value:
                new_human_value_list = [v.strip() for v in new_human_value.split(',')]

            new_human_value = new_human_value.strip()

            #This fixes a casing problem that sometimes shows up
            if human_key.lower() == 'id gloss':
                human_key = 'ID Gloss'

            #If these are not fields, but relations to other parts of the database, compare complex values
            if human_key == 'Signbank ID':
                continue

            annotation_idgloss_key_prefix = "Annotation ID Gloss ("
            if human_key.startswith(annotation_idgloss_key_prefix):
                language_name = human_key[len(annotation_idgloss_key_prefix):-1]
                languages = Language.objects.filter(name_en=language_name)
                if languages:
                    language = languages[0]
                    annotation_idglosses = gloss.annotationidglosstranslation_set.filter(language=language)
                    if annotation_idglosses:
                        annotation_idgloss_string = annotation_idglosses[0].text
                        if annotation_idgloss_string != new_human_value and new_human_value != 'None' and new_human_value != '':
                            differences.append({'pk': gloss.pk,
                                                'dataset': current_dataset,
                                                'annotationidglosstranslation': default_annotationidglosstranslation,
                                                'machine_key': human_key,
                                                'human_key': human_key,
                                                'original_machine_value': annotation_idgloss_string,
                                                'original_human_value': annotation_idgloss_string,
                                                'new_machine_value': new_human_value,
                                                'new_human_value': new_human_value})
                continue

            lemma_idgloss_key_prefix = "Lemma ID Gloss ("
            if human_key.startswith(lemma_idgloss_key_prefix):
                language_name = human_key[len(lemma_idgloss_key_prefix):-1]
                languages = Language.objects.filter(name_en=language_name)
                if languages:
                    language = languages[0]
                    lemma_idglosses = gloss.lemma.lemmaidglosstranslation_set.filter(language=language)
                    if lemma_idglosses:
                        lemma_idgloss_string = lemma_idglosses[0].text
                        if lemma_idgloss_string != new_human_value and new_human_value != 'None' and new_human_value != '':
                            differences.append({'pk': gloss.pk,
                                                'dataset': current_dataset,
                                                'machine_key': human_key,
                                                'human_key': human_key,
                                                'original_machine_value': lemma_idgloss_string,
                                                'original_human_value': lemma_idgloss_string,
                                                'new_machine_value': new_human_value,
                                                'new_human_value': new_human_value})
                continue

            elif human_key == 'Keywords':

                current_keyword_string = str(', '.join([str(translation.translation.text)+":"+translation.language.language_code_2char
                                                       for translation in gloss.translation_set.all()]))

                if current_keyword_string != new_human_value and new_human_value != 'None' and new_human_value != '':
                    differences.append({'pk':gloss.pk,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation':default_annotationidglosstranslation,
                                        'machine_key':human_key,
                                        'human_key':human_key,
                                        'original_machine_value':current_keyword_string,
                                        'original_human_value':current_keyword_string,
                                        'new_machine_value':new_human_value,
                                        'new_human_value':new_human_value})
                continue

            elif human_key == 'SignLanguages':

                # print('check sign languages: (', new_human_value_list, ')')

                if new_human_value == 'None' or new_human_value == '':
                    continue

                current_signlanguages_string = str(', '.join([str(lang.name) for lang in gloss.signlanguage.all()]))

                (found, not_found, errors) = check_existance_signlanguage(gloss, new_human_value_list)

                if len(errors):
                    errors_found += errors

                if current_signlanguages_string != new_human_value:
                    differences.append({'pk':gloss.pk,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation':default_annotationidglosstranslation,
                                        'machine_key':human_key,
                                        'human_key':human_key,
                                        'original_machine_value':current_signlanguages_string,
                                        'original_human_value':current_signlanguages_string,
                                        'new_machine_value':new_human_value,
                                        'new_human_value':new_human_value})
                continue

            elif human_key == 'Dialects':
                if new_human_value == 'None' or new_human_value == '':
                    continue

                current_dialects_string = str(', '.join([str(dia.name) for dia in gloss.dialect.all()]))

                (found, not_found, errors) = check_existance_dialect(gloss, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif current_dialects_string != new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation':default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': current_dialects_string,
                                        'original_human_value': current_dialects_string,
                                        'new_machine_value': new_human_value,
                                        'new_human_value': new_human_value})
                continue

            elif human_key == 'Dataset' or human_key == 'Glosses dataset':

                # cach legacy value
                if human_key == 'Glosses dataset':
                    human_key = 'Dataset'
                if new_human_value == 'None' or new_human_value == '':
                    # This check assumes that if the Dataset column is empty, it means no change
                    # Since we already know the id of the gloss, we keep the original dataset
                    # To be safe, confirm the original dataset is not empty, to catch legacy code
                    if not current_dataset or current_dataset == 'None' or current_dataset == None:
                        # Dataset must be non-empty to create a new gloss
                        error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) + '), Dataset must be non-empty. There is currently no dataset defined for this gloss.'

                        errors_found += [error_string]
                    continue

                # if we get to here, the user has specificed a new value for the dataset
                if new_human_value in my_datasets:
                    if current_dataset != new_human_value:
                        differences.append({'pk': gloss.pk,
                                            'dataset': current_dataset,
                                            'annotationidglosstranslation':default_annotationidglosstranslation,
                                            'machine_key': human_key,
                                            'human_key': human_key,
                                            'original_machine_value': current_dataset,
                                            'original_human_value': current_dataset,
                                            'new_machine_value': new_human_value,
                                            'new_human_value': new_human_value})
                else:
                    error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                        gloss.pk) + '), could not find ' + str(new_human_value) + ' for ' + human_key

                    errors_found += [error_string]

                continue

            elif human_key == 'Relations to other signs':
                if new_human_value == 'None' or new_human_value == '':
                    continue

                relations = [(relation.role, str(relation.target.id)) for relation in gloss.relation_sources.all()]

                # sort tuples on other gloss to allow comparison with imported values

                sorted_relations = sorted(relations, key=lambda tup: tup[1])

                relations_with_categories = []
                for rel_cat in sorted_relations:
                    relations_with_categories.append(':'.join(rel_cat))
                current_relations_string = ",".join(relations_with_categories)

                (checked_new_human_value, errors) = check_existance_relations(gloss, relations_with_categories, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif current_relations_string != checked_new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation':default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': current_relations_string,
                                        'original_human_value': current_relations_string,
                                        'new_machine_value': checked_new_human_value,
                                        'new_human_value': checked_new_human_value})
                continue

            elif human_key == 'Relations to foreign signs':
                if new_human_value == 'None' or new_human_value == '':
                    continue

                relations = [(str(relation.loan), relation.other_lang, relation.other_lang_gloss)
                             for relation in gloss.relationtoforeignsign_set.all().order_by('other_lang_gloss')]

                relations_with_categories = []
                for rel_cat in relations:
                    relations_with_categories.append(':'.join(rel_cat))
                current_relations_foreign_string = ",".join(relations_with_categories)

                (checked_new_human_value, errors) = check_existance_foreign_relations(gloss, relations_with_categories, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif current_relations_foreign_string != checked_new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation':default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': current_relations_foreign_string,
                                        'original_human_value': current_relations_foreign_string,
                                        'new_machine_value': checked_new_human_value,
                                        'new_human_value': checked_new_human_value})
                continue

            elif human_key == 'Sequential Morphology':
                if new_human_value == 'None' or new_human_value == '':
                    continue

                morphemes = [str(morpheme.morpheme.id) for morpheme in
                             MorphologyDefinition.objects.filter(parent_gloss=gloss)]
                morphemes_string = ", ".join(morphemes)

                (found, not_found, errors) = check_existance_sequential_morphology(gloss, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif morphemes_string != new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation':default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': morphemes_string,
                                        'original_human_value': morphemes_string,
                                        'new_machine_value': new_human_value,
                                        'new_human_value': new_human_value})
                continue

            elif human_key == 'Simultaneous Morphology':
                if new_human_value == 'None' or new_human_value == '':
                    continue

                morphemes = [(str(m.morpheme.id), m.role) for m in gloss.simultaneous_morphology.all()]
                sim_morphs = []
                for m in morphemes:
                    sim_morphs.append(':'.join(m))
                simultaneous_morphemes = ','.join(sim_morphs)

                (checked_new_human_value, errors) = check_existance_simultaneous_morphology(gloss, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif simultaneous_morphemes != checked_new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation':default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': simultaneous_morphemes,
                                        'original_human_value': simultaneous_morphemes,
                                        'new_machine_value': checked_new_human_value,
                                        'new_human_value': checked_new_human_value})
                continue

            elif human_key == 'Blend Morphology':
                if new_human_value == 'None' or new_human_value == '':
                    continue

                morphemes = [(str(m.glosses.id), m.role) for m in gloss.blend_morphology.all()]

                ble_morphs = []
                for m in morphemes:
                    ble_morphs.append(':'.join(m))
                blend_morphemes = ','.join(ble_morphs)

                (checked_new_human_value, errors) = check_existance_blend_morphology(gloss, new_human_value_list)

                if len(errors):
                    errors_found += errors

                elif blend_morphemes != checked_new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation':default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': blend_morphemes,
                                        'original_human_value': blend_morphemes,
                                        'new_machine_value': checked_new_human_value,
                                        'new_human_value': checked_new_human_value})
                continue

            elif human_key == 'Tags':
                if new_human_value == 'None' or new_human_value == '':
                    continue

                tags_of_gloss = TaggedItem.objects.filter(object_id=gloss.id)
                tag_names_of_gloss = []
                for t_obj in tags_of_gloss:
                    tag_id = t_obj.tag_id
                    tag_name = Tag.objects.get(id=tag_id)
                    tag_names_of_gloss += [str(tag_name)]
                tag_names_of_gloss = sorted(tag_names_of_gloss)

                tag_names = ", ".join(tag_names_of_gloss)

                tag_names_display = [ t.replace('_',' ') for t in tag_names_of_gloss ]
                tag_names_display = ', '.join(tag_names_display)

                new_human_value_list = [v.replace(' ', '_') for v in new_human_value_list]

                new_human_value_list_no_dups = list(set(new_human_value_list))
                sorted_new_tags = sorted(new_human_value_list_no_dups)

                # check for non-existant tags
                for t in sorted_new_tags:
                    if t in all_tags:
                        pass
                    else:
                        error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                            gloss.pk) + '), a new Tag name was found: ' + t.replace('_',' ') + '.'

                        errors_found += [error_string]
                        if not tag_name_error:
                            # error_string = 'Allowed column names are: ' + allowed_columns
                            error_string = 'Current tag names are: ' + all_tags_display + '.'
                            errors_found += [error_string]
                            tag_name_error = True


                new_tag_names_display = [ t.replace('_',' ') for t in sorted_new_tags ]
                new_tag_names_display = ', '.join(new_tag_names_display)

                sorted_new_tags = ", ".join(sorted_new_tags)

                if tag_names != sorted_new_tags:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'annotationidglosstranslation':default_annotationidglosstranslation,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': tag_names_display,
                                        'original_human_value': tag_names_display,
                                        'new_machine_value': new_tag_names_display,
                                        'new_human_value': new_tag_names_display})
                continue

            #If not, find the matching field in the gloss, and remember its 'real' name
            try:
                field = fields[human_key]
                machine_key = field.name
                # print('SUCCESS: accessing field name: (', human_key, ')')

            except KeyError:

                # Signbank ID is skipped, for this purpose it was popped from the fields to compare
                # Skip above fields with complex values: Keywords, Signlanguages, Dialects, Relations to other signs, Relations to foreign signs, Morphology.

                # print('Skipping unknown field name: (', human_key, ')')
                error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), could not identify column name: ' + str(human_key)

                errors_found += [error_string]

                if not column_name_error:
                    # error_string = 'Allowed column names are: ' + allowed_columns
                    error_string = 'HINT: Try exporting a CSV file to see what column names can be used.'
                    errors_found += [error_string]
                    column_name_error = True

                continue

            # print('SUCCESS: human_key (', human_key, '), machine_key: (', machine_key, '), new_human_value: (', new_human_value, ')')

            #Try to translate the value to machine values if needed
            if len(field.choices) > 0:
                human_to_machine_values = {human_value: machine_value for machine_value, human_value in field.choices}
                # print('Import CSV: human_to_machine_values: ', human_to_machine_values)
                try:
                    # print('new human value: ', new_human_value)

                    # Because some Handshape names can start with =, a special character ' is tested for in the name
                    if new_human_value[:1] == '\'':
                        new_human_value = new_human_value[1:]
                        # print('revised human value: ', new_human_value)

                    if new_human_value in human_to_machine_values.keys():
                        new_machine_value = human_to_machine_values[new_human_value]
                    else:
                        raise KeyError
                except KeyError:
                    #If you can't find a corresponding human value, maybe it's empty
                    if new_human_value in ['',' ', None, 'None']:
                        # print('exception in new human value to machine value: ', new_human_value)
                        new_human_value = 'None'
                        new_machine_value = None

                    #If not, stop trying
                    else:
                        new_machine_value = None
                        # raise MachineValueNotFoundError('At '+gloss.idgloss+' ('+str(gloss.pk)+'), could not find option '+str(new_human_value)+' for '+human_key)
                        error_string = 'For '+default_annotationidglosstranslation+' ('+str(gloss.pk)+'), could not find option '+str(new_human_value)+' for '+human_key

                        errors_found += [error_string]
            #Do something special for integers and booleans
            elif field.__class__.__name__ == 'IntegerField':

                try:
                    new_machine_value = int(new_human_value)
                except ValueError:
                    new_human_value = 'None'
                    new_machine_value = None
            elif field.__class__.__name__ == 'NullBooleanField':

                new_human_value_lower = new_human_value.lower()
                if new_human_value_lower == 'neutral' and (field.name == 'weakprop' or field.name == 'weakdrop'):
                    new_machine_value = None
                elif new_human_value_lower in ['true', 'yes', '1']:
                    new_machine_value = True
                    new_human_value = 'True'
                elif new_human_value_lower == 'none':
                    new_machine_value = None
                elif new_human_value_lower in ['false', 'no', '0']:
                    new_machine_value = False
                    new_human_value = 'False'
                else:
                    # Boolean expected
                    error_string = ''
                    # If the new value is empty, don't count this as a type error, error_string is generated conditionally
                    if field.name == 'weakdrop' or field.name == 'weakprop':
                        if new_human_value != None and new_human_value != '' and new_human_value != 'None':
                            error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) + '), value ' + str(new_human_value) + ' for ' + human_key + ' should be a Boolean or Neutral.'
                    else:
                        if new_human_value != None and new_human_value != '' and new_human_value != 'None':
                            error_string = 'For ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) + '), value ' + str(new_human_value) + ' for ' + human_key + ' is not a Boolean.'

                    if error_string:
                        errors_found += [error_string]
            #If all the above does not apply, this is a None value or plain text
            else:

                if new_human_value == 'None':
                    new_machine_value = None
                else:
                    new_machine_value = new_human_value

            #Try to translate the key to machine keys if possible
            try:
                original_machine_value = getattr(gloss,machine_key)
            except KeyError:
                continue

            #Translate back the machine value from the gloss
            try:
                original_human_value = dict(field.choices)[original_machine_value]
            except KeyError:

                original_human_value = original_machine_value

            #Remove any weird char
            try:
                new_human_value = unescape(new_human_value)
            except:
                print('unescape raised exception for new_human_value: ', new_human_value)
                pass

            # test if blank value

            original_human_value = str(original_human_value)
            new_human_value = str(new_human_value)
            # print("Hex values for machine key: ", machine_key)
            # print('Hex original: (', ", ".join([hex(ord(x)) for x in original_human_value]), ')')
            # print('Hex new:      (', ", ".join([hex(ord(x)) for x in new_human_value]), ')')

            s1 = re.sub(' ','',original_human_value)
            s2 = re.sub(' ','',new_human_value)

            # If the original value is implicitly not set, and the new value is not set, ignore this change
            if (s1 == '' or s1 == 'None' or s1 == 'False') and s2 == '':
                pass
            #Check for change, and save your findings if there is one
            elif original_machine_value != new_machine_value and new_machine_value != None:
                # print('for human key: ', human_key)
                # print('different: original_machine_value: ', original_machine_value, ', new machine value: ', new_machine_value)
                # print('different: original_human_value: ', original_human_value, ', new human value: ', new_human_value)
                if (human_key == 'WD' or human_key == 'WP') and original_human_value == 'None':
                    original_human_value = 'Neutral'
                differences.append({'pk':gloss.pk,
                                    'dataset': current_dataset,
                                    'annotationidglosstranslation':default_annotationidglosstranslation,
                                    'machine_key':machine_key,
                                    'human_key':human_key,
                                    'original_machine_value':original_machine_value,
                                    'original_human_value':original_human_value,
                                    'new_machine_value':new_machine_value,
                                    'new_human_value':new_human_value})

    return (differences, errors_found)


def check_existance_dialect(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    found = []
    not_found = []

    for new_value in values:
        if Dialect.objects.filter(name=new_value):
            if new_value in found:
                error_string = 'WARNING: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Dialect value ' + str(new_value) + ' is duplicate.'
                errors.append(error_string)
            else:
                found += [new_value]
        else:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) + '), new Dialect value ' + str(new_value) + ' not found.'
            errors.append(error_string)
            not_found += [new_value]
        continue

    return (found, not_found, errors)


def check_existance_signlanguage(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    found = []
    not_found = []

    for new_value in values:
        if SignLanguage.objects.filter(name=new_value):
            if new_value in found:
                error_string = 'WARNING: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Sign Language value ' + str(new_value) + ' is duplicate.'
                errors.append(error_string)
            else:
                found += [new_value]
        else:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) + '), new Sign Language value ' + str(new_value) + ' not found.'

            errors.append(error_string)
            not_found += [new_value]
        continue

    return (found, not_found, errors)

def check_existance_sequential_morphology(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    found = []
    not_found = []

    for new_value in values:

        try:

            morpheme = Gloss.objects.get(pk=new_value)

            if new_value in found:
                error_string = 'WARNING: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Sequential Morphology value ' + str(new_value) + ' is duplicate.'
                errors.append(error_string)
            else:
                found += [new_value]

        # except ObjectDoesNotExist:
        except:
            if new_value in not_found:
                error_string = 'WARNING: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Sequential Morphology value ' + str(new_value) + ' is duplicate.'
            else:
                error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Sequential Morphology value ' + str(new_value) + ' not found.'
            errors.append(error_string)
            not_found += [new_value]

            continue

    if len(values) > 4:
        error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) + ', too many Sequential Morphology components.'
        errors.append(error_string)

    return (found, not_found, errors)

def check_existance_simultaneous_morphology(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    tuples_list = []
    checked = ''
    index_sim_morph = 0

    # check syntax
    for new_value_tuple in values:
        try:
            (morpheme, role) = new_value_tuple.split(':')
            role = role.strip()
            morpheme = morpheme.strip()
            # print('taken apart: role: (', role, '), morpheme: (', morpheme, ')')
            tuples_list.append((morpheme,role))
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Simultaneous Morphology: ' + str(new_value_tuple) + '. Tuple morpheme:role expected.'
            errors.append(error_string)

    for (morpheme, role) in tuples_list:

        try:

            # get the id for the morpheme identifier
            # this is a gloss, make sure it exists
            morpheme_gloss = Gloss.objects.get(pk=morpheme)
            morpheme_id = Morpheme.objects.filter(gloss_ptr_id=morpheme_gloss)

            if not morpheme_id:
                error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Simultaneous Morphology gloss ' + str(morpheme) + ' is not a morpheme.'
                errors.append(error_string)
                continue

            if checked:
                checked += ',' + ':'.join([morpheme, role])
            else:
                checked = ':'.join([morpheme, role])

        except ObjectDoesNotExist:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                gloss.pk) + '), new Simultaneous Morphology value ' + str(morpheme) + ' is not a gloss.'
            errors.append(error_string)

            continue

    return (checked, errors)


def check_existance_blend_morphology(gloss, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    found = []
    not_found = []
    tuples_list = []
    checked = ''

    # check syntax
    for new_value_tuple in values:
        try:
            (gloss_id, role) = new_value_tuple.split(':')
            role = role.strip()
            gloss_id = gloss_id.strip()
            tuples_list.append((gloss_id,role))
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Blend Morphology: ' + str(new_value_tuple) + '. Tuple gloss:role expected.'
            errors.append(error_string)

    for (gloss_id, role) in tuples_list:

        try:

            morpheme_gloss = Gloss.objects.get(pk=gloss_id)

            if gloss_id in found:
                error_string = 'WARNING: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Blend Morphology value ' + str(gloss_id) + ' is duplicate.'
                errors.append(error_string)
            else:
                found += [gloss_id]

            if checked:
                checked += ',' + ':'.join([gloss_id, role])
            else:
                checked = ':'.join([gloss_id, role])

        except ObjectDoesNotExist:
            if gloss_id in not_found:
                # we've already seen this value
                error_string = 'WARNING: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Blend Morphology value ' + str(gloss_id) + ' is duplicate.'
                errors.append(error_string)
            else:
                error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(
                    gloss.pk) + '), new Blend Morphology value ' + str(gloss_id) + ' not found.'
                errors.append(error_string)
                not_found += [gloss_id]
            continue

    return (checked, errors)


RELATION_ROLES = ['homonym', 'Homonym', 'synonym', 'Synonym', 'variant', 'Variant',
                         'antonym', 'Antonym', 'hyponym', 'Hyponym', 'hypernym', 'Hypernym', 'seealso', 'See Also']

RELATION_ROLES_DISPLAY = 'homonym, synonym, variant, antonym, hyponym, hypernym, seealso'

def check_existance_relations(gloss, relations, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    checked = ''
    sorted_values = []

    # check syntax
    for new_value_tuple in values:
        try:
            (role, other_gloss) = new_value_tuple.split(':')
            role = role.strip()

            role = role.replace(' ', '')
            role = role.lower()
            other_gloss = other_gloss.strip()
            # print('taken apart: role: (', role, '), other gloss: (', other_gloss, ')')
            sorted_values.append((role,other_gloss))
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Relations to other signs: ' + str(new_value_tuple) + '. Tuple role:gloss expected.'
            errors.append(error_string)

    # remove duplicates
    sorted_values = list(set(sorted_values))

    sorted_values = sorted(sorted_values, key=lambda tup: tup[1])
    # print("sorted values: ", sorted_values)

    # check roles
    for (role, other_gloss) in sorted_values:

        try:
            if role not in RELATION_ROLES:
                raise ValueError
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), column Relations to other signs: ' + role + ':' + other_gloss + '. Role ' + role + ' not found.' \
                    + ' Role should be one of: ' + RELATION_ROLES_DISPLAY + '.'
            errors.append(error_string)

    # check other glosses
    for (role, other_gloss) in sorted_values:

        try:

            target_gloss = Gloss.objects.get(pk=other_gloss)

            if not target_gloss:
                raise ObjectDoesNotExist

            if checked:
                checked += ',' + ':'.join([role, other_gloss])
            else:
                checked = ':'.join([role, other_gloss])

        except ObjectDoesNotExist:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                    + '), column Relations to other signs: ' + role + ':' + other_gloss + '. Other gloss ' + other_gloss + ' not found.' \
                    + ' Please use Annotation ID Gloss: Dutch to identify the other gloss.'
            errors.append(error_string)

            pass

    return (checked, errors)


def check_existance_foreign_relations(gloss, relations, values):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    errors = []
    checked = ''
    sorted_values = []

    for new_value_tuple in values:
        try:
            (loan_word, other_lang, other_lang_gloss) = new_value_tuple.split(':')
            # print('taken apart: loan: (', loan_word, '), other: (', other_lang, '), gloss: (', other_lang_gloss, ')')
            sorted_values.append((loan_word,other_lang,other_lang_gloss))
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Relations to foreign signs: ' + str(new_value_tuple) + '. Tuple bool:string:string expected.'
            errors.append(error_string)

    # remove duplicates
    sorted_values = list(set(sorted_values))

    sorted_values = sorted(sorted_values, key=lambda tup: tup[2])
    # print("sorted values: ", sorted_values)

    for (loan_word, other_lang, other_lang_gloss) in sorted_values:

        # check the syntax of the tuple of changes
        try:
            loan_word = loan_word.strip()
            if loan_word not in ['false', 'False', 'true', 'True']:
                raise ValueError
            other_lang = other_lang.strip()
            other_lang_gloss = other_lang_gloss.strip()
            # print('taken apart: loan: (', loan_word, '), other: (', other_lang, '), gloss: (', other_lang_gloss, ')')
            if checked:
                checked += ',' + ':'.join([loan_word, other_lang, other_lang_gloss])
            else:
                checked = ':'.join([loan_word,other_lang,other_lang_gloss])
            # print('checked: ', checked)
        except ValueError:
            error_string = 'ERROR: For gloss ' + default_annotationidglosstranslation + ' (' + str(gloss.pk) \
                           + '), formatting error in Relations to foreign signs: ' \
                           + loan_word + ':' + other_lang + ':' + other_lang_gloss + '. Tuple bool:string:string expected.'
            errors.append(error_string)

            pass

    return (checked, errors)

def reload_signbank(request=None):
    """Functions to clear the cache of Apache, also works as view"""

    #Refresh the wsgi script
    os.utime(WSGI_FILE,None)

    #If this is an HTTP request, give an HTTP response
    if request != None:

        from django.shortcuts import render
        return render(request,'reload_signbank.html')

def get_static_urls_of_files_in_writable_folder(root_folder,since_timestamp=0, dataset=None):
    dataset_gloss_ids = []
    if dataset:
        dataset_gloss_ids = Gloss.objects.filter(lemma__dataset=dataset).values_list('pk', flat=True)
        print(str(dataset_gloss_ids))
        print(str(4611 in dataset_gloss_ids))

    full_root_path = signbank.settings.server_specific.WRITABLE_FOLDER+root_folder+'/'
    static_urls = {}

    for subfolder_name in os.listdir(full_root_path):
        if os.path.isdir(full_root_path+subfolder_name):
            for filename in os.listdir(full_root_path+subfolder_name):

                if os.path.getmtime(full_root_path+subfolder_name+'/'+filename) > since_timestamp:
                    res = re.search(r'(.+)\.[^\.]*', filename)

                    try:
                        gloss_id = res.group(1)
                        re_result = re.match(r'.*\-(\d+)', gloss_id)

                        if dataset is None or int(re_result.group(1)) in dataset_gloss_ids:
                            static_urls[gloss_id] = reverse('dictionary:protected_media',
                                                            args=['']) + root_folder + '/' + quote(
                                subfolder_name) + '/' + quote(filename)
                    except AttributeError:
                        continue

    return static_urls

def get_gloss_data(since_timestamp=0, dataset=None):
    if dataset:
        glosses = Gloss.objects.filter(lemma__dataset=dataset)
    else:
        glosses = Gloss.objects.all()
    gloss_data = {}
    for gloss in glosses:
        if int(format(gloss.lastUpdated, 'U')) > since_timestamp:
            gloss_data[gloss.pk] = gloss.get_fields_dict()

    return gloss_data

def create_zip_with_json_files(data_per_file,output_path):

    """Creates a zip file filled with the output of the functions supplied.

    Data should either be a json string or a list, which will be transformed to json."""

    INDENTATION_CHARS = 4

    zip = ZipFile(output_path,'w')

    for filename, data in data_per_file.items():

        if isinstance(data,list) or isinstance(data,dict):
            output = json.dumps(data,indent=INDENTATION_CHARS)
            zip.writestr(filename+'.json',output)

def get_deleted_gloss_or_media_data(item_type,since_timestamp):

    result = []
    from datetime import datetime, date
    deletion_date_range = [datetime.fromtimestamp(since_timestamp),date.today()]

    for deleted_gloss_or_media in DeletedGlossOrMedia.objects.filter(deletion_date__range=deletion_date_range,
                                                            item_type=item_type):
        if item_type == 'gloss':
            result.append((str(deleted_gloss_or_media.old_pk), deleted_gloss_or_media.idgloss))
        else:
            result.append(str(deleted_gloss_or_media.old_pk))

    return result


def generate_still_image(gloss_prefix, vfile_location, vfile_name):
    try:
        from CNGT_scripts.python.extractMiddleFrame import MiddleFrameExtracter
        from signbank.settings.server_specific import FFMPEG_PROGRAM, TMP_DIR
        from signbank.settings.base import GLOSS_IMAGE_DIRECTORY

        # Extract frames (incl. middle)
        extracter = MiddleFrameExtracter([vfile_location+vfile_name], TMP_DIR + os.sep + "signbank-extractMiddleFrame",
                                         FFMPEG_PROGRAM, True)
        output_dirs = extracter.run()

        # Copy video still to the correct location
        for dir in output_dirs:
            for filename in os.listdir(dir):
                if filename.replace('.png', '.mp4') == vfile_name:
                    destination = WRITABLE_FOLDER + GLOSS_IMAGE_DIRECTORY + os.sep + gloss_prefix
                    still_goal_location = destination + os.sep + filename
                    if not os.path.isdir(destination):
                        os.makedirs(destination, 0o770)
                    shutil.copy(dir + os.sep + filename, destination + os.sep + filename)
            shutil.rmtree(dir)
    except ImportError as i:
        print("Error resizing video: ", i)
    except IOError as io:
        print(io.message)


def get_selected_datasets_for_user(user):
    if user.is_authenticated:
        user_profile = UserProfile.objects.get(user=user)
        viewable_datasets = get_objects_for_user(user, 'view_dataset', Dataset)
        selected_datasets = user_profile.selected_datasets.all()
        if not selected_datasets:
            return viewable_datasets
        return selected_datasets & viewable_datasets # intersection of the selected and viewable datasets
    else:
        return Dataset.objects.filter(is_public=True)


def gloss_from_identifier(value):
    """Given an id of the form "idgloss (pk)" return the
    relevant gloss or None if none is found
    BUT: first check if a unique hit can be found by the string alone (if it is not empty)
    """

    match = re.match('(.*) \((\d+)\)', value)
    if match:
        print("MATCH: ", match)
        annotation_idgloss = match.group(1)
        pk = match.group(2)
        print("INFO: ", annotation_idgloss, pk)

        target = Gloss.objects.get(pk=int(pk))
        print("TARGET: ", target)
        return target
    elif value != '':
        annotation_idgloss = value
        target = Gloss.objects.get(annotation_idgloss=annotation_idgloss)
        return target
    else:
        return None

def get_default_annotationidglosstranslation(gloss):
    default_annotationidglosstranslation = ""
    language = Language.objects.get(**DEFAULT_KEYWORDS_LANGUAGE)
    annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
    if annotationidglosstranslations and len(annotationidglosstranslations) > 0:
        default_annotationidglosstranslation = annotationidglosstranslations[0].text
    return default_annotationidglosstranslation

def convert_language_code_to_2char(language_code):

    # reformat LANGUAGE_CODE for use in dictionary domain, accomodate multilingual codings
    if '-' in language_code:
        language_code_parts = language_code.split('-')
    elif '_' in language_code:
        language_code_parts = language_code.split('_')
    else:
        # only one part
        language_code_parts = [language_code]
    if len(language_code_parts) > 1:
        new_language_code = language_code_parts[0]
        new_language_code += '_' + language_code_parts[1].upper()
    else:
        new_language_code = language_code_parts[0]

    return new_language_code

from signbank.settings.base import ECV_FILE,EARLIEST_GLOSS_CREATION_DATE, FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD, LANGUAGE_CODE, ECV_SETTINGS, URL, LANGUAGE_CODE_MAP
from signbank.settings import server_specific
from signbank.settings.server_specific import *
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import datetime as DT

def write_ecv_files_for_all_datasets():

    all_dataset_objects = Dataset.objects.all()

    for ds in all_dataset_objects:
        ecv_filename = write_ecv_file_for_dataset(ds.name)
        print('Saved ECV for Dataset ', ds.name, ' to file: ', ecv_filename)

    return True


def write_ecv_file_for_dataset(dataset_name):

    description = 'DESCRIPTION'
    language = 'LANGUAGE'
    lang_ref = 'LANG_REF'

    cv_entry_ml = 'CV_ENTRY_ML'
    cve_id = 'CVE_ID'
    cve_value = 'CVE_VALUE'

    topattributes = {'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
                     'DATE': str(DT.date.today()) + 'T' + str(DT.datetime.now().time()),
                     'AUTHOR': '',
                     'VERSION': '0.2',
                     'xsi:noNamespaceSchemaLocation': "http://www.mpi.nl/tools/elan/EAFv2.8.xsd"}
    top = ET.Element('CV_RESOURCE', topattributes)

    for lang in ECV_SETTINGS['languages']:
        ET.SubElement(top, language, lang['attributes'])

    cv_element = ET.SubElement(top, 'CONTROLLED_VOCABULARY', {'CV_ID': ECV_SETTINGS['CV_ID']})

    # description for cv_element
    for lang in ECV_SETTINGS['languages']:
        myattributes = {lang_ref: lang['id']}
        desc_element = ET.SubElement(cv_element, description, myattributes)
        desc_element.text = lang['description']

    # set Dataset to NGT or other pre-specified Dataset, otherwise leave it empty
    try:
        dataset_id = Dataset.objects.get(name=dataset_name)
    except:
        dataset_id = ''

    if dataset_id:
        query_dataset = Gloss.none_morpheme_objects().filter(excludeFromEcv=False).filter(lemma__dataset=dataset_id)
    else:
        query_dataset = Gloss.none_morpheme_objects().filter(excludeFromEcv=False)

    # Make sure we iterate only over the none-Morpheme glosses
    for gloss in query_dataset:
        glossid = str(gloss.pk)
        myattributes = {cve_id: glossid, 'EXT_REF': 'signbank-ecv'}
        cve_entry_element = ET.SubElement(cv_element, cv_entry_ml, myattributes)

        for lang in ECV_SETTINGS['languages']:
            langId = lang['id']
            if len(langId) == 3:
                langId = [c[2] for c in LANGUAGE_CODE_MAP if c[3] == langId][0]
            desc = get_ecv_descripion_for_gloss(gloss, langId,
                                                     ECV_SETTINGS['include_phonology_and_frequencies'])
            cve_value_element = ET.SubElement(cve_entry_element, cve_value,
                                              {description: desc, lang_ref: lang['id']})
            cve_value_element.text = get_value_for_ecv(gloss, lang['annotation_idgloss_fieldname'])

    ET.SubElement(top, 'EXTERNAL_REF',
                  {'EXT_REF_ID': 'signbank-ecv', 'TYPE': 'resource_url', 'VALUE': URL + "/dictionary/gloss/"})

    xmlstr = minidom.parseString(ET.tostring(top, 'utf-8')).toprettyxml(indent="   ")
    ecv_file = os.path.join(ECV_FOLDER, dataset_name.lower().replace(" ","_") + ".ecv")
    import codecs
    with codecs.open(ecv_file, "w", "utf-8") as f:
        f.write(xmlstr)

    return ecv_file

def get_ecv_descripion_for_gloss(gloss, lang, include_phonology_and_frequencies=False):
    desc = ""
    if include_phonology_and_frequencies:
        description_fields = ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'locprim', 'relOriMov', 'movDir',
                              'movSh', 'tokNo',
                              'tokNoSgnr']

        for f in description_fields:
            if f in FIELDS['phonology']:
                choice_list = FieldChoice.objects.filter(field__iexact=fieldname_to_category(f))
                machine_value = getattr(gloss, f)
                value = machine_value_to_translated_human_value(machine_value, choice_list, lang)
                if value is None:
                    value = ' '
            else:
                value = get_value_for_ecv(gloss, f)

            if f == 'handedness':
                desc = value
            elif f == 'domhndsh':
                desc = desc + ', (' + value
            elif f == 'subhndsh':
                desc = desc + ',' + value
            elif f == 'handCh':
                desc = desc + '; ' + value + ')'
            elif f == 'tokNo':
                desc = desc + ' [' + value
            elif f == 'tokNoSgnr':
                desc = desc + '/' + value + ']'
            else:
                desc = desc + ', ' + value

    if desc:
        desc += ", "

    trans = [t.translation.text for t in gloss.translation_set.all()]
    desc += ", ".join(
        # The next line was adapted from an older version of this code,
        # that happened to do nothing. I left this for future usage.
        # map(lambda t: str(t.encode('ascii','xmlcharrefreplace')) if isinstance(t, unicode) else t, trans)
        trans
    )

    return desc

def get_value_for_ecv(gloss, fieldname):
    value = None
    annotationidglosstranslation_prefix = "annotationidglosstranslation_"
    if fieldname.startswith(annotationidglosstranslation_prefix):
        language_code_2char = fieldname[len(annotationidglosstranslation_prefix):]
        annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(
            language__language_code_2char=language_code_2char)
        if annotationidglosstranslations and len(annotationidglosstranslations) > 0:
            value = annotationidglosstranslations[0].text
    else:
        try:
            value = getattr(gloss, 'get_' + fieldname + '_display')()

        except AttributeError:
            value = getattr(gloss, fieldname)

    # This was disabled with the move to python 3... might not be needed anymore
    # if isinstance(value,unicode):
    #     value = str(value.encode('ascii','xmlcharrefreplace'))

    if value is None:
        value = " "
    elif not isinstance(value, str):
        value = str(value)

    if value == '-':
        value = ' '
    return value

def write_csv_for_handshapes(handshapelistview, csvwriter):
#  called from the HandshapeListView when search_type is handshape

    fieldnames = settings.HANDSHAPE_RESULT_FIELDS

    fields = [Handshape._meta.get_field(fieldname) for fieldname in fieldnames]

    with override(LANGUAGE_CODE):
        header = ['Handshape ID'] + [ f.verbose_name.encode('ascii', 'ignore').decode() for f in fields ]

    csvwriter.writerow(header)

    # case search result is list of handshapes

    handshape_list = handshapelistview.get_queryset()

    for handshape in handshape_list:
        row = [str(handshape.pk)]

        for f in fields:

            # Try the value of the choicelist
            try:
                value = getattr(handshape, 'get_' + f.name + '_display')()

            # If it's not there, try the raw value
            except AttributeError:
                value = getattr(handshape, f.name)

            if not isinstance(value, str):
                value = str(value)

            row.append(value)

        # Make it safe for weird chars
        safe_row = []
        for column in row:
            try:
                safe_row.append(column.encode('utf-8').decode())
            except AttributeError:
                safe_row.append(None)

        csvwriter.writerow(safe_row)

    return csvwriter


def get_users_who_can_view_dataset(dataset_name):

    dataset = Dataset.objects.get(name=dataset_name)

    all_users = User.objects.all()

    users_who_can_view_dataset = []

    for user in all_users:
        import guardian
        from guardian.shortcuts import get_objects_for_user
        user_view_datasets = guardian.shortcuts.get_objects_for_user(user, 'view_dataset', Dataset)
        if dataset in user_view_datasets:
            users_who_can_view_dataset.append(user.username)

    return users_who_can_view_dataset
