from django.core.exceptions import ObjectDoesNotExist

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.template import Context, RequestContext, loader
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from django.contrib.auth.decorators import permission_required
from django.db.models.fields import BooleanField, IntegerField
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag
import os, shutil, re
from datetime import datetime
from django.utils.timezone import get_current_timezone
from django.contrib import messages

from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from django.conf import settings

from signbank.settings.server_specific import OTHER_MEDIA_DIRECTORY, DATASET_METADATA_DIRECTORY, DATASET_EAF_DIRECTORY, LANGUAGES
from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value
from signbank.tools import get_selected_datasets_for_user, gloss_from_identifier
from signbank.frequency import document_identifiers_from_paths, documents_paths_dictionary

from django.utils.translation import gettext_lazy as _

from guardian.shortcuts import get_user_perms, get_group_perms, get_objects_for_user


def show_error(request, translated_message, form, dataset_languages):
    # this function is used by the add_gloss function below
    messages.add_message(request, messages.ERROR, translated_message)
    return render(request, 'dictionary/add_gloss.html',
                  {'add_gloss_form': form,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': get_selected_datasets_for_user(request.user),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


# this method is called from the GlossListView (Add Gloss button on the page)
def add_gloss(request):
    """Create a new gloss and redirect to the edit view"""
    if not request.method == "POST":
        return HttpResponseForbidden("Add gloss method must be POST")

    dataset = None
    if 'dataset' in request.POST and request.POST['dataset'] is not None:
        dataset = Dataset.objects.get(pk=request.POST['dataset'])
        selected_datasets = Dataset.objects.filter(pk=request.POST['dataset'])
    else:
        selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    if dataset:
        last_used_dataset = dataset.acronym
    elif len(selected_datasets) == 1:
        last_used_dataset = selected_datasets[0].acronym
    elif 'last_used_dataset' in request.session.keys():
        last_used_dataset = request.session['last_used_dataset']
    else:
        last_used_dataset = None

    form = GlossCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=last_used_dataset)

    # Lemma handling
    lemma_form = None
    if request.POST['select_or_new_lemma'] == 'new':
        lemma_form = LemmaCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=last_used_dataset)
        if not lemma_form.is_valid():
            return show_error(request, _("You are not authorized to change the selected dataset."), form, dataset_languages)

        lemmaidgloss = lemma_form.save()
    else:
        lemmaidgloss_id = request.POST['idgloss']
        if lemmaidgloss_id == '' or lemmaidgloss_id == 'confirmed':
            # if the user has typed in an identifier instead of selecting from the Lemma lookahead list
            # or if the user has gone to the previous page and not selected the lemma again
            # in this case, the original template value 'confirmed' has bot been replaced with a lemma id
            return show_error(request, _("The given Lemma Idgloss is a string, not a Lemma."), form, dataset_languages)
        try:
            lemmaidgloss = LemmaIdgloss.objects.get(id=lemmaidgloss_id)
        except (ObjectDoesNotExist, IntegerField, ValueError, TypeError):
            return show_error(request, _("The given Lemma Idgloss ID is unknown."), form, dataset_languages)

    # Check for 'change_dataset' permission
    if dataset and ('change_dataset' not in get_user_perms(request.user, dataset)) \
            and ('change_dataset' not in get_group_perms(request.user, dataset))\
            and not request.user.is_staff:
        return show_error(request, _("You are not authorized to change the selected dataset."), form, dataset_languages)

    elif not dataset:
        # Dataset is empty, this is an error
        return show_error(request, _("Please provide a dataset."), form, dataset_languages)

    # if we get to here a dataset has been chosen for the new gloss
    for item, value in request.POST.items():
        if item.startswith(form.gloss_create_field_prefix):
            language_code_2char = item[len(form.gloss_create_field_prefix):]
            language = Language.objects.get(language_code_2char=language_code_2char)
            glosses_in_dataset = Gloss.objects.filter(lemma__dataset=dataset)
            glosses_for_this_language_and_annotation_idgloss = glosses_in_dataset.filter(
                        annotationidglosstranslation__language=language,
                        annotationidglosstranslation__text__exact=value)
            if len(glosses_for_this_language_and_annotation_idgloss) != 0:
                messages.add_message(request, messages.ERROR, _('Annotation ID Gloss not unique.'))
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    if not form.is_valid():
        return show_error(request, _("The add gloss form is not valid."), form, dataset_languages)

    if lemma_form and not lemma_form.is_valid():
        return show_error(request, _("The new lemma form is not valid."), form, dataset_languages)

    if not lemmaidgloss:
        return show_error(request, _("Please select or create a lemma."), form, dataset_languages)

    try:
        gloss = form.save()
        gloss.creationDate = datetime.now()
        gloss.excludeFromEcv = False
        gloss.lemma = lemmaidgloss

        # Set a default for all FieldChoice fields
        for field in [f for f in Gloss._meta.fields if isinstance(f, FieldChoiceForeignKey)]:
            field_value = getattr(gloss, field.name)
            if field_value is None:
                field_choice_category = field.field_choice_category
                try:
                    fieldchoice = FieldChoice.objects.get(field=field_choice_category, machine_value=0)
                except ObjectDoesNotExist:
                    fieldchoice = FieldChoice.objects.create(field=field_choice_category, machine_value=0, name='-')
                setattr(gloss, field.name, fieldchoice)

        gloss.save()
        gloss.creator.add(request.user)
    except ValidationError as ve:
        return show_error(request, ve.message, form, dataset_languages)

    if not ('search_results' in request.session.keys()):
        request.session['search_results'] = None

    # new gloss created successfully, go to GlossDetailView
    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')


def update_gloss(request, glossid):
    """View to update a gloss model from the jeditable jquery form
    We are sent one field and value at a time, return the new value
    once we've updated it."""

    if not request.user.has_perm('dictionary.change_gloss'):
        return HttpResponseForbidden("Gloss Update Not Allowed")

    if not request.method == "POST":
        return HttpResponseForbidden("Gloss Update method must be POST")

    gloss = get_object_or_404(Gloss, id=glossid)
    gloss.save()  # This updates the lastUpdated field

    field = request.POST.get('id', '')
    value = request.POST.get('value', '')

    original_value = '' #will in most cases be set later, but can't be empty in case it is not set
    category_value = ''
    field_category = ''
    lemma_gloss_group = False
    lemma_group_string = gloss.idgloss
    other_glosses_in_lemma_group = Gloss.objects.filter(lemma__lemmaidglosstranslation__text__iexact=lemma_group_string).count()
    if other_glosses_in_lemma_group > 1:
        lemma_gloss_group = True

    if len(value) == 0:
        # this seems a bit dangerous
        value = ' '

    elif value[0] == '_':
        value = value[1:]

    values = request.POST.getlist('value[]')   # in case we need multiple values

    # this variable may or may not be needed, depending on what field is being changed
    # initialize it to empty
    choice_list = []
    # validate
    # field is a valid field
    # value is a valid value for field

    if field == 'deletegloss':
        if value == 'confirmed':
            # delete the gloss and redirect back to gloss list

            pk = gloss.pk
            gloss.delete()
            gloss.pk = pk

            return HttpResponseRedirect(reverse('dictionary:admin_gloss_list'))

    if field.startswith('definition'):

        return update_definition(request, gloss, field, value)

    elif field.startswith('keyword'):

        return update_keywords(gloss, field, value)

    elif field.startswith('relationforeign'):

        return update_relationtoforeignsign(gloss, field, value)

    elif field.startswith('relation'):

        return update_relation(gloss, field, value)

    elif field.startswith('morphology-definition'):

        return update_morphology_definition(gloss, field, value)

    elif field.startswith('morpheme-definition'):

        return update_morpheme_definition(gloss, field, value)

    elif field.startswith('blend-definition'):

        return update_blend_definition(gloss, field, value)

    elif field.startswith('other-media'):

        return update_other_media(gloss, field, value)

    elif field == 'signlanguage':
        # expecting possibly multiple values

        return update_signlanguage(gloss, field, values)

    elif field == 'dialect':
        # expecting possibly multiple values

        return update_dialect(gloss, field, values)

    elif field == 'semanticfield':
        # expecting possibly multiple values

        return update_semanticfield(request, gloss, field, values)

    elif field == 'derivationhistory':
        # expecting possibly multiple values

        return update_derivationhistory(request, gloss, field, values)

    elif field == 'dataset':
        original_value = getattr(gloss,field)

        # in case somebody tries an empty or non-existent dataset name
        try:
            ds = Dataset.objects.get(name=value)
        except:
            return HttpResponse(str(original_value), {'content-type': 'text/plain'})

        if ds.is_public:
            print('dataset is public')
            newvalue = value
            setattr(gloss, field, ds)
            gloss.save()

            request.session['last_used_dataset'] = ds.acronym

            return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

        import guardian
        if ds in guardian.shortcuts.get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                         Dataset, any_perm=True):
            newvalue = value
            setattr(gloss, field, ds)
            gloss.save()

            request.session['last_used_dataset'] = ds.acronym

            return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

        print('no permission for chosen dataset')
        newvalue = original_value
        return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

    elif field == "sn":
        # sign number must be unique, return error message if this SN is
        # already taken

        if value == '':
            gloss.__setattr__(field, None)
            gloss.save()
            newvalue = ''
        else:
            try:
                value = int(value)
            except:
                return HttpResponseBadRequest("SN value must be integer", {'content-type': 'text/plain'})

            existing_gloss = Gloss.objects.filter(sn__exact=value)
            if existing_gloss.count() > 0:
                g = existing_gloss[0].idgloss
                return HttpResponseBadRequest("SN value already taken for gloss %s" % g, {'content-type': 'text/plain'})
            else:
                gloss.sn = value
                gloss.save()
                newvalue = value


    elif field in 'inWeb':
        # only modify if we have publish permission
        original_value = getattr(gloss,field)
        if request.user.has_perm('dictionary.can_publish'):
            gloss.inWeb = value.lower() in [_('Yes').lower(),'true',True,1]
            gloss.save()

        if gloss.inWeb:
            newvalue = _('Yes')
        else:
            newvalue = _('No')

    elif field in 'isNew':
        original_value = getattr(gloss,field)
        # only modify if we have publish permission
        gloss.isNew = value.lower() in [_('Yes').lower(),'true',True,1]
        gloss.save()

        if gloss.isNew:
            newvalue = _('Yes')
        else:
            newvalue = _('No')
    elif field in 'excludeFromEcv':
        original_value = getattr(gloss,field)

        # only modify if we have publish permission

        gloss.excludeFromEcv = value.lower() in [_('Yes').lower(),'true',True,1]
        gloss.save()

        if gloss.excludeFromEcv:
            newvalue = _('Yes')
        else:
            newvalue = _('No')

    elif field.startswith('annotation_idgloss'):

        return update_annotation_idgloss(gloss, field, value)

    elif field.startswith('lemmaidgloss'):
        # Set new lemmaidgloss for this gloss
        # First check whether the gloss dataset is the same as the lemma dataset
        try:
            dataset = gloss.dataset
            lemma = LemmaIdgloss.objects.get(pk=value)
            if dataset is None or dataset == lemma.dataset:
                gloss.lemma = lemma
                gloss.save()
            else:
                messages.add_message(messages.ERROR, _("The dataset of the gloss is not the same as that of the lemma."))
        except ObjectDoesNotExist:
            messages.add_message(messages.ERROR, _("The specified lemma does not exist."))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    else:


        if field not in [f.name for f in Gloss._meta.get_fields()]:
            return HttpResponseBadRequest("Unknown field", {'content-type': 'text/plain'})

        whitespace = tuple(' \n\r\t')
        if value.startswith(whitespace) or value.endswith(whitespace):
            value = value.strip()
        original_value = getattr(gloss,field)

        if field == 'idgloss' and value == '':
            # don't allow user to set Lemma ID Gloss to empty
            # return HttpResponse(str(original_value), {'content-type': 'text/plain'})
            value = str(original_value)

        # special cases
        # - Foreign Key fields (Language, Dialect)
        # - keywords
        # - videos
        # - tags

        #Translate the value if a boolean
        # Language values are needed here!
        newvalue = value
        if isinstance(gloss._meta.get_field(field),BooleanField):
            # value is the html 'value' received during editing
            # value gets converted to a Boolean by the following statement
            if field in ['weakdrop', 'weakprop']:
                NEUTRALBOOLEANCHOICES = { 'None': '1', 'True': '2', 'False': '3' }
                category_value = 'phonology'
                if value not in ['1', '2', '3']:
                    # this code is for the case the user has not selected a value in the list
                    if value in ['None', 'True', 'False']:
                        value = NEUTRALBOOLEANCHOICES[value]
                    else:
                        # something is wrong, set to None
                        value = '1'
                newvalue = {'1': '&nbsp;', '2': '+WD', '3': '-WD'}[value]
                value = {'1': None, '2': True, '3': False}[value]

            elif field in ['domhndsh_letter', 'domhndsh_number', 'subhndsh_letter', 'subhndsh_number']:
                newvalue = value
                value = (value in ['letter', 'number'])
            else:
                value = (value.lower() in [_('Yes').lower(),'true',True,1])
                newvalue = value
        # special value of 'notset' or -1 means remove the value
        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
        fieldchoiceforeignkey_fields = [f.name for f in Gloss._meta.fields
                                        if f.name in fieldnames
                                        and isinstance(Gloss._meta.get_field(f.name), FieldChoiceForeignKey)]
        fields_empty_null = [f.name for f in Gloss._meta.fields
                                if f.name in fieldnames and f.null and f.name not in fieldchoiceforeignkey_fields ]

        char_fields_not_null = [f.name for f in Gloss._meta.fields
                                if f.name in fieldnames and f.__class__.__name__ == 'CharField'
                                    and f.name not in fieldchoiceforeignkey_fields and not f.null]

        char_fields = [f.name for f in Gloss._meta.fields
                                if f.name in fieldnames and f.__class__.__name__ == 'CharField'
                                    and f.name not in fieldchoiceforeignkey_fields]

        text_fields = [f.name for f in Gloss._meta.fields
                                if f.name in fieldnames and f.__class__.__name__ == 'TextField' ]

        text_fields_not_null = [f.name for f in Gloss._meta.fields
                                if f.name in fieldnames and f.__class__.__name__ == 'TextField' and not f.null]

        # The following code relies on the order of if else testing
        # The updates ignore Placeholder empty fields of '-' and '------'
        # The Placeholders are needed in the template Edit view so the user can "see" something to edit
        if field in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
            gloss_field = Gloss._meta.get_field(field)
            try:
                handshape = Handshape.objects.get(machine_value=value)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                print('Update handshape no unique machine value found: ', gloss_field.name, value)
                print('Setting to machine value 0')
                handshape = Handshape.objects.get(machine_value=0)
            gloss.__setattr__(field, handshape)
            gloss.save()
            newvalue = handshape.name
        elif field in fieldchoiceforeignkey_fields:
            gloss_field = Gloss._meta.get_field(field)
            try:
                fieldchoice = FieldChoice.objects.get(field=gloss_field.field_choice_category, machine_value=value)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                print('Update field choice no unique machine value found: ', gloss_field.name, gloss_field.field_choice_category, value)
                print('Setting to machine value 0')
                fieldchoice = FieldChoice.objects.get(field=gloss_field.field_choice_category, machine_value=0)
            gloss.__setattr__(field, fieldchoice)
            gloss.save()
            newvalue = fieldchoice.name
        elif value in ['notset','','-','------'] and field in fields_empty_null:
            gloss.__setattr__(field, None)
            gloss.save()
            newvalue = ''
        elif (field in char_fields or field in text_fields_not_null) and (value == '-' or value == '------'):
            value = ''
            gloss.__setattr__(field, value)
            gloss.save()
            newvalue = ''
        elif field in text_fields and (value == '-' or value == '------'):
            # this is to take care of legacy code where some values were set to the empty field display hint
            gloss.__setattr__(field, None)
            gloss.save()
            newvalue = ''
        #Regular field updating
        else:

            # Alert: Note that if field is idgloss, the following code updates it
            gloss.__setattr__(field,value)
            gloss.save()

            #If the value is not a Boolean, get the human readable value
            if not isinstance(value,bool):
                # if we get to here, field is a valid field of Gloss
                newvalue = value

    if field in FIELDS['phonology']:

        category_value = 'phonology'

    # the gloss has been updated, now prepare values for saving to GlossHistory and display in template
    #This is because you cannot concat none to a string in py3
    if original_value is None:
        original_value = ''
    # this takes care of a problem with None not being allowed as a value in GlossRevision
    # the weakdrop and weakprop fields make use of three-valued logic and None is a legitimate value aka Neutral
    if newvalue is None:
        newvalue = ''

    # if choice_list is empty, the original_value is returned by the called function
    # Remember this change for the history books
    original_human_value = original_value.name if isinstance(original_value, FieldChoice) else original_value
    if isinstance(value, bool) and field in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
    # store a boolean in the Revision History rather than a human value as for the template (e.g., 'letter' or 'number')
        glossrevision_newvalue = value
    else:
        glossrevision_newvalue = newvalue

    revision = GlossRevision(old_value=original_human_value,
                             new_value=glossrevision_newvalue,
                             field_name=field,
                             gloss=gloss,
                             user=request.user,
                             time=datetime.now(tz=get_current_timezone()))
    revision.save()
    # The machine_value (value) representation is also returned to accommodate Hyperlinks to Handshapes in gloss_edit.js
    return HttpResponse(
        str(original_value) + str('\t') + str(newvalue) + str('\t') +  str(value) + str('\t') + str(category_value) + str('\t') + str(lemma_gloss_group),
        {'content-type': 'text/plain'})


