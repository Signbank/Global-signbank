from django.core.exceptions import ObjectDoesNotExist

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from django.template import Context, RequestContext, loader
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from django.contrib.auth.decorators import permission_required
import guardian

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

from signbank.video.forms import VideoUploadForObjectForm
from signbank.video.models import AnnotatedVideo, GlossVideoNME, GlossVideoDescription, GlossVideoHistory

from signbank.settings.server_specific import OTHER_MEDIA_DIRECTORY, DATASET_METADATA_DIRECTORY, DATASET_EAF_DIRECTORY, LANGUAGES
from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value
from signbank.tools import get_selected_datasets_for_user, gloss_from_identifier, get_default_annotationidglosstranslation
from signbank.frequency import document_identifiers_from_paths, documents_paths_dictionary

from django.utils.translation import gettext_lazy as _

from guardian.shortcuts import get_user_perms, get_group_perms, get_objects_for_user
from django.shortcuts import redirect
from signbank.dictionary.update_senses_mapping import mapping_edit_keywords, mapping_group_keywords, mapping_add_keyword, \
    mapping_edit_senses_matrix, mapping_toggle_sense_tag
from signbank.dictionary.consistency_senses import reorder_translations
from signbank.dictionary.related_objects import gloss_related_objects, morpheme_related_objects
from signbank.dictionary.update_glosses import *
from signbank.dictionary.batch_edit import batch_edit_update_gloss, add_gloss_update_to_revision_history


