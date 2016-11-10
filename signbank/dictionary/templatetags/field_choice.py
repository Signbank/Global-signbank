from django.template import Library
from signbank.dictionary.models import FieldChoice

def get_field_choice(machine_value,field_category):

    if machine_value in [None,'None']:
        return ""
    elif machine_value == '0':
        return '-'
    elif machine_value == '1':
        return 'N/A'

    choice_list = FieldChoice.objects.filter(field__iexact=field_category)
    return choice_list.filter(machine_value=machine_value)[0]

register = Library()

@register.filter
def translate_to_dutch(machine_value,field_category):
    selected_field_choice = get_field_choice(machine_value, field_category)

    try:
        return selected_field_choice.dutch_name
    except AttributeError:
        return selected_field_choice

@register.filter
def translate_to_chinese(machine_value,field_category):
    selected_field_choice = get_field_choice(machine_value, field_category)

    try:
        return selected_field_choice.chinese_name
    except AttributeError:
        return selected_field_choice