def update_keywords(gloss, field, value):
    """Update the keyword field"""
    # Determine the language of the keywords
    language = Language.objects.get(id=get_default_language_id())
    try:
        language_code_2char = field[len('keyword_'):]
        language = Language.objects.filter(language_code_2char=language_code_2char)[0]
    except:
        pass

    kwds = [k.strip() for k in value.split(',')]

    keywords_list = []

    # omit duplicates
    for kwd in kwds:
        if kwd not in keywords_list:
            keywords_list.append(kwd)

    # remove current keywords
    current_trans = gloss.translation_set.filter(language=language)
    current_trans.delete()
    # add new keywords
    for i in range(len(keywords_list)):
        (kobj, created) = Keyword.objects.get_or_create(text=keywords_list[i])
        trans = Translation(gloss=gloss, translation=kobj, index=i, language=language)
        trans.save()
    
    newvalue = ", ".join([t.translation.text for t in gloss.translation_set.filter(language=language)])
    
    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def update_annotation_idgloss(gloss, field, value):
    """Update the AnnotationIdGlossTranslation"""

    # Determine the language of the keywords
    language = Language.objects.get(id=get_default_language_id())
    try:
        language_code_2char = field[len('annotation_idgloss_'):]
        language = Language.objects.filter(language_code_2char=language_code_2char).first()
    except ObjectDoesNotExist:
        pass

    # value might be empty string
    whitespace = tuple(' \n\r\t')
    if value.startswith(whitespace) or value.endswith(whitespace):
        value = value.strip()

    try:
        annotation_idgloss_translation = AnnotationIdglossTranslation.objects.get(gloss=gloss, language=language)
        original_value = annotation_idgloss_translation.text
    except ObjectDoesNotExist:
        # create an empty annotation for this gloss and language
        annotation_idgloss_translation = AnnotationIdglossTranslation(gloss=gloss, language=language)
        original_value = ''

    if value == '':
        # don't allow user to set Annotation ID Gloss to empty
        return HttpResponse(str(original_value), {'content-type': 'text/plain'})

    annotation_idgloss_translation.text = value
    annotation_idgloss_translation.save()

    return HttpResponse(str(value), {'content-type': 'text/plain'})

def update_signlanguage(gloss, field, values):
    # expecting possibly multiple values

    # Sign Language and Dialect are interdependent
    # When updated in Gloss Details, checks are made to insure consistency
    # Because we use Ajax calls to update the data, two values need to be returned in order to also have a side effect
    # on the other field. I.e., Changing the Sign Language may cause Dialects to be removed, and changing the Dialect
    # may cause the Sign Language to be filled in if not already set, with that of the new Dialect
    # To accommodate this in the interactive user interface for Editting a Gloss, two values are returned

    # The dialects value is set to the current dialects value
    dialects_value = ", ".join([str(d.signlanguage.name) + '/' + str(d.name) for d in gloss.dialect.all()])
    current_signlanguages = gloss.signlanguage.all()
    current_signlanguage_name = ''
    print('update_signlanguage: ', current_signlanguages)
    for lang in current_signlanguages:
        # this looks strange, is this a convenience for a singleton set
        current_signlanguage_name = lang.name

    try:
        gloss.signlanguage.clear()
        for value in values:
            lang = SignLanguage.objects.get(name=value)
            gloss.signlanguage.add(lang)
            if value != current_signlanguage_name:
                gloss.dialect.clear()
                # Has a side effect that the Dialects value is cleared, this will be passed back to the user interface
                dialects_value = ''
        gloss.save()
        new_signlanguage_value = ", ".join([str(g) for g in gloss.signlanguage.all()])
    except:
        return HttpResponseBadRequest("Unknown Language %s" % values, {'content-type': 'text/plain'})

    return HttpResponse(str(new_signlanguage_value) + '\t' + str(dialects_value), {'content-type': 'text/plain'})

def update_dialect(gloss, field, values):
    # expecting possibly multiple values

    dialect_choices = json.loads(gloss.dialect_choices())
    numerical_values_converted_to_dialects = [ dialect_choices[int(value)] for value in values ]
    error_string_values = ', '.join(numerical_values_converted_to_dialects)
    new_dialects_to_save = []
    try:
        # there is actually only one sign language
        gloss_signlanguage = gloss.lemma.dataset.signlanguage
        for value in numerical_values_converted_to_dialects:
            # Gloss Details pairs the Dialect with the Language in the update menu
            (sign_lang, dia) = value.split('/')
            lang = SignLanguage.objects.get(name=sign_lang)
            if lang != gloss_signlanguage:
                # There is currently a sign language assigned to this gloss, the new dialect does not match it
                raise Exception

            dialect_objs = Dialect.objects.filter(name=dia).filter(signlanguage_id=lang)
            for lang in dialect_objs:
                new_dialects_to_save.append(lang)

        # clear the old dialects only after we've parsed and checked the new ones
        gloss.dialect.clear()
        for lang in new_dialects_to_save:
            gloss.dialect.add(lang)
        gloss.save()

        # The signlanguage value is set to the currect sign languages value
        signlanguage_value = ", ".join([str(g) for g in gloss.signlanguage.all()])
        new_dialects_value = ", ".join([str(d.signlanguage.name)+'/'+str(d.name) for d in gloss.dialect.all()])
    except:
        return HttpResponseBadRequest("Dialect %s does not match Sign Language of Gloss" % error_string_values,
                                      {'content-type': 'text/plain'})

    return HttpResponse(str(signlanguage_value) + '\t' + str(new_dialects_value), {'content-type': 'text/plain'})

def update_semanticfield(request, gloss, field, values):
    # field is 'semanticfield'
    # expecting possibly multiple values
    # values is a list of strings
    new_semanticfields_to_save = []

    # fetch all the valid semantic field choices
    # create a lookup dictionary mapping names to objects
    # the name is a unique field in the model
    semanticfield_choices = {}
    for sf in SemanticField.objects.all():
        semanticfield_choices[sf.name] = sf

    # get the SmanticField objects for the values
    for value in values:
        # there's a conditional here, although it's not really needed
        # it is impossible for a value not to be found among the choices
        # we test for it among the keys to avoid a key error
        # if a value is not found it is simply ignored
        if value in semanticfield_choices.keys():
            new_semanticfields_to_save.append(semanticfield_choices[value])

    original_semanticfield_value = ", ".join([str(sf.name) for sf in gloss.semField.all()])

    # clear the old semantic fields only after we've parsed and checked the new ones
    gloss.semField.clear()
    for sf in new_semanticfields_to_save:
        gloss.semField.add(sf)
    gloss.save()

    new_semanticfield_value = ", ".join([str(sf.name) for sf in gloss.semField.all()])

    revision = GlossRevision(old_value=original_semanticfield_value, new_value=new_semanticfield_value, field_name='semField',
                             gloss=gloss, user=request.user, time=datetime.now(tz=get_current_timezone()))
    revision.save()

    return HttpResponse(str(new_semanticfield_value), {'content-type': 'text/plain'})

