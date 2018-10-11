from django.template import Library
from signbank.dictionary.models import FieldChoice, Dataset

def get_field_choice(machine_value,field_category):

    if machine_value in [None,'None']:
        return ""
    elif machine_value == '0':
        return '-'
    elif machine_value == '1':
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

@register.filter
def translate_to_english(machine_value,field_category):
    selected_field_choice = get_field_choice(machine_value, field_category)

    try:
        return selected_field_choice.english_name
    except AttributeError:
        return selected_field_choice

@register.filter
def machine_field_translate(field_value, args):
    # args = field_category language_code
    arg_list = args.split(" ")
    field_category = arg_list[0]
    language_code = arg_list[1]
    if language_code == 'nl':
        translation_function = translate_to_dutch(field_value,field_category)
    elif language_code == 'zh-hans':
        translation_function = translate_to_chinese(field_value,field_category)
    else:
        translation_function = translate_to_english(field_value,field_category)
    return translation_function

@register.filter
def translated_frequency_list(dataset, language_code):
    generated_dict = dataset.generate_frequency_dict(language_code)
    return generated_dict
