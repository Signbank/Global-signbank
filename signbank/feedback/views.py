import datetime as DT

import django
from django.utils.timezone import get_current_timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _, gettext
from django.contrib.auth.models import Group
from django.db.models import Q

from signbank.settings.server_specific import RECENTLY_ADDED_SIGNS_PERIOD

from django.shortcuts import render, get_object_or_404, redirect

from signbank.dictionary.models import Gloss, Morpheme
from signbank.dictionary.context_data import get_selected_datasets
from signbank.feedback.models import (GeneralFeedback, MissingSignFeedback, SignFeedback, SignFeedbackForm,
                                      GeneralFeedbackForm, MissingSignFeedbackForm, MorphemeFeedback, MorphemeFeedbackForm)


def index(request):
    return render(request, 'feedback/index.html',
                  {'selected_datasets': get_selected_datasets(request),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                   'language': settings.LANGUAGE_NAME})


@login_required
def generalfeedback(request):
    feedback = GeneralFeedback()
    valid = False

    if request.method == "POST":
        form = GeneralFeedbackForm(request.POST, request.FILES)
        if form.is_valid():           
            
            feedback = GeneralFeedback(user=request.user)
            if 'comment' in form.cleaned_data: 
                feedback.comment = form.cleaned_data['comment'] 
            
            if 'video' in form.cleaned_data and form.cleaned_data['video'] is not None:
                feedback.video = form.cleaned_data['video']
                
            feedback.save()
            valid = True
            request_path = request.path
            if 'return' in request.GET:
                sourcepage = request.GET['return']
            else:
                sourcepage = ""

            messages.add_message(request, messages.INFO, mark_safe(
                    'Thank you. Your feedback has been saved. <a href="' + sourcepage + '">Return to Previous Page</a>'))

            # return HttpResponseRedirect("")
            return render(request, 'feedback/generalfeedback.html',
                          {'language': settings.LANGUAGE_NAME,
                           'selected_datasets': get_selected_datasets(request),
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                           'title': gettext("General Feedback"),
                           'form': form,
                           'valid': valid})
    else:
        form = GeneralFeedbackForm()

    return render(request, "feedback/generalfeedback.html",
                  {'language': settings.LANGUAGE_NAME,
                   'selected_datasets': get_selected_datasets(request),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                   'title': gettext("General Feedback"),
                   'form': form,
                   'valid': valid})


@login_required
def missingsign(request):

    posted = False  # was the feedback posted?

    selected_datasets = get_selected_datasets(request)
    sign_languages = [dataset.signlanguage.id for dataset in selected_datasets]
    # get rid of duplicates
    sign_languages = list(set(sign_languages))

    # this is used to show a table of sign languages paired with the datasets
    signlanguage_to_dataset = dict()
    for dataset in selected_datasets:
        if dataset.signlanguage not in signlanguage_to_dataset.keys():
            signlanguage_to_dataset[dataset.signlanguage] = [(dataset.name, dataset.acronym)]
        else:
            signlanguage_to_dataset[dataset.signlanguage].append((dataset.name, dataset.acronym))

    if request.method == "POST":
        
        fb = MissingSignFeedback()
        fb.user = request.user
        
        form = MissingSignFeedbackForm(request.POST, request.FILES, sign_languages=sign_languages)

        if form.is_valid(): 
            
            # either we get video of the new sign or we get the 
            # description via the form

            if 'signlanguage' in form.cleaned_data:
                # the form yields a sign language object
                fb.signlanguage = form.cleaned_data['signlanguage']
            
            if 'video' in form.cleaned_data and form.cleaned_data['video'] is not None:
                fb.video = form.cleaned_data['video']

            if 'sentence' in form.cleaned_data and form.cleaned_data['sentence'] is not None:
                fb.sentence = form.cleaned_data['sentence']

            # these last two are required either way (video or not)
            fb.meaning = form.cleaned_data['meaning']
            fb.comments = form.cleaned_data['comments']
    
            fb.save()
            fb.save_video()
            fb.save_sentence_video()
            posted = True

    else:
        form = MissingSignFeedbackForm(sign_languages=sign_languages)

    return render(request, 'feedback/missingsign.html',
                  {'language': settings.LANGUAGE_NAME,
                   'selected_datasets': get_selected_datasets(request),
                   'signlanguage_to_dataset': signlanguage_to_dataset,
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                   'posted': posted,
                   'form': form})


