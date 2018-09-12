from collections import OrderedDict
import signbank.settings.base as settings


def choicelist_queryset_to_translated_dict(queryset,language_code,ordered=True,id_prefix='_',shortlist=False):

    codes_to_adjectives = dict(settings.LANGUAGES)

    if language_code not in codes_to_adjectives.keys():
        adjective = 'english'
    else:
        adjective = codes_to_adjectives[language_code].lower()

    try:
        raw_choice_list = [(id_prefix+str(choice.machine_value),getattr(choice,adjective+'_name')) for choice in queryset]
    except AttributeError:
        raw_choice_list = [(id_prefix+str(choice.machine_value),getattr(choice,'english_name')) for choice in queryset]

    if shortlist:
        sorted_choice_list = sorted(raw_choice_list,key = lambda x: x[1])
    else:
        sorted_choice_list = [(id_prefix+'0','-'),(id_prefix+'1','N/A')]+sorted(raw_choice_list,key = lambda x: x[1])

    if ordered:
        return OrderedDict(sorted_choice_list)
    else:
        return sorted_choice_list


def machine_value_to_translated_human_value(machine_value,choice_list,language_code):

    codes_to_adjectives = dict(settings.LANGUAGES)

    if language_code not in codes_to_adjectives.keys():
        adjective = 'english'
    else:
        adjective = codes_to_adjectives[language_code].lower()

    if machine_value == '0':
        human_value = '-'
    elif machine_value == '1':
        human_value = 'N/A'
    else:

        try:
            selected_field_choice = choice_list.filter(machine_value=machine_value)[0]

            try:
                human_value = getattr(selected_field_choice, adjective + '_name')
            except AttributeError:
                human_value = getattr(selected_field_choice, 'english_name')

        except (IndexError, ValueError):
            human_value = machine_value

    return human_value

def choicelist_queryset_to_machine_value_dict(queryset,id_prefix='_',ordered=False):

    raw_choice_list = [(id_prefix+str(choice.machine_value),getattr(choice,'machine_value')) for choice in queryset]

    sorted_choice_list = [(id_prefix+'0',0),(id_prefix+'1',1)]+sorted(raw_choice_list,key = lambda x: x[1])

    if ordered:
        return OrderedDict(sorted_choice_list)
    else:
        return sorted_choice_list

