import signbank.settings
from signbank.settings.base import WSGI_FILE, WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, LANGUAGE_CODE
import os
import shutil
from html.parser import HTMLParser
from zipfile import ZipFile
from datetime import datetime, date
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

def save_media(source_folder,goal_folder,gloss,extension):
        
    #Add a dot before the extension if needed
    if extension[0] != '.':
        extension = '.' + extension

    #Figure out some names
    annotation_id = gloss.annotation_idgloss
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
    already_exists_dutch = []
    already_exists_english = []
    glosses_dataset = ''

    this_gloss = ''
    dutch_found = False
    english_found = False

    #Create an overview of all fields, sorted by their human name
    with override(LANGUAGE_CODE):

        # initialise
        glosses_dataset = ''

        glosses_dataset = valuedict['Dataset']
        # python sets undefined items in dictionary to 'None'

        glosses_dataset = glosses_dataset.strip()

        # print('dataset found: ', glosses_dataset)

        if glosses_dataset != None and glosses_dataset != '' and glosses_dataset != 'None' and not glosses_dataset in datasets:
            error_string = 'Row ' + str(row_nr + 1) + ': Dataset ' + glosses_dataset + ' not found.'

            errors_found += [error_string]

        if not glosses_dataset or glosses_dataset == 'None' or glosses_dataset == None:
            # Dataset must be non-empty to create a new gloss
            error_string = 'Row ' + str(row_nr + 1) + ': Dataset must be non-empty.'

            errors_found += [error_string]


        lemma_id_gloss = valuedict['Lemma ID Gloss']

        lemma_id_gloss = lemma_id_gloss.strip()

        annotation_id_gloss = valuedict['Annotation ID Gloss: Dutch']

        annotation_id_gloss = annotation_id_gloss.strip()

        annotation_id_gloss_en = valuedict['Annotation ID Gloss: English']

        annotation_id_gloss_en = annotation_id_gloss_en.strip()

        try:
            dutch_gloss = gloss_from_identifier(annotation_id_gloss)

            if not dutch_gloss:
                raise ObjectDoesNotExist
            else:
                dutch_found = True

        except ObjectDoesNotExist:
            dutch_gloss = None
            pass

        try:

            english_gloss = Gloss.objects.get(annotation_idgloss_en=annotation_id_gloss_en)

            if not english_gloss:
                raise ObjectDoesNotExist
            else:
                english_found = True

        except ObjectDoesNotExist:
            english_gloss = None
            pass

        # print('dataset of gloss: ', glosses_dataset)
        if dutch_found and english_found and dutch_gloss == english_gloss:
            already_exists.append({'gloss_pk': dutch_gloss.pk,
                                    'dataset': dutch_gloss.dataset,
                                    'lemma_id_gloss': 'Lemma ID Gloss',
                                    'lemma_id_gloss_value': lemma_id_gloss,
                                    'annotation_id_gloss': 'Annotation ID Gloss: Dutch',
                                    'annotation_id_gloss_value': annotation_id_gloss,
                                    'annotation_id_gloss_en': 'Annotation ID Gloss: English',
                                    'annotation_id_gloss_en_value': annotation_id_gloss_en})
        elif dutch_found and english_found:
            already_exists_dutch.append({'gloss_pk': dutch_gloss.pk,
                                         'dataset': dutch_gloss.dataset,
                                         'lemma_id_gloss': 'Lemma ID Gloss',
                                         'lemma_id_gloss_value': lemma_id_gloss,
                                         'annotation_id_gloss': 'Annotation ID Gloss: Dutch',
                                         'annotation_id_gloss_value': annotation_id_gloss,
                                         'annotation_id_gloss_en': 'Annotation ID Gloss: English',
                                         'annotation_id_gloss_en_value': annotation_id_gloss_en})
            already_exists_english.append({'gloss_pk': english_gloss.pk,
                                           'dataset': english_gloss.dataset,
                                           'lemma_id_gloss': 'Lemma ID Gloss',
                                           'lemma_id_gloss_value': lemma_id_gloss,
                                           'annotation_id_gloss': 'Annotation ID Gloss: Dutch',
                                           'annotation_id_gloss_value': annotation_id_gloss,
                                           'annotation_id_gloss_en': 'Annotation ID Gloss: English',
                                           'annotation_id_gloss_en_value': annotation_id_gloss_en})
        elif dutch_found:
            already_exists_dutch.append({'gloss_pk': dutch_gloss.pk,
                                         'dataset': dutch_gloss.dataset,
                                         'lemma_id_gloss': 'Lemma ID Gloss',
                                         'lemma_id_gloss_value': lemma_id_gloss,
                                         'annotation_id_gloss': 'Annotation ID Gloss: Dutch',
                                         'annotation_id_gloss_value': annotation_id_gloss,
                                         'annotation_id_gloss_en': 'Annotation ID Gloss: English',
                                         'annotation_id_gloss_en_value': annotation_id_gloss_en})
        elif english_found:
            already_exists_english.append({'gloss_pk': english_gloss.pk,
                                           'dataset': english_gloss.dataset,
                                         'lemma_id_gloss': 'Lemma ID Gloss',
                                         'lemma_id_gloss_value': lemma_id_gloss,
                                         'annotation_id_gloss': 'Annotation ID Gloss: Dutch',
                                         'annotation_id_gloss_value': annotation_id_gloss,
                                         'annotation_id_gloss_en': 'Annotation ID Gloss: English',
                                         'annotation_id_gloss_en_value': annotation_id_gloss_en})
        else:
            new_gloss.append({'gloss_pk': str(row_nr),
                                'dataset': glosses_dataset,
                                'lemma_id_gloss': 'Lemma ID Gloss',
                                'lemma_id_gloss_value': lemma_id_gloss,
                                'annotation_id_gloss': 'Annotation ID Gloss: Dutch',
                                'annotation_id_gloss_value': annotation_id_gloss,
                                'annotation_id_gloss_en': 'Annotation ID Gloss: English',
                                'annotation_id_gloss_en_value': annotation_id_gloss_en})

        # print('create gloss field ', lemma_id_gloss, ' with annotation ', annotation_id_gloss, ' english: ', annotation_id_gloss_en)

        # print('create new gloss: ', new_gloss, ' already exists: ', already_exists, ' errors: ', errors_found)

    return (new_gloss, already_exists, already_exists_dutch, already_exists_english, errors_found)