def update_derivationhistory(request, gloss, field, values):
    # field is 'derivationhistory'
    # expecting possibly multiple values
    # values is a list of strings
    new_derivationhistory_to_save = []

    # fetch all the valid derivation history choices
    # create a lookup dictionary mapping names to objects
    # the name is a unique field in the model
    derivationhistory_choices = {}
    for dh in DerivationHistory.objects.all():
        derivationhistory_choices[dh.name] = dh

    # get the DerivationHistory objects for the values
    for value in values:
        # there's a conditional here, although it's not really needed
        # it is impossible for a value not to be found among the choices
        # we test for it among the keys to avoid a key error
        # if a value is not found it is simply ignored
        if value in derivationhistory_choices.keys():
            new_derivationhistory_to_save.append(derivationhistory_choices[value])

    original_derivationhistory_value = ", ".join([str(sf.name) for sf in gloss.derivHist.all()])

    # clear the old derivation histories only after we've parsed and checked the new ones
    gloss.derivHist.clear()
    for sf in new_derivationhistory_to_save:
        gloss.derivHist.add(sf)
    gloss.save()

    new_derivationhistory_value = ", ".join([str(sf.name) for sf in gloss.derivHist.all()])

    revision = GlossRevision(old_value=original_derivationhistory_value, new_value=new_derivationhistory_value, field_name='derivHist',
                             gloss=gloss, user=request.user, time=datetime.now(tz=get_current_timezone()))
    revision.save()

    return HttpResponse(str(new_derivationhistory_value), {'content-type': 'text/plain'})

def update_tags(gloss, field, values):
    # expecting possibly multiple values
    current_tag_ids = [tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    new_tag_ids = [tag.id for tag in Tag.objects.filter(name__in=values)]

    # the existence of the new tag has already been checked
    for tag_id in current_tag_ids:

        if tag_id not in new_tag_ids:
            # delete tag from object
            tagged_obj = TaggedItem.objects.get(object_id=gloss.id,tag_id=tag_id)
            print("DELETE TAGGED OBJECT: ", tagged_obj, ' for gloss: ', tagged_obj.object_id)
            tagged_obj.delete()

    if not new_tag_ids:
        # this was a delete
        return HttpResponse('', {'content-type': 'text/plain'})

    for value in values:
        Tag.objects.add_tag(gloss, value)

    new_tag_ids = [tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    newvalue = ', '.join([str(tag.name).replace('_',' ') for tag in  Tag.objects.filter(id__in=new_tag_ids) ])

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def update_sequential_morphology(gloss, field, values):
    # expecting possibly multiple values

    morphemes = [morpheme.id for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]

    role = 2

    # the existence of the morphemes in parameter values has already been checked
    try:
        for morpheme_def_id in morphemes:
            old_morpheme = MorphologyDefinition.objects.get(id=morpheme_def_id)
            print("DELETE Sequential Morphology: ", old_morpheme)
            old_morpheme.delete()
        for value in values:
            morpheme = Gloss.objects.get(pk=value)
            morph_def = MorphologyDefinition()
            morph_def.parent_gloss = gloss
            morph_def.role = role
            morph_def.morpheme = morpheme
            morph_def.save()
            role = role + 1
    except:
        return HttpResponseBadRequest("Unknown Morpheme %s" % values, {'content-type': 'text/plain'})

    seq_morphemes = [morpheme.morpheme for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]

    newvalue = ", ".join([str(g.idgloss) for g in seq_morphemes])

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def update_simultaneous_morphology(gloss, field, values):
    # expecting possibly multiple values

    existing_sim_ids = [morpheme.id for morpheme in SimultaneousMorphologyDefinition.objects.filter(parent_gloss_id=gloss)]
    new_sim_tuples = []
    for value in values:
        (morpheme_id, role) = value.split(':')
        new_sim_tuples.append((morpheme_id,role))

    # delete any existing simultaneous morphology objects rather than update
    # to allow (re-)insertion in the correct order
    for sim_id in existing_sim_ids:
        sim = SimultaneousMorphologyDefinition.objects.get(id=sim_id)
        print("DELETE Simultaneous Morphology: ", sim)
        sim.delete()

    # the existence of the morphemes has already been checked, but check again anyway
    for (morpheme_id, role) in new_sim_tuples:

        try:
            morpheme_gloss = Gloss.objects.get(pk=morpheme_id)

            # create new morphology
            sim = SimultaneousMorphologyDefinition()
            sim.parent_gloss_id = gloss.id
            sim.morpheme_id = morpheme_gloss.id
            sim.role = role
            sim.save()

        except:
            print("morpheme not found")
            continue


    # Refresh Simultaneous Morphology with newly inserted objects
    morphemes = [(str(morpheme.morpheme.id), morpheme.role)
                 for morpheme in SimultaneousMorphologyDefinition.objects.filter(parent_gloss_id=gloss)]
    sim_morphs = []
    for m in morphemes:
        sim_morphs.append(':'.join(m))
    simultaneous_morphemes = ', '.join(sim_morphs)

    newvalue = simultaneous_morphemes

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})


def update_blend_morphology(gloss, field, values):

    existing_blends = [ ble_morph.id for ble_morph in BlendMorphology.objects.filter(parent_gloss=gloss) ]

    new_blend_tuples = []
    for value in values:
        (gloss_id, role) = value.split(':')
        new_blend_tuples.append((gloss_id,role))

    try:

        # delete any existing blend morphology objects
        for existing_blend in existing_blends:
            blend_object = BlendMorphology.objects.get(id=existing_blend)
            print("DELETE Blend Morphology for gloss ", str(gloss.pk), ": ", blend_object.glosses.pk, " ", blend_object.role)
            blend_object.delete()

        for (gloss_id, role) in new_blend_tuples:

            morpheme_gloss = Gloss.objects.get(pk=gloss_id)

            # create new morphology
            new_blend = BlendMorphology()
            new_blend.parent_gloss = gloss
            new_blend.glosses = morpheme_gloss
            new_blend.role = role
            new_blend.save()

    except:
        return HttpResponseBadRequest("Unknown Morpheme in Blend Morphology %s" % values, {'content-type': 'text/plain'})

    # convert to display format
    blend_morphemes = [ (str(ble_morph.glosses.pk), ble_morph.role) for ble_morph in BlendMorphology.objects.filter(parent_gloss=gloss) ]
    ble_morphs = []
    for m in blend_morphemes:
        ble_morphs.append(':'.join(m))
    blend_morphemes = ', '.join(ble_morphs)

    newvalue = blend_morphemes

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})


def subst_notes(gloss, field, values):
    # this is called by csv_import to modify the notes for a gloss

    note_role_choices = FieldChoice.objects.filter(field='NoteType')
    # this is used to speedup matching updates to Notes
    # it allows the type of note to be in either English or Dutch in the CSV file
    # this actually isn't used at the moment, the CSV export is to English
    note_reverse_translation = {}
    for nrc in note_role_choices:
        for language in MODELTRANSLATION_LANGUAGES:
            name_languagecode = 'name_' + language.replace('-', '_')
            # check to make sure the model translation has been installed properly
            try:
                notes_translation = getattr(nrc, name_languagecode)
            except KeyError:
                continue

            note_reverse_translation[notes_translation] = nrc

    for original_note in gloss.definition_set.all():
        original_note.delete()

    # convert new Notes csv value to proper format
    # the syntax of the new note values has already been checked at a previous stage of csv import
    new_notes_values = []

    # the space is required in order to identify multiple notes in the input
    split_values = re.split(r', ', values)
    for note_value in split_values:
        take_apart = re.match("([^:]+):\s?\((False|True),(\d),(.*)\)", note_value)

        if take_apart:
            (field, name, count, text) = take_apart.groups()
            new_tuple = (field, name, count, text)
            new_notes_values.append(new_tuple)

    # make sure the delete code has run before saving the definitions again
    gloss.refresh_from_db()

    for (role, published, count, text) in new_notes_values:
        is_published = (published == 'True')
        note_role = note_reverse_translation[role]
        index_count = int(count)
        defn = Definition(gloss=gloss, count=index_count, role=note_role, text=text, published=is_published)
        defn.save()

    gloss_notes = gloss.definition_set.all()
    new_notes_refresh = [(note.get_role_display(), str(note.published), str(note.count), note.note_text())
                         for note in gloss_notes]
    notes_by_role = []
    for note in new_notes_refresh:
        notes_by_role.append(':'.join(note))

    new_gloss_notes = ", ".join(notes_by_role)

    return HttpResponse(str(new_gloss_notes), {'content-type': 'text/plain'})

def subst_foreignrelations(gloss, field, values):
    # expecting possibly multiple values
    # values is a list of values, where each value is a tuple of the form 'Boolean:String:String'
    # The format of argument values has been checked before calling this function

    existing_relations = [(relation.id, relation.other_lang_gloss) for relation in RelationToForeignSign.objects.filter(gloss=gloss)]

    existing_relation_ids = [r[0] for r in existing_relations]
    existing_relation_other_glosses = [r[1] for r in existing_relations]

    new_relations = []
    new_relation_tuples = []

    for value in values:
        (loan_word, other_lang, other_lang_gloss) = value.split(':')
        new_relation_tuples.append((loan_word,other_lang,other_lang_gloss))

    new_relations = [ t[2] for t in new_relation_tuples]

    # delete any existing relations with obsolete other language gloss
    for rel_id in existing_relation_ids:
        rel = RelationToForeignSign.objects.get(id=rel_id)
        if rel.other_lang_gloss not in new_relations:
            print("DELETE Relation to Foreign Sign: ", rel)
            rel.delete()

    # all remaining existing relations are to be updated
    for (loan_word, other_lang, other_lang_gloss) in new_relation_tuples:
        if other_lang_gloss in existing_relation_other_glosses:
            # update existing relation
            rel = RelationToForeignSign.objects.get(gloss=gloss, other_lang_gloss=other_lang_gloss)
            rel.loan = loan_word in ['Yes', 'yes', 'ja', 'Ja', '是', 'true', 'True', True, 1]
            rel.other_lang = other_lang
            rel.save()
        else:
            # create new relation
            new_relations += [other_lang_gloss]
            rel = RelationToForeignSign(gloss=gloss,loan=loan_word,other_lang=other_lang,other_lang_gloss=other_lang_gloss)
            rel.save()

    new_relations_refresh = [(str(relation.loan), relation.other_lang, relation.other_lang_gloss) for relation in
                 RelationToForeignSign.objects.filter(gloss=gloss)]
    relations_with_categories = []
    for rel_cat in new_relations_refresh:
        relations_with_categories.append(':'.join(rel_cat))

    relations_categories = ", ".join(relations_with_categories)

    newvalue = relations_categories

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def subst_relations(gloss, field, values):
    # expecting possibly multiple values
    # values is a list of values, where each value is a tuple of the form 'Role:String'
    # The format of argument values has been checked before calling this function

    existing_relations = [(relation.id, relation.role, relation.target.id) for relation in Relation.objects.filter(source=gloss)]
    existing_relation_ids = [ r[0] for r in existing_relations ]
    existing_relations_by_role = dict()

    for (rel_id, rel_role, rel_other_gloss) in existing_relations:

        if rel_role in existing_relations_by_role:
            existing_relations_by_role[rel_role].append(rel_other_gloss)
        else:
            existing_relations_by_role[rel_role] = [rel_other_gloss]

    new_tuples_to_add = []
    already_existing_to_keep = []

    for value in values:
        (role, target) = value.split(':')
        role = role.strip()
        target = target.strip()
        if role in existing_relations_by_role and target in existing_relations_by_role[role]:
            already_existing_to_keep.append((role,target))
        else:
            new_tuples_to_add.append((role, target))

    # delete existing relations and reverse relations involving this gloss
    for rel_id in existing_relation_ids:
        rel = Relation.objects.get(id=rel_id)

        if (rel.role, rel.target.id) in already_existing_to_keep:
            continue

        # Also delete the reverse relation
        reverse_relations = Relation.objects.filter(source=rel.target, target=rel.source,
                                                    role=Relation.get_reverse_role(rel.role))
        if reverse_relations.count() > 0:
            print("DELETE reverse relation: target: ", rel.target, ", relation: ", reverse_relations[0])
            reverse_relations[0].delete()

        print("DELETE Relation: ", rel)
        rel.delete()

    # all remaining existing relations are to be updated
    for (role, target) in new_tuples_to_add:
        try:
            target_gloss = Gloss.objects.get(pk=target)
            rel = Relation(source=gloss, role=role, target=target_gloss)
            rel.save()
            # Also add the reverse relation
            reverse_relation = Relation(source=target_gloss, target=gloss, role=Relation.get_reverse_role(role))
            reverse_relation.save()
        except:
            print("target gloss not found")
            continue

    new_relations_refresh = [ (relation.role, relation.target.idgloss) for relation in
                 Relation.objects.filter(source=gloss)]
    relations_with_categories = []
    for rel_cat in new_relations_refresh:
        relations_with_categories.append(':'.join(rel_cat))

    relations_categories = ", ".join(relations_with_categories)

    newvalue = relations_categories

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

