
from django.utils.translation import gettext_lazy as _, activate, gettext
from signbank.dictionary.models import *
from django.db.transaction import atomic
from django.utils.timezone import get_current_timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from guardian.shortcuts import get_objects_for_user
from signbank.tools import get_interface_language_and_default_language_codes


def api_update_gloss_fields(language_code='en'):
    activate(language_code)

    api_fields_2024 = []

    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
    gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

    # TO DO
    extra_columns = ['Sign Languages', 'Dialects', 'Sequential Morphology', 'Simultaneous Morphology',
                     'Blend Morphology', 'Relations to other signs', 'Relations to foreign signs', 'Tags', 'Notes']

    for field in gloss_fields:
        api_fields_2024.append(field.verbose_name.title())

    return api_fields_2024


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


def gloss_update_fields_check(value_dict, language_code):
    api_fields_2024 = api_update_gloss_fields(language_code)
    errors = dict()
    for field in value_dict.keys():
        if field not in api_fields_2024:
            errors[field] = _("Field update not allowed")
    return errors


def update_semantic_field(gloss, new_values, language_code):
    new_semanticfields_to_save = []

    activate(language_code)

    new_human_value_list = [v.strip() for v in new_values.split(',')]

    for value in new_human_value_list:
        field_value = SemanticField.objects.get(name__iexact=value)
        new_semanticfields_to_save.append(field_value)

    gloss.semField.clear()
    for sf in new_semanticfields_to_save:
        gloss.semField.add(sf)
    gloss.save()


def update_derivation_history_field(gloss, new_values, language_code):
    new_derivationhistory_to_save = []

    activate(language_code)

    new_human_value_list = [v.strip() for v in new_values.split(',')]

    for value in new_human_value_list:
        field_value = DerivationHistory.objects.get(name__iexact=value)
        new_derivationhistory_to_save.append(field_value)

    gloss.derivHist.clear()
    for dh in new_derivationhistory_to_save:
        gloss.derivHist.add(dh)
    gloss.save()


def type_check_multiselect(category, new_values, language_code):
    activate(language_code)

    if category not in CATEGORY_MODELS_MAPPING.keys():
        return True

    multiselect_model = CATEGORY_MODELS_MAPPING[category]

    new_human_value_list = [v.strip() for v in new_values.split(',')]

    for value in new_human_value_list:
        try:
            field_value = multiselect_model.objects.get(name__iexact=value)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            return False
    return True


def gloss_update_typecheck(changes, language_code):

    errors = dict()
    for field, (original_value, new_value) in changes.items():
        if not new_value:
            continue
        if isinstance(field, FieldChoiceForeignKey):
            field_choice_category = field.field_choice_category
            try:
                fieldchoice = FieldChoice.objects.get(field=field_choice_category, name__iexact=new_value)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
        elif isinstance(field, models.ForeignKey) and field.related_model == Handshape:
            try:
                handshape = Handshape.objects.get(name__iexact=new_value)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
        elif field.__class__.__name__ == 'BooleanField':
            if new_value not in ['true', 'True', 'TRUE']:
                errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
        elif field.name == 'semField':
            type_check = type_check_multiselect('SemField', new_value, language_code)
            if not type_check:
                errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
        elif field.name == 'derivHist':
            type_check = type_check_multiselect('derivHist', new_value, language_code)
            if not type_check:
                errors[field.verbose_name.title()] = gettext('NOT FOUND: ') + new_value
    return errors


def gloss_update_do_changes(request, gloss, changes, language_code):

    changes_done = []
    activate(language_code)
    with atomic():
        for field, (original_value, new_value) in changes.items():
            if isinstance(field, FieldChoiceForeignKey):
                field_choice_category = field.field_choice_category
                fieldchoice = FieldChoice.objects.get(field=field_choice_category, name__iexact=new_value)
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
                handshape = Handshape.objects.get(name__iexact=new_value)
                setattr(gloss, field.name, handshape)
                changes_done.append((field.name, original_value, new_value))
            elif field.name == 'semField':
                update_semantic_field(gloss, new_value, language_code)
                changes_done.append((field.name, original_value, new_value))
            elif field.name == 'derivHist':
                update_derivation_history_field(gloss, new_value, language_code)
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


def gloss_update(gloss, update_fields_dict, language_code):

    api_fields_2024 = api_update_gloss_fields(language_code)

    gloss_data_dict = gloss.get_fields_dict(api_fields_2024, language_code)
    fields_mapping_dict, human_values_dict = update_gloss_columns_to_value_dict_keys(language_code)

    fields_to_update = dict()
    for human_readable_field, new_field_value in update_fields_dict.items():
        if not new_field_value:
            continue
        if human_readable_field not in gloss_data_dict.keys():
            # new value
            original_value = ''
            gloss_field = human_values_dict[human_readable_field]
            fields_to_update[gloss_field] = (original_value, new_field_value)
            continue
        if human_readable_field in human_values_dict.keys():
            original_value = gloss_data_dict[human_readable_field]
            if original_value in ['False'] and new_field_value in ['', 'False']:
                # treat empty as False
                continue
            if new_field_value == original_value:
                continue
            gloss_field = human_values_dict[human_readable_field]
            fields_to_update[gloss_field] = (original_value, new_field_value)
    return fields_to_update


@csrf_exempt
def api_update_gloss(request, datasetid, glossid):

    (interface_language, interface_language_code,
     default_language, default_language_code) = get_interface_language_and_default_language_codes(request)

    results = dict()
    results['glossid'] = glossid

    errors = dict()

    if not request.user.is_authenticated:
        errors[_("User")] = _("You must be logged in to use this functionality.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        errors[_("Dataset")] = _("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[_("Dataset")] = _("No change permission for dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[_("Gloss")] = _("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        errors[_("Gloss")] = _("Gloss not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not gloss.lemma:
        errors[_("Gloss")] = _("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if gloss.lemma.dataset != dataset:
        errors[_("Gloss")] = _("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not request.user.has_perm('dictionary.change_gloss'):
        errors[_("Gloss")] = _("No change gloss permission.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    value_dict = get_gloss_update_human_readable_value_dict(request)
    errors = gloss_update_fields_check(value_dict, interface_language_code)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    fields_to_update = gloss_update(gloss, value_dict, interface_language_code)
    errors = gloss_update_typecheck(fields_to_update, interface_language_code)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    gloss_update_do_changes(request, gloss, fields_to_update, interface_language_code)

    results['errors'] = {}
    results['updatestatus'] = "Success"

    return JsonResponse(results)