def compare_valuedict_to_gloss(valuedict,gloss,my_datasets):
    """Takes a dict of arbitrary key-value pairs, and compares them to a gloss"""

    errors_found = []
    column_name_error = False
    tag_name_error = False
    all_tags = [t.name for t in Tag.objects.all()]
    all_tags_display = ', '.join([t.replace('_',' ') for t in all_tags])

    #Create an overview of all fields, sorted by their human name
    with override(LANGUAGE_CODE):

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

            elif human_key == 'Keywords':

                current_keyword_string = str(', '.join([str(translation.translation.text) for translation in gloss.translation_set.all()]))

                if current_keyword_string != new_human_value and new_human_value != 'None' and new_human_value != '':
                    differences.append({'pk':gloss.pk,
                                        'dataset': current_dataset,
                                        'idgloss':gloss.annotation_idgloss,
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
                                        'idgloss':gloss.annotation_idgloss,
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
                                        'idgloss': gloss.annotation_idgloss,
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
                        error_string = 'For ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) + '), Dataset must be non-empty. There is currently no dataset defined for this gloss.'

                        errors_found += [error_string]
                    continue

                # if we get to here, the user has specificed a new value for the dataset
                if new_human_value in my_datasets:
                    if current_dataset != new_human_value:
                        differences.append({'pk': gloss.pk,
                                            'dataset': current_dataset,
                                            'idgloss': gloss.annotation_idgloss,
                                            'machine_key': human_key,
                                            'human_key': human_key,
                                            'original_machine_value': current_dataset,
                                            'original_human_value': current_dataset,
                                            'new_machine_value': new_human_value,
                                            'new_human_value': new_human_value})
                else:
                    error_string = 'For ' + gloss.annotation_idgloss + ' (' + str(
                        gloss.pk) + '), could not find ' + str(new_human_value) + ' for ' + human_key

                    errors_found += [error_string]

                continue

            elif human_key == 'Relations to other signs':
                if new_human_value == 'None' or new_human_value == '':
                    continue

                relations = [(relation.role, relation.target.annotation_idgloss) for relation in gloss.relation_sources.all()]

                # sort tuples on other gloss to allow comparison with imported values

                sorted_relations = sorted(relations, key=lambda tup: tup[1])
                # print("sorted_relations: ", sorted_relations)

                relations_with_categories = []
                for rel_cat in sorted_relations:
                    relations_with_categories.append(':'.join(rel_cat))
                current_relations_string = ",".join(relations_with_categories)

                # print('Relations current: ', current_relations_string)

                (checked_new_human_value, errors) = check_existance_relations(gloss, relations_with_categories, new_human_value_list)

                # print('Relations new: ', checked_new_human_value)

                if len(errors):
                    errors_found += errors

                elif current_relations_string != checked_new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'idgloss': gloss.annotation_idgloss,
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

                # print('Relations foreign current: ', current_relations_foreign_string)

                (checked_new_human_value, errors) = check_existance_foreign_relations(gloss, relations_with_categories, new_human_value_list)

                # print('Relations foreign new: ', checked_new_human_value)

                if len(errors):
                    errors_found += errors

                elif current_relations_foreign_string != checked_new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'idgloss': gloss.annotation_idgloss,
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

                morphemes = [morpheme.morpheme.annotation_idgloss for morpheme in
                             MorphologyDefinition.objects.filter(parent_gloss=gloss)]
                morphemes_string = ", ".join(morphemes)

                # print('Sequential Morphology import: ', morphemes_string)

                (found, not_found, errors) = check_existance_sequential_morphology(gloss, new_human_value_list)

                # print('Sequential Morphology new: ', new_human_value)

                if len(errors):
                    errors_found += errors

                elif morphemes_string != new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'idgloss': gloss.annotation_idgloss,
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

                morphemes = [(m.morpheme.annotation_idgloss, m.role) for m in gloss.simultaneous_morphology.all()]
                sim_morphs = []
                for m in morphemes:
                    sim_morphs.append(':'.join(m))
                simultaneous_morphemes = ','.join(sim_morphs)

                # print('Simultaneous Morphology import: ', simultaneous_morphemes)

                (checked_new_human_value, errors) = check_existance_simultaneous_morphology(gloss, new_human_value_list)

                # print('Simultaneous Morphology new: ', checked_new_human_value)

                if len(errors):
                    errors_found += errors

                elif simultaneous_morphemes != checked_new_human_value:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'idgloss': gloss.annotation_idgloss,
                                        'machine_key': human_key,
                                        'human_key': human_key,
                                        'original_machine_value': simultaneous_morphemes,
                                        'original_human_value': simultaneous_morphemes,
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

                # print('current tag names: ', tag_names)

                new_human_value_list = [v.replace(' ', '_') for v in new_human_value_list]

                new_human_value_list_no_dups = list(set(new_human_value_list))
                sorted_new_tags = sorted(new_human_value_list_no_dups)

                # check for non-existant tags
                for t in sorted_new_tags:
                    if t in all_tags:
                        pass
                    else:
                        error_string = 'For ' + gloss.annotation_idgloss + ' (' + str(
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

                # print('Tags list: ', sorted_new_tags)

                if tag_names != sorted_new_tags:
                    differences.append({'pk': gloss.pk,
                                        'dataset': current_dataset,
                                        'idgloss': gloss.annotation_idgloss,
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
                error_string = 'For ' + gloss.annotation_idgloss + ' (' + str(
                    gloss.pk) + '), could not identify column name: ' + str(human_key)

                errors_found += [error_string]

                if not column_name_error:
                    # error_string = 'Allowed column names are: ' + allowed_columns
                    error_string = 'HINT: Try exporting a CSV file to see what column names can be used.'
                    errors_found += [error_string]
                    column_name_error = True

                continue

            # print('SUCCESS: human_key (', human_key, '), machine_key: (', machine_key, ')')

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

                    new_machine_value = human_to_machine_values[new_human_value]
                except KeyError:
                    # print('new human value: ', new_human_value)

                    #If you can't find a corresponding human value, maybe it's empty
                    if new_human_value in ['',' ', None, 'None']:
                        # print('exception in new human value to machine value: ', new_human_value)
                        new_human_value = 'None'
                        new_machine_value = None

                    #If not, stop trying
                    else:
                        # raise MachineValueNotFoundError('At '+gloss.idgloss+' ('+str(gloss.pk)+'), could not find option '+str(new_human_value)+' for '+human_key)
                        error_string = 'For '+gloss.annotation_idgloss+' ('+str(gloss.pk)+'), could not find option '+str(new_human_value)+' for '+human_key

                        errors_found += [error_string]
            #Do something special for integers and booleans
            elif field.__class__.__name__ == 'IntegerField':

                # print('import CSV IntegerField human value for ', human_key, ': ', new_human_value)

                try:
                    new_machine_value = int(new_human_value)
                except ValueError:
                    new_human_value = 'None'
                    new_machine_value = None
            elif field.__class__.__name__ == 'NullBooleanField':

                # print('import CSV NullBooleanField human value for ', human_key, ': ', new_human_value)

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
                            error_string = 'For ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) + '), value ' + str(new_human_value) + ' for ' + human_key + ' should be a Boolean or Neutral.'
                    else:
                        if new_human_value != None and new_human_value != '' and new_human_value != 'None':
                            error_string = 'For ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) + '), value ' + str(new_human_value) + ' for ' + human_key + ' is not a Boolean.'

                    if error_string:
                        errors_found += [error_string]
            #If all the above does not apply, this is a None value or plain text
            else:
                # print('Import CSV 148: not Integer, not Boolean: new human value: (', new_human_value, ')')

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
                new_machine_value = unescape(new_machine_value)
                new_human_value = unescape(new_human_value)
            except TypeError:
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
                                    'idgloss':gloss.annotation_idgloss,
                                    'machine_key':machine_key,
                                    'human_key':human_key,
                                    'original_machine_value':original_machine_value,
                                    'original_human_value':original_human_value,
                                    'new_machine_value':new_machine_value,
                                    'new_human_value':new_human_value})

    return (differences, errors_found)