## This function is called from the Gloss Details template when updating Relations to Other Signs
def update_relation(gloss, field, value):
    """Update one of the relations for this gloss"""
    (what, relid) = field.split('_')
    what = what.replace('-','_')

    try:
        rel = Relation.objects.get(id=relid)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Bad Relation ID '%s'" % relid, {'content-type': 'text/plain'})

    if not rel.source == gloss:
        return HttpResponseBadRequest("Relation doesn't match gloss", {'content-type': 'text/plain'})
    
    if what == 'relationdelete':
        rel.delete()

        # Also delete the reverse relation
        reverse_relations = Relation.objects.filter(source=rel.target, target=rel.source,
                                                    role=Relation.get_reverse_role(rel.role))
        if reverse_relations.count() > 0:
            reverse_relations[0].delete()

        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editrel')
    elif what == 'relationrole':
        rel.role = value
        rel.save()
        newvalue = rel.get_role_display()
    elif what == 'relationtarget':
        
        target = gloss_from_identifier(value)
        if target:
            rel.target = target
            rel.save()
            newvalue = str(target)
        else:
            return HttpResponseBadRequest("Badly formed gloss identifier '%s'" % value, {'content-type': 'text/plain'})
    else:
        
        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})           
    
    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def delete_relation(gloss, field):

    return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})

def update_relationtoforeignsign(gloss, field, value):
    """Update one of the relations for this gloss"""
    
    (what, relid) = field.split('_')
    what = what.replace('-','_')

    try:
        rel = RelationToForeignSign.objects.get(id=relid)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Bad RelationToForeignSign ID '%s'" % relid, {'content-type': 'text/plain'})

    if not rel.gloss == gloss:
        return HttpResponseBadRequest("Relation doesn't match gloss", {'content-type': 'text/plain'})
    
    if what == 'relationforeign_delete':
        rel.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editrelforeign')
    elif what == 'relationforeign_loan':
        rel.loan = value in ['Yes', 'yes', 'ja', 'Ja', '是', 'true', 'True', True, 1]
        rel.save()

    elif what == 'relationforeign_other_lang':
        rel.other_lang = value
        rel.save()

    elif what == 'relationforeign_other_lang_gloss':
        rel.other_lang_gloss = value
        rel.save()

    else:
        
        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})           
    
    return HttpResponse(str(value), {'content-type': 'text/plain'})


def morph_from_identifier(value):
    """Given an id of the form idgloss (pk) return the
    relevant Morpheme or None if none is found
    BUT: first check if a unique hit can be found by the string alone (if it is not empty)
    """

    match = re.match('(.*) \((\d+)\)', value)
    if match:
        print("MATCH: ", match)
        idgloss = match.group(1)
        pk = match.group(2)
        print("INFO: ", idgloss, pk)

        target = Morpheme.objects.get(pk=int(pk))
        print("TARGET: ", target)
        return target
    elif value != '':
        idgloss = value
        target = Morpheme.objects.get(idgloss=idgloss)
        return target
    else:
        return None


def update_definition(request, gloss, field, value):
    """Update one of the definition fields"""

    newvalue = ''
    (what, defid) = field.split('_')
    try:
        defn = Definition.objects.get(id=defid)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Bad Definition ID '%s'" % defid, {'content-type': 'text/plain'})

    if not defn.gloss == gloss:
        return HttpResponseBadRequest("Definition doesn't match gloss", {'content-type': 'text/plain'})
    
    if what == 'definitiondelete':
        defn.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editdef')
    
    if what == 'definition':
        # update the definition
        defn.text = value
        defn.save()
        newvalue = defn.text
    elif what == 'definitioncount':
        defn.count = int(value)
        defn.save()
        newvalue = defn.count
    elif what == 'definitionpub':
        
        if request.user.has_perm('dictionary.can_publish'):
            defn.published = value in ['Yes', 'yes', 'ja', 'Ja', '是', 'true', 'True', True, 1]
            defn.save()
        
        if defn.published:
            newvalue = 'Yes'
        else:
            newvalue = 'No'
    elif what == 'definitionrole':
        defn.role = FieldChoice.objects.get(field='NoteType', machine_value=int(value))
        defn.save()
        newvalue = defn.role.name

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def update_other_media(gloss,field,value):

    action_or_fieldname, other_media_id = field.split('_')

    other_media = None
    try:
        other_media = OtherMedia.objects.get(id=other_media_id)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Bad OtherMedia ID '%s'" % other_media, {'content-type': 'text/plain'})

    if not other_media.parent_gloss == gloss:
        return HttpResponseBadRequest("OtherMedia doesn't match gloss", {'content-type': 'text/plain'})

    if action_or_fieldname == 'other-media-delete':
        other_media.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.pk})+'?editothermedia')

    elif action_or_fieldname == 'other-media-type':
        # value is the (str) machine value of the Other Media Type from the choice list in the template
        other_media_type = FieldChoice.objects.filter(field='OtherMediaType', machine_value=int(value))
        other_media.type = other_media_type
        value = other_media_type.name

    elif action_or_fieldname == 'other-media-alternative-gloss':
        other_media.alternative_gloss = value

    other_media.save()

    return HttpResponse(str(value), {'content-type': 'text/plain'})

def add_relation(request):
    """Add a new relation instance"""
    
    if not request.method == "POST":
        return HttpResponseForbidden("Add relation method must be POST")

    form = RelationForm(request.POST)

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    role = form.cleaned_data['role']
    sourceid = form.cleaned_data['sourceid']
    targetid = form.cleaned_data['targetid']

    try:
        source = Gloss.objects.get(pk=int(sourceid))
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Source gloss not found.", {'content-type': 'text/plain'})

    try:
        target = Gloss.objects.get(id=int(targetid))
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Target gloss not found.", {'content-type': 'text/plain'})

    rel = Relation(source=source, target=target, role=role)
    rel.save()

    # Also add the reverse relation
    reverse_relation = Relation(source=target, target=source, role=Relation.get_reverse_role(role))
    reverse_relation.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': source.id})+'?editrel')


@permission_required('dictionary.change_gloss')
def variants_of_gloss(request):

    if not request.method == "POST":
        return HttpResponseForbidden("Variants of gloss method must be POST")

    form = VariantsForm(request.POST)

    if not form.is_valid():
        return HttpResponseRedirect('/')

    role = 'variant'
    sourceid = form.cleaned_data['sourceid']
    targetid = form.cleaned_data['targetid']

    try:
        source = Gloss.objects.get(pk=int(sourceid))
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Source gloss not found.", {'content-type': 'text/plain'})

    try:
        target = Gloss.objects.get(id=int(targetid))
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Target gloss not found.", {'content-type': 'text/plain'})

    rel = Relation(source=source, target=target, role=role)
    rel.save()

    return HttpResponse(json.dumps(rel), content_type="application/json")


def add_relationtoforeignsign(request):
    """Add a new relationtoforeignsign instance"""
    
    if not request.method == "POST":
        return HttpResponseForbidden("Add relation to foreign sign method must be POST")

    form = RelationToForeignSignForm(request.POST)

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    sourceid = form.cleaned_data['sourceid']
    loan = form.cleaned_data['loan']
    other_lang = form.cleaned_data['other_lang']
    other_lang_gloss = form.cleaned_data['other_lang_gloss']

    try:
        gloss = Gloss.objects.get(pk=int(sourceid))
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Source gloss not found.", {'content-type': 'text/plain'})

    rel = RelationToForeignSign(gloss=gloss,loan=loan,other_lang=other_lang,other_lang_gloss=other_lang_gloss)
    rel.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editrelforeign')


def add_definition(request, glossid):
    """Add a new definition for this gloss"""

    thisgloss = get_object_or_404(Gloss, id=glossid)
    
    if not request.method == "POST":
        return HttpResponseForbidden("Add definition method must be POST")

    form = DefinitionForm(request.POST)
        
    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    published = form.cleaned_data['published']
    count = form.cleaned_data['count']
    role = FieldChoice.objects.get(field='NoteType', machine_value=int(form.cleaned_data['note']))
    text = form.cleaned_data['text']

    defn = Definition(gloss=thisgloss, count=count, role=role, text=text, published=published)
    defn.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editdef')


def add_morphology_definition(request):
    if not request.method == "POST":
        return HttpResponseForbidden("Add morphology definition method must be POST")

    form = GlossMorphologyForm(request.POST)

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    parent_gloss = form.cleaned_data['parent_gloss_id']
    role_id = form.cleaned_data['role']
    morpheme_id = form.cleaned_data['morpheme_id']
    # This is now a gloss ID
    morpheme = Gloss.objects.get(id=morpheme_id)

    thisgloss = get_object_or_404(Gloss, pk=parent_gloss)
    role = get_object_or_404(FieldChoice, pk=role_id, field='MorphologyType')

    # create definition, default to not published
    morphdef = MorphologyDefinition(parent_gloss=thisgloss, role=role, morpheme=morpheme)
    morphdef.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')