def show_error(request, translated_message, form, dataset_languages):
    # this function is used by the add_gloss function below
    messages.add_message(request, messages.ERROR, translated_message)
    return render(request, 'dictionary/add_gloss.html',
                  {'add_gloss_form': form,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': get_selected_datasets_for_user(request.user),
                   'USE_REGULAR_EXPRESSIONS': settings.USE_REGULAR_EXPRESSIONS,
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
            if glosses_for_this_language_and_annotation_idgloss.count() > 0:
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

        gloss_fields = [Gloss.get_field(fname) for fname in Gloss.get_field_names()]

        # Set a default for all FieldChoice fields
        for field in [f for f in gloss_fields if isinstance(f, FieldChoiceForeignKey)]:
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
        user_affiliations = AffiliatedUser.objects.filter(user=request.user)
        if user_affiliations.count() > 0:
            for ua in user_affiliations:
                new_affiliation, created = AffiliatedGloss.objects.get_or_create(affiliation=ua.affiliation,
                                                                                 gloss=gloss)
    except ValidationError as ve:
        return show_error(request, ve.message, form, dataset_languages)

    if 'search_results' not in request.session.keys():
        request.session['search_results'] = []

    # new gloss created successfully, go to GlossDetailView
    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')


def update_examplesentence(request, examplesentenceid):
    """View to update an examplesentence model from the editable modal"""

    if not request.user.has_perm('dictionary.change_examplesentence'):
        return HttpResponseForbidden("Example sentence Update Not Allowed")

    if not request.method == "POST":
        return HttpResponseForbidden("Example sentence Update method must be POST")
    
    examplesentence = ExampleSentence.objects.all().get(id=examplesentenceid)
    old_example_sentence = str(examplesentence)
    sense = Sense.objects.all().get(id=request.POST['senseid'])
    glosses_for_sense = [gs.gloss for gs in GlossSense.objects.filter(sense=sense)]

    dataset = Dataset.objects.get(id = request.POST['dataset'])
    dataset_languages = dataset.translation_languages.all()

    # Use "on" given by checkbox value instead of True
    if request.POST['negative'] == 'on':
        negative = True
    else:
        negative = False
    stype = FieldChoice.objects.filter(field='SentenceType').get(machine_value = request.POST['sentenceType'])

    # Make a dictionary of the posted values
    vals = {}
    for dataset_language in dataset_languages:
        stc = request.POST[str(dataset_language)]
        if stc:
            vals[str(dataset_language)] = stc

    # Edit and save the sentence translations
    with atomic():

        # If change is made in negative or type then change and save that
        if not examplesentence.sentenceType:
            examplesentence.sentenceType = stype
        elif examplesentence.sentenceType != stype: 
            examplesentence.sentenceType = stype
        if examplesentence.negative != negative:
            examplesentence.negative = negative
        examplesentence.save()

        # Check if input was not empty and if both sentences already existed together
        if len(vals) == 0 or vals == examplesentence.get_examplestc_translations_dict_without():
            messages.add_message(request, messages.INFO, _('This example sentence was not changed.'))
            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': request.POST['glossid']})+'?edit')
        
        # Update the examplesentence with examplesentencetranslations
        for dataset_language in dataset_languages:
            if ExampleSentenceTranslation.objects.filter(examplesentence=examplesentence, language=dataset_language).exists():
                examplesentencetranslation = ExampleSentenceTranslation.objects.all().get(examplesentence=examplesentence, language=dataset_language)
                if str(dataset_language) in vals:
                    examplesentencetranslation.text = vals[str(dataset_language)]
                    examplesentencetranslation.save()
                else:
                    examplesentencetranslation.delete()
            elif str(dataset_language) in vals:
                examplesentencetranslation = ExampleSentenceTranslation.objects.create(examplesentence=examplesentence,
                                                                        language=dataset_language,
                                                                        text=vals[str(dataset_language)])

        new_example_sentence = str(examplesentence)
        for gloss in glosses_for_sense:
            # add create sentence to revision history, indicated by empty old_value
            sentence_label = 'Sentence'
            revision = GlossRevision(old_value=old_example_sentence,
                                     new_value=new_example_sentence,
                                     field_name=sentence_label,
                                     gloss=gloss,
                                     user=request.user,
                                     time=datetime.now(tz=get_current_timezone()))
            revision.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': request.POST['glossid']})+'?edit')


def create_examplesentence(request, senseid):
    """View to create an exampelsentence model from the editable modal"""

    if not request.user.has_perm('dictionary.add_examplesentence'):
        return HttpResponseForbidden("Sense Creation Not Allowed")

    if not request.method == "POST":
        return HttpResponseForbidden("Example sentence Creation method must be POST")
    
    dataset = Dataset.objects.get(id = request.POST['dataset'])
    dataset_languages = dataset.translation_languages.all()
    sense = Sense.objects.all().get(id=senseid)
    glosses_for_sense = [gs.gloss for gs in GlossSense.objects.filter(sense=sense)]

    # Use "on" given by checkbox value instead of True
    if request.POST['negative'] == 'on':
        negative = True
    else:
        negative = False

    # Make a dictionary of the posted values
    vals = {}
    for dataset_language in dataset_languages:
        stc = request.POST[str(dataset_language)]
        if stc:
            vals[str(dataset_language)] = stc

    # Check if input was not empty and if both sentences already existed together
    if len(vals) == 0:
        messages.add_message(request, messages.ERROR, _('No input sentence given.'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': request.POST['glossid']})+'?edit')
    
    with atomic():
        stype = FieldChoice.objects.filter(field='SentenceType').get(machine_value = request.POST['sentenceType'])
        examplesentence = ExampleSentence.objects.create(negative=negative, sentenceType=stype)
        sense.exampleSentences.add(examplesentence, through_defaults={'order':sense.exampleSentences.count()+1})
        for dataset_language in dataset_languages:
            if str(dataset_language) in vals:
                ExampleSentenceTranslation.objects.create(language=dataset_language, examplesentence=examplesentence, text=vals[str(dataset_language)])

        new_example_sentence = str(examplesentence)
        for gloss in glosses_for_sense:
            # add create sentence to revision history, indicated by empty old_value
            sentence_label = 'Sentence'
            revision = GlossRevision(old_value="",
                                     new_value=new_example_sentence,
                                     field_name=sentence_label,
                                     gloss=gloss,
                                     user=request.user,
                                     time=datetime.now(tz=get_current_timezone()))
            revision.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': request.POST['glossid']})+'?edit')


def delete_examplesentence(request, senseid):
    """View to delete an examplesentence model from the editable modal"""

    if not request.user.has_perm('dictionary.delete_examplesentence'):
        return HttpResponseForbidden("Example sentence Deletion Not Allowed")

    if not request.method == "POST":
        return HttpResponseForbidden("Example sentence Deletion method must be POST")

    examplesentence = ExampleSentence.objects.all().get(id=request.POST['examplesentenceid'])
    old_example_sentence = str(examplesentence)
    sense = Sense.objects.all().get(id=senseid)
    glosses_for_sense = [gs.gloss for gs in GlossSense.objects.filter(sense=sense)]
    sense.exampleSentences.remove(examplesentence)

    if Sense.objects.filter(exampleSentences=examplesentence).count() == 0:
        examplesentence.delete()

    for gloss in glosses_for_sense:
        # add delete sentence to revision history, indicated by non-empty old_value
        sentence_label = 'Sentence'
        revision = GlossRevision(old_value=old_example_sentence,
                                 new_value="",
                                 field_name=sentence_label,
                                 gloss=gloss,
                                 user=request.user,
                                 time=datetime.now(tz=get_current_timezone()))
        revision.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': request.POST['glossid']})+'?edit')


def sort_sense(request, glossid, order, direction):
    order = int(order)
    gloss = Gloss.objects.get(id=glossid, archived=False)
    gloss_senses_matching_order = GlossSense.objects.filter(gloss=gloss, order=order).count()
    if gloss_senses_matching_order != 1:
        print('sort_sense: multiple or no match for order: ', glossid, str(order))
        messages.add_message(request, messages.ERROR, _('Could not sort this sense.'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')

    glosssense = GlossSense.objects.get(gloss=gloss, order=order)
    swaporder = 0
    if direction == "up":
        swaporder = order - 1
    elif direction == "down":
        swaporder = order + 1
    else:
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')
    
    try:
        glosssensetoswap = GlossSense.objects.get(gloss=gloss, order=swaporder)
        glosssensetoswap.order = order
        glosssense.order = swaporder 
        glosssense.save()
        glosssensetoswap.save()
        reorder_translations(glosssensetoswap, order)
        reorder_translations(glosssense, swaporder)
    except (ObjectDoesNotExist, MultipleObjectsReturned, DatabaseError, TransactionManagementError):
        print('sort_sense ', direction.upper(), ': multiple or no match for order: ', glossid, str(swaporder))
        messages.add_message(request, messages.ERROR, _('Could not sort this sense.'))

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')

def sort_examplesentence(request, senseid, glossid, order, direction):
    order = int(order)
    sense = Sense.objects.get(id=senseid)
    gloss = Gloss.objects.get(id=glossid, archived=False)
    sense_examplesentences_matching_order = SenseExamplesentence.objects.filter(sense=sense, order=order).count()
    if sense_examplesentences_matching_order != 1:
        sense.reorder_examplesentences()

    senseexamplesentence = SenseExamplesentence.objects.get(sense=sense, order=order)
    swaporder = 0
    if direction == "up":
        swaporder = order - 1
    elif direction == "down":
        swaporder = order + 1
    else:
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')

    try:
        senseexamplesentencetoswap = SenseExamplesentence.objects.get(sense=sense, order=swaporder)
        senseexamplesentencetoswap.order = order
        senseexamplesentence.order = swaporder
        senseexamplesentence.save()
        senseexamplesentencetoswap.save()
    except (ObjectDoesNotExist, MultipleObjectsReturned, DatabaseError, TransactionManagementError):
        print('sort_examplesentence ', direction.upper(), ': multiple or no match for order: ', senseid, str(swaporder))
        messages.add_message(request, messages.ERROR, _('Could not sort this examplesentence.'))

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')


def add_sentence_video(request, glossid, examplesentenceid):
    template = 'dictionary/add_sentence_video.html'
    gloss = Gloss.objects.get(id=glossid, archived=False)
    languages = gloss.lemma.dataset.translation_languages.all()
    examplesentence = ExampleSentence.objects.get(id=examplesentenceid)
    context = {
        'examplesentence': examplesentence,
        'gloss': gloss,
        'videoform': VideoUploadForObjectForm(languages=languages),
    }
    return render(request, template, context)


def link_sense(request, senseid):
    return HttpResponseForbidden("TEMPORARY: Sense Linking Not Allowed")


def update_sense(request, senseid):
    """View to update a sense model from the editable modal"""

    if not request.method == "POST":
        return HttpResponseForbidden("Sense Update method must be POST")

    if 'glossid' not in request.POST:
        return HttpResponseForbidden("Sense Update missing gloss id")

    glossid = request.POST['glossid']

    if not request.user.has_perm('dictionary.change_sense'):
        messages.add_message(request, messages.ERROR, _('Sense Update Not Allowed'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid})+'?edit')

    # Make a dict of new values
    gloss = Gloss.objects.all().get(id=glossid)
    dataset = Dataset.objects.get(id=request.POST['dataset'])
    dataset_languages = dataset.translation_languages.all()
    vals = {}
    for dataset_language in dataset_languages:
        if str(dataset_language) in request.POST:
            input_values = request.POST[str(dataset_language)].splitlines()
            values = [v for v in input_values if v]
            if values:
                vals[str(dataset_language)] = values

    # Check if input given is empty
    if vals == {}:
        messages.add_message(request, messages.ERROR, _('No keywords given for edited sense.'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')
    
    # Check if this sense changed at all
    sense = Sense.objects.get(id=senseid)

    # save the old value for revision history, store it as a string before updating it
    sense_old_value = str(sense)

    sensetranslation_dict = sense.get_sense_translations_dict_without_list()

    if sensetranslation_dict == vals:
        messages.add_message(request, messages.ERROR, _('Sense did not change.'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')

    gloss_senses = GlossSense.objects.filter(gloss_id=gloss.id, sense=sense)

    if not gloss_senses.count():
        messages.add_message(request, messages.ERROR, _('GlossSense not found for gloss.'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')
    if gloss_senses.count() > 1:
        messages.add_message(request, messages.ERROR, _('GlossSense duplicate found for gloss.'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')

    # Check if sense already exists in this gloss
    for existing_sense in gloss.senses.all():
        if existing_sense == sense:
            continue
        if vals == existing_sense.get_sense_translations_dict_without_list():
            messages.add_message(request, messages.ERROR, _('This sense was already in this gloss.'))
            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')

    # Update sensetranslations
    this_sense_order = gloss_senses.first().order

    for dataset_language in dataset_languages:
        # sense translation is added, so create it if it doesn't already exist
        if str(dataset_language) not in sensetranslation_dict and str(dataset_language) not in vals:
            continue
        if str(dataset_language) not in sensetranslation_dict and str(dataset_language) in vals:
            sensetranslation = sense.senseTranslations.filter(language=dataset_language).first()
            if not sensetranslation:
                sensetranslation = SenseTranslation.objects.create(language=dataset_language)
                sense.senseTranslations.add(sensetranslation)
            for inx, tr_v in enumerate(vals[str(dataset_language)], 1):
                if not tr_v:
                    continue
                keyword = Keyword.objects.get_or_create(text =tr_v)[0]
                matching_translations = Translation.objects.filter(translation=keyword,
                                                         language=dataset_language,
                                                         gloss=gloss,
                                                         orderIndex=this_sense_order)
                if matching_translations.count() > 1:
                    print('update_sense multiple Translation objects found for sense: ', matching_translations)
                translation = matching_translations.first()
                if not translation:
                    translation = Translation(translation=keyword,
                                              language=dataset_language,
                                              gloss=gloss,
                                              orderIndex=this_sense_order,
                                              index=inx)
                    translation.save()
                else:
                    translation.index = inx
                    translation.save()
                sensetranslation.translations.add(translation)

        else:
            sensetranslation = sense.senseTranslations.get(language=dataset_language)

            # remove the translations of sensetranslation from the sense
            if str(dataset_language) in sensetranslation_dict and str(dataset_language) not in vals:

                for translation in sensetranslation.translations.all():
                    sensetranslation.translations.remove(translation)
                    translation.delete()

            # Check if input field exists and is different from database
            elif sensetranslation_dict[str(dataset_language)] != vals[str(dataset_language)]:
                translation_st_all = sensetranslation.translations.all()
                translation_st = translation_st_all.order_by('index')

                trs, trv = [], []
                for tr_st in translation_st:
                    trs.append(tr_st)
                    trv.append(tr_st.translation.text)
                for tr_s in trs:
                    if tr_s.translation.text not in vals[str(dataset_language)]:
                        sensetranslation.translations.remove(tr_s)
                        tr_s.delete()
                for inx, tr_v in enumerate(vals[str(dataset_language)], 1):
                    if not tr_v:
                        continue
                    keyword = Keyword.objects.get_or_create(text=tr_v)[0]
                    matching_translations = Translation.objects.filter(translation=keyword,
                                                                       language=dataset_language,
                                                                       gloss=gloss,
                                                                       orderIndex=this_sense_order)
                    if matching_translations.count() > 1:
                        print('update_sense multiple Translation objects found for sense: ', matching_translations)
                    translation = matching_translations.first()
                    if not translation:
                        # tr_v not in trv, create a keyword translation object
                        translation = Translation(translation=keyword,
                                                  language=dataset_language,
                                                  gloss=gloss,
                                                  orderIndex=this_sense_order,
                                                  index=inx)
                        translation.save()
                    else:
                        # update the index
                        translation.index = inx
                        translation.save()
                    sensetranslation.translations.add(translation)

    # add update sense to revision history, indicated by both old and new values
    # save the new value for revision history
    sense_new_value = str(sense)

    sense_label = 'Sense'
    revision = GlossRevision(old_value=sense_old_value,
                             new_value=sense_new_value,
                             field_name=sense_label,
                             gloss=gloss,
                             user=request.user,
                             time=datetime.now(tz=get_current_timezone()))
    revision.save()

    messages.add_message(request, messages.INFO, _('Given sense was updated.'))
    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')


def create_sense(request, glossid):
    """View to create a sense model from the editable modal"""

    if not request.method == "POST":
        return HttpResponseForbidden("Sense Creation method must be POST")

    if not request.user.has_perm('dictionary.add_sense'):
        messages.add_message(request, messages.ERROR, _('Sense Creation Not Allowed'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid})+'?edit')

    # Make a dict of new values
    gloss = Gloss.objects.get(id=glossid, archived=False)
    dataset = Dataset.objects.get(id = request.POST['dataset'])
    dataset_languages = dataset.translation_languages.all()
    vals = {}
    for dataset_language in dataset_languages:
        if str(dataset_language) in request.POST:
            input_values = request.POST[str(dataset_language)].splitlines()
            values = [v for v in input_values if v]
            if values:
                for k, v in enumerate(values): 
                    values[k] = v.strip()
                values = values
                vals[str(dataset_language)]=values

    # Check if input given is empty
    if vals == {}:
        messages.add_message(request, messages.ERROR, _('No keywords given for new sense.'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid})+'?edit')

    # Check if sense already exists in this gloss
    for existing_sense in gloss.senses.all():
        if vals == existing_sense.get_sense_translations_dict_without_list():
            messages.add_message(request, messages.ERROR, _('This sense was already in this gloss.'))
            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid})+'?edit')

    # Make a new sense object
    sense = Sense.objects.create()
    gloss.senses.add(sense, through_defaults={'order':gloss.senses.count()+1})
    # this is the order of the new sense
    new_order_gloss_senses = gloss.senses.count()

    with atomic():
        for dataset_language in dataset_languages:
            if str(dataset_language) in vals:
                try:
                    sensetranslation = sense.senseTranslations.get(language=dataset_language)
                except ObjectDoesNotExist:
                    # there should only be one per language
                    sensetranslation = SenseTranslation.objects.create(language=dataset_language)
                    sense.senseTranslations.add(sensetranslation)
                for inx, kw in enumerate(vals[str(sensetranslation.language)], 1):
                    # this is a new sense so it has no translations yet
                    # the combination with gloss, language, orderIndex does not exist yet
                    # the index is the order the keyword was entered by the user
                    if not kw:
                        continue
                    keyword = Keyword.objects.get_or_create(text=kw)[0]
                    translation = Translation(translation=keyword,
                                              language=dataset_language,
                                              gloss=gloss,
                                              orderIndex=new_order_gloss_senses,
                                              index=inx)
                    translation.save()
                    sensetranslation.translations.add(translation)

    # add create sense to revision history, indicated by empty old_value
    sense_new_value = str(sense)
    sense_label = 'Sense'
    revision = GlossRevision(old_value="",
                             new_value=sense_new_value,
                             field_name=sense_label,
                             gloss=gloss,
                             user=request.user,
                             time=datetime.now(tz=get_current_timezone()))
    revision.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid})+'?edit')


def delete_sense(request, glossid):
    """View to delete a sense model from the editable modal"""

    if not request.method == "POST":
        return HttpResponseForbidden("Sense Deletion method must be POST")

    if not request.user.has_perm('dictionary.delete_sense'):
        messages.add_message(request, messages.ERROR, _('Sense Deletion Not Allowed'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid})+'?edit')
    
    sense = Sense.objects.get(id=request.POST['senseid'])
    gloss = Gloss.objects.get(id=glossid, archived=False)
    dataset = Dataset.objects.get(id = request.POST['dataset'])
    dataset_languages = dataset.translation_languages.all()

    # save the old value for revision history, store it as a string before deleting it
    sense_old_value = str(sense)

    gloss.senses.remove(sense)

    other_glosses_for_sense = GlossSense.objects.filter(sense=sense).exclude(gloss=gloss).count()
    if not other_glosses_for_sense:
        # If this is this only gloss this sense was in, delete the sense
        for dataset_language in dataset_languages:
            # number of senseTranslation objects for language should be 1 or none
            # this code also removes spurious sense translations
            # this is done as a separate variable for use in the loop since the loop removes objects
            sensetranslation_for_language = sense.senseTranslations.filter(language=dataset_language)
            sense_translations_list = [st for st in sensetranslation_for_language]
            for sensetranslation in sense_translations_list:
                # iterate over a list because the objects will be removed
                sense_translations = sensetranslation.translations.all()
                for translation in sense_translations:
                    sensetranslation.translations.remove(translation)
                    translation.delete()
                sense.senseTranslations.remove(sensetranslation)
                sensetranslation.delete()
        # also remove its examplesentences if they are not in another sense
        example_sentences = sense.exampleSentences.all()
        for examplesentence in example_sentences:
            sense.exampleSentences.remove(examplesentence)
            if Sense.objects.filter(exampleSentences=examplesentence).count() == 0:
                examplesentence.delete()
        sense.delete()

    # add delete sense to revision history, indicated by non-empty old_value
    sense_label = 'Sense'
    revision = GlossRevision(old_value=sense_old_value,
                             new_value="",
                             field_name=sense_label,
                             gloss=gloss,
                             user=request.user,
                             time=datetime.now(tz=get_current_timezone()))
    revision.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid})+'?edit')


def update_gloss(request, glossid):
    """View to update a gloss model from the jeditable jquery form
    We are sent one field and value at a time, return the new value
    once we've updated it."""

    if not request.user.has_perm('dictionary.change_gloss'):
        return HttpResponseForbidden("Gloss Update Not Allowed")

    if not request.method == "POST":
        return HttpResponseForbidden("Gloss Update method must be POST")

    gloss = get_object_or_404(Gloss, id=glossid, archived=False)

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
    input_value = value

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

            related_objects = gloss_related_objects(gloss)

            if settings.GUARDED_GLOSS_DELETE and related_objects:
                reverse_url = 'dictionary:admin_gloss_view'
                messages.add_message(request, messages.INFO,
                                     _("GUARDED_GLOSS_DELETE is set to True. The gloss has relations to other glosses and was not deleted."))
                return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': gloss.id}))

            # gloss.delete()
            gloss.archived = True
            gloss.save(update_fields=['archived'])

            annotation = get_default_annotationidglosstranslation(gloss)
            add_gloss_update_to_revision_history(request.user, gloss, 'archived', annotation,
                                                 annotation)

            return HttpResponseRedirect(reverse('dictionary:admin_gloss_list'))

    if field.startswith('definition'):

        return update_definition(request, gloss, field, value)

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

        if ds in guardian.shortcuts.get_objects_for_user(request.user, ['view_dataset'],
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

    elif field.startswith('nmevideo'):

        return update_nmevideo(request.user, gloss, field, value)

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

        if field not in Gloss.get_field_names():
            return HttpResponseBadRequest("Unknown field", {'content-type': 'text/plain'})

        whitespace = tuple(' \n\r\t')
        if value.startswith(whitespace) or value.endswith(whitespace):
            value = value.strip()
        original_value = getattr(gloss,field)
        if field in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
            original_value = original_value.name if original_value else original_value
        if field == 'idgloss' and value == '':
            # don't allow user to set Lemma ID Gloss to empty
            # return HttpResponse(str(original_value), {'content-type': 'text/plain'})
            value = str(original_value)

        # special cases
        # - Foreign Key fields (Language, Dialect)
        # - keywords
        # - videos
        # - tags

        gloss_fields = [Gloss.get_field(fname) for fname in Gloss.get_field_names()]

        #Translate the value if a boolean
        # Language values are needed here!
        newvalue = value
        if isinstance(Gloss.get_field(field),BooleanField):
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
                if value:
                    newvalue = _('Yes')
                else:
                    newvalue = _('No')
        # special value of 'notset' or -1 means remove the value
        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
        fieldchoiceforeignkey_fields = [f.name for f in gloss_fields
                                        if f.name in fieldnames
                                        and isinstance(f, FieldChoiceForeignKey)]
        fields_empty_null = [f.name for f in gloss_fields
                                if f.name in fieldnames and f.null and f.name not in fieldchoiceforeignkey_fields ]

        char_fields_not_null = [f.name for f in gloss_fields
                                if f.name in fieldnames and f.__class__.__name__ == 'CharField'
                                    and f.name not in fieldchoiceforeignkey_fields and not f.null]

        char_fields = [f.name for f in gloss_fields
                                if f.name in fieldnames and f.__class__.__name__ == 'CharField'
                                    and f.name not in fieldchoiceforeignkey_fields]

        text_fields = [f.name for f in gloss_fields
                                if f.name in fieldnames and f.__class__.__name__ == 'TextField' ]

        text_fields_not_null = [f.name for f in gloss_fields
                                if f.name in fieldnames and f.__class__.__name__ == 'TextField' and not f.null]

        # The following code relies on the order of if else testing
        # The updates ignore Placeholder empty fields of '-' and '------'
        # The Placeholders are needed in the template Edit view so the user can "see" something to edit
        if field in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
            gloss_field = Gloss.get_field(field)
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
            if value == '':
                value = 0
            gloss_field = Gloss.get_field(field)
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

            # If the value is not a Boolean, get the human readable value
            if not isinstance(value,bool):
                # if we get to here, field is a valid field of Gloss
                newvalue = value

    if field in FIELDS['phonology']:

        category_value = 'phonology'

    # the gloss has been updated, now prepare values for saving to GlossHistory and display in template
    # This is because you cannot concat none to a string in py3
    if original_value is None:
        original_value = ''

    # if choice_list is empty, the original_value is returned by the called function
    # Remember this change for the history books
    original_human_value = original_value.name if isinstance(original_value, FieldChoice) else original_value
    if isinstance(value, bool) and field in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
    # store a boolean in the Revision History rather than a human value
    # as for the template (e.g., 'letter' or 'number')
        glossrevision_newvalue = value
    else:
        # this takes care of a problem with None not being allowed as a value in GlossRevision
        # the weakdrop and weakprop fields make use of three-valued logic and None is a legitimate value aka Neutral
        if newvalue is None:
            newvalue = ''
        glossrevision_newvalue = newvalue

    revision = GlossRevision(old_value=original_human_value,
                             new_value=glossrevision_newvalue,
                             field_name=field,
                             gloss=gloss,
                             user=request.user,
                             time=datetime.now(tz=get_current_timezone()))
    revision.save()
    # The machine_value (value) representation is also returned to accommodate Hyperlinks to Handshapes in gloss_edit.js
    return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' +  str(value) + '\t' + category_value
                        + '\t' + str(lemma_gloss_group) + '\t' + input_value, {'content-type': 'text/plain'})


def update_keywords(gloss, field, value):
    """Update the keyword field"""
    # Determine the language of the keywords
    language = Language.objects.get(id=get_default_language_id())
    try:
        language_code_2char = field[len('keyword_'):]
        language = Language.objects.filter(language_code_2char=language_code_2char).first()
    except ObjectDoesNotExist:
        pass

    kwds = [k.strip() for k in value.split(',')]

    keywords_list = []
    # omit duplicates to make sure constraint holds
    for kwd in kwds:
        if kwd not in keywords_list:
            keywords_list.append(kwd)

    current_trans = gloss.translation_set.filter(language=language).order_by('orderIndex', 'index')
    current_keywords = [t.translation.text for t in current_trans]

    missing_keywords = []
    for trans in current_trans:
        if trans.translation.text not in keywords_list:
            missing_keywords.append(trans)
    # remove deleted keywords
    for t in missing_keywords:
        t.delete()
    # add new keywords
    for i in range(len(keywords_list)):
        new_text = keywords_list[i]
        if new_text in current_keywords:
            continue
        (keyword_object, created) = Keyword.objects.get_or_create(text=keywords_list[i])
        trans = Translation(gloss=gloss, translation=keyword_object, index=i, language=language, orderIndex=1)
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


def update_nmevideo(user, gloss, field, value):
    """Update the GlossVideoNME"""
    if field.startswith('nmevideo_description_'):
        nmevideoid_language_code_2char = field[len('nmevideo_description_'):]
        nmevideoid, language_code_2char = nmevideoid_language_code_2char.split('_')
        nmevideo = GlossVideoNME.objects.get(id=int(nmevideoid))
        language = Language.objects.filter(language_code_2char=language_code_2char).first()
        whitespace = tuple(' \n\r\t')
        if value.startswith(whitespace) or value.endswith(whitespace):
            value = value.strip()
        try:
            description = GlossVideoDescription.objects.get(nmevideo=nmevideo, language=language)
        except ObjectDoesNotExist:
            # if no description object exists yet, create it
            description = GlossVideoDescription.objects.create(nmevideo=nmevideo, language=language)
        description.text = value
        description.save()
    elif field.startswith('nmevideo_offset_'):
        nmevideoid = field[len('nmevideo_offset_'):]
        nmevideo = GlossVideoNME.objects.get(id=int(nmevideoid))
        new_offset = int(value)
        existing_nmevideos = GlossVideoNME.objects.filter(gloss=gloss).exclude(id=int(nmevideoid))
        existing_offsets = [nmev.offset for nmev in existing_nmevideos]
        if new_offset in existing_offsets or new_offset == nmevideo.offset:
            return HttpResponse(value, {'content-type': 'text/plain'})
        nmevideo.offset = new_offset
        nmevideo.save()
    elif field.startswith('nmevideo_delete_'):
        nmevideoid = field[len('nmevideo_delete_'):]
        nmevideo = GlossVideoNME.objects.get(id=int(nmevideoid))
        filename = os.path.basename(nmevideo.videofile.name)
        filepath = nmevideo.videofile.path
        nmevideo.reversion(revert=False)
        log_entry = GlossVideoHistory(action="delete", gloss=gloss,
                                      actor=user,
                                      uploadfile=filename,
                                      goal_location=filepath)
        log_entry.save()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id}))

    else:
        print('unknown nme video update field: ', field)
    return HttpResponse(value, {'content-type': 'text/plain'})


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


