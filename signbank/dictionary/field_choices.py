from signbank.dictionary.models import *
from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value, \
    choicelist_queryset_to_translated_dict, choicelist_queryset_to_machine_value_dict, choicelist_queryset_to_colors, \
    choicelist_queryset_to_field_colors

def get_static_choice_lists(fieldname):
    static_choice_lists = dict()
    static_choice_list_colors = dict()
    if fieldname in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
        choice_list = Handshape.objects.all()
    elif fieldname in ['semField']:
        choice_list = SemanticField.objects.all()
    elif fieldname in ['derivHist']:
        choice_list = DerivationHistory.objects.all()
    elif fieldname in [f.name for f in Gloss._meta.fields]:
        gloss_field = Gloss._meta.get_field(fieldname)
        if hasattr(gloss_field, 'field_choice_category'):
            choice_list = FieldChoice.objects.filter(field__iexact=gloss_field.field_choice_category)
        else:
            return (static_choice_lists, static_choice_list_colors)
    if len(choice_list) == 0:
        return (static_choice_lists, static_choice_list_colors)
    display_choice_list = choicelist_queryset_to_translated_dict(choice_list)
    display_choice_list_colors = choicelist_queryset_to_colors(choice_list)
    for (key, value) in display_choice_list.items():
        this_value = value
        static_choice_lists[key] = this_value

    for (key, value) in display_choice_list_colors.items():
        this_value = value
        static_choice_list_colors[key] = this_value

    return (static_choice_lists, static_choice_list_colors)
