
from signbank.dictionary.models import Gloss, GlossRevision, Language, FieldChoice, Handshape
import datetime as DT
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect, JsonResponse
from signbank.dictionary.update import okay_to_update_gloss
from django.urls import reverse
from django.conf import settings
from signbank.dictionary.translate_choice_list import check_value_to_translated_human_value
from django.utils.translation import gettext_lazy as _, activate, gettext
from signbank.dictionary.context_data import get_selected_datasets
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, MultipleObjectsReturned
from signbank.csv_interface import normalize_field_choice
from django.db.models import Q, Count, CharField, TextField, Value as V


def get_field_choice_from_name(fieldname, value, language_codes):
    # try to get a matching field choice in one of the languages
    if fieldname not in Gloss.get_field_names():
        return value
    field = Gloss.get_field(fieldname)
    if not hasattr(field, 'field_choice_category'):
        return value
    field_choice_category = field.field_choice_category
    for language_name_field in language_codes:
        # next_language_name = 'name_'+language_code
        fieldchoice = FieldChoice.objects.filter(Q(**{'field': field_choice_category,
                                                      language_name_field: value})).first()
        if not fieldchoice:
            normalised_choice = normalize_field_choice(value)
            fieldchoice = FieldChoice.objects.filter(Q(**{'field': field_choice_category,
                                                          language_name_field: normalised_choice})).first()
        if fieldchoice:
            break
    return fieldchoice.name if fieldchoice else '-'


def get_handshape_from_name(fieldname, value, language_codes):
    # try to get a matching handshape name in one of the languages
    if fieldname not in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
        return value
    for language_name_field in language_codes:
        # next_language_name = 'name_'+language_code
        handshape = Handshape.objects.filter(Q(**{language_name_field: value})).first()
        if not handshape:
            normalised_choice = normalize_field_choice(value)
            handshape = Handshape.objects.filter(Q(**{language_name_field: normalised_choice})).first()
        if handshape:
            break
    return handshape.name if handshape else '-'