# This function is called from the Gloss Details template when updating Relations to Other Signs
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

    match = re.match(r'(.*) \((\d+)\)', value)
    if match:
        print("MATCH: ", match)
        idgloss = match.group(1)
        pk = match.group(2)
        print("INFO: ", idgloss, pk)

        target = Morpheme.objects.get(pk=int(pk))
        print("TARGET: ", target)
        return target
    elif value:
        idgloss = value
        target = Morpheme.objects.get(idgloss=idgloss)
        return target
    else:
        return None


def update_definition(request, gloss, field, value):
    """Update one of the definition fields"""

    if gloss.is_morpheme():
        gloss_or_morpheme = gloss.morpheme
        reverse_url = 'dictionary:admin_morpheme_view'
    else:
        gloss_or_morpheme = gloss
        reverse_url = 'dictionary:admin_gloss_view'

    newvalue = ''
    (what, defid) = field.split('_')
    try:
        defn = Definition.objects.get(id=defid)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Bad Definition ID '%s'" % defid, {'content-type': 'text/plain'})

    if not defn.gloss.id == gloss_or_morpheme.id:
        return HttpResponseBadRequest("Definition doesn't match gloss", {'content-type': 'text/plain'})
    
    if what == 'definitiondelete':
        defn.delete()
        return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': gloss_or_morpheme.id})+'?editdef')
    
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

    if gloss.is_morpheme():
        gloss_or_morpheme = gloss.morpheme
        reverse_url = 'dictionary:admin_morpheme_view'
    else:
        gloss_or_morpheme = gloss
        reverse_url = 'dictionary:admin_gloss_view'

    action_or_fieldname, other_media_id = field.split('_')

    other_media = None
    try:
        other_media = OtherMedia.objects.get(id=other_media_id)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Bad OtherMedia ID '%s'" % other_media, {'content-type': 'text/plain'})

    if not other_media.parent_gloss.id == gloss_or_morpheme.id:
        return HttpResponseBadRequest("OtherMedia doesn't match gloss", {'content-type': 'text/plain'})

    if action_or_fieldname == 'other-media-delete':
        other_media.delete()
        return HttpResponseRedirect(reverse(reverse_url,
                                            kwargs={'pk': gloss_or_morpheme.pk})+'?editothermedia')

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
        source = Gloss.objects.get(pk=int(sourceid), archived=False)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Source gloss not found.", {'content-type': 'text/plain'})

    try:
        target = Gloss.objects.get(id=int(targetid), archived=False)
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
        source = Gloss.objects.get(pk=int(sourceid), archived=False)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Source gloss not found.", {'content-type': 'text/plain'})

    try:
        target = Gloss.objects.get(id=int(targetid), archived=False)
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
        gloss = Gloss.objects.get(pk=int(sourceid), archived=False)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Source gloss not found.", {'content-type': 'text/plain'})

    rel = RelationToForeignSign(gloss=gloss,loan=loan,other_lang=other_lang,other_lang_gloss=other_lang_gloss)
    rel.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editrelforeign')


