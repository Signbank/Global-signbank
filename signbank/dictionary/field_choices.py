from signbank.dictionary.models import *
from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value, \
    choicelist_queryset_to_translated_dict, choicelist_queryset_to_machine_value_dict, choicelist_queryset_to_colors, \
    choicelist_queryset_to_field_colors


def fields_to_categories():
    choice_categories = []
    for topic in ['main', 'phonology', 'semantics']:
        for field in FIELDS[topic]:
            if field == 'semField':
                # capitalize it
                if 'SemField' not in choice_categories:
                    choice_categories.append('SemField')
                continue
            elif field in ['derivHist']:
                if field not in choice_categories:
                    choice_categories.append(field)
                continue
            # the following check will be used when querying is added, at the moment these don't appear in the phonology list
            if field in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
                continue
            if field in [f.name for f in Gloss._meta.fields]:
                field_field = Gloss._meta.get_field(field)
            elif field in [f.name for f in Handshape._meta.fields]:
                field_field = Handshape._meta.get_field(field)
            elif field in [f.name for f in Morpheme._meta.fields]:
                field_field = Morpheme._meta.get_field(field)
            else:
                print('field_to_categories: field not found in Gloss, Handshape, Morpheme: ', field)
                continue
            if field in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
                if 'Handshape' not in choice_categories:
                    choice_categories.append('Handshape')
            elif hasattr(field_field, 'field_choice_category'):
                if field_field.field_choice_category not in choice_categories:
                    choice_categories.append(field_field.field_choice_category)
    return choice_categories


def fields_to_fieldcategory_dict(fieldnames=[]):
    # allows an optional fields parameter for cases where FieldChoiceForeignKey fields from other classes are needed
    # Normally only Gloss fields are needed
    # use parameter fieldnames as read-only
    if not fieldnames:
        fields = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics']
    else:
        fields = fieldnames
    choice_categories = {}
    for field in fields:
        if field == 'semField':
            choice_categories[field] = 'SemField'
            continue
        elif field in ['derivHist']:
            choice_categories[field] = 'derivHist'
            continue
        # the following check will be used when querying is added, at the moment these don't appear in the phonology list
        if field in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
            continue
        if field in [f.name for f in Gloss._meta.fields]:
            field_field = Gloss._meta.get_field(field)
        elif field in [f.name for f in Handshape._meta.fields]:
            field_field = Handshape._meta.get_field(field)
        elif field in [f.name for f in Morpheme._meta.fields]:
            field_field = Morpheme._meta.get_field(field)
        elif field in [f.name for f in Definition._meta.fields]:
            field_field = Definition._meta.get_field(field)
        elif field in [f.name for f in OtherMedia._meta.fields]:
            field_field = OtherMedia._meta.get_field(field)
        elif field in [f.name for f in MorphologyDefinition._meta.fields]:
            field_field = MorphologyDefinition._meta.get_field(field)
        else:
            print('field_to_categories: field not found in Gloss, Handshape, Morpheme: ', field)
            continue
        if field in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
            choice_categories[field] = 'Handshape'
        elif hasattr(field_field, 'field_choice_category'):
            choice_categories[field] = field_field.field_choice_category
    return choice_categories


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

def get_frequencies_for_category(category, fields, selected_datasets):

    if category in CATEGORY_MODELS_MAPPING.keys():
        field_choices = CATEGORY_MODELS_MAPPING[category].objects.all()
        field_filter = '__in'
    else:
        field_choices = FieldChoice.objects.filter(field__iexact=category)
        field_filter = '__machine_value__in'

    choices = dict()

    choice_list_machine_values = choicelist_queryset_to_machine_value_dict(field_choices)
    for field in fields:
        for choice_list_field, machine_value in choice_list_machine_values:
            if machine_value == 0:
                filter = field + '__machine_value'
                frequency_for_field = Gloss.objects.filter(Q(lemma__dataset__in=selected_datasets),
                                                           Q(**{field + '__isnull': True}) |
                                                           Q(**{filter: 0})).count()

            else:
                filter = field + field_filter
                filter_value = [machine_value]
                frequency_for_field = Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(
                    **{filter: filter_value}).count()
            if choice_list_field not in choices.keys():
                choices[choice_list_field] = frequency_for_field
            else:
                # this is needed because multiple fields can have the same category
                choices[choice_list_field] += frequency_for_field
    choice_list = choicelist_queryset_to_translated_dict(field_choices)
    category_choices = []
    for machine_value_string, frequency in choices.items():
        mvid, mvv = machine_value_string.split('_')
        machine_value = int(mvv)
        choice_object = field_choices.get(machine_value=machine_value)
        choice_name = choice_list[machine_value_string]
        display_with_frequency = choice_name + ' [' + str(frequency) + ']'
        category_choices.append((choice_object, display_with_frequency))
    # the first two choices need to be put at the front
    choice_machine_value_0 = category_choices[0]
    choice_machine_value_1 = category_choices[1]
    # the other choices will be sorted on the name
    otherchoices = category_choices[2:]
    category_choices = [choice_machine_value_0, choice_machine_value_1] + sorted(otherchoices,key=lambda x:x[1])
    return category_choices


def category_to_fields():

    category_to_fields_dict = dict()
    field_categories_dict = fields_to_fieldcategory_dict()

    for (fieldname, category) in field_categories_dict.items():
        if category not in category_to_fields_dict.keys():
            category_to_fields_dict[category] = []
        category_to_fields_dict[category].append(fieldname)

    return category_to_fields_dict
