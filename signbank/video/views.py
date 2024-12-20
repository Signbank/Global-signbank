from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context, RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext as _
from django.forms.utils import ValidationError

from signbank.video.models import GlossVideo, ExampleVideo, GlossVideoHistory, ExampleVideoHistory, GlossVideoNME, GlossVideoPerspective
from signbank.dictionary.models import Gloss, DeletedGlossOrMedia, ExampleSentence, Morpheme, AnnotatedSentence, Dataset, AnnotatedSentenceSource
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
        last_used_dataset = request.session['last_used_dataset']
        dataset = Dataset.objects.filter(acronym=last_used_dataset).first()
        dataset_languages = dataset.translation_languages.all()
        form = VideoUploadForObjectForm(request.POST, request.FILES, languages=dataset_languages, dataset=dataset)
        if form.is_valid():
            # Unpack the form
            object_id = form.cleaned_data['object_id']
            object_type = form.cleaned_data['object_type']
            vfile = form.cleaned_data['videofile']
            redirect_url = form.cleaned_data['redirect']
            recorded = form.cleaned_data['recorded']
            # add the video, depending on which type of object it is added to
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
            elif object_type == 'gloss_perspectivevideo':
                gloss = Gloss.objects.filter(id=object_id).first()
                if not gloss:
                    redirect(redirect_url)
                perspective = form.cleaned_data['perspective']
                stringpersp = str(perspective)
                perspvideo = gloss.add_perspective_video(request.user, vfile, stringpersp, recorded)
                if settings.DEBUG_VIDEOS:
                    print('Perspective video created: ', str(perspvideo))
            elif object_type == 'gloss_nmevideo':
                gloss = Gloss.objects.filter(id=object_id).first()
                if not gloss:
                    redirect(redirect_url)
                offset = form.cleaned_data['offset']
                perspective = form.cleaned_data['nme_perspective']
                nmevideo = gloss.add_nme_video(request.user, vfile, offset, recorded, perspective)
                translation_languages = gloss.lemma.dataset.translation_languages.all()
                descriptions = dict()
                for language in translation_languages:
                    form_field = 'description_' + language.language_code_2char
                    form_value = form.cleaned_data[form_field]
                    descriptions[language.language_code_2char] = form_value.strip()
                nmevideo.add_descriptions(descriptions)
                nmevideo.perspective = perspective
                nmevideo.save()
            elif object_type == 'morpheme_video':
                morpheme = Morpheme.objects.filter(id=object_id).first()
                if not morpheme:
                    redirect(redirect_url)
                morpheme.add_video(request.user, vfile, recorded)
            elif object_type == 'annotated_video': 
                eaf_file = form.cleaned_data['eaffile']
                annotated_sentence = AnnotatedSentence.objects.create()
                
                gloss = Gloss.objects.filter(id=object_id).first()
                annotations = form.cleaned_data['feedbackdata']
                annotations = json.loads(annotations)
                annotated_sentence.add_annotations(annotations, gloss)
                
                translations = form.cleaned_data['translations']
                if translations:
                    annotated_sentence.add_translations(json.loads(translations))

                contexts = form.cleaned_data['contexts']
                if contexts:
                    annotated_sentence.add_contexts(json.loads(contexts))
                    
                source = form.cleaned_data['source_id']
                url = form.cleaned_data['url']
                annotated_video = annotated_sentence.add_video(request.user, vfile, eaf_file, source, url)
                
                if annotated_video is None:
                    messages.add_message(request, messages.ERROR, _('Annotated sentence upload went wrong. Please try again.'))
                    annotated_sentence.delete()
                else:
                    annotated_sentence.save()

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


def get_glosses_from_eaf(eaf, dataset_acronym):
    from signbank.dictionary.models import AnnotationIdglossTranslation
    glosses, labels_not_found, sentences = [], [], []
    sentence_dict = {}

    # Add glosses from the right hand
    for annotation in eaf.tiers['Glosses R'][0].values():
        gloss_label = annotation[2]
        if AnnotationIdglossTranslation.objects.filter(gloss__lemma__dataset__acronym=dataset_acronym, text__exact=gloss_label).exists():
            start = int(eaf.timeslots[annotation[0]])
            end = int(eaf.timeslots[annotation[1]])
            glosses.append([gloss_label, start, end])
        else:
            labels_not_found.append(gloss_label)

    # Add glosses from the left hand, if they don't overlap with the right hand
    for annotation in find_non_overlapping_annotated_glosses(eaf.timeslots, eaf.tiers['Glosses R'][0].values(), eaf.tiers['Glosses L'][0].values()):
        gloss_label = annotation[2]
        if AnnotationIdglossTranslation.objects.filter(gloss__lemma__dataset__acronym=dataset_acronym, text__exact=gloss_label).exists():
            start = int(eaf.timeslots[annotation[0]])
            end = int(eaf.timeslots[annotation[1]])
            glosses.append([gloss_label, start, end])
        else:
            labels_not_found.append(gloss_label)

    # Sort the list of glosses by the "start" value
    glosses = sorted(glosses, key=lambda x: x[1])

    if 'Sentences' in eaf.tiers:
        for annotation in eaf.tiers['Sentences'][0].values():
            sentences.append(annotation[2])
    
    dataset_language = Dataset.objects.get(acronym=dataset_acronym).default_language.language_code_3char
    for sentence_i, sentence in enumerate(sentences):
        sentence_dict[dataset_language] = sentence

    return glosses, labels_not_found, sentence_dict


