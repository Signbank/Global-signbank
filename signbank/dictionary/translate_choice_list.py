from collections import OrderedDict
# from signbank.dictionary.models import Gloss, GlossRevision, Morpheme, Handshape
import signbank.settings.base as settings
from django.utils.translation import ugettext_lazy as _
from django.db.models import When, Case, NullBooleanField, IntegerField

def choicelist_queryset_to_translated_dict(queryset,language_code,ordered=True,id_prefix='_',shortlist=False,choices_to_exclude=None):

    # When this method is called, the queryset is a set of either FieldChoice objects, all of which have the same field;
    # Or the queryset is a set of Handshape objects
    # Other functions that call this function expect either a list or an OrderedDict that maps machine values to human values
    # Make sure the machine values are unique by only using the first human value

    codes_to_adjectives = dict(settings.LANGUAGES)

    if language_code not in codes_to_adjectives.keys():
        adjective = settings.FALLBACK_FIELDCHOICE_HUMAN_LANGUAGE
    else:
        adjective = codes_to_adjectives[language_code].lower()

    temp_mapping_dict = {}
    raw_choice_list = []
    machine_values_seen = []
    for choice in queryset:
        try:
            human_value = getattr(choice, adjective + '_name')
        except AttributeError:
            human_value = getattr(choice,'english_name')

        if choice.machine_value in machine_values_seen:
            # don't append to raw_choice_list
            continue
        temp_mapping_dict[choice.machine_value] = human_value
        if choices_to_exclude == None or choice not in choices_to_exclude:
            machine_values_seen.append(choice.machine_value)
            raw_choice_list.append((id_prefix + str(choice.machine_value), human_value))

    if ordered:

        if shortlist:
            sorted_choice_list = OrderedDict(sorted(raw_choice_list,key = lambda x: x[1]))
        else:
            sorted_choice_list = OrderedDict(sorted(raw_choice_list,key = lambda x: x[1]))
            sorted_choice_list.update({id_prefix+'1':'N/A'})
            sorted_choice_list.move_to_end(id_prefix+'1', last=False)
            sorted_choice_list.update({id_prefix+'0':'-'})
            sorted_choice_list.move_to_end(id_prefix+'0', last=False)
        return sorted_choice_list
    else:

        if shortlist:
            sorted_choice_list = sorted(raw_choice_list, key=lambda x: x[1])
        else:
            sorted_choice_list = [(id_prefix + '0', '-'), (id_prefix + '1', 'N/A')] + sorted(raw_choice_list,
                                                                                             key=lambda x: x[1])
        return sorted_choice_list

def choicelist_queryset_to_colors(queryset,language_code,ordered=True,id_prefix='_',shortlist=False,choices_to_exclude=None):

    # When this method is called, the queryset is a set of either FieldChoice objects, all of which have the same field;
    # Or the queryset is a set of Handshape objects
    # Other functions that call this function expect either a list or an OrderedDict that maps machine values to human values
    # Make sure the machine values are unique by only using the first human value

    codes_to_adjectives = dict(settings.LANGUAGES)

    if language_code not in codes_to_adjectives.keys():
        adjective = settings.FALLBACK_FIELDCHOICE_HUMAN_LANGUAGE
    else:
        adjective = codes_to_adjectives[language_code].lower()

    temp_mapping_dict = {}
    raw_choice_list = []
    machine_values_seen = []
    for choice in queryset:
        human_value = getattr(choice, adjective + '_name')
        if choice.machine_value in machine_values_seen:
            # don't append to raw_choice_list
            continue
        temp_mapping_dict[choice.machine_value] = human_value
        if choices_to_exclude == None or choice not in choices_to_exclude:
            machine_values_seen.append(choice.machine_value)
            raw_choice_list.append((id_prefix + str(choice.machine_value), getattr(choice, adjective + '_name'), getattr(choice, 'field_color')))

    if ordered:
        sorted_choices = sorted(raw_choice_list,key = lambda x: x[1])
        sorted_choice_list = []

        if not shortlist:
            sorted_choice_list = [ (id_prefix+'0', '-', 'ffffff'), (id_prefix+'1', 'N/A', 'ffffff')] + sorted_choices

        sorted_tuple_dict = []
        for (a, b, c) in sorted_choice_list:
            sorted_tuple_dict.append((a, c))
        sorted_choice_dict = OrderedDict(sorted_tuple_dict)

        return sorted_choice_dict
    # else:
    #
    #     if shortlist:
    #         sorted_choice_list = sorted(raw_choice_list, key=lambda x: x[1])
    #     else:
    #         sorted_choice_list = [(id_prefix + '0', 'ffffff'), (id_prefix + '1', 'ffffff')] + sorted(raw_choice_list,
    #                                                                                          key=lambda x: x[1])
    #     return sorted_choice_list

    return OrderedDict([])