# Add a 'morpheme' (according to the Morpheme model)
def add_morpheme_definition(request, glossid):

    if not request.method == "POST":
        return HttpResponseForbidden("Add morpheme definition method must be POST")

    form = GlossMorphemeForm(request.POST)

    # Get the glossid at any rate
    thisgloss = get_object_or_404(Gloss, pk=glossid)

    # check availability of morpheme before continuing
    if form.data['morph_id'] == "":
        # The user has not selected a morpheme
        # Check if there are morphemes available for this dataset
        if 'datasetid' in request.session.keys():
            datasetid = request.session['datasetid']
            dataset_id = Dataset.objects.get(name=datasetid)
            count_morphemes_in_dataset = Morpheme.objects.filter(lemma__dataset=dataset_id).count()
            if count_morphemes_in_dataset < 1:
                messages.add_message(request, messages.INFO, _('Edit Simultaneuous Morphology: The dataset of this gloss has no morphemes.'))
                return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

        messages.add_message(request, messages.INFO, _('Edit Simultaneuous Morphology: No morpheme selected.'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    morph_id = form.cleaned_data['morph_id'] ## This is a morpheme ID now

    try:
        morph = Morpheme.objects.get(id=morph_id)
    except ObjectDoesNotExist:

        # The user has tried to type in a name rather than select from the list.
        messages.add_message(request, messages.ERROR, _('Simultaneuous morphology: no morpheme found with identifier {}.'.format(morph_id)))

        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

    definition = SimultaneousMorphologyDefinition()
    definition.parent_gloss = thisgloss
    definition.morpheme = morph
    definition.role = form.cleaned_data['description']
    definition.save()
    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')


# Add a 'blend' (according to the Blend model)
def add_blend_definition(request, glossid):

    if not request.method == "POST":
        return HttpResponseForbidden("Add blend definition method must be POST")

    form = GlossBlendForm(request.POST)

    # Get the glossid at any rate
    thisgloss = get_object_or_404(Gloss, pk=glossid)

    # check availability of morpheme before continuing
    if form.data['blend_id'] == "":
        # The user has obviously not selected a morpheme
        # Desired action (Issue #199): nothing happens
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    blend_id = form.cleaned_data['blend_id'] # This is a gloss ID now
    blend = Gloss.objects.get(id=blend_id)

    if blend != None:
        definition = BlendMorphology()
        definition.parent_gloss = thisgloss
        definition.glosses = blend
        definition.role = form.cleaned_data['role']
        definition.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')


def update_handshape(request, handshapeid):

    if not request.method == "POST":
        return HttpResponseForbidden("Update handshape method must be POST")

    hs = get_object_or_404(Handshape, machine_value=handshapeid)
    hs.save() # This updates the lastUpdated field

    get_field = request.POST.get('id', '')
    value = request.POST.get('value', '')
    original_value = ''
    value = str(value)
    newPattern = ''

    field = get_field

    if len(value) == 0:
        value = ' '

    elif value[0] == '_':
        value = value[1:]

    values = request.POST.getlist('value[]')  # in case we need multiple values

    if value == '':
        hs.__setattr__(field, None)
        hs.save()
        newvalue = ''
    elif isinstance(Handshape._meta.get_field(field), FieldChoiceForeignKey):
        # this is needed because the new value is a machine value, not an id
        field_choice_category = Handshape._meta.get_field(field).field_choice_category
        original_value = getattr(hs, field)
        field_choice = FieldChoice.objects.get(field=field_choice_category, machine_value=int(value))
        setattr(hs, field, field_choice)
        hs.save()
        newvalue = field_choice.name
    else:
        original_value = getattr(hs, field)
        hs.__setattr__(field, value)
        hs.save()
        newvalue = value

        if not isinstance(value, bool):
            # field is a choice list and we need to get the translated human value
            newvalue = value.name if isinstance(value, FieldChoice) else value

    # Finger selections are saved as both boolean values per finger and as patterns that include the fingers
    # The patterns, such as TIM, are stored as choice lists in FieldChoice.
    # This is done automatically for display and sorting purposes.
    # A user always modifies the selected fingers data per finger.

    if field in ['fsT', 'fsI', 'fsM', 'fsR', 'fsP']:
        category_value = 'fingerSelection1'

        if newvalue != original_value:
            hs_mod = get_object_or_404(Handshape, machine_value=handshapeid)
            newPattern = hs_mod.get_fingerSelection_display()
            object_fingSelection = FieldChoice.objects.filter(field='FingerSelection', name__iexact=newPattern)
            if object_fingSelection:
                mv = object_fingSelection[0].machine_value
                hs_mod.__setattr__('hsFingSel', mv)
                hs_mod.save()
            else:
                print("finger selection not found: ", newPattern)
    elif field in ['fs2T', 'fs2I', 'fs2M', 'fs2R', 'fs2P']:
        category_value = 'fingerSelection2'

        if newvalue != original_value:
            hs_mod = get_object_or_404(Handshape, machine_value=handshapeid)
            newPattern = hs_mod.get_fingerSelection2_display()
            object_fingSelection = FieldChoice.objects.filter(field='FingerSelection',
                                                              name__iexact=newPattern)
            if object_fingSelection:
                mv = object_fingSelection[0].machine_value
                hs_mod.__setattr__('hsFingSel2', mv)
                hs_mod.save()
            else:
                print("finger selection not found: ", newPattern)
    elif field in ['ufT', 'ufI', 'ufM', 'ufR', 'ufP']:
        category_value = 'unselectedFingers'

        if newvalue != original_value:
            hs_mod = get_object_or_404(Handshape, machine_value=handshapeid)
            newPattern = hs_mod.get_unselectedFingers_display()
            object_fingSelection = FieldChoice.objects.filter(field='FingerSelection',
                                                              name__iexact=newPattern)
            if object_fingSelection:
                mv = object_fingSelection[0].machine_value
                hs_mod.__setattr__('hsFingUnsel', mv)
                hs_mod.save()
    else:
        category_value = 'fieldChoice'

    return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' + str(category_value) + '\t' + str(newPattern), {'content-type': 'text/plain'})

def add_othermedia(request):

    if not request.method == "POST":
        return HttpResponseForbidden("Add other media method must be POST")

    form = OtherMediaForm(request.POST,request.FILES)

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    morpheme__or_gloss = Gloss.objects.get(id=request.POST['gloss'])
    if morpheme__or_gloss.is_morpheme():
        reverse_url = 'dictionary:admin_morpheme_view'
    else:
        reverse_url = 'dictionary:admin_gloss_view'

    import os

    othermedia_exists = os.path.exists(OTHER_MEDIA_DIRECTORY)
    if not othermedia_exists:
        messages.add_message(request, messages.ERROR, _("Upload other media failed: The othermedia folder is missing."))
        return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']}))

    # Create the folder if needed
    goal_directory = os.path.join(OTHER_MEDIA_DIRECTORY,request.POST['gloss'])

    filename = request.FILES['file'].name
    filetype = request.FILES['file'].content_type

    type_machine_value = request.POST['type']
    try:
        othermediatype = FieldChoice.objects.get(field=FieldChoice.OTHERMEDIATYPE,
                                                 machine_value=type_machine_value)
    except ObjectDoesNotExist:
        # if something goes wrong just set it to empty
        othermediatype = FieldChoice.objects.get(field=FieldChoice.OTHERMEDIATYPE,
                                                 machine_value=0)

    if not filetype:
        # unrecognised file type has been uploaded
        messages.add_message(request, messages.ERROR, _("Upload other media failed: The file has an unknown type."))
        return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']}))

    norm_filename = os.path.normpath(filename)
    split_norm_filename = norm_filename.split('.')

    if len(split_norm_filename) == 1:
        # file has no extension
        messages.add_message(request, messages.ERROR, _("Upload other media failed: The file has no extension."))
        return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']}))

    extension = split_norm_filename[-1]
    filename_base = '.'.join(split_norm_filename[:-1])

    if filetype == 'video/mp4':
        # handle 'm4v' extension
        extension = 'mp4'

    if not os.path.isdir(goal_directory):
        os.mkdir(goal_directory)

    # use '+' to concatinate
    # if the source filename is right to left, the extension is at the end
    destination_filename = filename_base + '.' + extension
    goal_path = os.path.join(goal_directory, destination_filename)

    # to accommodate large files, the Other Media data is first stored in the database
    # if something goes wrong this object is deleted again
    #Save the database record
    parent_gloss = Gloss.objects.filter(pk=request.POST['gloss'])[0]
    other_media_path = request.POST['gloss']+'/'+destination_filename
    newothermedia = OtherMedia(path=other_media_path,
                               alternative_gloss=request.POST['alternative_gloss'],
                               type=othermediatype,
                               parent_gloss=parent_gloss)
    newothermedia.save()

    # the above creates the new OtherMedia object
    # the video has not been saved yet

    # create the destination file
    try:
        if os.path.exists(goal_path):
            raise OSError
        f = open(goal_path, 'wb+')
        filename_plus_extension = destination_filename
    except (UnicodeEncodeError, IOError, OSError):
        import urllib.parse
        quoted_filename = urllib.parse.quote(filename_base, safe='')
        filename_plus_extension = quoted_filename + '.' + extension
        goal_location_str = os.path.join(goal_directory, filename_plus_extension)
        # we need to use a quoted filename instead, update the other media object
        other_media_path = request.POST['gloss'] + '/' + filename_plus_extension
        newothermedia.path = other_media_path
        newothermedia.save()
        try:
            if os.path.exists(goal_location_str):
                raise OSError
            f = open(goal_location_str, 'wb+')
        except (UnicodeEncodeError, IOError, OSError):
            # something went wrong with uploading, delete the object
            newothermedia.delete()
            messages.add_message(request, messages.ERROR,
                        _("The other media file could not be uploaded. Please use a different filename."))
            return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']}))

    destination = File(f)
    # Save the file
    for chunk in request.FILES['file'].chunks():
        destination.write(chunk)
    destination.close()

    destination_location = os.path.join(goal_directory,filename_plus_extension)

    import magic
    magic_file_type = magic.from_buffer(open(destination_location,"rb").read(2040), mime=True)

    if not magic_file_type:
        # unrecognised file type has been uploaded
        os.remove(destination_location)
        # something went wrong with uploading, delete the object
        newothermedia.delete()
        messages.add_message(request, messages.ERROR, _("Upload other media failed: The file has an unknown type."))
        return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']}))
    # the code below converts the file to an mp4 file if it is currently another type of video
    if magic_file_type == 'video/quicktime':
        # convert using ffmpeg
        temp_destination_location = destination_location + ".mov"
        os.rename(destination_location, temp_destination_location)

        from signbank.video.convertvideo import convert_video
        # convert the quicktime video to h264
        success = convert_video(temp_destination_location, destination_location)

        if success:
            # the destination filename already has the extension mp4
            os.remove(temp_destination_location)
        else:
            # problems converting a quicktime media to h264
            os.remove(temp_destination_location)
            os.remove(destination_location)
            # something went wrong with uploading, delete the object
            newothermedia.delete()
            messages.add_message(request, messages.ERROR,
                                 _("Upload other media failed: The Quicktime file could not be converted to H264."))
            return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']}))
    elif magic_file_type != 'video/mp4':
        # convert using ffmpeg
        temp_destination_location = destination_location + ".mov"
        os.rename(destination_location, temp_destination_location)

        from signbank.video.convertvideo import convert_video
        # convert the video to h264
        success = convert_video(temp_destination_location, destination_location)

        if success:
            # the destination filename already has the extension mp4
            os.remove(temp_destination_location)
        else:
            # problems converting a quicktime media to h264
            os.remove(temp_destination_location)
            os.remove(destination_location)
            # something went wrong with uploading, delete the object
            newothermedia.delete()
            messages.add_message(request, messages.ERROR,
                                 _("Upload other media failed: The file could not be converted to H264."))
            return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']}))

    if filetype.split('/')[0] != magic_file_type.split('/')[0]:
        # the uploaded file extension does not match its type
        os.remove(destination_location)
        # something went wrong with uploading, delete the object
        newothermedia.delete()
        messages.add_message(request, messages.ERROR, _("Upload other media failed: The file extension does not match its type."))
        return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']}))

    return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']})+'?editothermedia')


def update_morphology_definition(gloss, field, value):
    """Update one of the relations for this gloss"""

    (what, morph_def_id) = field.split('_')
    what = what.replace('-','_')

    try:
        morph_def = MorphologyDefinition.objects.get(id=morph_def_id)
    except:
        return HttpResponseBadRequest("Bad Morphology Definition ID '%s'" % morph_def_id, {'content-type': 'text/plain'})

    if not morph_def.parent_gloss == gloss:
        return HttpResponseBadRequest("Morphology Definition doesn't match gloss", {'content-type': 'text/plain'})

    if what == 'morphology_definition_delete':
        print("DELETE morphology definition: ", morph_def)
        morph_def.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editmorphdef')
    elif what == 'morphology_definition_role':
        morph_def.role = value
        morph_def.save()

        choice_list = FieldChoice.objects.filter(field='MorphologyType')
        newvalue = machine_value_to_translated_human_value(value, choice_list)


    elif what == 'morphology_definition_morpheme':

        morpheme = gloss_from_identifier(value)
        if morpheme:
            morph_def.morpheme = morpheme
            morph_def.save()
            newvalue = str(morpheme)
        else:
            return HttpResponseBadRequest("Badly formed gloss identifier '%s'" % value, {'content-type': 'text/plain'})
    else:

        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})


