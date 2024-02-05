from django.core.exceptions import ObjectDoesNotExist

from django.contrib.auth.decorators import permission_required
from django.db.models.fields import BooleanField, IntegerField
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag
import os
import shutil
import re
from datetime import datetime
from django.utils.timezone import get_current_timezone
from django.contrib import messages

from signbank.dictionary.models import *
from signbank.dictionary.forms import *

from signbank.tools import gloss_from_identifier, get_default_annotationidglosstranslation

from django.utils.translation import gettext_lazy as _

from guardian.shortcuts import get_user_perms, get_group_perms, get_objects_for_user


def update_sequential_morphology(gloss, values):
    # expecting possibly multiple values
    # this function updates according to the input csv
    # it processes the morphemes in order and creates new components
    # with the appropriate role

    # machine value of the first component
    role = 2

    morphemes = [get_default_annotationidglosstranslation(morpheme.morpheme)
                 for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]

    # the existence of the morphemes in parameter values has already been checked
    for morpheme_def_id in morphemes:
        old_morpheme = MorphologyDefinition.objects.get(id=morpheme_def_id)
        print("DELETE Sequential Morphology: ", old_morpheme)
        old_morpheme.delete()
    for value in values:
        filter_morphemes = Gloss.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                                annotationidglosstranslation__text__exact=value).distinct()
        morpheme = filter_morphemes.first()
        if not morpheme:
            print("morpheme not found")
            continue
        morph_def = MorphologyDefinition()
        morph_def.parent_gloss = gloss
        role_choice = FieldChoice.objects.get(field=FieldChoice.MORPHOLOGYTYPE, machine_value=role)
        morph_def.role = role_choice
        morph_def.morpheme = morpheme
        morph_def.save()
        role = role + 1

    return


def update_simultaneous_morphology(gloss, values):
    # expecting possibly multiple values

    existing_sim_ids = [morpheme.id
                        for morpheme in SimultaneousMorphologyDefinition.objects.filter(parent_gloss_id=gloss)]
    new_sim_tuples = []
    for value in values:
        (morpheme, role) = value.split(':')
        new_sim_tuples.append((morpheme, role))

    # delete any existing simultaneous morphology objects rather than update
    # to allow (re-)insertion in the correct order
    for sim_id in existing_sim_ids:
        sim = SimultaneousMorphologyDefinition.objects.get(id=sim_id)
        print("DELETE Simultaneous Morphology: ", sim)
        sim.delete()

    # the existence of the morphemes has already been checked, but check again anyway
    for (morpheme, role) in new_sim_tuples:

        filter_morphemes = Gloss.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                                annotationidglosstranslation__text__exact=morpheme).distinct()
        morpheme_gloss = filter_morphemes.first()
        if not morpheme_gloss:
            print("morpheme not found")
            continue
        # create new morphology
        sim = SimultaneousMorphologyDefinition()
        sim.parent_gloss = gloss
        sim.morpheme = morpheme_gloss
        sim.role = role
        sim.save()

    return


def update_blend_morphology(gloss, values):

    existing_blends = [ble_morph.id
                       for ble_morph in BlendMorphology.objects.filter(parent_gloss=gloss)]

    new_blend_tuples = []
    for value in values:
        (morpheme, role) = value.split(':')
        new_blend_tuples.append((morpheme, role))

    # delete any existing blend morphology objects
    for existing_blend in existing_blends:
        blend_object = BlendMorphology.objects.get(id=existing_blend)
        print("DELETE Blend Morphology for gloss ", str(gloss.pk), ": ", blend_object.glosses.pk, " ", blend_object.role)
        blend_object.delete()

    for (morpheme, role) in new_blend_tuples:

        filter_morphemes = Gloss.objects.filter(lemma__dataset=gloss.lemma.dataset,
                                                annotationidglosstranslation__text__exact=morpheme).distinct()
        morpheme_gloss = filter_morphemes.first()
        if not morpheme_gloss:
            print("morpheme not found")
            continue
        # create new morphology
        new_blend = BlendMorphology()
        new_blend.parent_gloss = gloss
        new_blend.glosses = morpheme_gloss
        new_blend.role = role
        new_blend.save()

    return


