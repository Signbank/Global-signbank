from signbank.dictionary.models import *
from signbank.dictionary.translate_choice_list import choicelist_queryset_to_translated_dict, \
    choicelist_queryset_to_machine_value_dict, choicelist_queryset_to_colors, \
    choicelist_queryset_to_field_colors


def fields_to_categories():
    # this function returns a list of all the categories for fields with choices
    # it gets these based on settings
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

            if field in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
                continue
            if field in Gloss.get_field_names():
                field_field = Gloss.get_field(field)
            elif field in Handshape.get_field_names():
                field_field = Handshape.get_field(field)
            elif field in Morpheme.get_field_names():
                field_field = Morpheme.get_field(field)
            elif field in ExampleSentence.get_field_names():
                field_field = ExampleSentence.get_field(field)
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
        elif field in ['definitionRole']:
            # this is a search form field for Definition role
            choice_categories[field] = 'NoteType'
            continue
        elif field in ['mrpType']:
            # this is a search form field for Definition role
            choice_categories[field] = 'MorphemeType'
            continue
        elif field in ['hasComponentOfType']:
            choice_categories[field] = 'MorphologyType'
            continue
        elif field in ['hasRelation']:
            choice_categories[field] = 'Relation'
            continue
        if field in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
            continue
        if field in Gloss.get_field_names():
            field_field = Gloss.get_field(field)
        elif field in Handshape.get_field_names():
            field_field = Handshape.get_field(field)
        elif field in Morpheme.get_field_names():
            field_field = Morpheme.get_field(field)
        elif field in Definition.get_field_names():
            field_field = Definition.get_field(field)
        elif field in OtherMedia.get_field_names():
            field_field = OtherMedia.get_field(field)
        elif field in MorphologyDefinition.get_field_names():
            field_field = MorphologyDefinition.get_field(field)
        elif field in ExampleSentence.get_field_names():
            field_field = ExampleSentence.get_field(field)
        else:
            print('field_to_categories: field not found in Gloss, Handshape, Morpheme: ', field)
            continue
        if field in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
            choice_categories[field] = 'Handshape'
        elif hasattr(field_field, 'field_choice_category'):
            choice_categories[field] = field_field.field_choice_category
    return choice_categories


def get_static_choice_lists(fieldname):
    # this function constructs two dictionaries for a given field
    # if the field does not have choices, these are empty
    # they are constructed here to be consistent since the colors should match up with the choices
    # the queried models all have color fields
    # these are eventually used in the select2 pull-downs
    static_choice_lists = dict()
    static_choice_list_colors = dict()
    choice_list = []
    if fieldname in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
        choice_list = Handshape.objects.all()
    elif fieldname in ['semField']:
        choice_list = SemanticField.objects.all()
    elif fieldname in ['derivHist']:
        choice_list = DerivationHistory.objects.all()
    elif fieldname in Gloss.get_field_names():
        gloss_field = Gloss.get_field(fieldname)
        if hasattr(gloss_field, 'field_choice_category'):
            choice_list = FieldChoice.objects.filter(field__iexact=gloss_field.field_choice_category)
        else:
            # there are no choices for this field
            # it does not have a declared category or recognised choices model
            return static_choice_lists, static_choice_list_colors
    if len(choice_list) == 0 or choice_list.count() < 1:
        # there are no choices in the database for this field
        return static_choice_lists, static_choice_list_colors

    # there are choices for the fieldname parameter
    # these functions add the '_' prefix to the machine value key
    display_choice_list = choicelist_queryset_to_translated_dict(choice_list)
    display_choice_list_colors = choicelist_queryset_to_colors(choice_list)
    for (key, value) in display_choice_list.items():
        this_value = value
        static_choice_lists[key] = this_value

    for (key, value) in display_choice_list_colors.items():
        this_value = value
        static_choice_list_colors[key] = this_value

    return static_choice_lists, static_choice_list_colors


def get_frequencies_for_category(category, fields, selected_datasets):

    # get the field choices and the appropriate filter for querying the Gloss model (next step)
    if category in CATEGORY_MODELS_MAPPING.keys():
        field_choices = CATEGORY_MODELS_MAPPING[category].objects.all()
        # the Gloss field is a handshape object or a many-to-many relation
        field_filter = '__in'
    else:
        field_choices = FieldChoice.objects.filter(field__iexact=category)
        # the Gloss field is a FieldChoiceForeignKey
        field_filter = '__machine_value__in'

    choices = dict()

    # construct a dictionary that maps each choice to the frequency of that choice in the selected datasets
    # get the field choices as machine values
    # this list of tuples that is iterated over
    # maps machine values (with the '_' prefix) to machine values (that will be looked up)
    choice_list_machine_values = choicelist_queryset_to_machine_value_dict(field_choices)
    for field in fields:
        # normally fields is just a singleton
        # but for handshapes multiple fields have the same category, so this is a loop over the fields
        # the frequencies for all handshape fields for each choice are included
        for choice_list_field, machine_value in choice_list_machine_values:

            if machine_value == 0:
                # if the machine value is 0 or the field has not been set
                # check for the machine value 0 object or a null field value

                filter = field + '__machine_value'
                frequency_for_field = Gloss.objects.filter(Q(lemma__dataset__in=selected_datasets, archived=False),
                                                           Q(**{field + '__isnull': True}) |
                                                           Q(**{filter: 0})).count()

            else:
                # otherwise, count the number of matches to the machine value
                filter = field + field_filter
                filter_value = [machine_value]
                frequency_for_field = Gloss.objects.filter(lemma__dataset__in=selected_datasets, archived=False).filter(
                    **{filter: filter_value}).count()
            if choice_list_field not in choices.keys():
                choices[choice_list_field] = frequency_for_field
            else:
                # this is needed because multiple fields can have the same category
                choices[choice_list_field] += frequency_for_field
    # get the choices again
    choice_list = choicelist_queryset_to_translated_dict(field_choices)
    category_choices = []
    for machine_value_string, frequency in choices.items():
        # concatenate the frequency determined above to the 'name' of the choice
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

    # this function returns a "flipped" dictionary that maps categories to a list of fields with that category
    category_to_fields_dict = dict()
    field_categories_dict = fields_to_fieldcategory_dict()

    for (fieldname, category) in field_categories_dict.items():
        if category not in category_to_fields_dict.keys():
            category_to_fields_dict[category] = []
        category_to_fields_dict[category].append(fieldname)

    return category_to_fields_dict
