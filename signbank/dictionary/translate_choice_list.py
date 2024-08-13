from collections import OrderedDict
# from signbank.dictionary.models import Gloss, GlossRevision, Morpheme, Handshape
import signbank.settings.base as settings
from django.utils.translation import gettext_lazy as _
from django.db.models import When, Case, BooleanField, IntegerField
from django.db.utils import OperationalError
from django.utils.translation import gettext


def choicelist_queryset_to_translated_dict(queryset,ordered=True, id_prefix='_',
                                           shortlist=False, choices_to_exclude=None):
    # When this method is called, the queryset is a set of either FieldChoice objects, all of which have the same field;
    # Or the queryset is a set of Handshape objects
    # Other functions that call this function expect either a list or an OrderedDict
    # that maps machine values to human values
    # Make sure the machine values are unique by only using the first human value

    if not queryset:
        return []

    list_head_values = ['-', 'N/A']

    raw_choice_list = []
    machine_values_seen = []
    empty_or_NA = {}
    for choice in queryset:
        if choice.machine_value in machine_values_seen:
            # don't append to raw_choice_list
            continue

        human_value = choice.name
        if human_value in list_head_values:
            empty_or_NA[human_value] = choice
            continue

        if not choices_to_exclude or choice not in choices_to_exclude:
            machine_values_seen.append(choice.machine_value)
            raw_choice_list.append((id_prefix + str(choice.machine_value), choice.name))

    list_head = [] if shortlist else [(id_prefix + str(empty_or_NA[v].machine_value), v) for v in list_head_values]

    if ordered:
        sorted_choice_list = OrderedDict(list_head)
        sorted_choice_list.update(OrderedDict(sorted(raw_choice_list, key=lambda x: x[1])))
        return sorted_choice_list
    else:
        sorted_choice_list = list_head + sorted(raw_choice_list, key=lambda x: x[1])
        return sorted_choice_list


def choicelist_queryset_to_colors(queryset, ordered=True, id_prefix='_',
                                  shortlist=False, choices_to_exclude=None):
    # When this method is called, the queryset is a set of either FieldChoice objects, all of which have the same field;
    # Or the queryset is a set of Handshape objects
    # Other functions that call this function expect either a list or an OrderedDict
    # that maps machine values to human values
    # Make sure the machine values are unique by only using the first human value

    if not queryset:
        return []

    list_head_values = ['-', 'N/A']

    raw_choice_list = []
    machine_values_seen = []
    empty_or_NA = {}
    for choice in queryset:
        if choice.machine_value in machine_values_seen:
            # don't append to raw_choice_list
            continue

        human_value = choice.name
        if human_value in list_head_values:
            empty_or_NA[human_value] = choice
            continue

        if choices_to_exclude is None or choice not in choices_to_exclude:
            machine_values_seen.append(choice.machine_value)
            field_color = getattr(choice, 'field_color')
            # this should not happen, but it could be a legacy value that has a #
            if field_color[0] == '#':
                field_color = field_color[1:]
            raw_choice_list.append((id_prefix + str(choice.machine_value), human_value, field_color))

    list_head = [] if shortlist else [(id_prefix + str(empty_or_NA[v].machine_value), v, 'ffffff') for v in list_head_values]

    if ordered:
        # sort by human value
        sorted_choices = list_head + sorted(raw_choice_list, key=lambda x: x[1])
        sorted_tuple_dict = []
        for (a, b, c) in sorted_choices:
            sorted_tuple_dict.append((a, c))
        sorted_choice_list = OrderedDict(sorted_tuple_dict)
        return sorted_choice_list


def choicelist_queryset_to_field_colors(queryset):
    temp_mapping_dict = {}
    temp_mapping_dict[0] = 'ffffff'
    for choice in queryset:
        temp_mapping_dict[choice.machine_value] = getattr(choice, 'field_color')
    return temp_mapping_dict


def choicelist_choicelist_to_field_colors(choices):
    temp_mapping_dict = {}
    mapping_default = 'ffffff'
    for key in choices:
        temp_mapping_dict[key] = mapping_default
    return temp_mapping_dict

def machine_value_to_translated_human_value(machine_value,choice_list):

    if not choice_list or len(choice_list) == 0:
        # this function has been called with an inappropriate choice_list
        return machine_value

    if machine_value is None or type(machine_value) == bool:
        return machine_value

    if machine_value == '':
        return machine_value

    if machine_value == '0':
        human_value = '-'
    elif machine_value == '1':
        human_value = 'N/A'
    else:

        try:
            selected_field_choice = choice_list.filter(machine_value=machine_value)[0]
            human_value = selected_field_choice.name

        except (IndexError, ValueError):
            human_value = machine_value

    return human_value


def check_value_to_translated_human_value(field_name, check_value):
    # check_value has type CharField
    # translates to a human value dynamically
    # used to translate the values stored in GlossRevision when booleans
    # the Gloss model needs to be imported here, at runtime
    from signbank.dictionary.models import Gloss
    gloss_fields = Gloss.get_field_names()
    if field_name not in gloss_fields or Gloss.get_field(field_name).__class__.__name__ != 'BooleanField':
        # don't do anything to value
        return check_value

    # the value is a Boolean or it might not be set
    # if it's weakdrop or weakprop, it has a value Neutral when it's not set
    # look for aliases for empty to account for legacy data
    if field_name not in settings.HANDEDNESS_ARTICULATION_FIELDS:
        # This accounts for legacy values stored in the revision history
        if check_value == '' or check_value in ['False', 'No', 'Nee', '&nbsp;']:
            translated_value = _('No')
            return translated_value
        elif check_value in ['True', 'Yes', 'Ja', '1', 'letter', 'number']:
            translated_value = _('Yes')
            return translated_value
        else:
            return check_value
    else:
        # field is in settings.HANDEDNESS_ARTICULATION_FIELDS
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

def choicelist_queryset_to_machine_value_dict(queryset,id_prefix='_',ordered=False):
    # When this method is called, the queryset is a set of either FieldChoice objects, all of which have the same field;
    # Or the queryset is a set of Handshape objects
    # Other functions that call this function expect either a list or an OrderedDict that maps machine values to machine values
    # Make sure the machine values are unique by only using the first human value

    raw_choice_list = [(id_prefix+str(choice.machine_value),choice.machine_value) for choice in queryset]

    sorted_choice_list = sorted(raw_choice_list,key = lambda x: x[1])

    if ordered:
        return OrderedDict(sorted_choice_list)
    else:
        return sorted_choice_list

