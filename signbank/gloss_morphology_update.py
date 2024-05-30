from django.utils.translation import gettext_lazy as _, activate, gettext
from signbank.dictionary.models import *
from django.db.transaction import atomic
from django.utils.timezone import get_current_timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from guardian.shortcuts import get_objects_for_user
from signbank.tools import get_interface_language_and_default_language_codes
from signbank.csv_interface import normalize_field_choice
from signbank.api_token import hash_token
from signbank.tools import (gloss_from_identifier, get_default_annotationidglosstranslation,
                            check_existence_sequential_morphology,
                            check_existence_simultaneous_morphology,
                            check_existence_blend_morphology)
from signbank.dictionary.update_csv import (update_simultaneous_morphology, update_blend_morphology,
                                            update_sequential_morphology, subst_relations, subst_foreignrelations,
                                            update_tags, subst_notes, subst_semanticfield)
import datetime as DT
import ast


@csrf_exempt
def get_gloss_update_human_readable_value_dict(request):
    post_data = json.loads(request.body.decode('utf-8'))

    value_dict = dict()
    for field in post_data.keys():
        value = post_data.get(field, '')
        value_dict[field] = value.strip()
    return value_dict


def get_morphology_fields(language_code):
    activate(language_code)
    morphology_fields = [gettext("Sequential Morphology"),
                         gettext("Simultaneous Morphology"),
                         gettext("Blend Morphology")]
    return morphology_fields


def check_fields_can_be_updated(value_dict, language_code):
    morphology_fields = get_morphology_fields(language_code)
    errors = dict()
    for field in value_dict.keys():
        if field not in morphology_fields:
            errors[field] = _("Field update not available")
    return errors


def human_readable_morphology_to_internal(language_code):

    activate(language_code)
    human_readable_to_internal = dict()
    human_readable_to_internal[gettext("Sequential Morphology")] = 'sequential_morphology'
    human_readable_to_internal[gettext("Simultaneous Morphology")] = 'simultaneous_morphology'
    human_readable_to_internal[gettext("Blend Morphology")] = 'blend_morphology'

    return human_readable_to_internal


def internal_morphology_to_human_readable(language_code):

    activate(language_code)
    internal_to_human_readable = dict()
    internal_to_human_readable['sequential_morphology'] = gettext("Sequential Morphology")
    internal_to_human_readable['simultaneous_morphology'] = gettext("Simultaneous Morphology")
    internal_to_human_readable['blend_morphology'] = gettext("Blend Morphology")

    return internal_to_human_readable


def gloss_update(gloss, update_fields_dict, language_code):

    morphology_fields = get_morphology_fields(language_code)

    human_readable_to_internal = human_readable_morphology_to_internal(language_code)

    gloss_data_dict = gloss.get_fields_dict(morphology_fields, language_code)

    fields_to_update = dict()
    for human_readable_field, new_field_value in update_fields_dict.items():
        if human_readable_field not in gloss_data_dict.keys():
            # new value
            original_value = ''
            gloss_field = human_readable_to_internal[human_readable_field]
            fields_to_update[gloss_field] = (original_value, new_field_value)
            continue
        original_value = gloss_data_dict[human_readable_field]
        if new_field_value == original_value:
            continue
        gloss_field = human_readable_to_internal[human_readable_field]
        fields_to_update[gloss_field] = (original_value, new_field_value)
    return fields_to_update


def detect_type_related_problems_for_gloss_update(gloss, changes, language_code):
    internal_to_human_readable = internal_morphology_to_human_readable(language_code)
    errors = dict()
    for field, (original_value, new_value) in changes.items():
        if field == 'sequential_morphology':
            (found, not_found, errors) = check_existence_sequential_morphology(gloss, new_value)
            if len(errors):
                morphology_field = internal_to_human_readable[field]
                errors[morphology_field] = errors
        elif field == 'simultaneous_morphology':
            new_human_value_list = [v.strip() for v in new_value.split(',')]
            (checked_new_human_value, errors) = check_existence_simultaneous_morphology(gloss, new_human_value_list)
            if len(errors):
                morphology_field = internal_to_human_readable[field]
                errors[morphology_field] = errors
        elif field == 'blend_morphology':
            new_human_value_list = [v.strip() for v in new_value.split(',')]
            (checked_new_human_value, errors) = check_existence_blend_morphology(gloss, new_human_value_list)
            if len(errors):
                morphology_field = internal_to_human_readable[field]
                errors[morphology_field] = errors
    return errors