def check_existance_dialect(gloss, values):

    errors = []
    found = []
    not_found = []

    for new_value in values:
        if Dialect.objects.filter(name=new_value):
            if new_value in found:
                error_string = 'WARNING: For gloss ' + gloss.annotation_idgloss + ' (' + str(
                    gloss.pk) + '), new Dialect value ' + str(new_value) + ' is duplicate.'
                errors.append(error_string)
            else:
                found += [new_value]
        else:
            error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) + '), new Dialect value ' + str(new_value) + ' not found.'
            errors.append(error_string)
            not_found += [new_value]
        continue

    return (found, not_found, errors)


def check_existance_signlanguage(gloss, values):

    errors = []
    found = []
    not_found = []

    for new_value in values:
        if SignLanguage.objects.filter(name=new_value):
            if new_value in found:
                error_string = 'WARNING: For gloss ' + gloss.annotation_idgloss + ' (' + str(
                    gloss.pk) + '), new Sign Language value ' + str(new_value) + ' is duplicate.'
                errors.append(error_string)
            else:
                found += [new_value]
        else:
            error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) + '), new Sign Language value ' + str(new_value) + ' not found.'

            errors.append(error_string)
            not_found += [new_value]
        continue

    return (found, not_found, errors)

def check_existance_sequential_morphology(gloss, values):

    errors = []
    found = []
    not_found = []

    for new_value in values:

        try:

            # get the id for the morpheme identifier
            # morpheme_id = gloss_from_identifier(new_value)
            # print('check_existance_sequential_morphology, new_value: ', new_value)
            # this is a gloss, make sure it exists
            morpheme = gloss_from_identifier(new_value)

            if new_value in found:
                error_string = 'WARNING: For gloss ' + gloss.annotation_idgloss + ' (' + str(
                    gloss.pk) + '), new Sequential Morphology value ' + str(new_value) + ' is duplicate.'
                errors.append(error_string)
            else:
                found += [new_value]

        # except ObjectDoesNotExist:
        except:
            if new_value in not_found:
                error_string = 'WARNING: For gloss ' + gloss.annotation_idgloss + ' (' + str(
                    gloss.pk) + '), new Sequential Morphology value ' + str(new_value) + ' is duplicate.'
            else:
                error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(
                    gloss.pk) + '), new Sequential Morphology value ' + str(new_value) + ' not found.'
            errors.append(error_string)
            not_found += [new_value]

            continue

    if len(values) > 4:
        error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) + ', too many Sequential Morphology components.'
        errors.append(error_string)

    return (found, not_found, errors)

