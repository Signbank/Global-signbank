
from signbank.settings.server_specific import PREFIX_URL
import os
from signbank.feedback.models import *
from django import forms
from django.shortcuts import render, get_object_or_404, redirect, render_to_response
from django.template import Context, RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.conf import settings 
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.utils.safestring import mark_safe
from signbank.tools import get_selected_datasets_for_user
from django.utils.translation import override, ugettext_lazy as _, activate
from signbank.settings.server_specific import RECENTLY_ADDED_SIGNS_PERIOD
import datetime as DT
from django.utils.timezone import get_current_timezone

from django.db.transaction import atomic


import time

def index(request):
    return render(request, 'feedback/index.html',
                              { 'selected_datasets': get_selected_datasets_for_user(request.user),
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
            
            if 'video' in form.cleaned_data and form.cleaned_data['video'] != None:
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
            return render(request, 'feedback/generalfeedback.html', {'language': settings.LANGUAGE_NAME,
                                                                     'selected_datasets': get_selected_datasets_for_user(request.user),
                                                                     'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                                                                    'title':"General Feedback",
                                                                    'form': form,
                                                                    'valid': valid })
    else:
        form = GeneralFeedbackForm()

    return render(request,"feedback/generalfeedback.html",
                              {'language': settings.LANGUAGE_NAME,
                                'selected_datasets': get_selected_datasets_for_user(request.user),
                                'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                               'title':"General Feedback",
                               'form': form,
                               'valid': valid })

@login_required
def missingsign(request):

    posted = False  # was the feedback posted?

    selected_datasets = get_selected_datasets_for_user(request.user)
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
            
            if 'video' in form.cleaned_data and form.cleaned_data['video'] != None:
                fb.video = form.cleaned_data['video']

            # these last two are required either way (video or not)
            fb.meaning = form.cleaned_data['meaning']
            fb.comments = form.cleaned_data['comments']
    
            fb.save()
            posted = True

    else:
        form = MissingSignFeedbackForm(sign_languages=sign_languages)

    return render(request, 'feedback/missingsign.html',
                               {'language': settings.LANGUAGE_NAME,
                                'selected_datasets': get_selected_datasets_for_user(request.user),
                                'signlanguage_to_dataset': signlanguage_to_dataset,
                                'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                                'posted': posted,
                                'form': form})


@permission_required('feedback.delete_generalfeedback')
def showfeedback(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    from django.contrib.auth.models import Group
    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets_for_user(request.user),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    general = GeneralFeedback.objects.filter(status='unread')
    
    return render(request, "feedback/show_general_feedback.html",
                              {'general': general,
                               'selected_datasets': get_selected_datasets_for_user(request.user),
                                'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


@permission_required('feedback.delete_generalfeedback')
def showfeedback_signs(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    from django.contrib.auth.models import Group
    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets_for_user(request.user),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    selected_datasets = get_selected_datasets_for_user(request.user)
    signfb = SignFeedback.objects.filter(Q(**{'gloss__lemma__dataset__in': selected_datasets})).filter(
        status__in=('unread', 'read'))

    return render(request, "feedback/show_feedback_signs.html",
                  {'signfb': signfb,
                   'selected_datasets': get_selected_datasets_for_user(request.user),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


@permission_required('feedback.delete_generalfeedback')
def showfeedback_morphemes(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    from django.contrib.auth.models import Group
    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets_for_user(request.user),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    selected_datasets = get_selected_datasets_for_user(request.user)
    # morpheme feedback exists since after the morpheme field was added to the MorphemeFeedback model
    morphfb = MorphemeFeedback.objects.filter(Q(**{'morpheme__lemma__dataset__in': selected_datasets})).filter(
        status__in=('unread', 'read'))

    return render(request, "feedback/show_feedback_morphemes.html",
                  {'morphfb': morphfb,
                   'selected_datasets': get_selected_datasets_for_user(request.user),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


@permission_required('feedback.delete_generalfeedback')
def showfeedback_missing(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    from django.contrib.auth.models import Group
    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets_for_user(request.user),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    missing = MissingSignFeedback.objects.filter(status='unread')

    return render(request, "feedback/show_feedback_missing_signs.html",
                  {'missing': missing,
                   'selected_datasets': get_selected_datasets_for_user(request.user),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


@login_required
def glossfeedback(request, glossid):
    request_path = request.path
    if 'morpheme' in request_path:
        morpheme = get_object_or_404(Morpheme, id=glossid)
    else:
        gloss = get_object_or_404(Gloss, id=glossid)
    return recordsignfeedback(request, glossid)


@login_required
def morphemefeedback(request, glossid):
    request_path = request.path
    if 'morpheme' in request_path:
        morpheme = get_object_or_404(Morpheme, id=glossid)
    else:
        gloss = get_object_or_404(Gloss, id=glossid)
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
        sign_or_morpheme = get_object_or_404(Gloss, id=glossid)
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
                                                       'selected_datasets': get_selected_datasets_for_user(request.user),
                                                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})
        except (KeyError, PermissionError):
            messages.add_message(request, messages.ERROR, 'There was an error processing your feedback data.')
            return render(request, feedback_template, {'feedback_form': feedback_form,
                                                       'sourcepage': sourcepage,
                                                       'selected_datasets': get_selected_datasets_for_user(request.user),
                                                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})
    return render(request, feedback_template,
                              {'feedback_form': feedback_form,
                               'sourcepage': sourcepage,
                               'selected_datasets': get_selected_datasets_for_user(request.user),
                                'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

#--------------------
#  deleting feedback
#--------------------

import django
# @permission_required('feedback.delete_generalfeedback')
def delete(request, kind, id):
    """Mark a feedback item as deleted, kind 'signfeedback', 'generalfeedback' or 'missingsign'"""

    # print('delete feedback kind: ', kind)
    if kind == 'sign':
        KindModel = django.apps.apps.get_model('feedback', 'SignFeedback')
    elif kind == 'morpheme':
        KindModel = django.apps.apps.get_model('feedback', 'MorphemeFeedback')
    elif kind == 'general':
        KindModel = django.apps.apps.get_model('feedback', 'GeneralFeedback')
    elif kind == 'missingsign':
        KindModel = django.apps.apps.get_model('feedback', 'MissingSignFeedback')
    else:
        raise Http404

    field = request.POST.get('id', '')
    value = request.POST.get('value', '')

    print('feedback delete id: ', field)
    (what, fbid) = field.split('_')

    if value == 'confirmed':
        print('confirmed')
    item = get_object_or_404(KindModel, pk=fbid)
    print('feedback id: ', id, ', delete kind: ', kind, ', KindModel: ', KindModel, ', what: ', what)
    # mark as deleted
    item.status = 'deleted'
    item.save()

    # return to referer
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)
    

@permission_required('feedback.delete_generalfeedback')
def recent_feedback(request):
    """View to list the feedback that's been submitted on the site"""

    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR, _('Please login to view feedback.'))
        return HttpResponseRedirect(reverse('registration:auth_login'))

    from django.contrib.auth.models import Group
    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': get_selected_datasets_for_user(request.user),
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    selected_datasets = get_selected_datasets_for_user(request.user)
    signfb = SignFeedback.objects.filter(Q(**{'gloss__lemma__dataset__in': selected_datasets})).filter(
        status__in=('unread', 'read'))
    recently_added_feedback_since_date = DT.datetime.now(tz=get_current_timezone()) - RECENTLY_ADDED_SIGNS_PERIOD
    signfb = signfb.filter(
        date__range=[recently_added_feedback_since_date, DT.datetime.now(tz=get_current_timezone())]).order_by(
        'date').reverse()

    return render(request, "feedback/recent_feedback.html",
                  {'signfb': signfb,
                   'selected_datasets': get_selected_datasets_for_user(request.user),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