def add_morpheme(request):
    """Create a new morpheme and redirect to the edit view"""
    if request.method != "POST":
        return HttpResponseRedirect(reverse('dictionary:admin_morpheme_list'))
    dataset = None
    if 'dataset' in request.POST and request.POST['dataset'] is not None:
        dataset = Dataset.objects.get(pk=request.POST['dataset'])
        selected_datasets = Dataset.objects.filter(pk=request.POST['dataset'])
    else:
        selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    if len(selected_datasets) == 1:
        last_used_dataset = selected_datasets[0].acronym
    elif 'last_used_dataset' in request.session.keys():
        last_used_dataset = request.session['last_used_dataset']
    else:
        last_used_dataset = None

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    form = MorphemeCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=last_used_dataset)

    # Lemma handling
    lemmaidgloss = None
    lemma_form = None
    if request.POST['select_or_new_lemma'] == 'new':
        lemma_form = LemmaCreateForm(request.POST, languages=dataset_languages, user=request.user)
    else:
        try:
            lemmaidgloss_id = request.POST['idgloss']
            lemmaidgloss = LemmaIdgloss.objects.get(id=lemmaidgloss_id)
        except:
            messages.add_message(request, messages.ERROR,
                                 _("The given Lemma Idgloss ID is unknown."))
            return render(request, 'dictionary/add_morpheme.html', {'add_morpheme_form': form})

    # Check for 'change_dataset' permission
    if dataset and ('change_dataset' not in get_user_perms(request.user, dataset)) \
            and ('change_dataset' not in get_group_perms(request.user, dataset))\
            and not request.user.is_staff:
        messages.add_message(request, messages.ERROR, _("You are not authorized to change the selected dataset."))
        return render(request, 'dictionary/add_morpheme.html', {'add_morpheme_form': form})
    elif not dataset:
        # Dataset is empty, this is an error
        messages.add_message(request, messages.ERROR, _("Please provide a dataset."))
        return render(request, 'dictionary/add_morpheme.html', {'add_morpheme_form': form})

    # if we get to here a dataset has been chosen for the new gloss

    for item, value in request.POST.items():
        if item.startswith(form.morpheme_create_field_prefix):
            language_code_2char = item[len(form.morpheme_create_field_prefix):]
            language = Language.objects.get(language_code_2char=language_code_2char)
            morphemes_for_this_language_and_annotation_idgloss = Morpheme.objects.filter(
                annotationidglosstranslation__language=language,
                annotationidglosstranslation__text__exact=value)
            if len(morphemes_for_this_language_and_annotation_idgloss) != 0:
                translated_message = _('Annotation ID Gloss not unique.')
                return render(request, 'dictionary/warning.html',
                       {'warning': translated_message,
                        'dataset_languages': dataset_languages,
                        'selected_datasets': selected_datasets,
                        'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

    if form.is_valid() and (lemmaidgloss or lemma_form.is_valid()):
        try:
            morpheme = form.save()
            morpheme.creationDate = datetime.now()
            morpheme.creator.add(request.user)
            if lemma_form:
                lemmaidgloss = lemma_form.save()
            morpheme.lemma = lemmaidgloss
            morpheme.save()
        except ValidationError as ve:
            messages.add_message(request, messages.ERROR, ve.message)
            return render(request, 'dictionary/add_morpheme.html', {'add_morpheme_form': form,
                                                 'dataset_languages': dataset_languages,
                                                 'selected_datasets': get_selected_datasets_for_user(request.user),
                                                 'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        if not ('search_results' in request.session.keys()):
            request.session['search_results'] = None
        if not ('search_type' in request.session.keys()):
            request.session['search_type'] = None
        request.session['last_used_dataset'] = dataset.acronym

        return HttpResponseRedirect(reverse('dictionary:admin_morpheme_view', kwargs={'pk': morpheme.id})+'?edit')
    else:
        return render(request,'dictionary/add_morpheme.html', {'add_morpheme_form': form,
                                                                'dataset_languages': dataset_languages,
                                                                'selected_datasets': get_selected_datasets_for_user(request.user),
                                                               'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


def update_morpheme(request, morphemeid):
    """View to update a morpheme model from the jeditable jquery form
    We are sent one field and value at a time, return the new value
    once we've updated it."""
    if not request.user.has_perm('dictionary.change_morpheme'):
        return HttpResponseForbidden("Morpheme Update Not Allowed")

    if not request.method == "POST":
        return HttpResponseForbidden("Update morpheme method must be POST")

    morpheme = get_object_or_404(Morpheme, id=morphemeid)

    field = request.POST.get('id', '')
    value = request.POST.get('value', '')
    original_value = ''  # will in most cases be set later, but can't be empty in case it is not set
    category_value = ''
    lemma_gloss_group = False

    if len(value) == 0:
        value = ' '

    elif value[0] == '_':
        value = value[1:]

    values = request.POST.getlist('value[]')  # in case we need multiple values

    # validate
    # field is a valid field
    # value is a valid value for field

    if field == 'deletemorpheme':
        if value == 'confirmed':
            # delete the morpheme and redirect back to morpheme list
            morpheme.delete()
            return HttpResponseRedirect(reverse('dictionary:admin_morpheme_list'))

    if field.startswith('definition'):

        return update_definition(request, morpheme, field, value)

    elif field.startswith('keyword'):

        return update_keywords(morpheme, field, value)

    elif field.startswith('relationforeign'):

        return update_relationtoforeignsign(morpheme, field, value)

    elif field.startswith('relation'):

        return update_relation(morpheme, field, value)

    elif field.startswith('morphology-definition'):

        return update_morphology_definition(morpheme, field, value)

    elif field.startswith('other-media'):

        return update_other_media(morpheme, field, value)

    elif field == 'signlanguage':
        # expecting possibly multiple values

        return update_signlanguage(morpheme, field, values)

    elif field == 'dialect':
        # expecting possibly multiple values

        return update_dialect(morpheme, field, values)

    elif field == 'semanticfield':
        # expecting possibly multiple values

        return update_semanticfield(request, morpheme, field, values)

    elif field == 'derivationhistory':
        # expecting possibly multiple values

        return update_derivationhistory(request, morpheme, field, values)

    elif field == 'dataset':
        # this has been hidden
        original_value = getattr(morpheme,field)

        # in case somebody tries an empty or non-existent dataset name
        try:
            ds = Dataset.objects.get(name=value)
        except:
            return HttpResponse(str(original_value), {'content-type': 'text/plain'})

        if ds.is_public:
            newvalue = value
            setattr(morpheme, field, ds)
            morpheme.save()

            request.session['last_used_dataset'] = ds.acronym

            return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

        import guardian
        if ds in guardian.shortcuts.get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                         Dataset, any_perm=True):
            newvalue = value
            setattr(morpheme, field, ds)
            morpheme.save()

            request.session['last_used_dataset'] = ds.acronym

            return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

        print('no permission for chosen dataset')
        newvalue = original_value
        return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

    elif field == "sn":
        # sign number must be unique, return error message if this SN is
        # already taken

        if value == '':
            morpheme.__setattr__(field, None)
            morpheme.save()
            newvalue = ''
        else:
            try:
                value = int(value)
            except:
                return HttpResponseBadRequest("SN value must be integer", {'content-type': 'text/plain'})

            existing_morpheme = Morpheme.objects.filter(sn__exact=value)
            if existing_morpheme.count() > 0:
                g = existing_morpheme[0].idgloss
                return HttpResponseBadRequest("SN value already taken for morpheme %s" % g,
                                              {'content-type': 'text/plain'})
            else:
                morpheme.sn = value
                morpheme.save()
                newvalue = value


    elif field == 'inWeb':
        # only modify if we have publish permission
        if request.user.has_perm('dictionary.can_publish'):
            morpheme.inWeb = (value in ['Yes', 'yes', 'ja', 'Ja', '是', 'true', 'True', True, 1])
            morpheme.save()

        if morpheme.inWeb:
            newvalue = 'Yes'
        else:
            newvalue = 'No'

    elif field.startswith('annotation_idgloss'):

        return update_annotation_idgloss(morpheme, field, value)

    elif field.startswith('lemmaidgloss'):
        # Set new lemmaidgloss for this gloss
        # First check whether the morpheme dataset is the same as the lemma dataset
        try:
            dataset = morpheme.dataset
            lemma = LemmaIdgloss.objects.get(pk=value)
            if dataset is None or dataset == lemma.dataset:
                morpheme.lemma = lemma
                morpheme.save()
            else:
                messages.add_message(messages.ERROR, _("The dataset of the morpheme is not the same as that of the lemma."))
        except ObjectDoesNotExist:
            messages.add_message(messages.ERROR, _("The specified lemma does not exist."))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    else:
        if field not in [f.name for f in Morpheme._meta.get_fields()]:
            return HttpResponseBadRequest("Unknown field", {'content-type': 'text/plain'})

        whitespace = tuple(' \n\r\t')
        if value.startswith(whitespace) or value.endswith(whitespace):
            value = value.strip()
        original_value = getattr(morpheme,field)

        if field == 'idgloss' and value == '':
            # don't allow user to set Lemma ID Gloss to empty
            return HttpResponse(str(original_value), {'content-type': 'text/plain'})
        # special cases
        # - Foreign Key fields (Language, Dialect)
        # - keywords
        # - videos
        # - tags

        # Translate the value if a boolean
        if isinstance(morpheme._meta.get_field(field), BooleanField):
            newvalue = value
            value = (value in ['Yes', 'yes', 'ja', 'Ja', '是', 'true', 'True', True, 1])

        # special value of 'notset' or -1 means remove the value
        fieldnames = FIELDS['main'] + settings.MORPHEME_DISPLAY_FIELDS + FIELDS['semantics'] + ['inWeb', 'isNew', 'mrpType']

        if field in FIELDS['phonology']:
            # this is used as part of the feedback to the interface, to alert the user to refresh the display
            category_value = 'phonology'

        fieldchoiceforeignkey_fields = [f.name for f in Morpheme._meta.fields
                                        if f.name in fieldnames
                                        and isinstance(Morpheme._meta.get_field(f.name), FieldChoiceForeignKey)]
        fields_empty_null = [f.name for f in Morpheme._meta.fields
                             if f.name in fieldnames and f.null and f.name not in fieldchoiceforeignkey_fields]

        char_fields_not_null = [f.name for f in Morpheme._meta.fields
                                if f.name in fieldnames and f.name not in fieldchoiceforeignkey_fields and not f.null]

        # The following code relies on the order of if else testing
        # The updates ignore Placeholder empty fields of '-' and '------'
        # The Placeholders are needed in the template Edit view so the user can "see" something to edit
        if field in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
            gloss_field = Morpheme._meta.get_field(field)
            try:
                handshape = Handshape.objects.get(machine_value=value)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                print('Update handshape no unique machine value found: ', gloss_field.name, value)
                print('Setting to machine value 0')
                handshape = Handshape.objects.get(machine_value=0)
            morpheme.__setattr__(field, handshape)
            morpheme.save()
            newvalue = handshape.name
        elif field in fieldchoiceforeignkey_fields:
            gloss_field = Morpheme._meta.get_field(field)
            try:
                fieldchoice = FieldChoice.objects.get(field=gloss_field.field_choice_category, machine_value=value)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                print('Update field choice no unique machine value found: ', gloss_field.name,
                      gloss_field.field_choice_category, value)
                print('Setting to machine value 0')
                fieldchoice = FieldChoice.objects.get(field=gloss_field.field_choice_category, machine_value=0)
            morpheme.__setattr__(field, fieldchoice)
            morpheme.save()
            newvalue = fieldchoice.name

        elif value in ['notset',''] and field not in char_fields_not_null:
            morpheme.__setattr__(field, None)
            morpheme.save()
            newvalue = ''

        # Regular field updating
        else:
            morpheme.__setattr__(field, value)
            morpheme.save()

            # If the value is not a Boolean, return the new value
            if not isinstance(value, bool):
                # field is a choice list and we need to get the translated human value
                newvalue = newvalue.name if isinstance(value, FieldChoice) else value

    return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' + str(value) + str('\t') + str(category_value) + str('\t') + str(lemma_gloss_group), {'content-type': 'text/plain'})


def update_morpheme_definition(gloss, field, value):
    """Update the morpheme definition for this gloss"""

    newvalue = value
    original_value = ''
    category_value = 'simultaneous_morphology'
    (what, morph_def_id) = field.split('_')
    what = what.replace('-','_')

    if what == 'morpheme_definition_delete':
        definition = SimultaneousMorphologyDefinition.objects.get(id=morph_def_id)
        definition.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editmorphdef')
    elif what == 'morpheme_definition_meaning':
        definition = SimultaneousMorphologyDefinition.objects.get(id=morph_def_id)
        original_value = getattr(definition, 'role')
        definition.__setattr__('role', value)
        definition.save()
        return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' +  str(value) + str('\t') + str(category_value), {'content-type': 'text/plain'})
    else:
        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})


def update_blend_definition(gloss, field, value):
    """Update the morpheme definition for this gloss"""

    newvalue = value
    original_value = ''
    category_value = 'blend_morphology'
    (what, blend_id) = field.split('_')
    what = what.replace('-','_')

    if what == 'blend_definition_delete':
        definition = BlendMorphology.objects.get(id=blend_id)
        definition.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editmorphdef')
    elif what == 'blend_definition_role':
        definition = BlendMorphology.objects.get(id=blend_id)
        original_value = getattr(definition, 'role')
        definition.__setattr__('role', value)
        definition.save()
        return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' +  str(value) + str('\t') + str(category_value), {'content-type': 'text/plain'})
    else:
        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})


@permission_required('dictionary.change_gloss')
def add_tag(request, glossid):
    """View to add a tag to a gloss"""

    # default response
    response = HttpResponse('invalid', {'content-type': 'text/plain'})

    if not request.method == "POST":
        return HttpResponseForbidden("Add tag method must be POST")

    thisgloss = get_object_or_404(Gloss, id=glossid)
    tags_label = 'Tags'
    form = TagUpdateForm(request.POST)

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    tag = form.cleaned_data['tag']

    if form.cleaned_data['delete']:
        old_tags_string = tag

        # get the relevant TaggedItem
        ti = get_object_or_404(TaggedItem, object_id=thisgloss.id, tag__name=tag)
        ti.delete()
        new_tags_string = ''

        revision = GlossRevision(old_value=old_tags_string, new_value=new_tags_string, field_name=tags_label,
                                 gloss=thisgloss, user=request.user, time=datetime.now(tz=get_current_timezone()))
        revision.save()
        response = HttpResponse('deleted', {'content-type': 'text/plain'})
    else:
        old_tags_string = ''

        # we need to wrap the tag name in quotes since it might contain spaces
        Tag.objects.add_tag(thisgloss, '"%s"' % tag)
        new_tags_string = tag
        revision = GlossRevision(old_value=old_tags_string, new_value=new_tags_string, field_name=tags_label,
                                 gloss=thisgloss, user=request.user, time=datetime.now(tz=get_current_timezone()))
        revision.save()
        # response is new HTML for the tag list and form
        response = render(request,'dictionary/glosstags.html',
                                      {'gloss': thisgloss,
                                       'tagform': TagUpdateForm()})
            
    return response


def add_morphemetag(request, morphemeid):
    """View to add a tag to a morpheme"""

    # default response
    response = HttpResponse('invalid', {'content-type': 'text/plain'})

    if not request.method == "POST":
        return HttpResponseForbidden("Add morpheme tag method must be POST")

    thismorpheme = get_object_or_404(Morpheme, id=morphemeid)

    form = TagUpdateForm(request.POST)

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    tag = form.cleaned_data['tag']

    if form.cleaned_data['delete']:
        # get the relevant TaggedItem
        ti = get_object_or_404(TaggedItem, object_id=thismorpheme.id, tag__name=tag)
        ti.delete()
        response = HttpResponse('deleted', {'content-type': 'text/plain'})
    else:
        # we need to wrap the tag name in quotes since it might contain spaces
        Tag.objects.add_tag(thismorpheme, '"%s"' % tag)
        # response is new HTML for the tag list and form
        response = render(request,'dictionary/morphemetags.html',
                                      {'morpheme': thismorpheme,
                                       'tagform': TagUpdateForm()})
    return response

def change_dataset_selection(request):
    """View to change dataset selection"""

    if not request.method == "POST":
        return HttpResponseForbidden("Change dataset selection method must be POST")

    dataset_prefix = 'dataset_'

    if request.user.is_authenticated:
        selected_dataset_acronyms = []
        for attribute in request.POST:
            if attribute[:len(dataset_prefix)] == dataset_prefix:
                dataset_name = attribute[len(dataset_prefix):]
                selected_dataset_acronyms.append(dataset_name)

        if selected_dataset_acronyms:
            # check that the selected datasets exist
            for dataset_name in selected_dataset_acronyms:
                try:
                    dataset = Dataset.objects.get(acronym=dataset_name)
                except ObjectDoesNotExist:
                    print('Exception updating selected datasets, dataset acronym does not exist: ', dataset_name)
                    return HttpResponseRedirect(reverse('admin_dataset_select'))

            user_profile = UserProfile.objects.get(user=request.user)
            user_profile.selected_datasets.clear()
            for dataset_name in selected_dataset_acronyms:
                try:
                    dataset = Dataset.objects.get(acronym=dataset_name)
                    user_profile.selected_datasets.add(dataset)
                except (ObjectDoesNotExist, KeyError, TransactionManagementError, DatabaseError, IntegrityError):
                    print('exception to updating selected datasets')
                    pass
            user_profile.save()
    else:
        # clear old selection
        selected_dataset_acronyms = []
        for attribute in request.POST:
            if attribute[:len(dataset_prefix)] == dataset_prefix:
                dataset_name = attribute[len(dataset_prefix):]
                selected_dataset_acronyms.append(dataset_name)
        new_selection = []
        successful = True
        for dataset_name in selected_dataset_acronyms:
            try:
                dataset = Dataset.objects.get(acronym=dataset_name)
                new_selection.append(dataset.acronym)
            except ObjectDoesNotExist:
                print('exception to updating selected datasets anonymous user')
                successful = False
                pass
        if successful:
            request.session['selected_datasets'] = new_selection

    # check whether the last used dataset is still in the selected datasets
    if 'last_used_dataset' in request.session.keys():
        if selected_dataset_acronyms and request.session['last_used_dataset'] not in selected_dataset_acronyms:
            request.session['last_used_dataset'] = selected_dataset_acronyms[0]
    else:
        # set the last_used_dataset?
        pass
    return HttpResponseRedirect(reverse('admin_dataset_select'))


def update_dataset(request, datasetid):
    """View to update a dataset model from the jeditable jquery form
    We are sent one field and value at a time, return the new value
    once we've updated it."""

    if request.method == "POST":

        dataset = get_object_or_404(Dataset, id=datasetid)
        dataset.save() # This updates the lastUpdated field

        import guardian
        from django.contrib.auth.models import Group

        try:
            group_manager = Group.objects.get(name='Dataset_Manager')
        except:
            messages.add_message(request, messages.ERROR, _('No group Dataset_Manager found.'))
            return HttpResponseForbidden("Dataset Update Not Allowed")

        groups_of_user = request.user.groups.all()
        if not group_manager in groups_of_user:
            messages.add_message(request, messages.ERROR,
                                 _('You must be in group Dataset Manager to modify dataset details.'))
            return HttpResponseForbidden("Dataset Update Not Allowed")

        user_change_datasets = guardian.shortcuts.get_objects_for_user(request.user, 'change_dataset', Dataset, accept_global_perms=False)
        if not dataset in user_change_datasets:
            return HttpResponseForbidden("Dataset Update Not Allowed")

        field = request.POST.get('id', '')
        value = request.POST.get('value', '')
        original_value = ''

        if field == 'description':
            original_value = getattr(dataset,field)
            setattr(dataset, field, value)
            dataset.save()
            return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'copyright':
                original_value = getattr(dataset, field)
                setattr(dataset, field, value)
                dataset.save()
                return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'reference':
                original_value = getattr(dataset, field)
                setattr(dataset, field, value)
                dataset.save()
                return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'conditions_of_use':
                original_value = getattr(dataset, field)
                setattr(dataset, field, value)
                dataset.save()
                return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'acronym':
                original_value = getattr(dataset, field)
                setattr(dataset, field, value)
                dataset.save()
                return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'is_public':
                original_value = getattr(dataset, field)
                dataset.is_public = value == 'True'
                dataset.save()
                if dataset.is_public:
                    newvalue = True
                else:
                    newvalue = False
                return HttpResponse(str(original_value) + str('\t') + str(newvalue), {'content-type': 'text/plain'})
        elif field == 'add_owner':
            update_owner(dataset, field, value)
        elif field == 'default_language':
            original_value = getattr(dataset, field)
            # variable original_value is used for feedback to the interface
            if original_value:
                original_value = original_value.name
            else:
                original_value = '-'
            if value == '-':
                # this option is not offered by the interface, value must be one of the translation languages (not empty '-')
                # this code is here if we want to user to be able to "unset" the default language in the interface
                setattr(dataset, field, None)
                dataset.save()
            else:
                try:
                    new_default_language = Language.objects.get(name=value)
                    setattr(dataset, field, new_default_language)
                    dataset.save()
                except:
                    value = original_value
            return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        else:

            if not field in [f.name for f in Dataset._meta.get_fields()]:
                return HttpResponseBadRequest("Unknown field", {'content-type': 'text/plain'})

            # unknown if we need this code yet for the above fields
            whitespace = tuple(' \n\r\t')
            if value.startswith(whitespace) or value.endswith(whitespace):
                value = value.strip()
            original_value = getattr(dataset,field)

        #This is because you cannot concat none to a string in py3
        if original_value == None:
            original_value = ''

        # The machine_value (value) representation is also returned to accommodate Hyperlinks to Handshapes in gloss_edit.js
        return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})

    else:
        print('update dataset is not POST')
        return HttpResponseForbidden("Dataset Update Not Allowed")