def check_existance_simultaneous_morphology(gloss, values):

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
            error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) \
                           + '), formatting error in Simultaneous Morphology: ' + str(new_value_tuple) + '. Tuple morpheme:role expected.'
            errors.append(error_string)

    for (morpheme, role) in tuples_list:

        try:

            # get the id for the morpheme identifier
            # morpheme_id = gloss_from_identifier(new_value)
            # print('check_existance_simultaneous_morphology, new_value: ', morpheme)
            # this is a gloss, make sure it exists
            morpheme_gloss = gloss_from_identifier(morpheme)
            morpheme_id = Morpheme.objects.filter(gloss_ptr_id=morpheme_gloss)

            # print('check_existance_simultaneous_morphology, morpheme_id: ', morpheme_id, ' morpheme_gloss: ', morpheme_gloss)

            if not morpheme_id:
                # print('check_existance_simultaneous_morphology: morpheme not found')
                error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(
                    gloss.pk) + '), new Simultaneous Morphology gloss ' + str(morpheme) + ' is not a morpheme.'
                errors.append(error_string)
                continue

            if checked:
                checked += ',' + ':'.join([morpheme, role])
            else:
                checked = ':'.join([morpheme, role])

        except ObjectDoesNotExist:
            error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(
                gloss.pk) + '), new Simultaneous Morphology value ' + str(morpheme) + ' is not a gloss.'
            errors.append(error_string)

            continue

    return (checked, errors)