def add_definition(request, glossid):
    """Add a new definition for this gloss"""

    thisgloss = get_object_or_404(Gloss, id=glossid, archived=False)

    if thisgloss.is_morpheme():
        gloss_or_morpheme = thisgloss.morpheme
        reverse_url = 'dictionary:admin_morpheme_view'
    else:
        gloss_or_morpheme = thisgloss
        reverse_url = 'dictionary:admin_gloss_view'

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

    defn = Definition(gloss=gloss_or_morpheme, count=count, role=role, text=text, published=published)
    defn.save()

    return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': gloss_or_morpheme.id})+'?editdef')


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
    # This is no a gloss ID
    morpheme = Gloss.objects.get(id=morpheme_id)

    thisgloss = get_object_or_404(Gloss, pk=parent_gloss, archived=False)

    original_sequential = thisgloss.get_hasComponentOfType_display()

    role = get_object_or_404(FieldChoice, pk=role_id, field='MorphologyType')

    # create definition, default to not published
    morphdef = MorphologyDefinition(parent_gloss=thisgloss, role=role, morpheme=morpheme)
    morphdef.save()

    new_sequential = thisgloss.get_hasComponentOfType_display()
    add_gloss_update_to_revision_history(request.user, thisgloss, 'sequential_morphology', original_sequential, new_sequential)

    thisgloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    thisgloss.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')