def update_owner(dataset, field, values):
    # expecting possibly multiple values

    # The owners value is set to the current owners value
    owners_value = ", ".join([str(o.username) for o in dataset.owners.all()])
    current_owners = dataset.owners.all()
    current_owners_name = ''
    for co in current_owners:
        current_owners_name = co.name

    try:
        # dataset.owners.clear()
        for value in values:
            user = User.objects.get(username=value)
            # dataset.owners.add(user)
            print('add owner ', value, ' to dataset')
            if value != current_owners_name:
                print('clear owners field')
                # dataset.owners.clear()
                owners_value = ''
        # dataset.save()
        print('save dataset')
        new_owners_value = ", ".join([str(o.username) for o in dataset.owners.all()])
    except:
        return HttpResponseBadRequest("Unknown Language %s" % values, {'content-type': 'text/plain'})

    return HttpResponse(str(new_owners_value) + '\t' + str(owners_value), {'content-type': 'text/plain'})

def update_excluded_choices(request):
    selected_datasets = get_selected_datasets_for_user(request.user)

    managed_datasets = []
    change_dataset_permission = get_objects_for_user(request.user, 'change_dataset', Dataset)
    for dataset in selected_datasets:
        if dataset in change_dataset_permission:
            managed_datasets.append(dataset)

    excluded_choices = {dataset.acronym: [] for dataset in managed_datasets}

    field = request.POST.get('id', '')
    value = request.POST.get('value', '')
    print('update excluded choices: field, value: ', field, value)
    for key in request.POST.keys():

        if key == 'csrfmiddlewaretoken':
            continue
        try:
            dataset, choice_pk = key.split('|')
            category = None
        except:
            category, choice_pk = key.split('_color_')
            dataset = None

        if dataset:
            try:
                choice_pk = int(choice_pk)
                excluded_choices[dataset].append(choice_pk)
            except:
                print('dataset, field choice not possible: ', key, dataset, choice_pk)
        else:
            # category
            fco = FieldChoice.objects.get(pk=choice_pk)
            # fco.field_color =
            # print('category: ', category)

    #Now update all datasets but only if user manages the dataset
    for dataset_name, choice_pks in excluded_choices.items():
        dataset = Dataset.objects.get(acronym=dataset_name)
        excluded_objects = []
        # get the field choice objects corresponding to the pk's to exclude
        for fcpk in choice_pks:
            try:
                fco = FieldChoice.objects.get(pk=fcpk)
            except:
                # something went wrong
                print('Field choice pk not found: ', fcpk)
                continue
            excluded_objects.append(fco)
        # # replace the excluded field choices with the new field choices to exclude
        # dataset.exclude_choices.clear()
        # for eo in excluded_objects:
        #     dataset.exclude_choices.add(eo)

    return HttpResponseRedirect(reverse('admin_dataset_field_choices'))

