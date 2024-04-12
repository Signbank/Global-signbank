import json

from django.utils.translation import activate
from signbank.dictionary.models import *
from signbank.api_interface import api_fields
from django.db.transaction import atomic
from django.utils.timezone import get_current_timezone


def update_gloss_columns_to_value_dict_keys(language_code):
    value_dict = dict()
    value_dict_reverse = dict()

    activate(language_code)
    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
    gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

    for field in gloss_fields:
        value_dict[field.name] = field.verbose_name.title()
        value_dict_reverse[field.verbose_name.title()] = field

    return value_dict, value_dict_reverse


def get_gloss_update_human_readable_value_dict(request):
    value_dict = dict()
    for field in request.POST.keys():
        value = request.POST.get(field, '')
        value_dict[field] = value.strip()
    return value_dict


def update_semantic_field(gloss, new_values, language_code):
    errors = []
    new_semanticfields_to_save = []

    activate(language_code)
    semanticfield_choices = {}
    for sf in SemanticField.objects.all():
        semanticfield_choices[sf.name] = sf

    for value in new_values:
        if value in semanticfield_choices.keys():
            new_semanticfields_to_save.append(semanticfield_choices[value])
        else:
            errors.append('Semantic field not found: '+value)

    if errors:
        return errors

    gloss.semField.clear()
    for sf in new_semanticfields_to_save:
        gloss.semField.add(sf)
    gloss.save()

    return errors


def update_derivation_history_field(gloss, new_values, language_code):
    errors = []
    new_derivationhistory_to_save = []

    activate(language_code)
    derivationhistory_choices = {}
    for dh in DerivationHistory.objects.all():
        derivationhistory_choices[dh.name] = dh

    for value in new_values:
        if value in derivationhistory_choices.keys():
            new_derivationhistory_to_save.append(derivationhistory_choices[value])
        else:
            errors.append('Derivation history field not found: '+value)

    if errors:
        return errors

    gloss.derivHist.clear()
    for dh in new_derivationhistory_to_save:
        gloss.derivHist.add(dh)
    gloss.save()

    return errors


def gloss_update_do_changes(request, gloss, changes, language_code):

    changes_done = []
    errors = []
    activate(language_code)
    with atomic():
        for field, (original_value, new_value) in changes.items():
            if isinstance(field, FieldChoiceForeignKey):
                field_choice_category = field.field_choice_category
                try:
                    fieldchoice = FieldChoice.objects.get(field=field_choice_category, name=new_value)
                except ObjectDoesNotExist:
                    print(field_choice_category, ' value ', new_value, ' not found.')
                    errors.append(field.verbose_name + ' value not found for ' + new_value)
                    continue
                setattr(gloss, field.name, fieldchoice)
                changes_done.append((field.name, original_value, new_value))
            elif field.__class__.__name__ == 'BooleanField':

                if new_value in ['true', 'True', 'TRUE']:
                    new_value = True
                elif new_value == 'None' or new_value == 'Neutral':
                    new_value = None
                else:
                    new_value = False
                setattr(gloss, field.name, new_value)
                changes_done.append((field.name, original_value, new_value))
            elif isinstance(field, models.ForeignKey) and field.related_model == Handshape:
                try:
                    handshape = Handshape.objects.get(name=new_value)
                except ObjectDoesNotExist:
                    print('Handshape value ', new_value, ' not found.')
                    errors.append(field.verbose_name + ' value not found for ' + new_value)
                setattr(gloss, field.name, handshape)
                changes_done.append((field.name, original_value, new_value))
            elif field.name == 'semanticfield':
                semantic_fields_errors = update_semantic_field(gloss, new_value, language_code)
                if semantic_fields_errors:
                    errors += semantic_fields_errors
                else:
                    changes_done.append((field.name, original_value, new_value))
            elif field.name == 'derivationhistory':
                derivationhistory_errors = update_derivation_history_field(gloss, new_value, language_code)
                if derivationhistory_errors:
                    errors += derivationhistory_errors
                else:
                    changes_done.append((field.name, original_value, new_value))
            else:
                # text field
                setattr(gloss, field.name, new_value)
                changes_done.append((field.name, original_value, new_value))
        gloss.save()
        for field, original_human_value, glossrevision_newvalue in changes_done:
            revision = GlossRevision(old_value=original_human_value,
                                     new_value=glossrevision_newvalue,
                                     field_name=field,
                                     gloss=gloss,
                                     user=request.user,
                                     time=datetime.now(tz=get_current_timezone()))
            revision.save()

    return errors


def gloss_update(request, glossid):

    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    try:
        gloss_id = int(glossid)
    except TypeError:
        return {}

    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        return {}

    from signbank.tools import get_interface_language_and_default_language_codes
    (interface_language, interface_language_code,
     default_language, default_language_code) = get_interface_language_and_default_language_codes(request)

    api_fields_2023 = api_fields(gloss.lemma.dataset, interface_language_code, advanced=True)

    gloss_data_dict = gloss.get_fields_dict(api_fields_2023, interface_language_code)
    update_fields_dict = get_gloss_update_human_readable_value_dict(request)
    fields_mapping_dict, human_values_dict = update_gloss_columns_to_value_dict_keys(interface_language_code)

    fields_to_update = dict()
    for human_readable_field, new_field_value in update_fields_dict.items():
        if human_readable_field not in gloss_data_dict.keys():
            print(human_readable_field, ' not found.')
            continue
        if human_readable_field in human_values_dict.keys():
            original_value = gloss_data_dict[human_readable_field]
            if new_field_value == original_value:
                print('not changed')
                continue
            gloss_field = human_values_dict[human_readable_field]
            fields_to_update[gloss_field] = (original_value, new_field_value)
    return fields_to_update
