from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context, RequestContext
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from signbank.video.models import Video, GlossVideo, ExampleVideo, GlossVideoHistory, ExampleVideoHistory
from signbank.dictionary.models import Gloss, DeletedGlossOrMedia, ExampleSentence, Morpheme, AnnotatedSentence
from signbank.video.forms import VideoUploadForObjectForm
from django.http import JsonResponse
# from django.contrib.auth.models import User
# from datetime import datetime as DT
import os
import json

from signbank.settings.base import WRITABLE_FOLDER
from signbank.tools import generate_still_image, get_default_annotationidglosstranslation


def addvideo(request):
    """View to present a video upload form and process the upload"""

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
            if object_type == 'examplesentence_video':
                sentence = ExampleSentence.objects.filter(id=object_id).first()
                if not sentence:
                    redirect(redirect_url)
                sentence.add_video(request.user, vfile, recorded)
            elif object_type == 'gloss_video':
                gloss = Gloss.objects.filter(id=object_id).first()
                if not gloss:
                    redirect(redirect_url)
                gloss.add_video(request.user, vfile, recorded)
            elif object_type == 'morpheme_video':
                morpheme = Morpheme.objects.filter(id=object_id).first()
                if not morpheme:
                    redirect(redirect_url)
                morpheme.add_video(request.user, vfile, recorded)
            elif object_type == 'annotated_video': 
                # make an annotated sentence
                eaf_file = form.cleaned_data['eaffile']
                annotatedSentence = AnnotatedSentence.objects.create()
                
                gloss = Gloss.objects.filter(id=object_id).first()
                annotations = form.cleaned_data['feedbackdata']
                annotatedSentence.add_annotations(annotations, gloss)
                
                translations = form.cleaned_data['translations']
                if translations:
                    annotatedSentence.add_translations(json.loads(translations))

                contexts = form.cleaned_data['contexts']
                if contexts:
                    annotatedSentence.add_contexts(json.loads(contexts))
                    
                corpus = form.cleaned_data['corpus_name']
                annotatedSentence.add_video(request.user, vfile, eaf_file, corpus)
                
                annotatedSentence.save()

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

def find_non_overlapping_annotated_glosses(timeslots, annotations_tier_1, annotations_tier_2):
    non_overlapping_glosses = []

    for annotation_2 in annotations_tier_2:
        is_overlapping = False
        for annotation_1 in annotations_tier_1:
            # timecode to time in ms
            start_1 = int(timeslots[annotation_1[0]])
            end_1 = int(timeslots[annotation_1[1]])
            start_2 = int(timeslots[annotation_2[0]])
            end_2 = int(timeslots[annotation_2[1]])
            if (start_2 >= start_1 and start_2 <= end_1) or (end_2 >= start_1 and end_2 <= end_1):
                is_overlapping = True
                break
        if not is_overlapping:
            non_overlapping_glosses.append(annotation_2)

    return non_overlapping_glosses

def process_eaffile(request):
    import magic
    from pympi.Elan import Eaf
    from signbank.dictionary.models import AnnotationIdglossTranslation
    glosses, sentences = [], []
    sentence_dict = {}

    if request.method == 'POST':
        check_gloss_label = request.POST.get('check_gloss_label', '')
        labels_not_found = []
        uploaded_file = request.FILES['eaffile']
        file_type = magic.from_buffer(open(uploaded_file.temporary_file_path(), "rb").read(2040), mime=True)
        if not (uploaded_file.name.endswith('.eaf') and file_type == 'text/xml'):
            return JsonResponse({'error': 'Invalid file. Please try again.'})

        eaf = Eaf(uploaded_file.temporary_file_path())
        
        # Add glosses from the right hand
        for annotation in eaf.tiers['Glosses R'][0].values():
            gloss_label = annotation[2]
            if AnnotationIdglossTranslation.objects.filter(text__exact=gloss_label).exists():
                start = int(eaf.timeslots[annotation[0]])
                end = int(eaf.timeslots[annotation[1]])
                glosses.append([gloss_label, start, end])
            else:
                labels_not_found.append(gloss_label)

        # Add glosses from the left hand, if they don't overlap with the right hand
        for annotation in find_non_overlapping_annotated_glosses(eaf.timeslots, eaf.tiers['Glosses R'][0].values(), eaf.tiers['Glosses L'][0].values()):
            gloss_label = annotation[2]
            if AnnotationIdglossTranslation.objects.filter(text__exact=gloss_label).exists():
                start = int(eaf.timeslots[annotation[0]])
                end = int(eaf.timeslots[annotation[1]])
                glosses.append([gloss_label, start, end])
            else:
                labels_not_found.append(gloss_label)
        
        # Sort the list of glosses by the "start" value
        glosses = sorted(glosses, key=lambda x: x[1])

        if glosses == []:
            return JsonResponse({'error': 'No annotations found. Please try again.'})
        
        if 'Sentences' in eaf.tiers:
            for annotation in eaf.tiers['Sentences'][0].values():
                sentences.append(annotation[2])
        
        for sentence_i, sentence in enumerate(sentences):
            sentence_dict[sentence_i] = sentence

    # Create the annotations table
    annotations_table_html = render(request, 'annotations_table.html', {'glosses_list': glosses, 'check_gloss_label': [check_gloss_label], 'labels_not_found': labels_not_found}).content.decode('utf-8')
    sentences_json = json.dumps(sentence_dict)

    return JsonResponse({'annotations_table_html': annotations_table_html, 'sentences': sentences_json})


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