def update_field_choice_color(request, category, fieldchoiceid):

    if request.method == "POST":
        if category == 'SemField':
            form = SemanticFieldColorForm(request.POST)
            thisfieldchoice = get_object_or_404(SemanticField, pk=fieldchoiceid)
        elif category == 'derivHist':
            form = DerivationHistoryColorForm(request.POST)
            thisfieldchoice = get_object_or_404(DerivationHistory, pk=fieldchoiceid)
        elif category == 'Handshape':
            form = HandshapeColorForm(request.POST)
            thisfieldchoice = get_object_or_404(Handshape, pk=fieldchoiceid)
        else:
            form = FieldChoiceColorForm(request.POST)
            thisfieldchoice = get_object_or_404(FieldChoice, pk=fieldchoiceid)

        if form.is_valid():

            new_color = form.cleaned_data['field_color']

            if new_color[0] == '#':
                new_color = new_color[1:]

            original_value = thisfieldchoice.field_color
            machine_value = str(thisfieldchoice.machine_value)
            thisfieldchoice.field_color = new_color
            thisfieldchoice.save()
            # category = thisfieldchoice.field

            return HttpResponse(category + '\t' + fieldchoiceid + '\t' + str(original_value) + '\t' + str(new_color) + '\t' + machine_value,
                                {'content-type': 'text/plain'})

    # If we get here the request method has apparently been changed to get instead of post, can this happen?
    raise Http404('Incorrect request')


def upload_metadata(request):
    if request.method == "POST":

        form = CSVMetadataForm(request.POST,request.FILES)

        if form.is_valid():

            new_metadata = request.FILES['file']

            # extension = '.'+new_metadata.name.split('.')[-1]
            # print('extension: ', extension)

            for key in request.POST.keys():
                if key == 'dataset_acronym':
                    dataset_acronym = request.POST['dataset_acronym']

            metafile_name = dataset_acronym + '_metadata.csv'

            if not os.path.isdir(WRITABLE_FOLDER + DATASET_METADATA_DIRECTORY):
                os.mkdir(WRITABLE_FOLDER + DATASET_METADATA_DIRECTORY, mode=0o755)

            goal_string = WRITABLE_FOLDER + DATASET_METADATA_DIRECTORY + '/' + metafile_name

            f_handle = open(goal_string, mode='wb+')

            for chunk in request.FILES['file'].chunks():
                f_handle.write(chunk)

            return HttpResponseRedirect(reverse('admin_dataset_manager'))

    raise Http404('Incorrect request')


def remove_eaf_files(request):
    if request.method != "POST":
        return

    # Process the request data
    selected_paths = []
    dataset_acronym = ''

    for key in request.POST.keys():
        if key == 'dataset_acronym':
            dataset_acronym = request.POST['dataset_acronym']
        if key.startswith('select_document:'):
            value = request.POST[key]
            selected_paths.append(value)

    if dataset_acronym == '':
        messages.add_message(request, messages.ERROR, _('No acronym for dataset.'))
        return HttpResponseRedirect(reverse('admin_dataset_view'))

    # Get the dataset
    try:
        dataset = Dataset.objects.get(acronym=dataset_acronym)

    except ObjectDoesNotExist:
        messages.add_message(request, messages.ERROR, _('Dataset does not exist.'))
        return HttpResponseRedirect(reverse('admin_dataset_view'))

    # Check for 'change_dataset' permission
    user_change_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset, accept_global_perms=False)
    if not user_change_datasets.exists() or dataset not in user_change_datasets:
        messages.add_message(request, messages.ERROR, _("You are not authorized to remove eaf files."))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    # The actual removal
    dataset_eaf_folder = os.path.join(WRITABLE_FOLDER,DATASET_EAF_DIRECTORY,dataset_acronym)
    for selected_path in selected_paths:
        os.remove(dataset_eaf_folder + '/' + selected_path)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def upload_eaf_files(request):
    if request.method != "POST":
        raise Http404('Incorrect request')

    form = EAFFilesForm(request.POST,request.FILES)
    if form.is_valid():

        # Process the request data
        if not request.FILES:
            messages.add_message(request, messages.ERROR, _('No eaf files found.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        folder = ''
        dataset_acronym = ''
        eaf_filenames_list = []

        for f in request.FILES.getlist('file'):
            eaf_filenames_list.append(f.name)

        for key in request.POST.keys():
            if key == 'dataset_acronym':
                dataset_acronym = request.POST['dataset_acronym']
            if key == 'dir_name':
                folder = request.POST.get('dir_name', '')

        if dataset_acronym == '':
            messages.add_message(request, messages.ERROR, _('No acronym for dataset.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        # Get the dataset
        try:
            dataset = Dataset.objects.get(acronym=dataset_acronym)

        except ObjectDoesNotExist:
            messages.add_message(request, messages.ERROR, _('Dataset does not exist.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        # Check for 'change_dataset' permission
        user_change_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset, accept_global_perms=False)
        if not user_change_datasets.exists() or dataset not in user_change_datasets:
            messages.add_message(request, messages.ERROR, _("You are not authorized to upload eaf files."))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        # For the following, we want to keep track of which files are already uploaded
        # Some files may be uploaded but may or may not be processed in the corpus
        already_uploaded_eafs = dataset.uploaded_eafs()
        document_identifiers_of_uploaded_eafs = document_identifiers_from_paths(already_uploaded_eafs)

        # this structure is used by the corpus overview template
        # We're using it here during upload in the database manager template because it's already implemented
        (eaf_paths_dict, duplicates) = documents_paths_dictionary(dataset_acronym)

        # if this is the first time eaf files are uploadd to the system, create the folder
        if not os.path.isdir(WRITABLE_FOLDER + DATASET_EAF_DIRECTORY):
            os.mkdir(WRITABLE_FOLDER + DATASET_EAF_DIRECTORY, mode=0o755)

        # if this is the first time eaf files are uploadd for the dataset, create a dataset folder
        dataset_eaf_folder = os.path.join(WRITABLE_FOLDER,DATASET_EAF_DIRECTORY,dataset_acronym)
        if not os.path.isdir(dataset_eaf_folder):
            os.mkdir(dataset_eaf_folder, mode=0o755)

        # folder was retrieved by the template during selection to upload a folder
        if folder:
            # this could have a side effect of creating an empty folder
            # at a later step the files are checked to be eaf files
            # incorrectly typed files are removed after creation, but not the folder
            dataset_eaf_folder = os.path.join(dataset_eaf_folder,folder)
            if not os.path.isdir(dataset_eaf_folder):
                os.mkdir(dataset_eaf_folder, mode=0o755)

        # move uploaded files to appropriate location
        for f in request.FILES.getlist('file'):
            next_eaf_file = os.path.join(dataset_eaf_folder,f.name)
            f_handle = open(next_eaf_file, mode='wb+')
            for chunk in f.chunks():
                f_handle.write(chunk)

        # this import has limited usage, reduce its scope
        import magic
        # check whether anything should not have been uploaded
        # check the type of the first chunk of the uploaded files
        # check that the files do not already exist

        # Create lists for all problems we might encounter
        ignored_files = []
        duplicate_files = []
        already_seen = []
        import_twice = []

        for new_file in eaf_filenames_list:

            # Get the normalized file name
            norm_filename = os.path.normpath(new_file)
            split_norm_filename = norm_filename.split('.')

            # Validate format
            if len(split_norm_filename) == 1:
                # file has no extension
                wrong_format = True
            else:
                extension = split_norm_filename[-1]
                wrong_format = (extension.lower() != 'eaf')

            # Get full paths
            destination_location = os.path.join(dataset_eaf_folder,new_file)
            file_basename = os.path.basename(new_file)
            basename = os.path.splitext(file_basename)[0]

            # Check if the new file is in the same location
            if basename in document_identifiers_of_uploaded_eafs or basename in eaf_paths_dict.keys():
                new_file_location = os.path.join(folder,file_basename)
                if new_file_location not in eaf_paths_dict[basename]:
                    duplicate_files.append(new_file)

            # Potential conflict, the same file is being imported twice from different locations
            if basename in already_seen:
                import_twice.append(new_file)
            else:
                already_seen.append(basename)

            # Maybe the file is not an eaf file or is missing an extension
            magic_file_type = magic.from_buffer(open(destination_location, "rb").read(2040), mime=True)
            if magic_file_type != 'text/xml' or wrong_format:
                ignored_files.append(new_file)
                os.remove(destination_location)

        # Any problems encountered? Add error messages
        if ignored_files:
            message_string = ", ".join(ignored_files)
            messages.add_message(request, messages.ERROR, _('Non-EAF file(s) ignored: ')+message_string)

        if import_twice:
            message_string = ", ".join(import_twice)
            messages.add_message(request, messages.WARNING, _('File(s) encountered twice: ')+message_string)

        if duplicate_files:
            message_string = ", ".join(duplicate_files)
            messages.add_message(request, messages.INFO, _('Already imported to different folder: ')+message_string)

        return HttpResponseRedirect(reverse('admin_dataset_manager'))

def update_expiry(request):

    # if something is wrong with the call, proceed to Signbank Welcome Page
    # This can happen if the user types in the url rather than getting there via the User Profile View
    # And the Extend Expiry button was not shown on their profile

    # Check for request type
    if request.method != "POST":
        return HttpResponseRedirect(settings.URL + settings.PREFIX_URL + '/')

    # Check if we have a username
    if 'username' in request.POST.keys():
        username = request.POST['username']
    else:
        username = ''

    if not username or request.user.username != username:
        HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    # Check if user exists
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except ObjectDoesNotExist:
        HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    from dateutil.relativedelta import relativedelta
    expiry = getattr(user_profile, 'expiry_date')

    # Check if we have an expiry date
    if not expiry:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    user_profile.expiry_date = expiry + relativedelta(months=+6)
    user_profile.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def update_query(request, queryid):

    if not request.user.is_authenticated:
        return HttpResponseForbidden("Query Update Not Allowed")

    if not request.user.has_perm('dictionary.change_searchhistory'):
        return HttpResponseForbidden("Query Update Not Allowed")

    if not request.method == "POST":
        return HttpResponseForbidden("Query Update method must be POST")

    query = get_object_or_404(SearchHistory, id=queryid)

    if not query.user == request.user:
        return HttpResponseForbidden("Query Update Not Allowed")

    field = request.POST.get('id', '')
    value = request.POST.get('value', '')
    original_value = query.queryName

    if field == 'deletequery':
        if value == 'confirmed':
            # delete the query, its parameters and redirect back to search history
            query_parameters_of_query = QueryParameter.objects.filter(search_history=query)
            for param in query_parameters_of_query:
                param.delete()
            query.delete()
        # if for some reason the value is other than confirmed, do nothing and just go back to the search history
        return HttpResponseRedirect(reverse('admin_search_history'))

    if field == "queryname" and value:
        query.queryName = value
        query.save()

    if not value:
        # if the user has tried to remove the query name but erasing the field, leave it as it was
        # handling of the response value is done on return from the ajax call and displayed in the template
        # this has the effect of doing nothing
        value = original_value

    return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