RELATION_ROLES = ['homonym', 'Homonym', 'synonym', 'Synonym', 'variant', 'Variant',
                         'antonym', 'Antonym', 'hyponym', 'Hyponym', 'hypernym', 'Hypernym', 'seealso', 'See Also']

RELATION_ROLES_DISPLAY = 'homonym, synonym, variant, antonym, hyponym, hypernym, seealso'

def check_existance_relations(gloss, relations, values):

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
            error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) \
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
            error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) \
                           + '), column Relations to other signs: ' + role + ':' + other_gloss + '. Role ' + role + ' not found.' \
                    + ' Role should be one of: ' + RELATION_ROLES_DISPLAY + '.'
            errors.append(error_string)

    # check other glosses
    for (role, other_gloss) in sorted_values:

        try:

            target_gloss = gloss_from_identifier(other_gloss)

            if not target_gloss:
                raise ObjectDoesNotExist

            if checked:
                checked += ',' + ':'.join([role, other_gloss])
            else:
                checked = ':'.join([role, other_gloss])

        except ObjectDoesNotExist:
            error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) \
                    + '), column Relations to other signs: ' + role + ':' + other_gloss + '. Other gloss ' + other_gloss + ' not found.' \
                    + ' Please use Annotation ID Gloss: Dutch to identify the other gloss.'
            errors.append(error_string)

            pass

    return (checked, errors)


def check_existance_foreign_relations(gloss, relations, values):

    errors = []
    checked = ''
    sorted_values = []

    for new_value_tuple in values:
        try:
            (loan_word, other_lang, other_lang_gloss) = new_value_tuple.split(':')
            # print('taken apart: loan: (', loan_word, '), other: (', other_lang, '), gloss: (', other_lang_gloss, ')')
            sorted_values.append((loan_word,other_lang,other_lang_gloss))
        except ValueError:
            error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) \
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
            error_string = 'ERROR: For gloss ' + gloss.annotation_idgloss + ' (' + str(gloss.pk) \
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

def get_static_urls_of_files_in_writable_folder(root_folder,since_timestamp=0):

    full_root_path = signbank.settings.server_specific.WRITABLE_FOLDER+root_folder+'/'
    static_urls = {}

    for subfolder_name in os.listdir(full_root_path):
        if os.path.isdir(full_root_path+subfolder_name):
            for filename in os.listdir(full_root_path+subfolder_name):

                if os.path.getmtime(full_root_path+subfolder_name+'/'+filename) > since_timestamp:
                    res = re.search(r'(.+)\.[^\.]*', filename)

                    try:
                        gloss_id = res.group(1)
                    except AttributeError:
                        continue

                    static_urls[gloss_id] = reverse('dictionary:protected_media', args=[''])+root_folder+'/'+quote(subfolder_name)+'/'+quote(filename)

    return static_urls

def get_gloss_data(since_timestamp=0):

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
                    elif os.path.isfile(still_goal_location):
                        # Make a backup
                        backup_id = 1
                        made_backup = False

                        while not made_backup:

                            if not os.path.isfile(still_goal_location + '_' + str(backup_id)):
                                os.rename(still_goal_location, still_goal_location + '_' + str(backup_id))
                                made_backup = True
                            else:
                                backup_id += 1
                    shutil.copy(dir + os.sep + filename, destination + os.sep + filename)
            shutil.rmtree(dir)
    except ImportError as i:
        print(i.message)
    except IOError as io:
        print(io.message)


def get_selected_datasets_for_user(user):
    if user.is_authenticated:
        user_profile = UserProfile.objects.get(user=user)
        selected_datasets = user_profile.selected_datasets.all()
        if not selected_datasets:
            selected_datasets = get_objects_for_user(user, 'view_dataset', Dataset)
        return selected_datasets
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
