from django.db.models import Q, BooleanField
from django.db.models.fields import TextField, CharField
from django.utils.translation import gettext, gettext_lazy as _

from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse

from signbank.settings.server_specific import HANDEDNESS_ARTICULATION_FIELDS, MODELTRANSLATION_LANGUAGES

from signbank.dictionary.models import Gloss, GlossRevision, Language, FieldChoice, Handshape, FieldChoiceForeignKey
from signbank.dictionary.update import okay_to_update_gloss
from signbank.csv_interface import normalize_field_choice


def check_value_to_translated_human_value(field_name, check_value):
    # check_value has type CharField
    # translates to a human value dynamically
    # used to translate the values stored in GlossRevision when booleans
    # the Gloss model needs to be imported here, at runtime
    gloss_fields = Gloss.get_field_names()
    if field_name not in gloss_fields or Gloss.get_field(field_name).__class__.__name__ != 'BooleanField':
        # don't do anything to value
        return check_value

    # the value is a Boolean or it might not be set
    # if it's weakdrop or weakprop, it has a value Neutral when it's not set
    # look for aliases for empty to account for legacy data
    if field_name not in HANDEDNESS_ARTICULATION_FIELDS:
        # This accounts for legacy values stored in the revision history
        if check_value == '' or check_value in ['False', 'None', 'No', 'Nee', '&nbsp;']:
            translated_value = _('No')
            return translated_value
        elif check_value in ['True', 'Yes', 'Ja', '1', 'letter', 'number']:
            translated_value = _('Yes')
            return translated_value
        else:
            return check_value
    else:
        # field is in HANDEDNESS_ARTICULATION_FIELDS
        # use the abbreviation that appears in the template
        value_abbreviation = 'WD' if field_name == 'weakdrop' else 'WP'
        if check_value in ['True', '+WD', '+WP', '1']:
            translated_value = '+' + value_abbreviation
        elif check_value in ['None', '', 'Neutral', 'notset']:
            translated_value = _('Neutral')
        else:
            # here, the value is False
            translated_value = '-' + value_abbreviation
        return translated_value


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
    for interface_language_code in MODELTRANSLATION_LANGUAGES:
        name_languagecode = 'name_' + interface_language_code.replace('-', '_')
        if name_languagecode not in language_codes:
            language_codes.append(name_languagecode)
    simple_translation_dict = {
        'sequential_morphology': gettext("Sequential Morphology"),
        'simultaneous_morphology': gettext("Simultaneous Morphology"),
        'gloss_video': gettext("Upload Primary Video"),
        'gloss_video_restore': gettext("Restore Backup Video"),
        'gloss_perspectivevideo_left': gettext("Upload Perspective Video (left)"),
        'gloss_perspectivevideo_right': gettext("Upload Perspective Video (right)"),
        'blend_morphology': gettext("Blend Morphology"),
        'archived': gettext("Deleted"),
        'restored': gettext("Restored"),
        'definitiondelete': gettext("Note"),
        'definitioncount': gettext("Note Index"),
        'definitionpub': gettext("Note Published"),
        'definition': gettext("Note Text"),
        'definition_create': gettext("Note"),
        'definitionrole': gettext("Note Type"),
        'provenance_create': gettext("Provenance"),
        'provenancedelete': gettext("Provenance"),
        'provenancedescription': gettext("Provenance Description"),
        'provenancemethod': gettext("Provenance Method")
    }
    revisions = []
    for revision in GlossRevision.objects.filter(gloss=gloss):
        if revision.field_name.startswith('sense_'):
            prefix, order, language_2char = revision.field_name.split('_')
            language = Language.objects.get(language_code_2char=language_2char)
            revision_verbose_fieldname = gettext('Sense') + ' ' + order + " (%s)" % language.name
        elif revision.field_name.startswith('Sense'):
            revision_verbose_fieldname = gettext('Sense')
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
        elif revision.field_name.startswith('gloss_nmevideo_'):
            try:
                prefix, operation, offset, perspective = revision.field_name.split('_')
            except ValueError:
                prefix, operation, offset, perspective = 'gloss', 'nmevideo', '0', ''
            if perspective == 'left':
                video_perspective = " ({left})".format(left=gettext("left"))
            elif perspective == 'right':
                video_perspective = " ({right})".format(right=gettext("right"))
            else:
                video_perspective = ""
            revision_verbose_fieldname = "{operation} {offset}{perspective}".format(operation=gettext("Upload NME Video"), offset=offset, perspective=video_perspective)
        elif revision.field_name in Gloss.get_field_names():
            revision_verbose_fieldname = gettext(Gloss.get_field(revision.field_name).verbose_name)
        elif revision.field_name in simple_translation_dict.keys():
            revision_verbose_fieldname = simple_translation_dict[revision.field_name]
        elif revision.field_name.startswith('lemma'):
            language_2char = revision.field_name[-2:]
            language = Language.objects.get(language_code_2char=language_2char)
            revision_verbose_fieldname = gettext('Lemma ID Gloss') + " (%s)" % language.name
        elif revision.field_name.startswith('annotation'):
            language_2char = revision.field_name[-2:]
            language = Language.objects.get(language_code_2char=language_2char)
            revision_verbose_fieldname = gettext('Annotation ID Gloss') + " (%s)" % language.name
        else:
            # some legacy data may fall through
            revision_verbose_fieldname = gettext(revision.field_name)
            # print('fall through: ', revision.field_name, revision_verbose_fieldname)

        # field name qualification is stored separately here
        # Django was having a bit of trouble translating it when embedded in the field_name string below
        if revision.field_name == 'Tags':
            if revision.old_value:
                # this translation exists in the interface of Gloss Edit View
                delete_command = gettext('Delete this tag')
                field_name_qualification = ' (' + delete_command + ')'
            elif revision.new_value:
                # this translation exists in the interface of Gloss Edit View
                add_command = gettext('Add Tag')
                field_name_qualification = ' (' + add_command + ')'
            else:
                # this shouldn't happen
                field_name_qualification = ''
        elif revision.field_name in ['Sense', 'Senses', 'senses',
                                     'Sentence',
                                     'sequential_morphology', 'simultaneous_morphology', 'blend_morphology',
                                     'definition', 'definitiondelete', 'definition_create', 'definitioncount', 'definitionpub', 'definitionrole',
                                     'provenance_create', 'provenancedelete', 'provenancedescription', 'provenancemethod']:
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
            elif isinstance(field, TextField) or isinstance(field, CharField):
                display_old_value = revision.old_value.replace('\n', '\\n')
                display_new_value = revision.new_value.replace('\n', '\\n')
            else:
                display_old_value = check_value_to_translated_human_value(revision.field_name, revision.old_value)
                display_new_value = check_value_to_translated_human_value(revision.field_name, revision.new_value)
        elif revision.field_name in ['definitionpub']:
            display_old_value = _("Yes") if revision.old_value == 'True' else _("No")
            display_new_value = _("Yes") if revision.new_value == 'True' else _("No")
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
            'new_value': display_new_value}
        revisions.append(revision_dict)

    return revisions