@permission_required('feedback.delete_generalfeedback')
def showfeedback(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets(request),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    general = GeneralFeedback.objects.filter(status='unread')
    
    return render(request, "feedback/show_general_feedback.html",
                  {'general': general,
                   'selected_datasets': get_selected_datasets(request),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


@permission_required('feedback.delete_signfeedback')
def showfeedback_signs(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets(request),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    selected_datasets = get_selected_datasets(request)
    signfb = SignFeedback.objects.filter(Q(**{'gloss__lemma__dataset__in': selected_datasets})).filter(
        status__in=('unread', 'read'))

    return render(request, "feedback/show_feedback_signs.html",
                  {'signfb': signfb,
                   'selected_datasets': get_selected_datasets(request),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


@permission_required('feedback.delete_morphemefeedback')
def showfeedback_morphemes(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets(request),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    selected_datasets = get_selected_datasets(request)
    # morpheme feedback exists since after the morpheme field was added to the MorphemeFeedback model
    morphfb = MorphemeFeedback.objects.filter(Q(**{'morpheme__lemma__dataset__in': selected_datasets})).filter(
        status__in=('unread', 'read'))

    return render(request, "feedback/show_feedback_morphemes.html",
                  {'morphfb': morphfb,
                   'selected_datasets': get_selected_datasets(request),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


@permission_required('feedback.delete_missingsignfeedback')
def showfeedback_missing(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets(request),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    missing = MissingSignFeedback.objects.filter(status='unread')

    return render(request, "feedback/show_feedback_missing_signs.html",
                  {'missing': missing,
                   'selected_datasets': get_selected_datasets(request),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


@login_required
def glossfeedback(request, glossid):
    # this function checks the existence of the gloss or morpheme in the url
    request_path = request.path
    if 'morpheme' in request_path:
        morpheme = get_object_or_404(Morpheme, id=glossid)
    else:
        gloss = get_object_or_404(Gloss, id=glossid, archived=False)
    return recordsignfeedback(request, glossid)


@login_required
def morphemefeedback(request, glossid):
    # this function checks the existence of the gloss or morpheme in the url
    request_path = request.path
    if 'morpheme' in request_path:
        morpheme = get_object_or_404(Morpheme, id=glossid)
    else:
        gloss = get_object_or_404(Gloss, id=glossid, archived=False)
    return recordsignfeedback(request, glossid)


# @atomic  # This rolls back saving feedback on failure
def recordsignfeedback(request, glossid):
    """record feedback for a gloss or morpheme"""

    # get the page to return to from the get request
    if 'return' in request.GET:
        sourcepage = request.GET['return']
    else:
        sourcepage = ""

    is_morpheme = 'morpheme' in request.path

    if is_morpheme:
        sign_or_morpheme = get_object_or_404(Morpheme, id=glossid)
        feedback_form = MorphemeFeedbackForm(request.POST) if request.method == 'POST' else MorphemeFeedbackForm()
        feedback_template = "feedback/morphemefeedback.html"
        redirect_page = settings.PREFIX_URL + '/dictionary/morpheme/' + str(glossid)
    else:
        sign_or_morpheme = get_object_or_404(Gloss, id=glossid, archived=False)
        feedback_form = SignFeedbackForm(request.POST) if request.method == 'POST' else SignFeedbackForm()
        feedback_template = "feedback/signfeedback.html"
        redirect_page = settings.PREFIX_URL + '/dictionary/gloss/' + str(glossid)

    if feedback_form.is_valid():
        clean = feedback_form.cleaned_data
        # create a SignFeedback object to store the result in the db

        try:
            if is_morpheme:
                sfb = MorphemeFeedback(
                    comment=clean['comment'],
                    user=request.user,
                    morpheme=sign_or_morpheme
                    )
                sfb.save()
            else:
                sfb = SignFeedback(
                    comment=clean['comment'],
                    user=request.user,
                    gloss=sign_or_morpheme
                    )
                sfb.save()
            # return a message with a link to the original gloss or morpheme page
            messages.add_message(request, messages.INFO, mark_safe('Thank you. Your feedback has been saved. <a href="'+redirect_page+'">Return to Detail View</a>'))
            return render(request, feedback_template, {'feedback_form': feedback_form,
                                                       'sourcepage': sourcepage,
                                                       'selected_datasets': get_selected_datasets(request),
                                                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})
        except (KeyError, PermissionError):
            messages.add_message(request, messages.ERROR, 'There was an error processing your feedback data.')
            return render(request, feedback_template, {'feedback_form': feedback_form,
                                                       'sourcepage': sourcepage,
                                                       'selected_datasets': get_selected_datasets(request),
                                                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})
    return render(request, feedback_template,
                  {'feedback_form': feedback_form,
                   'sourcepage': sourcepage,
                   'selected_datasets': get_selected_datasets(request),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

#
#  deleting feedback
#
@permission_required('feedback.delete_generalfeedback')
def delete(request, kind, id):
    """Mark a feedback item as deleted, kind 'signfeedback', 'generalfeedback' or 'missingsign'"""

    # return to referer
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'

    if kind == 'sign':
        KindModel = django.apps.apps.get_model('feedback', 'SignFeedback')
    elif kind == 'morpheme':
        KindModel = django.apps.apps.get_model('feedback', 'MorphemeFeedback')
    elif kind == 'general':
        KindModel = django.apps.apps.get_model('feedback', 'GeneralFeedback')
    elif kind == 'missingsign':
        KindModel = django.apps.apps.get_model('feedback', 'MissingSignFeedback')
    else:
        return redirect(url)

    field = request.POST.get('id', '')
    value = request.POST.get('value', '')

    (what, fbid) = field.split('_')

    if value == 'confirmed':
        item = get_object_or_404(KindModel, pk=fbid)
        item.status = 'deleted'
        item.save()

    return redirect(url)
    

@permission_required('feedback.delete_signfeedback')
def recent_feedback(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets(request),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    selected_datasets = get_selected_datasets(request)
    signfb = SignFeedback.objects.filter(Q(**{'gloss__lemma__dataset__in': selected_datasets})).filter(
        status__in=('unread', 'read'))
    recently_added_feedback_since_date = DT.datetime.now(tz=get_current_timezone()) - RECENTLY_ADDED_SIGNS_PERIOD
    signfb = signfb.filter(
        date__range=[recently_added_feedback_since_date, DT.datetime.now(tz=get_current_timezone())]).order_by(
        '-date')

    return render(request, "feedback/recent_feedback.html",
                  {'signfb': signfb,
                   'selected_datasets': get_selected_datasets(request),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

