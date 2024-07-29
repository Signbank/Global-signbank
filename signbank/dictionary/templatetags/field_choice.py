from django.template import Library
from signbank.dictionary.models import FieldChoice, Dataset
from django.utils.translation import gettext


def get_field_choice(machine_value,field_category):

    if machine_value == '' or machine_value in [None,'None']:
        return '-'
    elif machine_value == '0' or machine_value == 0:
        return '-'
    elif machine_value == '1' or machine_value == 1:
        return 'N/A'

    choice_list = FieldChoice.objects.filter(field__iexact=field_category).filter(machine_value=machine_value)
    if len(choice_list) > 0:
        return choice_list[0]
    else:
        return '-'


register = Library()


@register.filter
def normalise_empty(machine_value):
    if machine_value in [None,'None']:
        return None
    elif machine_value == '0' or machine_value == 0:
        return None
    else:
        return machine_value


@register.filter
def translated_frequency_list(dataset):
    generated_dict = dataset.generate_frequency_dict()
    return generated_dict


@register.filter
def get_gloss_field(gloss, field):
    field_value = getattr(gloss, field)
    if field in ['repeat', 'altern']:
        if not field_value:
            return gettext("No")
        else:
            return gettext("Yes")
    elif field_value:
        return field_value.name
    else:
        return '-'