def pretty_print_revisions(gloss):
    # set up all the various translation fields for the interface languages
    language_codes = ['name_en']
    for interface_language_code in settings.MODELTRANSLATION_LANGUAGES:
        name_languagecode = 'name_' + interface_language_code.replace('-', '_')
        if name_languagecode not in language_codes:
            language_codes.append(name_languagecode)
    revisions = []
    for revision in GlossRevision.objects.filter(gloss=gloss):
        if revision.field_name.startswith('sense_'):
            prefix, order, language_2char = revision.field_name.split('_')
            language = Language.objects.get(language_code_2char=language_2char)
            revision_verbose_fieldname = gettext('Sense') + ' ' + order + " (%s)" % language.name
        elif revision.field_name.startswith('description_'):
            prefix, language_2char = revision.field_name.split('_')
            language = Language.objects.get(language_code_2char=language_2char)
            revision_verbose_fieldname = gettext('NME Video Description') + " (%s)" % language.name
        elif revision.field_name.startswith('nmevideo_'):
            prefix, operation = revision.field_name.split('_')
            if operation == 'create':
                revision_verbose_fieldname = gettext("NME Video") + ' ' + gettext("Create")
            elif operation == 'delete':
                revision_verbose_fieldname = gettext("NME Video") + ' ' + gettext("Delete")
            else:
                revision_verbose_fieldname = gettext("NME Video") + ' ' + gettext("Update")
        elif revision.field_name in Gloss.get_field_names():
            revision_verbose_fieldname = gettext(Gloss.get_field(revision.field_name).verbose_name)
        elif revision.field_name == 'sequential_morphology':
            revision_verbose_fieldname = gettext("Sequential Morphology")
        elif revision.field_name == 'simultaneous_morphology':
            revision_verbose_fieldname = gettext("Simultaneous Morphology")
        elif revision.field_name == 'blend_morphology':
            revision_verbose_fieldname = gettext("Blend Morphology")
        elif revision.field_name.startswith('lemma'):
            language_2char = revision.field_name[-2:]
            language = Language.objects.get(language_code_2char=language_2char)
            revision_verbose_fieldname = gettext('Lemma ID Gloss') + " (%s)" % language.name
        elif revision.field_name.startswith('annotation'):
            language_2char = revision.field_name[-2:]
            language = Language.objects.get(language_code_2char=language_2char)
            revision_verbose_fieldname = gettext('Annotation ID Gloss') + " (%s)" % language.name
        elif revision.field_name == 'archived':
            revision_verbose_fieldname = gettext("Deleted")
        elif revision.field_name == 'restored':
            revision_verbose_fieldname = gettext("Restored")
        else:
            revision_verbose_fieldname = gettext(revision.field_name)
            # print('fall through: ', revision.field_name, revision_verbose_fieldname)

        # field name qualification is stored separately here
        # Django was having a bit of trouble translating it when embedded in the field_name string below
        if revision.field_name == 'Tags':
            if revision.old_value:
                # this translation exists in the interface of Gloss Edit View
                delete_command = gettext('delete this tag')
                field_name_qualification = ' (' + delete_command + ')'
            elif revision.new_value:
                # this translation exists in the interface of Gloss Edit View
                add_command = gettext('Add Tag')
                field_name_qualification = ' (' + add_command + ')'
            else:
                # this shouldn't happen
                field_name_qualification = ''
        elif revision.field_name in ['Sense', 'Senses', 'senses']:
            if revision.old_value and not revision.new_value:
                # this translation exists in the interface of Gloss Edit View
                delete_command = gettext('Delete')
                field_name_qualification = ' (' + delete_command + ')'
            elif revision.new_value and not revision.old_value:
                # this translation exists in the interface of Gloss Edit View
                add_command = gettext('Create')
                field_name_qualification = ' (' + add_command + ')'
            else:
                # this translation exists in the interface of Gloss Edit View
                add_command = gettext('Update')
                field_name_qualification = ' (' + add_command + ')'
        elif revision.field_name == 'Sentence':
            if revision.old_value and not revision.new_value:
                # this translation exists in the interface of Gloss Edit View
                delete_command = gettext('Delete')
                field_name_qualification = ' (' + delete_command + ')'
            elif revision.new_value and not revision.old_value:
                # this translation exists in the interface of Gloss Edit View
                add_command = gettext('Create')
                field_name_qualification = ' (' + add_command + ')'
            else:
                # this translation exists in the interface of Gloss Edit View
                add_command = gettext('Update')
                field_name_qualification = ' (' + add_command + ')'
        elif revision.field_name in ['sequential_morphology', 'simultaneous_morphology', 'blend_morphology']:
            if revision.old_value and not revision.new_value:
                # this translation exists in the interface of Gloss Edit View
                delete_command = gettext('Delete')
                field_name_qualification = ' (' + delete_command + ')'
            elif revision.new_value and not revision.old_value:
                # this translation exists in the interface of Gloss Edit View
                add_command = gettext('Create')
                field_name_qualification = ' (' + add_command + ')'
            else:
                # this translation exists in the interface of Gloss Edit View
                add_command = gettext('Update')
                field_name_qualification = ' (' + add_command + ')'
        elif revision.field_name.startswith('lemma') or revision.field_name.startswith('annotation'):
            field_name_qualification = ''
        elif revision.field_name.startswith('sense'):
            field_name_qualification = ''
        else:
            field_name_qualification = ''
        if revision.field_name in Gloss.get_field_names():
            field = Gloss.get_field(revision.field_name)
            if hasattr(field, 'field_choice_category'):
                display_old_value = get_field_choice_from_name(revision.field_name, revision.old_value, language_codes)
                display_new_value = get_field_choice_from_name(revision.field_name, revision.new_value, language_codes)
            elif field.name in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
                display_old_value = get_handshape_from_name(revision.field_name, revision.old_value, language_codes)
                display_new_value = get_handshape_from_name(revision.field_name, revision.new_value, language_codes)
            else:
                display_old_value = check_value_to_translated_human_value(revision.field_name, revision.old_value)
                display_new_value = check_value_to_translated_human_value(revision.field_name, revision.new_value)
        else:
            display_old_value = revision.old_value
            display_new_value = revision.new_value
        revision_dict = {
            'is_tag': revision.field_name == 'Tags',
            'gloss': revision.gloss,
            'user': revision.user,
            'time': revision.time,
            'field_name': revision_verbose_fieldname,
            'field_name_qualification': field_name_qualification,
            'old_value': display_old_value,
            'new_value': display_new_value }
        revisions.append(revision_dict)

    return revisions


@permission_required('dictionary.change_gloss')
def cleanup(request, glossid):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    revisions = GlossRevision.objects.filter(gloss=gloss).order_by('time')

    empty_revisions = []
    duplicate_revisions = dict()
    tuple_updates = []
    tuple_update_already_seen = []
    for revision in revisions:
        if revision.old_value in ['', '-'] and revision.new_value in ['', '-']:
            empty_revisions.append(revision)
        elif revision.old_value == revision.new_value:
            if revision.field_name not in duplicate_revisions.keys():
                # this is the first time the duplicate occurs
                duplicate_revisions[revision.field_name] = []
            else:
                # we have already seen this duplicate, schedule to delete
                duplicate_revisions[revision.field_name].append(revision)
        else:
            if not tuple_updates:
                tuple_updates.append((revision.field_name, revision.old_value, revision.new_value))
            else:
                (last_field, last_old_value, last_new_value) = tuple_updates[-1]
                if last_field == revision.field_name and last_old_value == revision.old_value and last_new_value == revision.new_value:
                    tuple_update_already_seen.append(revision)
                else:
                    tuple_updates.append((revision.field_name, revision.old_value, revision.new_value))
    for empty_revision in empty_revisions:
        empty_revision.delete()

    for field_name, duplicates in duplicate_revisions.items():
        for duplicate in duplicates:
            duplicate.delete()

    for already_seen in tuple_update_already_seen:
        already_seen.delete()

    return JsonResponse({})
