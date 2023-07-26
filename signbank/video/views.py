from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context, RequestContext
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from signbank.video.models import Video, GlossVideo, ExampleVideo, GlossVideoHistory, ExampleVideoHistory
from signbank.dictionary.models import Gloss, DeletedGlossOrMedia, ExampleSentence
from signbank.video.forms import VideoUploadForObjectForm
# from django.contrib.auth.models import User
# from datetime import datetime as DT
import os

from signbank.settings.base import WRITABLE_FOLDER
from signbank.tools import generate_still_image, get_default_annotationidglosstranslation


def addvideo(request):
    """View to present a video upload form and process
    the upload"""

    if request.method == 'POST':
        form = VideoUploadForObjectForm(request.POST, request.FILES)
        if form.is_valid():
            # Unpack the form
            object_id = form.cleaned_data['object_id']
            object_type = form.cleaned_data['object_type']
            vfile = form.cleaned_data['videofile']
            redirect_url = form.cleaned_data['redirect']
            recorded = form.cleaned_data['recorded']
            # Get the object, either a gloss or an example sentences
            if object_type == 's':
                object = get_object_or_404(ExampleSentence, id=object_id)
            elif object_type == 'g':
                object = get_object_or_404(Gloss, id=object_id)
            else: 
                return redirect(redirect_url)
            
            object.add_video(request.user, vfile, recorded)

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

@login_required
def deletesentencevideo(request, videoid):
    """Remove the video for this gloss, if there is an older version
    then reinstate that as the current video (act like undo)"""

    if request.method == "POST":
        # deal with any existing video for this sign
        examplesentence = get_object_or_404(ExampleSentence, id=videoid)
        vids = ExampleVideo.objects.filter(examplesentence=examplesentence).order_by('version')
        for v in vids:
            # this will remove the most recent video, ie it's equivalent
            # to delete if version=0
            v.reversion(revert=True)

            # Issue #162: log the deletion history
            log_entry = ExampleVideoHistory(action="delete", examplesentence=examplesentence,
                                          actor=request.user,
                                          uploadfile=os.path.basename(v.videofile.name),
                                          goal_location=v.videofile.path)
            log_entry.save()

    try:
        video = examplesentence.examplevideo_set.get(version=0)
        video.make_small_video()
    except ObjectDoesNotExist:
        pass

    # return to referer
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)


@login_required
def deletevideo(request, videoid):
    """Remove the video for this gloss, if there is an older version
    then reinstate that as the current video (act like undo)"""

    if request.method == "POST":
        # deal with any existing video for this sign
        gloss = get_object_or_404(Gloss, pk=videoid)
        vids = GlossVideo.objects.filter(gloss=gloss).order_by('version')
        for v in vids:
            # this will remove the most recent video, ie it's equivalent
            # to delete if version=0
            v.reversion(revert=True)

            # Issue #162: log the deletion history
            log_entry = GlossVideoHistory(action="delete", gloss=gloss,
                                          actor=request.user,
                                          uploadfile=os.path.basename(v.videofile.name),
                                          goal_location=v.videofile.path)
            log_entry.save()

    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    deleted_video = DeletedGlossOrMedia()
    deleted_video.item_type = 'video'
    deleted_video.idgloss = gloss.idgloss
    deleted_video.annotation_idgloss = default_annotationidglosstranslation
    deleted_video.old_pk = gloss.pk
    deleted_video.filename = gloss.get_video_path()
    deleted_video.save()

    try:
        video = gloss.glossvideo_set.get(version=0)
        video.make_small_video()
        video.make_poster_image()
    except ObjectDoesNotExist:
        pass

    # return to referer
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)


def video(request, videoid):
    """Redirect to the video url for this videoid"""

    video = get_object_or_404(GlossVideo, gloss_id=videoid)

    return redirect(video)


def create_still_images(request):
    processed_videos = []
    for video in GlossVideo.objects.filter(version=0):
        generate_still_image(video)
        processed_videos.append(str(video))
    return HttpResponse('Processed videos: <br/>' + "<br/>".join(processed_videos))