def gloss_update_do_changes(user, gloss, fields_to_update, language_code):
    changes_done = []
    for (field, new_value) in fields_to_update.items():
        if field == 'sequential_morphology':
            morphemes = [get_default_annotationidglosstranslation(morpheme.morpheme)
                         for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]
            original_value = " + ".join(morphemes)
            new_human_value_list = [v.strip() for v in new_value.split(' + ')]
            # the new values have already been parsed at the previous stage
            update_sequential_morphology(gloss, new_human_value_list)
            changes_done.append((field, original_value, new_value))
        elif field == 'simultaneous_morphology':
            morphemes = [(get_default_annotationidglosstranslation(m.morpheme), m.role) for m in
                         gloss.simultaneous_morphology.all()]
            sim_morphs = []
            for m in morphemes:
                sim_morphs.append(':'.join(m))
            original_value = ','.join(sim_morphs)
            new_human_value_list = [v.strip() for v in new_value.split(',')]
            update_simultaneous_morphology(gloss, new_human_value_list)
            changes_done.append((field, original_value, new_value))
        elif field == 'blend_morphology':
            morphemes = [(get_default_annotationidglosstranslation(m.glosses), m.role)
                         for m in gloss.blend_morphology.all()]

            ble_morphs = []
            for m in morphemes:
                ble_morphs.append(':'.join(m))
            original_value = ','.join(ble_morphs)
            new_human_value_list = [v.strip() for v in new_value.split(',')]
            update_blend_morphology(gloss, new_human_value_list)
            changes_done.append((field, original_value, new_value))
    for field, original_human_value, glossrevision_newvalue in changes_done:
        revision = GlossRevision(old_value=original_human_value,
                                 new_value=glossrevision_newvalue,
                                 field_name=field,
                                 gloss=gloss,
                                 user=user,
                                 time=datetime.now(tz=get_current_timezone()))
        revision.save()
    gloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    gloss.save()


@csrf_exempt
def api_update_gloss_morphology(request, datasetid, glossid):

    results = dict()
    auth_token_request = request.headers.get('Authorization', '')
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)
    if auth_token_request:
        auth_token = auth_token_request.split('Bearer ')[-1]
        hashed_token = hash_token(auth_token)
        signbank_token = SignbankAPIToken.objects.filter(api_token=hashed_token).first()
        if not signbank_token:
            results['errors'] = [gettext("Your Authorization Token does not match anything.")]
            return JsonResponse(results)
        username = signbank_token.signbank_user.username
        user = User.objects.get(username=username)
    elif request.user:
        user = request.user
    else:
        results['errors'] = [gettext("User not found in request.")]
        return JsonResponse(results)

    activate(interface_language_code)

    results['glossid'] = glossid

    errors = dict()

    if not user.is_authenticated:
        errors[gettext("User")] = gettext("You must be logged in to use this functionality.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        errors[gettext("Dataset")] = gettext("Dataset ID does not exist.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    change_permit_datasets = get_objects_for_user(user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        errors[gettext("Dataset")] = gettext("No change permission for dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    try:
        gloss_id = int(glossid)
    except TypeError:
        # the glossid in the url is a sequence of digits
        # this error can occur if it begins with a 0
        errors[gettext("Gloss")] = gettext("Gloss ID must be a number.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        errors[gettext("Gloss")] = gettext("Gloss not found.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not gloss.lemma:
        errors[gettext("Gloss")] = gettext("Gloss does not have a lemma.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if gloss.lemma.dataset != dataset:
        errors[gettext("Gloss")] = gettext("Gloss not found in the dataset.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    if not user.has_perm('dictionary.change_gloss'):
        errors[gettext("Gloss")] = gettext("No change gloss permission.")
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    value_dict = get_gloss_update_human_readable_value_dict(request)
    errors = check_fields_can_be_updated(value_dict, interface_language_code)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    fields_to_update = gloss_update(gloss, value_dict, interface_language_code)
    errors = detect_type_related_problems_for_gloss_update(gloss, fields_to_update, interface_language_code)
    if errors:
        results['errors'] = errors
        results['updatestatus'] = "Failed"
        return JsonResponse(results)

    gloss_update_do_changes(user, gloss, fields_to_update, interface_language_code)

    results['errors'] = {}
    results['updatestatus'] = "Success"

    return JsonResponse(results)
