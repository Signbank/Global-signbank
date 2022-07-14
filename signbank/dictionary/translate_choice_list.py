from collections import OrderedDict
import signbank.settings.base as settings


def choicelist_queryset_to_translated_dict(queryset,language_code,ordered=True,id_prefix='_',shortlist=False,choices_to_exclude=None):
    # When this method is called, the queryset is a set of either FieldChoice objects, all of which have the same field;
    # Or the queryset is a set of Handshape objects
    # Other functions that call this function expect either a list or an OrderedDict that maps machine values to human values
    # Make sure the machine values are unique by only using the first human value

    list_head_values = ['-', 'N/A']

    temp_mapping_dict = {}
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

        temp_mapping_dict[choice.machine_value] = human_value
        if choices_to_exclude == None or choice not in choices_to_exclude:
            machine_values_seen.append(choice.machine_value)
            raw_choice_list.append((id_prefix + str(choice.pk), choice.name))

    if 'NoteType' in str(queryset.query):
        print(raw_choice_list)

    list_head = [] if shortlist else [(id_prefix + str(empty_or_NA[v].pk), v) for v in list_head_values]

    if ordered:
        sorted_choice_list = OrderedDict(list_head)
        sorted_choice_list.update(OrderedDict(sorted(raw_choice_list,key = lambda x: x[1])))
        return sorted_choice_list
    else:
        sorted_choice_list = list_head + sorted(raw_choice_list, key=lambda x: x[1])
        return sorted_choice_list


def machine_value_to_translated_human_value(machine_value,choice_list,language_code):

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

def choicelist_queryset_to_machine_value_dict(queryset,id_prefix='_',ordered=False):
    # When this method is called, the queryset is a set of either FieldChoice objects, all of which have the same field;
    # Or the queryset is a set of Handshape objects
    # Other functions that call this function expect either a list or an OrderedDict that maps machine values to machine values
    # Make sure the machine values are unique by only using the first human value

    queryset_no_dupes = []
    machine_values_seen = []
    for choice in queryset:
        if choice.machine_value in machine_values_seen:
            # print('Duplicate machine value for FieldChoice ', choice.field, ' (', choice.machine_value, ')')
            # don't append to queryset_no_dupes
            continue
        machine_values_seen.append(choice.machine_value)
        queryset_no_dupes.append(choice)

    raw_choice_list = [(id_prefix+str(choice.pk),choice.pk) for choice in queryset_no_dupes]

    sorted_choice_list = [(id_prefix+'0',0),(id_prefix+'1',1)]+sorted(raw_choice_list,key = lambda x: x[1])

    if ordered:
        return OrderedDict(sorted_choice_list)
    else:
        return sorted_choice_list

