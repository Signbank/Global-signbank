from collections import OrderedDict


def choicelist_queryset_to_translated_dict(queryset, ordered=True, id_prefix='_',
                                           shortlist=False):
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
                                  shortlist=False):
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
    else:
        sorted_choices = list_head + raw_choice_list
    sorted_tuple_dict = []
    for (a, b, c) in sorted_choices:
        sorted_tuple_dict.append((a, c))
    sorted_choice_list = OrderedDict(sorted_tuple_dict)
    return sorted_choice_list


def choicelist_queryset_to_field_colors(queryset):
    temp_mapping_dict = {}
    temp_mapping_dict[0] = 'ffffff'
    for choice in queryset:
        field_color = getattr(choice, 'field_color')
        temp_mapping_dict[choice.machine_value] = field_color
    return temp_mapping_dict


def choicelist_choicelist_to_field_colors(choices):
    temp_mapping_dict = {}
    mapping_default = 'ffffff'
    for key in choices:
        temp_mapping_dict[key] = mapping_default
    return temp_mapping_dict


def machine_value_to_translated_human_value(machine_value, choice_list):

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


def choicelist_queryset_to_machine_value_dict(queryset, id_prefix='_', ordered=False):
    # When this method is called, the queryset is a set of either FieldChoice objects, all of which have the same field;
    # Or the queryset is a set of Handshape objects
    # Other functions that call this function expect either a list or an OrderedDict that maps machine values to machine values
    # Make sure the machine values are unique by only using the first human value

    raw_choice_list = [(id_prefix+str(choice.machine_value), choice.machine_value) for choice in queryset]

    sorted_choice_list = sorted(raw_choice_list, key=lambda x: x[1])

    if ordered:
        return OrderedDict(sorted_choice_list)
    else:
        return sorted_choice_list
