import datetime as DT
from collections import defaultdict

from django.utils.timezone import get_current_timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpRequest
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _, gettext
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
    template_name = 'feedback/missingsign.html'
    context = {
        "language": settings.LANGUAGE_NAME,
        "SHOW_DATASET_INTERFACE_OPTIONS": settings.SHOW_DATASET_INTERFACE_OPTIONS,
        "posted": False,
    }

    context['selected_datasets'] = selected_datasets = get_selected_datasets(request)
    sign_languages = list(set([dataset.signlanguage_id for dataset in selected_datasets]))

    signlanguage_to_dataset = defaultdict(list)
    for dataset in selected_datasets:
        signlanguage_to_dataset[dataset.signlanguage].append((dataset.name, dataset.acronym))
    context['signlanguage_to_dataset'] = dict(signlanguage_to_dataset)

    if request.method != "POST":
        context['form'] = MissingSignFeedbackForm(sign_languages=sign_languages)
        return render(request, template_name, context)

    context['posted'] = True
    context['form'] = form = MissingSignFeedbackForm(request.POST, request.FILES, sign_languages=sign_languages)
    if not form.is_valid():
        return render(request, template_name, context)

    create_missing_sign_feedback(request.user, form.cleaned_data)

    return render(request, template_name, context)


def create_missing_sign_feedback(user, data):
    missing_sign_feedback = MissingSignFeedback(
        user=user,
        meaning=data["meaning"],
        comments=data["comments"],
        signlanguage=data.get("signlanguage"),
        video=data.get("video"),
        sentence=data.get("sentence"),
    )
    missing_sign_feedback.save()
    missing_sign_feedback.save_video()
    missing_sign_feedback.save_sentence_video()


def generic_showfeedback(request: HttpRequest, extra_context: dict, template_name: str) -> HttpResponse:
    context = {
        "selected_datasets": get_selected_datasets(request),
        "SHOW_DATASET_INTERFACE_OPTIONS": settings.SHOW_DATASET_INTERFACE_OPTIONS,
    }

    if not request.user.groups.filter(name='Editor').exists():
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        context['language'] = settings.LANGUAGE_NAME
        return render(request, 'feedback/index.html', context)

    context.update(extra_context)
    return render(request, template_name, context)


@permission_required('feedback.delete_generalfeedback')
def showfeedback(request):
    """View to list the feedback that's been submitted on the site"""
    extra_context = {'general': GeneralFeedback.objects.filter(status='unread')}
    return generic_showfeedback(request, extra_context, "feedback/show_general_feedback.html")


@permission_required('feedback.delete_signfeedback')
def showfeedback_signs(request):
    """View to list the feedback that's been submitted on the site"""
    extra_context = {'signfb': (SignFeedback.objects
                                .filter(gloss__lemma__dataset__in=get_selected_datasets(request))
                                .filter(status__in=('unread', 'read')))}
    return generic_showfeedback(request, extra_context, "feedback/show_feedback_signs.html")


@permission_required('feedback.delete_morphemefeedback')
def showfeedback_morphemes(request):
    """View to list the feedback that's been submitted on the site"""
    extra_context = {'morphfb': (MorphemeFeedback.objects
                                 .filter(morpheme__lemma__dataset__in=get_selected_datasets(request))
                                 .filter(status__in=('unread', 'read')))}
    return generic_showfeedback(request, extra_context, "feedback/show_feedback_morphemes.html")


@permission_required('feedback.delete_missingsignfeedback')
def showfeedback_missing(request):
    """View to list the feedback that's been submitted on the site"""
    extra_context = {'missing': MissingSignFeedback.objects.filter(status='unread')}
    return generic_showfeedback(request, extra_context, "feedback/show_feedback_missing_signs.html")


@login_required
def glossfeedback(request, glossid):
    # this function checks the existence of the gloss or morpheme in the url
    return recordsignfeedback(request, id=glossid, is_morpheme=False)


@login_required
def morphemefeedback(request, morphemeid):
    # this function checks the existence of the gloss or morpheme in the url
    return recordsignfeedback(request, id=morphemeid, is_morpheme=True)


# @atomic  # This rolls back saving feedback on failure
def recordsignfeedback(request, id, is_morpheme):
    """record feedback for a gloss or morpheme"""
    sourcepage = request.GET.get('return', "")
    form_class = MorphemeFeedbackForm if is_morpheme else SignFeedbackForm
    form = form_class(request.POST) if request.method == "POST" else form_class()
    template_name = "feedback/morphemefeedback.html" if is_morpheme else "feedback/signfeedback.html"

    context = {
        "feedback_form": form,
        "sourcepage": sourcepage,
        "selected_datasets": get_selected_datasets(request),
        "SHOW_DATASET_INTERFACE_OPTIONS": settings.SHOW_DATASET_INTERFACE_OPTIONS,
    }

    if not form.is_valid():
        return render(request, template_name, context)

    model = Morpheme if is_morpheme else Gloss
    obj = get_object_or_404(model, id=id, archived=False)

    comment = form.cleaned_data.get('comment')
    if not comment:
        messages.add_message(request, messages.ERROR, "There was an error processing your feedback data.")
        return render(request, template_name, context)

    feedback_obj = MorphemeFeedback(comment=comment, user=request.user, morpheme=obj) \
                    if is_morpheme else SignFeedback(comment=comment, user=request.user, gloss=obj)
    feedback_obj.save()

    obj_type = 'morpheme' if is_morpheme else 'gloss'
    message = (f'Thank you. Your feedback has been saved. '
               f'<a href="{settings.PREFIX_URL}/dictionary/{obj_type}/{str(id)}">Return to Detail View</a>')
    messages.add_message(request, messages.INFO, mark_safe(message))

    return render(request, template_name, context)


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

    if request.POST.get('value', '') == 'confirmed':
        item = get_object_or_404(model, pk=id)
        item.status = 'deleted'
        item.save()

    return redirect(url)


@permission_required('feedback.delete_signfeedback')
def recent_feedback(request):
    """View to list the feedback that's been submitted on the site"""
    selected_datasets = get_selected_datasets(request)
    context = {
        "selected_datasets": selected_datasets,
        "SHOW_DATASET_INTERFACE_OPTIONS": settings.SHOW_DATASET_INTERFACE_OPTIONS,
    }

    if not request.user.groups.filter(name='Editor').exists():
        messages.add_message(request, messages.ERROR, _('You must be in group Editor to view feedback.'))
        context['language'] = settings.LANGUAGE_NAME
        return render(request, 'feedback/index.html', context)

    now = DT.datetime.now(tz=get_current_timezone())
    context['signfb'] = (SignFeedback.objects
                         .filter(gloss__lemma__dataset__in=selected_datasets)
                         .filter(status__in=('unread', 'read'))
                         .filter(date__range=[now - RECENTLY_ADDED_SIGNS_PERIOD, now])
                         .order_by('-date'))
    return render(request, "feedback/recent_feedback.html", context)