# Add a 'morpheme' (according to the Morpheme model)
def add_morpheme_definition(request, glossid):

    if not request.method == "POST":
        return HttpResponseForbidden("Add morpheme definition method must be POST")

    form = GlossMorphemeForm(request.POST)

    thisgloss = get_object_or_404(Gloss, pk=glossid, archived=False)

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

    original_simultaneous = thisgloss.get_morpheme_display()

    definition = SimultaneousMorphologyDefinition()
    definition.parent_gloss = thisgloss
    definition.morpheme = morph
    definition.role = form.cleaned_data['description']
    definition.save()

    new_simultaneous = thisgloss.get_morpheme_display()
    add_gloss_update_to_revision_history(request.user, thisgloss, 'simultaneous_morphology', original_simultaneous, new_simultaneous)

    thisgloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    thisgloss.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')


# Add a 'blend' (according to the Blend model)
def add_blend_definition(request, glossid):

    if not request.method == "POST":
        return HttpResponseForbidden("Add blend definition method must be POST")

    form = GlossBlendForm(request.POST)

    thisgloss = get_object_or_404(Gloss, pk=glossid, archived=False)

    original_blend = thisgloss.get_blendmorphology_display()

    # check availability of morpheme before continuing
    if form.data['blend_id'] == "":
        # The user has obviously not selected a morpheme
        # Desired action (Issue #199): nothing happens
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    blend_id = form.cleaned_data['blend_id'] # This is a gloss ID now
    blend = Gloss.objects.get(id=blend_id, archived=False)

    if blend is not None:
        definition = BlendMorphology()
        definition.parent_gloss = thisgloss
        definition.glosses = blend
        definition.role = form.cleaned_data['role']
        definition.save()

    new_blend = thisgloss.get_blendmorphology_display()
    add_gloss_update_to_revision_history(request.user, thisgloss, 'blend_morphology', original_blend, new_blend)

    thisgloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    thisgloss.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')


def update_handshape(request, handshapeid):

    handshape_fields = Handshape.get_field_names()

    if not request.method == "POST":
        # return HttpResponseForbidden("Update handshape method must be POST")
        return HttpResponse(" \t \t \t ", {'content-type': 'text/plain'})

    hs = get_object_or_404(Handshape, machine_value=handshapeid)
    hs.save() # This updates the lastUpdated field

    get_field = request.POST.get('id', '')
    value = request.POST.get('value', '')
    original_value = ''
    value = str(value)
    newPattern = ' '

    field = get_field
    if field not in handshape_fields:
        print(field, ' not in handshape fields')

    if len(value) == 0:
        value = ' '

    elif value[0] == '_':
        value = value[1:]

    handshape_field = Handshape.get_field(field)
    if hasattr(handshape_field, 'field_choice_category'):
        # this is needed because the new value is a machine value, not an id
        field_choice_category = handshape_field.field_choice_category
        original_value_object = getattr(hs, field)
        field_choice = FieldChoice.objects.get(field=field_choice_category, machine_value=int(value))
        setattr(hs, field, field_choice)
        hs.save()
        newvalue = field_choice.name if field_choice else '-'
        original_value = original_value_object.name if original_value_object else '-'
    elif value == '':
        hs.__setattr__(field, None)
        hs.save()
        newvalue = ''
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
                mv = object_fingSelection.first()
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
                mv = object_fingSelection.first()
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
                mv = object_fingSelection.first()
                hs_mod.__setattr__('hsFingUnsel', mv)
                hs_mod.save()
            else:
                print("finger selection not found: ", newPattern)
    else:
        category_value = 'fieldChoice'

    return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' + str(category_value) + '\t' + str(newPattern),
                        {'content-type': 'text/plain'})


def add_annotated_media(request, glossid):
    template = 'dictionary/add_annotated_sentence.html'
    gloss = Gloss.objects.get(id=glossid, archived=False)
    dataset = gloss.lemma.dataset
    languages = dataset.translation_languages.all()
    annotated_sentence_sources = AnnotatedSentenceSource.objects.filter(dataset=dataset)
    context = {
        'gloss': gloss,
        'annotationidgloss': gloss.annotationidglosstranslation_set.filter(language = dataset.default_language).first().text,
        'videoform': VideoUploadForObjectForm(languages=languages, dataset=dataset),
        'annotated_sentence_sources': annotated_sentence_sources,
        'dataset': dataset,
    }
    return render(request, template, context)


def edit_annotated_sentence(request, glossid, annotatedsentenceid):
    """View to pass context variables to the annotated sentence edit page"""
    template = 'dictionary/edit_annotated_sentence.html'
    gloss = Gloss.objects.get(id=glossid, archived=False)
    annotated_translations, annotated_contexts = {}, {}
    annotated_sentence = None
    annotated_sentence_sources = AnnotatedSentenceSource.objects.filter(dataset=gloss.lemma.dataset)
    
    if AnnotatedSentence.objects.filter(id=annotatedsentenceid).count() == 1:
        annotated_sentence = AnnotatedSentence.objects.get(id=annotatedsentenceid)
        if annotated_sentence.annotatedvideo.source:
            annotated_sentence_sources = annotated_sentence_sources.exclude(id=annotated_sentence.annotatedvideo.source.id)
        annotated_translations = annotated_sentence.get_annotatedstc_translations_dict_with()
        annotated_contexts = annotated_sentence.get_annotatedstc_contexts_dict_with()
        annotationidgloss = gloss.annotationidglosstranslation_set.filter(language = annotated_sentence.get_dataset().default_language).first().text

    annotated_glosses, checked_glosses = annotated_sentence.get_annotated_glosses_list()
    annotations_table_html = render(request, 'annotations_table.html', {'glosses_list': annotated_glosses, 'check_gloss_label': checked_glosses, 'labels_not_found': []}).content.decode('utf-8')

    context = {
        'gloss': gloss,
        'annotationidgloss': annotationidgloss,
        'annotated_sentence': annotated_sentence,
        'annotated_translations': annotated_translations,
        'annotated_contexts': annotated_contexts,
        'annotations_table_html': annotations_table_html,
        'annotated_sentence_sources': annotated_sentence_sources,
    }
    return render(request, template, context)