def process_eaffile(request):
    import magic
    from pympi.Elan import Eaf

    if request.method == 'POST':
        check_gloss_label = request.POST.get('check_gloss_label', '')
        dataset_acronym = request.POST.get('dataset', '')
        uploaded_file = request.FILES['eaffile']
        file_type = magic.from_buffer(open(uploaded_file.temporary_file_path(), "rb").read(2040), mime=True)
        if not (uploaded_file.name.endswith('.eaf') and file_type == 'text/xml'):
            return JsonResponse({'error': _('Invalid file. Please try again.')})

        eaf = Eaf(uploaded_file.temporary_file_path())
        glosses, labels_not_found, sentence_dict = get_glosses_from_eaf(eaf, dataset_acronym)

    # Create the annotations table
    annotations_table_html = render(request, 'annotations_table.html', {'glosses_list': glosses, 'check_gloss_label': [check_gloss_label], 'labels_not_found': labels_not_found}).content.decode('utf-8')
    sentences_json = json.dumps(sentence_dict)

    if glosses == []:
        return JsonResponse({'error': annotations_table_html})
    
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
def deletevideo(request, glossid):
    """Remove the video for this gloss, if there is an older version
    then reinstate that as the current video (act like undo)"""

    # return to referer
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'

    if not request.method == "POST":
        return redirect(url)

    # deal with any existing video for this sign
    gloss = get_object_or_404(Gloss, pk=glossid, archived=False)
    # save the video path of the version 0 video before it gets deleted by the reversion method in the loop
    deleted_video_filename = gloss.get_video_path()
    glossvideos_nme = [gv.id for gv in GlossVideoNME.objects.filter(gloss=gloss)]
    glossvideos_persp = [gv.id for gv in GlossVideoPerspective.objects.filter(gloss=gloss)]
    # get existing gloss video objects but exclude NME and perspective videos
    existing_videos = GlossVideo.objects.filter(gloss=gloss).exclude(
        id__in=glossvideos_nme).exclude(id__in=glossvideos_persp)
    vids = existing_videos.order_by('version')
    reversion_log = []
    for v in vids:
        # this will remove the most recent video, ie it's equivalent
        # to delete if version=0
        # save the to be deleted data in a list of tuples
        uploadfile = os.path.basename(v.videofile.name)
        goal_location = v.videofile.path
        reversion_log.append((v.version, uploadfile, goal_location))
        v.reversion(revert=True)
    for (version, uploadfile, goal_location) in reversion_log:
        # Issue #162: log the deletion history
        if version > 0:
            continue
        log_entry = GlossVideoHistory(action="delete", gloss=gloss,
                                      actor=request.user,
                                      uploadfile=uploadfile,
                                      goal_location=goal_location)
        log_entry.save()

    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    deleted_video = DeletedGlossOrMedia()
    deleted_video.item_type = 'video'
    deleted_video.idgloss = gloss.idgloss
    deleted_video.annotation_idgloss = default_annotationidglosstranslation
    deleted_video.old_pk = gloss.pk
    deleted_video.filename = deleted_video_filename
    deleted_video.save()

    return redirect(url)


# CHECK FUNCTIONALITY
# WHY IS VIDEOID USED AS GLOSSID?
# IS THIS METHOD USED?
def video(request, videoid):
    """Redirect to the video url for this videoid"""

    video = get_object_or_404(GlossVideo, gloss_id=videoid, gloss__archived=False)

    return redirect(video)


def create_still_images(request):
    processed_videos = []
    for video in GlossVideo.objects.filter(glossvideonme=None, glossvideoperspective=None, version=0):
        generate_still_image(video)
        processed_videos.append(str(video))
    return HttpResponse('Processed videos: <br/>' + "<br/>".join(processed_videos))
