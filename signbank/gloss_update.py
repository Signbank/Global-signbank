
from django.utils.translation import gettext_lazy as _, activate, gettext
from signbank.dictionary.models import *
from django.db.transaction import atomic
from django.utils.timezone import get_current_timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from guardian.shortcuts import get_objects_for_user
from signbank.api_token import hash_token

import ast


def api_update_gloss_fields(language_code='en'):
    activate(language_code)

    api_fields_2024 = []

    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv', 'senses']
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
    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv', 'senses']
    gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

    for field in gloss_fields:
        value_dict[field.name] = field.verbose_name.title()
        value_dict_reverse[field.verbose_name.title()] = field

    return value_dict, value_dict_reverse


@csrf_exempt
def get_gloss_update_human_readable_value_dict(request):
    post_data = json.loads(request.body.decode('utf-8'))

    value_dict = dict()
    for field in post_data.keys():
        value = post_data.get(field, '')
        value_dict[field] = value.strip()
    return value_dict


def gloss_update_fields_check(value_dict, language_code):
    api_fields_2024 = api_update_gloss_fields(language_code)
    errors = dict()
    for field in value_dict.keys():
        if field not in api_fields_2024:
            errors[field] = _("Field update not allowed")
    return errors


def remove_duplicates_preserve_order(translation_list):
    unique_list = []
    seen = set()
    for item in translation_list:
        if item not in seen:
            unique_list.append(item)
            seen.add(item)
    return unique_list


def convert_string_to_dict_of_list_of_lists(input_string):
    """
    Convert a string to a dictionary of lists of lists.
    """
    try:
        dict_of_lists = ast.literal_eval(input_string)
    except (ValueError, SyntaxError):
        return {}, "Sense input if not in the expected format. \nTry: '{\"en\":[[\"sense 1 keyword1\", \"sense 1 keyword2\"],[\"sense 2 keyword1\"]], \"nl\":[[\"sense 1 keyword1\"],[\"sense 2 keyword1\", \"sense 2 keyword2\"]]}'"

    # Verify if the result is a dictionary
    if isinstance(dict_of_lists, dict):
        lengths = set()
        for key, value in dict_of_lists.items():
            if not isinstance(value, list):
                return {}, f"The value associated with key '{key}' is not a list."
            lengths.add(len(value))
            for item in value:
                if not isinstance(item, list):
                    return {}, f"The value associated with key '{key}' contains a non-list element."
        if len(lengths) > 1:
            return {}, "Lists within the dictionary have different lengths."
        return dict_of_lists, None
    else:
        return {}, "Input is not a dictionary."


def update_senses(gloss, new_value): 
    """"
    new_value is a string of comma separated senses, where each sense is a string of comma separated translations
    """
    new_senses, _ = convert_string_to_dict_of_list_of_lists(new_value)

    dataset = gloss.lemma.dataset
    dataset_languages = dataset.translation_languages.all()

    # First remove the senses from the gloss
    old_senses = gloss.senses.all()
    for old_sense in old_senses:
        
        gloss.senses.remove(old_sense)

        # if this sense is part of another gloss, don't delete it
        other_glosses_for_sense = GlossSense.objects.filter(sense=old_sense).exclude(gloss=gloss).count()
        if not other_glosses_for_sense:
            # If this is this only gloss this sense was in, delete the sense
            for sense_translation in old_sense.senseTranslations.all():
                # iterate over a list because the objects will be removed
                for translation in sense_translation.translations.all():
                    sense_translation.translations.remove(translation)
                    translation.delete()
                old_sense.senseTranslations.remove(sense_translation)
                sense_translation.delete()
            # also remove its examplesentences if they are not in another sense
            example_sentences = old_sense.exampleSentences.all()
            for example_sentence in example_sentences:
                old_sense.exampleSentences.remove(example_sentence)
                if Sense.objects.filter(exampleSentences=example_sentence).count() == 0:
                    example_sentence.delete()
            old_sense.delete()

    # Then add the new senses
    for dataset_language in dataset_languages:
        if dataset_language.language_code_2char in new_senses:
            for new_sense_i, new_sense in enumerate(new_senses[dataset_language.language_code_2char], 1):
                # Make a new sense object or get the existing one
                if gloss.senses.count() < new_sense_i:
                    sense = Sense.objects.create()
                    gloss.senses.add(sense, through_defaults={'order':new_sense_i})
                else:
                    sense = gloss.senses.get(glosssense__order=new_sense_i)

                try:
                    sensetranslation = sense.senseTranslations.get(language=dataset_language)
                except ObjectDoesNotExist:
                    # there should only be one per language
                    sensetranslation = SenseTranslation.objects.create(language=dataset_language)
                    sense.senseTranslations.add(sensetranslation)
                new_sense_translations = remove_duplicates_preserve_order(new_sense)
                for inx, kw in enumerate(new_sense_translations, 1):
                    # this is a new sense so it has no translations yet
                    # the combination with gloss, language, orderIndex does not exist yet
                    # the index is the order the keyword was entered by the user
                    if not kw:
                        continue
                    keyword = Keyword.objects.get_or_create(text=kw)[0]
                    translation = Translation(translation=keyword,
                                              language=dataset_language,
                                              gloss=gloss,
                                              orderIndex=new_sense_i,
                                              index=inx)
                    translation.save()
                    sensetranslation.translations.add(translation)
                sensetranslation.save()
                sense.save()
    gloss.save()
    

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


@csrf_exempt
def gloss_update_do_changes(user, gloss, changes, language_code):

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
            elif field.name == "senses" and isinstance(field, models.ManyToManyField):
                update_senses(gloss, new_value)
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
                                     user=user,
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
    
    if 'Senses' in value_dict:
        _, errors = convert_string_to_dict_of_list_of_lists(value_dict['Senses'])
        if errors:
            results['errors'] = [errors]
            results['updatestatus'] = "Failed"
            return JsonResponse(results)

    gloss_update_do_changes(user, gloss, fields_to_update, interface_language_code)

    results['errors'] = {}
    results['updatestatus'] = "Success"

    return JsonResponse(results)