def save_edit_annotated_sentence(request):
    """Save the edits made for an annotated sentence from the edit page"""
    if not request.method == "POST":
        return HttpResponseForbidden("Annotated Sentence Edit method must be POST")
    
    redirect_url = request.POST.get('redirect')
    gloss = Gloss.objects.get(id=request.POST.get('glossid'), archived=False)
    annotated_sentence = AnnotatedSentence.objects.get(id=request.POST.get('annotatedsentenceid'))
    annotations = request.POST['feedbackdata']

    with atomic():
        annotated_sentence.annotated_glosses.all().delete()
        cut = False
        if 'trim-video-checked' in request.POST:
            cut = True
            start_cut = int(request.POST['start-ms'])
            end_cut = int(request.POST['end-ms'])
            annotated_sentence.add_annotations(annotations, gloss, start_cut, end_cut)
        else:
            annotated_sentence.add_annotations(annotations, gloss)

        for language in gloss.lemma.dataset.translation_languages.all():
            context_key = 'context_' + language.language_code_3char
            if context_key in request.POST:
                context_in_lang = request.POST[context_key]
                if context_in_lang != '':
                    annotated_sentence_context, _ = AnnotatedSentenceContext.objects.get_or_create(annotatedsentence=annotated_sentence, language=language)
                    annotated_sentence_context.text = context_in_lang
                    annotated_sentence_context.save()
                else:
                    annotated_sentence_context = AnnotatedSentenceContext.objects.filter(annotatedsentence=annotated_sentence, language=language)
                    if annotated_sentence_context:
                        annotated_sentence_context.delete()
            translation_key = 'translation_' + language.language_code_3char
            if translation_key in request.POST:
                translation_in_lang = request.POST[translation_key]
                if translation_in_lang != '':
                    annotated_sentence_translation, _ = AnnotatedSentenceTranslation.objects.get_or_create(annotatedsentence=annotated_sentence, language=language)
                    annotated_sentence_translation.text = translation_in_lang
                    annotated_sentence_translation.save()
                else:
                    annotated_sentence_translation = AnnotatedSentenceTranslation.objects.filter(annotatedsentence=annotated_sentence, language=language)
                    if annotated_sentence_translation:
                        annotated_sentence_translation.delete()
        if 'source_id' in request.POST:
            source = request.POST['source_id']
            if source != "":
                annotated_sentence.annotatedvideo.source = AnnotatedSentenceSource.objects.get(id=source)
            else:
                annotated_sentence.annotatedvideo.source = None
            annotated_sentence.annotatedvideo.save()
        if 'eaffile' in request.FILES:
            annotated_sentence.annotatedvideo.delete_files(only_eaf=True)
            eaffile = request.FILES['eaffile']
            from signbank.video.models import get_annotated_video_file_path
            eaf_file_path = get_annotated_video_file_path(instance=annotated_sentence.annotatedvideo, filename=eaffile.name)
            annotated_sentence.annotatedvideo.eaffile.save(eaf_file_path, eaffile)

        if cut:
            annotated_sentence.annotatedvideo.cut_video_and_eaf(start_cut, end_cut)
    
    return redirect(redirect_url)

def delete_annotated_sentence(request, glossid):
    """View to delete an annotated sentence model from the editable modal"""
    if not request.method == "POST":
        return HttpResponseForbidden("Annotated Sentence Deletion method must be POST")

    if not request.user.has_perm('dictionary.annotated_sentence_sense'):
        messages.add_message(request, messages.ERROR, _('Annotated Sentence Deletion Not Allowed'))
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid}))

    annotated_sentence = AnnotatedSentence.objects.get(id=request.POST['annotatedsentenceid'])
    annotated_videos = AnnotatedVideo.objects.filter(annotatedsentence=annotated_sentence)
    for annotated_video in annotated_videos:
        annotated_video.delete_files()
        annotated_video.delete()
    annotated_sentence.delete()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid}))

