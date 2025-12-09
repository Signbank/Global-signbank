import datetime as DT

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
from django.shortcuts import render, get_object_or_404, redirect

from signbank.settings.server_specific import RECENTLY_ADDED_SIGNS_PERIOD, PREFIX_URL
from signbank.dictionary.models import Gloss, Morpheme
from signbank.dictionary.context_data import get_selected_datasets
from signbank.feedback.models import (GeneralFeedback, MissingSignFeedback, SignFeedback, SignFeedbackForm,
                                      GeneralFeedbackForm, MissingSignFeedbackForm, MorphemeFeedback,
                                      MorphemeFeedbackForm)


def index(request):
    general_feedback_form = f'{PREFIX_URL}/feedback/site'
    return render(request, 'feedback/index.html',
                  {'selected_datasets': get_selected_datasets(request),
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                   'language': settings.LANGUAGE_NAME,
                   'general_feedback_form': general_feedback_form})


@login_required
def generalfeedback(request):
    template_name = 'feedback/generalfeedback.html'
    context = {
        'language': settings.LANGUAGE_NAME,
        'selected_datasets': get_selected_datasets(request),
        'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
        'title': gettext("General Feedback"),
        'valid': False
    }

    if request.method != "POST":
        context['form'] = GeneralFeedbackForm()
        return render(request, template_name, context)

    context['form'] = form = GeneralFeedbackForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, template_name, context)

    context['valid'] = True
    feedback = GeneralFeedback(user=request.user)
    if 'comment' in form.cleaned_data:
        feedback.comment = form.cleaned_data['comment']
    if 'video' in form.cleaned_data and form.cleaned_data['video'] is not None:
        feedback.video = form.cleaned_data['video']
    feedback.save()

    sourcepage = request.GET.get('return', "")
    messages.add_message(request, messages.INFO, mark_safe(f'Thank you. Your feedback has been saved. '
                                                           f'<a href="{sourcepage}">Return to Previous Page</a>'))
    return render(request, template_name, context)


@login_required
def missingsign(request):

    posted = False  # was the feedback posted?

    selected_datasets = get_selected_datasets(request)
    sign_languages = [dataset.signlanguage.id for dataset in selected_datasets]
    # get rid of duplicates
    sign_languages = list(set(sign_languages))

    # this is used to show a table of sign languages paired with the datasets
    signlanguage_to_dataset = {}
    for dataset in selected_datasets:
        if dataset.signlanguage not in signlanguage_to_dataset:
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
    return recordsignfeedback(request, glossid, is_morpheme=False)


@login_required
def morphemefeedback(request, glossid):
    # this function checks the existence of the gloss or morpheme in the url
    return recordsignfeedback(request, glossid, is_morpheme=True)


# @atomic  # This rolls back saving feedback on failure
def recordsignfeedback(request, glossid, is_morpheme):
    """record feedback for a gloss or morpheme"""
    sourcepage = request.GET['return'] if 'return' in request.GET else ""

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
        try:
            feedback_obj = MorphemeFeedback(comment=clean['comment'],user=request.user, morpheme=sign_or_morpheme) \
                            if is_morpheme \
                            else SignFeedback(comment=clean['comment'], user=request.user, gloss=sign_or_morpheme)
            feedback_obj.save()
            messages.add_message(request, messages.INFO, mark_safe('Thank you. Your feedback has been saved. <a href="'
                                                                   + redirect_page + '">Return to Detail View</a>'))
        except (KeyError, PermissionError):
            messages.add_message(request, messages.ERROR, 'There was an error processing your feedback data.')

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
    url = request.META.get('HTTP_REFERER', '/')

    kinds = {
        'sign': SignFeedback,
        'morpheme': MorphemeFeedback,
        'general': GeneralFeedback,
        'missingsign': MissingSignFeedback
    }
    if kind not in kinds:
        return redirect(url)
    model = kinds[kind]

    field = request.POST.get('id', '')
    value = request.POST.get('value', '')

    _, id = field.split('_')

    if value == 'confirmed':
        item = get_object_or_404(model, pk=id)
        item.status = 'deleted'
        item.save()

    return redirect(url)


@permission_required('feedback.delete_signfeedback')
def recent_feedback(request):
    """View to list the feedback that's been submitted on the site"""
    selected_datasets = get_selected_datasets(request)
    group_editor = Group.objects.get(name='Editor')
    groups_of_user = request.user.groups.all()
    if group_editor not in groups_of_user:
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        return render(request, 'feedback/index.html',
                      {'selected_datasets': selected_datasets,
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                       'language': settings.LANGUAGE_NAME})

    signfeedback_objs = (SignFeedback.objects.filter(Q(**{'gloss__lemma__dataset__in': selected_datasets}))
                         .filter(status__in=('unread', 'read')))
    recently_added_feedback_since_date = DT.datetime.now(tz=get_current_timezone()) - RECENTLY_ADDED_SIGNS_PERIOD
    signfeedback_objs = (signfeedback_objs
                         .filter(date__range=[recently_added_feedback_since_date,
                                              DT.datetime.now(tz=get_current_timezone())])
                         .order_by('-date'))

    return render(request, "feedback/recent_feedback.html",
                  {'signfb': signfeedback_objs,
                   'selected_datasets': selected_datasets,
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})