def choicelist_queryset_to_field_colors(queryset):

    temp_mapping_dict = {}
    temp_mapping_dict[0] = 'ffffff'
    for choice in queryset:
        temp_mapping_dict[choice.machine_value] = getattr(choice, 'field_color')
    return temp_mapping_dict

def machine_value_to_translated_human_value(machine_value,choice_list,language_code):

    codes_to_adjectives = dict(settings.LANGUAGES)

    if language_code not in codes_to_adjectives.keys():
        adjective = settings.FALLBACK_FIELDCHOICE_HUMAN_LANGUAGE
    else:
        adjective = codes_to_adjectives[language_code].lower()

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

            try:
                human_value = getattr(selected_field_choice, adjective + '_name')
            except AttributeError:
                human_value = getattr(selected_field_choice, 'english_name')

        except (IndexError, ValueError):
            human_value = machine_value

    return human_value

def fieldname_to_translated_human_value(field_name):
    # translates the field name dynamically
    # used to translate the field names stored in GlossRevision
    # the Gloss model needs to be imported here, at runtime
    from signbank.dictionary.models import Gloss
    gloss_fields = [ field.name for field in Gloss._meta.get_fields() ]
    if field_name in gloss_fields:
        # commented out version shows field name of model, if available
        # verbose_name = _(Gloss._meta.get_field(field_name).verbose_name) + " (" + field_name + ")"
        verbose_name = _(Gloss._meta.get_field(field_name).verbose_name)
    else:
        verbose_name = _(field_name)
    return verbose_name

def check_value_to_translated_human_value(field_name, check_value):
    # check_value has type CharField
    # translates to a human value dynamically
    # used to translate the values stored in GlossRevision when booleans
    # the Gloss model needs to be imported here, at runtime
    from signbank.dictionary.models import Gloss
    gloss_fields = [ field.name for field in Gloss._meta.get_fields() ]
    if field_name not in gloss_fields or Gloss._meta.get_field(field_name).__class__.__name__ != 'NullBooleanField':
        # don't do anything to value
        return check_value

    # the value is a Boolean or it might not be set
    # if it's weakdrop or weakprop, it has a value Neutral when it's not set
    # look for aliases for empty to account for legacy data
    if field_name in settings.HANDEDNESS_ARTICULATION_FIELDS:
        # use the abbreviation that appears in the template
        value_abbreviation = 'WD' if field_name == 'weakdrop' else 'WP'
        if check_value in ['True', '+WD', '+WP', '1']:
            translated_value = '+' + value_abbreviation
        elif check_value in ['None', '', 'Neutral', 'notset']:
            translated_value = _('Neutral')
        else:
            # here, the value is False
            translated_value = '-' + value_abbreviation
    elif check_value in ['True', '1', 'letter', 'number']:
        translated_value = _('Yes')
    else:
        # this is the default
        # if previously a None value has been converted to string 'None' it ends up here
        translated_value = _('No')
    return translated_value

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

    raw_choice_list = [(id_prefix+str(choice.machine_value),getattr(choice,'machine_value')) for choice in queryset_no_dupes]

    sorted_choice_list = [(id_prefix+'0',0),(id_prefix+'1',1)]+sorted(raw_choice_list,key = lambda x: x[1])

    if ordered:
        return OrderedDict(sorted_choice_list)
    else:
        return sorted_choice_list