def add_othermedia(request):

    if not request.method == "POST":
        return HttpResponseForbidden("Add other media method must be POST")

    form = OtherMediaForm(request.POST,request.FILES)

    if not form.is_valid():
        # fallback to the requesting page
        return HttpResponseRedirect('/')

    morpheme_or_gloss = Gloss.objects.get(id=request.POST['gloss'], archived=False)

    if morpheme_or_gloss.is_morpheme():
        gloss_or_morpheme = morpheme_or_gloss.morpheme
        reverse_url = 'dictionary:admin_morpheme_view'
    else:
        gloss_or_morpheme = morpheme_or_gloss
        reverse_url = 'dictionary:admin_gloss_view'

    import os

    othermedia_exists = os.path.exists(OTHER_MEDIA_DIRECTORY)
    if not othermedia_exists:
        messages.add_message(request, messages.ERROR, _("Upload other media failed: The othermedia folder is missing."))
        return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': gloss_or_morpheme.pk}))

    # Create the folder if needed
    goal_directory = os.path.join(OTHER_MEDIA_DIRECTORY, str(gloss_or_morpheme.pk))

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
        return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': gloss_or_morpheme.pk}))

    norm_filename = os.path.normpath(filename)
    split_norm_filename = norm_filename.split('.')

    if len(split_norm_filename) == 1:
        # file has no extension
        messages.add_message(request, messages.ERROR, _("Upload other media failed: The file has no extension."))
        return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': gloss_or_morpheme.pk}))

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
    # Save the database record
    other_media_path = str(gloss_or_morpheme.pk)+'/'+destination_filename
    newothermedia = OtherMedia(path=other_media_path,
                               alternative_gloss=request.POST['alternative_gloss'],
                               type=othermediatype,
                               parent_gloss=gloss_or_morpheme)
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

    destination_location = os.path.join(goal_directory, filename_plus_extension)

    import magic
    magic_file_type = magic.from_buffer(open(destination_location, "rb").read(2040), mime=True)

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
        new_destination_location = filename_base + ".mp4"
        other_media_path = str(gloss_or_morpheme.pk) + '/' + new_destination_location
        target_destination_location = os.path.join(goal_directory, new_destination_location)

        from signbank.video.convertvideo import convert_video
        # convert the quicktime video to mp4
        success = convert_video(destination_location, target_destination_location)
        if not success:
            # problems converting a quicktime media to mp4
            os.remove(target_destination_location)
            os.remove(destination_location)
            # something went wrong with uploading, delete the object
            newothermedia.delete()
            messages.add_message(request, messages.ERROR,
                                 _("Upload other media failed: The Quicktime file could not be converted to MP4."))
            return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': request.POST['gloss']}))
        else:
            newothermedia.path = other_media_path
            newothermedia.save()
            os.remove(destination_location)

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

    gloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    gloss.save()

    try:
        morph_def = MorphologyDefinition.objects.get(id=morph_def_id)
    except ObjectDoesNotExist:
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

    show_dataset_interface = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
    use_regular_expressions = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

    form = MorphemeCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=last_used_dataset)

    # Lemma handling
    lemmaidgloss = None
    lemma_form = None
    if request.POST['select_or_new_lemma'] == 'new':
        lemma_form = LemmaCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=last_used_dataset)
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
                lemma__dataset=dataset,
                annotationidglosstranslation__language=language,
                annotationidglosstranslation__text__exact=value)
            if morphemes_for_this_language_and_annotation_idgloss.count() > 0:
                translated_message = _('Annotation ID Gloss not unique.')
                return render(request, 'dictionary/warning.html',
                       {'warning': translated_message,
                        'dataset_languages': dataset_languages,
                        'selected_datasets': selected_datasets,
                        'USE_REGULAR_EXPRESSIONS': use_regular_expressions,
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
                                                 'USE_REGULAR_EXPRESSIONS': settings.USE_REGULAR_EXPRESSIONS,
                                                 'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        if 'search_results' not in request.session.keys():
            request.session['search_results'] = []
        if 'search_type' not in request.session.keys():
            request.session['search_type'] = ''
        request.session['last_used_dataset'] = dataset.acronym

        return HttpResponseRedirect(reverse('dictionary:admin_morpheme_view', kwargs={'pk': morpheme.id})+'?edit')
    else:
        return render(request,'dictionary/add_morpheme.html', {'add_morpheme_form': form,
                                                                'dataset_languages': dataset_languages,
                                                                'selected_datasets': get_selected_datasets_for_user(request.user),
                                                                'USE_REGULAR_EXPRESSIONS': settings.USE_REGULAR_EXPRESSIONS,
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
    # this copies any '_' + machine_value code to pass back to the success method, if relevant
    input_value = value

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
            related_objects = morpheme_related_objects(morpheme)

            if settings.GUARDED_MORPHEME_DELETE or related_objects:
                reverse_url = 'dictionary:admin_morpheme_view'
                messages.add_message(request, messages.INFO,
                                     _("GUARDED_MORPHEME_DELETE is set to True or the morpheme has relations to other glosses and was not deleted."))
                return HttpResponseRedirect(reverse(reverse_url, kwargs={'pk': morpheme.id}))
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

        if ds in guardian.shortcuts.get_objects_for_user(request.user, ['view_dataset'],
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
            except IntegerField:
                return HttpResponseBadRequest("SN value must be integer", {'content-type': 'text/plain'})

            existing_morpheme = Morpheme.objects.filter(sn__exact=value)
            if existing_morpheme.count() > 0:
                g = existing_morpheme[0].idgloss
                return HttpResponseBadRequest("SN value already taken for morpheme %s" % g,
                                              {'content-type': 'text/plain'})
            else:
                morpheme.sn = value
                morpheme.save()
                newvalue = str(value)

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
        if field not in Morpheme.get_field_names():
            return HttpResponseBadRequest("Unknown field", {'content-type': 'text/plain'})

        original_value = getattr(morpheme, field)
        newvalue = value
        if isinstance(original_value, FieldChoice):
            original_value = original_value.name if original_value else original_value

        # special cases
        # - Foreign Key fields (Language, Dialect)
        # - keywords
        # - videos
        # - tags

        morpheme_fields = [Morpheme.get_field(fname) for fname in Morpheme.get_field_names()]

        # Translate the value if a boolean
        if isinstance(Morpheme.get_field(field), BooleanField):
            value = (value.lower() in [_('Yes').lower(), 'true', True, 1])
            if value:
                newvalue = _('Yes')
            else:
                newvalue = _('No')

        # special value of 'notset' or -1 means remove the value
        fieldnames = FIELDS['main'] + settings.MORPHEME_DISPLAY_FIELDS + FIELDS['semantics'] + ['inWeb', 'isNew', 'mrpType']

        if field in FIELDS['phonology']:
            # this is used as part of the feedback to the interface, to alert the user to refresh the display
            category_value = 'phonology'

        fieldchoiceforeignkey_fields = [field.name for field in morpheme_fields
                                        if field.name in fieldnames
                                        and isinstance(field, FieldChoiceForeignKey)]
        fields_empty_null = [field.name for field in morpheme_fields
                             if field.name in fieldnames and field.null and field.name not in fieldchoiceforeignkey_fields]

        char_fields_not_null = [field.name for field in morpheme_fields
                                if field.name in fieldnames and field.name not in fieldchoiceforeignkey_fields and not field.null]

        # The following code relies on the order of if else testing
        # The updates ignore Placeholder empty fields of '-' and '------'
        # The Placeholders are needed in the template Edit view so the user can "see" something to edit
        if field in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
            # Handshapes not included, ignore
            newvalue = ''
        elif field in fieldchoiceforeignkey_fields:
            gloss_field = Morpheme.get_field(field)
            if value == ' ':
                value = '0'
            try:
                fieldchoice = FieldChoice.objects.get(field=gloss_field.field_choice_category, machine_value=int(value))
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                print('Update field choice no unique machine value found: ', gloss_field.name,
                      gloss_field.field_choice_category, value)
                print('Setting to machine value 0')
                fieldchoice = FieldChoice.objects.get(field=gloss_field.field_choice_category, machine_value=0)
            setattr(morpheme, field, fieldchoice)
            morpheme.save()
            newvalue = fieldchoice.name

        elif value in ['notset', ''] and field not in char_fields_not_null:
            morpheme.__setattr__(field, None)
            morpheme.save()
            newvalue = ''

        # Regular field updating
        else:
            morpheme.__setattr__(field, value)
            morpheme.save()

    return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' + str(value) + '\t' + category_value
                        + '\t' + str(lemma_gloss_group) + '\t' + input_value, {'content-type': 'text/plain'})


def update_morpheme_definition(gloss, field, value):
    """Update the morpheme definition for this gloss"""

    newvalue = value
    original_value = ''
    category_value = 'simultaneous_morphology'
    (what, morph_def_id) = field.split('_')
    what = what.replace('-','_')

    gloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    gloss.save()

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

    gloss.lastUpdated = DT.datetime.now(tz=get_current_timezone())
    gloss.save()

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

    if not request.method == "POST":
        return HttpResponseForbidden("Add gloss tag method must be POST")

    thisgloss = get_object_or_404(Gloss, id=glossid, archived=False)
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
        response = render(request, 'dictionary/glosstags.html',
                          {'gloss': thisgloss,
                           'tagform': TagUpdateForm()})
            
    return response


def edit_keywords(request, glossid):
    """Edit the keywords"""
    if not request.user.is_authenticated:
        return JsonResponse({})

    if not request.user.has_perm('dictionary.change_gloss'):
        return JsonResponse({})

    glossXsenses = mapping_edit_keywords(request, glossid)

    return JsonResponse(glossXsenses)


def group_keywords(request, glossid):
    """Update the keyword field"""

    if not request.user.is_authenticated:
        return JsonResponse({})

    if not request.user.has_perm('dictionary.change_gloss'):
        return JsonResponse({})

    glossXsenses = mapping_group_keywords(request, glossid)

    return JsonResponse(glossXsenses)


def add_keyword(request, glossid):
    """Add keywords"""
    if not request.user.is_authenticated:
        return JsonResponse({})

    if not request.user.has_perm('dictionary.change_gloss'):
        return JsonResponse({})

    glossXsenses = mapping_add_keyword(request, glossid)

    return JsonResponse(glossXsenses)


def edit_senses_matrix(request, glossid):
    """Edit the keywords"""
    if not request.user.is_authenticated:
        return JsonResponse({})

    if not request.user.has_perm('dictionary.change_gloss'):
        return JsonResponse({})

    glossXsenses = mapping_edit_senses_matrix(request, glossid)

    return JsonResponse(glossXsenses)


@permission_required('dictionary.change_gloss')
def toggle_sense_tag(request, glossid):

    if not request.user.is_authenticated:
        return JsonResponse({})

    if not request.user.has_perm('dictionary.change_gloss'):
        return JsonResponse({})

    result = mapping_toggle_sense_tag(request, glossid)

    return JsonResponse(result)


def add_morphemetag(request, morphemeid):
    """View to add a tag to a morpheme"""

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
                except (ObjectDoesNotExist, TransactionManagementError, DatabaseError, IntegrityError):
                    print('exception to updating selected datasets')
                    pass
            user_profile.save()
        else:
            # no datasets selected
            user_profile = UserProfile.objects.get(user=request.user)
            user_profile.selected_datasets.clear()
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
            # erase previous search results session variable since the dataset selection has changed
            request.session['search_results'] = []
            request.session.modified = True

    # check whether the last used dataset is still in the selected datasets
    if 'last_used_dataset' in request.session.keys():
        if selected_dataset_acronyms and request.session['last_used_dataset'] not in selected_dataset_acronyms:
            request.session['last_used_dataset'] = selected_dataset_acronyms[0]
            request.session.modified = True
    else:
        # set the last_used_dataset?
        pass
    return redirect(settings.PREFIX_URL + '/datasets/select')


def update_dataset(request, datasetid):
    """View to update a dataset model from the jeditable jquery form
    We are sent one field and value at a time, return the new value
    once we've updated it."""

    if request.method == "POST":

        dataset = get_object_or_404(Dataset, id=datasetid)
        dataset.save() # This updates the lastUpdated field

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
        if dataset not in user_change_datasets:
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

            if not field in Dataset.get_field_names():
                return HttpResponseBadRequest("Unknown field", {'content-type': 'text/plain'})

            # unknown if we need this code yet for the above fields
            whitespace = tuple(' \n\r\t')
            if value.startswith(whitespace) or value.endswith(whitespace):
                value = value.strip()
            original_value = getattr(dataset,field)

        #This is because you cannot concat none to a string in py3
        if original_value is None:
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
        return HttpResponseRedirect(settings.PREFIX_URL + '/')

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


def update_semfield(request, semfieldid):

    if not request.user.is_authenticated:
        return HttpResponseForbidden("Semantic Field Update Not Allowed")

    if not request.user.has_perm('dictionary.add_semanticfieldtranslation'):
        return HttpResponseForbidden("Semantic Field Update Not Allowed")

    if not request.method == "POST":
        return HttpResponse("", {'content-type': 'text/plain'})

    semfield = get_object_or_404(SemanticField, machine_value=int(semfieldid))

    field = request.POST.get('id', '')
    value = request.POST.get('value', '')
    original_value = ''

    if value and field == 'description':
        semfield.description = value
        semfield.save()
    elif value:
        (namefield, lang_code) = field.rsplit('_', 1)
        language = Language.objects.filter(language_code_2char=lang_code)
        if not language:
            return HttpResponse("", {'content-type': 'text/plain'})
        translation_for_language = semfield.semanticfieldtranslation_set.filter(language=language.first())
        for old_translation in translation_for_language:
            old_translation.delete()
        new_translation = SemanticFieldTranslation(semField=semfield, language=language.first(), name=value)
        new_translation.save()

    if not value:
        # if the user has tried to remove the query name but erasing the field, leave it as it was
        # handling of the response value is done on return from the ajax call and displayed in the template
        # this has the effect of doing nothing
        value = original_value

    return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})

def assign_lemma_dataset_to_gloss(request, glossid):

    # if anything fails nothing is done, but messages are output

    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, _('Please login to use this functionality.'))
        return HttpResponse(json.dumps({}), {'content-type': 'application/json'})

    if not request.user.has_perm('dictionary.change_gloss'):
        messages.add_message(request, messages.ERROR, _('You do not have permission to change glosses.'))
        return HttpResponse(json.dumps({}), {'content-type': 'application/json'})

    gloss = get_object_or_404(Gloss, id=glossid, archived=False)

    lemma_get = request.POST.get('lemmaid', '')
    if not lemma_get:
        print('assign_lemma_dataset_to_gloss: no lemmaid in POST.get')
        return HttpResponse(json.dumps({}), {'content-type': 'application/json'})
    lemmaid = int(lemma_get)

    try:
        dummy_lemma = LemmaIdgloss.objects.get(pk=lemmaid)
    except ObjectDoesNotExist:
        print('assign_lemma_dataset_to_gloss: dummy lemma does not exist: ', lemmaid)
        return HttpResponse(json.dumps({}), {'content-type': 'application/json'})

    dataset_of_dummy = dummy_lemma.dataset
    dummy_dataset_name = str(dataset_of_dummy.name)

    selected_datasets = get_selected_datasets_for_user(request.user)

    if not request.user.is_superuser:
        # check that user can write to the dataset
        datasets_user_can_change = get_objects_for_user(request.user, 'change_dataset', Dataset)
        if dataset_of_dummy not in datasets_user_can_change:
            failure_message = _('You do not have change permission for') + ' ' + dummy_lemma.dataset.name
            return HttpResponse(json.dumps({'glossid': str(glossid),
                                            'datasetname': str(failure_message) }), {'content-type': 'application/json'})

    try:
        gloss.lemma = dummy_lemma
        gloss.save()
    except (DatabaseError, IntegrityError):
        failure_message = _('Error assigning lemma to gloss.')
        return HttpResponse(json.dumps({'glossid': str(glossid),
                                        'datasetname': str(failure_message)}), {'content-type': 'application/json'})

    success_message = _('Gloss saved to dataset') + ' ' + dummy_lemma.dataset.name

    return HttpResponse(json.dumps({'glossid': str(gloss.id),
                                    'datasetname': str(success_message) }), {'content-type': 'application/json'})


def okay_to_update_gloss(request, gloss):

    if not gloss or not gloss.lemma:
        return False

    if gloss.lemma.dataset not in guardian.shortcuts.get_objects_for_user(request.user, ['change_dataset'],
                                                                          Dataset, any_perm=True):
        return False
    
    return True


@permission_required('dictionary.change_gloss')
def toggle_tag(request, glossid, tagid):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_tag(request, gloss, tagid)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_semantic_field(request, glossid, semanticfield):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_semanticfield(request, gloss, semanticfield)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_wordclass(request, glossid, wordclass):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_wordclass(request, gloss, wordclass)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_namedentity(request, glossid, namedentity):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_namedentity(request, gloss, namedentity)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_handedness(request, glossid, handedness):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_handedness(request, gloss, handedness)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_domhndsh(request, glossid, domhndsh):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_domhndsh(request, gloss, domhndsh)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_subhndsh(request, glossid, subhndsh):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_subhndsh(request, gloss, subhndsh)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_handCh(request, glossid, handCh):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_handCh(request, gloss, handCh)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_relatArtic(request, glossid, relatArtic):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_relatArtic(request, gloss, relatArtic)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_locprim(request, glossid, locprim):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_locprim(request, gloss, locprim)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_contType(request, glossid, contType):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_contType(request, gloss, contType)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_movSh(request, glossid, movSh):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_movSh(request, gloss, movSh)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_movDir(request, glossid, movDir):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_movDir(request, gloss, movDir)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_repeat(request, glossid, repeat):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_repeat(request, gloss, repeat)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_altern(request, glossid, altern):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_altern(request, gloss, altern)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_relOriMov(request, glossid, relOriMov):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_relOriMov(request, gloss, relOriMov)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_relOriLoc(request, glossid, relOriLoc):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_relOriLoc(request, gloss, relOriLoc)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_oriCh(request, glossid, oriCh):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = mapping_toggle_oriCh(request, gloss, oriCh)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def toggle_language_fields(request, glossid):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = batch_edit_update_gloss(request, gloss)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def quick_create_sense(request, glossid):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    result = batch_edit_create_sense(request, gloss)

    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def add_affiliation(request, glossid):
    """View to add an affiliation to a gloss"""
    form = AffiliationUpdateForm(request.POST)

    if not form.is_valid():
        return JsonResponse({})

    thisgloss = get_object_or_404(Gloss, id=glossid, archived=False)

    if not okay_to_update_gloss(request, thisgloss):
        return JsonResponse({})

    tags_label = 'Affiliation'

    deletetag = request.POST.get('delete', '')
    affiliation_id = request.POST.get('affiliation', '')
    if not deletetag or not affiliation_id:
        # fallback to the requesting page
        return JsonResponse({})

    try:
        affiliationid = int(affiliation_id)
        affiliation = Affiliation.objects.get(id=affiliationid)
        old_tags_string = affiliation.name
    except (ValueError, ObjectDoesNotExist, MultipleObjectsReturned):
        # fallback to the requesting page
        return JsonResponse({})

    if deletetag == "True":
        # get the relevant AffiliatedGloss
        with atomic():
            aff = get_object_or_404(AffiliatedGloss, gloss__id=thisgloss.id, affiliation=affiliation)
            aff.delete()
            new_tags_string = ''

            revision = GlossRevision(old_value=old_tags_string, new_value=new_tags_string, field_name=tags_label,
                                     gloss=thisgloss, user=request.user, time=datetime.now(tz=get_current_timezone()))
            revision.save()
        # response = HttpResponse('deleted', {'content-type': 'text/plain'})
        result = {'affiliation': affiliation_id}
        return JsonResponse(result)

    old_tags_string = ''
    with atomic():
        affiliation = Affiliation.objects.get(id=affiliationid)
        new_affiliation, created = AffiliatedGloss.objects.get_or_create(affiliation=affiliation, gloss=thisgloss)
        new_tags_string = affiliation.name
        revision = GlossRevision(old_value=old_tags_string, new_value=new_tags_string, field_name=tags_label,
                                 gloss=thisgloss, user=request.user, time=datetime.now(tz=get_current_timezone()))
        revision.save()

    result = {'affiliation': affiliation_id}
    return JsonResponse(result)


@permission_required('dictionary.change_gloss')
def restore_gloss(request, glossid):

    gloss = Gloss.objects.filter(id=glossid, archived=True).first()

    if not okay_to_update_gloss(request, gloss):
        return JsonResponse({})

    gloss.archived = False
    gloss.save(update_fields=['archived'])

    annotation = get_default_annotationidglosstranslation(gloss)
    add_gloss_update_to_revision_history(request.user, gloss, 'restored', annotation,
                                         annotation)

    result = dict()
    result['glossid'] = str(gloss.id)

    return JsonResponse(result)
