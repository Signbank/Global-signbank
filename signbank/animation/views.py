from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context, RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext as _

from signbank.animation.models import GlossAnimation
from signbank.dictionary.models import Gloss, DeletedGlossOrMedia, ExampleSentence, Morpheme, AnnotatedSentence, Dataset, AnnotatedSentenceSource
from signbank.animation.forms import AnimationUploadForObjectForm
from django.http import JsonResponse
# from django.contrib.auth.models import User
# from datetime import datetime as DT
import os
import json

from signbank.settings.base import WRITABLE_FOLDER
from signbank.tools import generate_still_image, get_default_annotationidglosstranslation


def addanimation(request):
    """View to present an animation upload form and process the upload"""

    if request.method == 'POST':
        last_used_dataset = request.session['last_used_dataset']
        dataset = Dataset.objects.filter(acronym=last_used_dataset).first()
        dataset_languages = dataset.translation_languages.all()
        form = AnimationUploadForObjectForm(request.POST, request.FILES, languages=dataset_languages, dataset=dataset)
        if form.is_valid():
            # Unpack the form
            gloss_id = form.cleaned_data['gloss_id']
            object_type = form.cleaned_data['object_type']
            file = form.cleaned_data['file']
            redirect_url = form.cleaned_data['redirect']
            if object_type == 'gloss_animation':
                gloss = Gloss.objects.filter(id=int(gloss_id)).first()
                if not gloss:
                    redirect(redirect_url)
                gloss.add_animation(request.user, file)

            return redirect(redirect_url)

    # if we can't process the form, just redirect back to the
    # referring page, should just be the case of hitting
    # Upload without choosing a file but could be
    # a malicious request, if no referrer, go back to root
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)


def animation(request, animationid):
    """Redirect to the animation url for this animationid"""

    animation = get_object_or_404(GlossAnimation, id=animationid, gloss__archived=False)

    return redirect(animation)