def identical_booleans(field_name, value1, value2):

    # these are internal and display representations of the 3-valued Booleans, including possible legacy storage
    NEUTRAL_VALUES = ['None', '', 'Neutral', '&nbsp;']
    PLUS_VALUES = ['True', '+WD', '+WP', '1', 'ja', 'Ja', '是']
    MINUS_VALUES = ['False', '-WD', '-WP', '0', 'No', 'Nee', '否']

    # these are internal and display representations of the traditional Boolean values, not the 3-valued ones
    TRUE_VALUES = ['True', 'true', 'Yes', 'yes', 'ja', 'Ja', '是', 'letter', 'number']
    FALSE_VALUES = ['False', 'false', 'No', 'no', 'Nee', 'nee', '否', 'None', '&nbsp;', '']
    if field_name in HANDEDNESS_ARTICULATION_FIELDS:
        if value1 in NEUTRAL_VALUES and value2 in NEUTRAL_VALUES:
            return True
        if value1 in PLUS_VALUES and value2 in PLUS_VALUES:
            return True
        if value1 in MINUS_VALUES and value2 in MINUS_VALUES:
            return True
        return False

    if value1 in TRUE_VALUES and value2 in TRUE_VALUES:
        return True
    if value1 in FALSE_VALUES and value2 in FALSE_VALUES:
        return True
    return False


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
        if revision.field_name in Gloss.get_field_names():
            field = Gloss.get_field(revision.field_name)
            if isinstance(field, BooleanField):
                if identical_booleans(revision.field_name, revision.old_value, revision.new_value):
                    empty_revisions.append(revision)
                    continue
                else:
                    continue
            elif isinstance(field, FieldChoiceForeignKey):
                if revision.old_value == revision.new_value:
                    empty_revisions.append(revision)
                    continue
        if revision.old_value in ['', '-'] and revision.new_value in ['', '-']:
            empty_revisions.append(revision)
            continue
        if revision.old_value == revision.new_value:
            if revision.field_name not in duplicate_revisions.keys():
                # this is the first time the duplicate occurs
                duplicate_revisions[revision.field_name] = []
            else:
                # we have already seen this duplicate, schedule to delete
                duplicate_revisions[revision.field_name].append(revision)
            continue
        if not tuple_updates:
            tuple_updates.append((revision.field_name, revision.old_value, revision.new_value))
            continue
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
