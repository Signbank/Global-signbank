from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context, RequestContext
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from signbank.video.models import Video, GlossVideo, GlossVideoHistory
from signbank.video.forms import VideoUploadForm, VideoUploadForGlossForm, VideoUploadForSentenceForm
# from django.contrib.auth.models import User
# from datetime import datetime as DT
import os

from signbank.dictionary.models import Gloss, DeletedGlossOrMedia, ExampleSentence
from signbank.settings.base import WRITABLE_FOLDER
from signbank.tools import generate_still_image, get_default_annotationidglosstranslation


def addvideo(request):
    """View to present a video upload form and process
    the upload"""

    if request.method == 'POST':
        form = VideoUploadForGlossForm(request.POST, request.FILES)
        if form.is_valid():
            # Unpack the form
            gloss_id = form.cleaned_data['gloss_id']
            vfile = form.cleaned_data['videofile']
            redirect_url = form.cleaned_data['redirect']
            recorded = form.cleaned_data['recorded']

            # Get the gloss
            gloss = get_object_or_404(Gloss, pk=gloss_id)

            gloss.add_video(request.user, vfile, recorded)

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

def addsentencevideo(request):
    """View to present a video upload form and process
    the upload"""

    if request.method == 'POST':
        form = VideoUploadForSentenceForm(request.POST, request.FILES)
        if form.is_valid():
            # Unpack the form
            examplesentence_id = form.cleaned_data['examplesentence_id']
            vfile = form.cleaned_data['videofile']
            redirect_url = form.cleaned_data['redirect']
            recorded = form.cleaned_data['recorded']

            # Get the example sentence
            examplesentence = get_object_or_404(ExampleSentence, id=examplesentence_id)

            examplesentence.add_video(request.user, vfile, recorded)

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