def subst_relations(gloss, values):
    # expecting possibly multiple values
    # values is a list of values, where each value is a tuple of the form 'Role:String'
    # The format of argument values has been checked before calling this function

    existing_relations = [(relation.id, relation.role, relation.target.id) for relation in Relation.objects.filter(source=gloss)]
    existing_relation_ids = [ r[0] for r in existing_relations ]
    existing_relations_by_role = dict()

    for (rel_id, rel_role, rel_other_gloss) in existing_relations:

        if rel_role in existing_relations_by_role:
            existing_relations_by_role[rel_role].append(rel_other_gloss)
        else:
            existing_relations_by_role[rel_role] = [rel_other_gloss]

    new_tuples_to_add = []
    already_existing_to_keep = []

    for value in values:
        (role, target) = value.split(':')
        role = role.strip()
        target = target.strip()
        if role in existing_relations_by_role and target in existing_relations_by_role[role]:
            already_existing_to_keep.append((role,target))
        else:
            new_tuples_to_add.append((role, target))

    # delete existing relations and reverse relations involving this gloss
    for rel_id in existing_relation_ids:
        rel = Relation.objects.get(id=rel_id)

        if (rel.role, rel.target.id) in already_existing_to_keep:
            continue

        # Also delete the reverse relation
        reverse_relations = Relation.objects.filter(source=rel.target, target=rel.source,
                                                    role=Relation.get_reverse_role(rel.role))
        if reverse_relations.count() > 0:
            print("DELETE reverse relation: target: ", rel.target, ", relation: ", reverse_relations[0])
            reverse_relations[0].delete()

        print("DELETE Relation: ", rel)
        rel.delete()

    # all remaining existing relations are to be updated
    for (role, target) in new_tuples_to_add:
        try:
            target_gloss = Gloss.objects.get(pk=target)
            rel = Relation(source=gloss, role=role, target=target_gloss)
            rel.save()
            # Also add the reverse relation
            reverse_relation = Relation(source=target_gloss, target=gloss, role=Relation.get_reverse_role(role))
            reverse_relation.save()
        except:
            print("target gloss not found")
            continue

    return


def subst_foreignrelations(gloss, values):
    # expecting possibly multiple values
    # values is a list of values, where each value is a tuple of the form 'Boolean:String:String'
    # The format of argument values has been checked before calling this function

    existing_relations = [(relation.id, relation.other_lang_gloss)
                          for relation in RelationToForeignSign.objects.filter(gloss=gloss)]

    existing_relation_ids = [r[0] for r in existing_relations]
    existing_relation_other_glosses = [r[1] for r in existing_relations]

    new_relation_tuples = []
    for value in values:
        (loan_word, other_lang, other_lang_gloss) = value.split(':')
        new_relation_tuples.append((loan_word, other_lang, other_lang_gloss))

    new_relations = [t[2] for t in new_relation_tuples]

    # delete any existing relations with obsolete other language gloss
    for rel_id in existing_relation_ids:
        rel = RelationToForeignSign.objects.get(id=rel_id)
        if rel.other_lang_gloss not in new_relations:
            print("DELETE Relation to Foreign Sign: ", rel)
            rel.delete()

    # all remaining existing relations are to be updated
    for (loan_word, other_lang, other_lang_gloss) in new_relation_tuples:
        if other_lang_gloss in existing_relation_other_glosses:
            # update existing relation
            rel = RelationToForeignSign.objects.get(gloss=gloss, other_lang_gloss=other_lang_gloss)
            rel.loan = loan_word in ['Yes', 'yes', 'ja', 'Ja', '是', 'true', 'True', True, 1]
            rel.other_lang = other_lang
            rel.save()
        else:
            # create new relation
            rel = RelationToForeignSign(gloss=gloss, loan=loan_word,
                                        other_lang=other_lang, other_lang_gloss=other_lang_gloss)
            rel.save()

    return


def update_tags(gloss, values):
    # expecting possibly multiple values
    current_tag_ids = [tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    new_tag_ids = [tag.id for tag in Tag.objects.filter(name__in=values)]

    # the existence of the new tag has already been checked
    for tag_id in current_tag_ids:

        if tag_id not in new_tag_ids:
            # delete tag from object
            tagged_obj = TaggedItem.objects.get(object_id=gloss.id,tag_id=tag_id)
            print("DELETE TAGGED OBJECT: ", tagged_obj, ' for gloss: ', tagged_obj.object_id)
            tagged_obj.delete()

    if not new_tag_ids:
        # this was a delete
        return

    for value in values:
        Tag.objects.add_tag(gloss, value)

    return


def subst_notes(gloss, values):
    # this is called by csv_import to modify the notes for a gloss

    note_role_choices = FieldChoice.objects.filter(field='NoteType')
    # this is used to speedup matching updates to Notes
    # it allows the type of note to be in either English or Dutch in the CSV file
    # this actually isn't used at the moment, the CSV export is to English
    note_reverse_translation = {}
    for nrc in note_role_choices:
        for language in MODELTRANSLATION_LANGUAGES:
            name_languagecode = 'name_' + language.replace('-', '_')
            # check to make sure the model translation has been installed properly
            try:
                notes_translation = getattr(nrc, name_languagecode)
            except KeyError:
                continue

            note_reverse_translation[notes_translation] = nrc

    for original_note in gloss.definition_set.all():
        original_note.delete()

    # convert new Notes csv value to proper format
    # the syntax of the new note values has already been checked at a previous stage of csv import
    new_notes_values = []

    # the space is required in order to identify multiple notes in the input
    split_values = re.split(r', ', values)
    for note_value in split_values:
        take_apart = re.match(r'([^:]+):\s?\((False|True),(\d),(.*)\)', note_value)

        if take_apart:
            (field, name, count, text) = take_apart.groups()
            new_tuple = (field, name, count, text)
            new_notes_values.append(new_tuple)

    # make sure the delete code has run before saving the definitions again
    gloss.refresh_from_db()

    for (role, published, count, text) in new_notes_values:
        is_published = (published == 'True')
        note_role = note_reverse_translation[role]
        index_count = int(count)
        defn = Definition(gloss=gloss, count=index_count, role=note_role, text=text, published=is_published)
        defn.save()

    return
