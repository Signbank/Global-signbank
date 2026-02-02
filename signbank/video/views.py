import os
import json
import datetime as DT

import magic
from pympi.Elan import Eaf

from django.utils.timezone import get_current_timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext as _

from signbank.video.models import (GlossVideo, GlossVideoHistory, ExampleVideoHistory, GlossVideoNME,
                                   GlossVideoPerspective)
from signbank.video.forms import VideoUploadForObjectForm
from signbank.dictionary.models import (Gloss, DeletedGlossOrMedia, ExampleSentence, Morpheme, AnnotatedSentence,
                                        Dataset, GlossRevision, AnnotationIdglossTranslation)
from signbank.tools import get_default_annotationidglosstranslation


@require_http_methods(["POST"])
def addvideo(request):
    """View to present a video upload form and process the upload"""
    last_used_dataset = request.session.get('last_used_dataset')
    dataset = Dataset.objects.filter(acronym=last_used_dataset).first()
    dataset_languages = dataset.translation_languages.all()
    form = VideoUploadForObjectForm(request.POST, request.FILES, languages=dataset_languages, dataset=dataset)
    if not form.is_valid():
        return redirect(request.META.get('HTTP_REFERER', '/'))

    object_id = form.cleaned_data['object_id']
    object_type = form.cleaned_data['object_type']
    video_file = form.cleaned_data['videofile']
    redirect_url = form.cleaned_data['redirect']
    recorded = form.cleaned_data['recorded']

    object_type_model_mapping = {
        'examplesentence_video': ExampleSentence,
        'morpheme_video': Morpheme,
        'gloss_video': Gloss,
        'gloss_perspectivevideo': Gloss,
        'gloss_nmevideo': Gloss,
        'annotated_video': Gloss
    }

    model = object_type_model_mapping.get(object_type)
    if not model:
        return redirect(redirect_url)
    first_obj = model.objects.filters(id=object_id).first()
    if not first_obj and object_type != 'annotated_video':
        return redirect(redirect_url)

    if model in [ExampleSentence, Morpheme]:
        first_obj.add_video(request.user, video_file, recorded)
        return redirect(redirect_url)

    gloss = first_obj
    uploaded_video = None
    fieldname = object_type

    if object_type == "gloss_video":
        gloss_video = gloss.add_video(request.user, video_file, recorded)
        uploaded_video = gloss_video.videofile.name
    elif object_type == 'gloss_perspectivevideo':
        perspective = str(form.cleaned_data['perspective'])
        if perspective:
            fieldname = f'{fieldname}_{perspective}'
        perspective_video = gloss.add_perspective_video(request.user, video_file, perspective, recorded)
        uploaded_video = perspective_video.videofile.name
    elif object_type == 'gloss_nmevideo':
        offset = form.cleaned_data['offset']
        perspective = form.cleaned_data['nme_perspective']
        fieldname += f'_{offset}_{perspective}'
        nmevideo = gloss.add_nme_video(request.user, video_file, offset, recorded, perspective)
        translation_languages = gloss.lemma.dataset.translation_languages.all()
        descriptions = {
            language.language_code_2char: form.cleaned_data["description_" + language.language_code_2char].strip()
            for language in translation_languages
        }
        nmevideo.add_descriptions(descriptions)
        nmevideo.perspective = perspective
        nmevideo.save()
        uploaded_video = nmevideo.videofile.name
    elif object_type == 'annotated_video':
        annotated_sentence = AnnotatedSentence.objects.create()
        annotations = json.loads(form.cleaned_data['feedbackdata'])
        annotated_sentence.add_annotations(annotations, gloss)

        if translations := form.cleaned_data['translations']:
            annotated_sentence.add_translations(json.loads(translations))
        if contexts := form.cleaned_data['contexts']:
            annotated_sentence.add_contexts(json.loads(contexts))

        eaf_file = form.cleaned_data['eaffile']
        source = form.cleaned_data['source_id']
        url = form.cleaned_data['url']
        annotated_video = annotated_sentence.add_video(request.user, video_file, eaf_file, source, url)

        if annotated_video is None:
            messages.add_message(request, messages.ERROR, _('Annotated sentence upload went wrong. Please try again.'))
            annotated_sentence.delete()
            return redirect(redirect_url)

        uploaded_video = annotated_video.videofile.name
        annotated_sentence.save()

    if gloss and uploaded_video:
        GlossRevision.objects.create(old_value='', new_value=uploaded_video, field_name=fieldname, gloss=gloss,
                                     ser=request.user, time=DT.datetime.now(tz=get_current_timezone()))

    return redirect(redirect_url)


def find_non_overlapping_annotated_glosses(timeslots, annotations_tier_1, annotations_tier_2):
    """Find annotations in second tier that do not overlap with any annotation is the first tier."""
    return [
        annotation for annotation in annotations_tier_2
        if not has_overlapping_annotations(annotation, annotations_tier_1, timeslots)
    ]


def has_overlapping_annotations(annotation, tier, timeslots) -> bool:
    """True if the annotation overlaps with any annotation from the tier."""
    start_2 = int(timeslots[annotation[0]])
    end_2 = int(timeslots[annotation[1]])
    for annotation_from_tier in tier:
        start_1 = int(timeslots[annotation_from_tier[0]])
        end_1 = int(timeslots[annotation_from_tier[1]])
        if start_1 <= start_2 <= end_1 or start_1 <= end_2 <= end_1:
            return True
    return False


def add_glosses_from_annotations(annotations, dataset_acronym, eaf, glosses, labels_not_found):
    for annotation in annotations:
        gloss_label = annotation[2]
        if AnnotationIdglossTranslation.objects.filter(gloss__lemma__dataset__acronym=dataset_acronym,
                                                       text__exact=gloss_label).exists():
            start = int(eaf.timeslots[annotation[0]])
            end = int(eaf.timeslots[annotation[1]])
            glosses.append([gloss_label, start, end])
        else:
            labels_not_found.append(gloss_label)


def get_glosses_from_eaf(eaf, dataset_acronym):
    glosses = []
    labels_not_found = []

    # check whether to use 'Signbank ID glossen' or 'Glosses R' and 'Glosses L' tiers
    if 'Signbank ID glossen' in eaf.tiers:
        # Add glosses from this one tier
        annotations = eaf.tiers['Signbank ID glossen'][0].values()
        add_glosses_from_annotations(annotations, dataset_acronym, eaf, glosses, labels_not_found)
    else:
        # Add glosses from the right hand
        annotations = eaf.tiers['Glosses R'][0].values()
        add_glosses_from_annotations(annotations, dataset_acronym, eaf, glosses, labels_not_found)

        # Add glosses from the left hand, if they don't overlap with the right hand
        annotations = find_non_overlapping_annotated_glosses(eaf.timeslots, eaf.tiers['Glosses R'][0].values(),
                                                             eaf.tiers['Glosses L'][0].values())
        add_glosses_from_annotations(annotations, dataset_acronym, eaf, glosses, labels_not_found)

    # Sort the list of glosses by the "start" value
    glosses = sorted(glosses, key=lambda x: x[1])

    sentences = []
    for tier_name in ['Sentences', 'Nederlands']:
        if tier_name in eaf.tiers:
            for annotation in eaf.tiers['Sentences'][0].values():
                sentences.append(annotation[2])

    dataset_language = Dataset.objects.get(acronym=dataset_acronym).default_language.language_code_3char
    sentence_dict = {dataset_language: sentence for sentence in sentences}

    return glosses, labels_not_found, sentence_dict


@require_http_methods(["POST"])
def process_eaffile(request):
    uploaded_file = request.FILES['eaffile']
    with open(uploaded_file.temporary_file_path(), "rb") as eaf_file:
        if not uploaded_file.name.endswith('.eaf') or magic.from_buffer(eaf_file.read(2040), mime=True) != 'text/xml':
            return JsonResponse({'error': _('Invalid file. Please try again.')})

    glosses, labels_not_found, sentence_dict = get_glosses_from_eaf(eaf=Eaf(uploaded_file.temporary_file_path()),
                                                                    dataset_acronym=request.POST.get('dataset', ''))

    # Create the annotations table
    check_gloss_label = request.POST.get('check_gloss_label', '')
    annotations_table_html = render(request, 'annotations_table.html',
                                    {'glosses_list': glosses, 'check_gloss_label': [check_gloss_label],
                                     'labels_not_found': labels_not_found}).content.decode('utf-8')
    if glosses == []:
        return JsonResponse({'error': annotations_table_html})

    return JsonResponse({'annotations_table_html': annotations_table_html, 'sentences': json.dumps(sentence_dict)})


@login_required
@require_http_methods(["POST"])
def deletesentencevideo(request, videoid):
    """Remove the video for this gloss, if there is an older version
    then reinstate that as the current video (act like undo)"""
    examplesentence = get_object_or_404(ExampleSentence, id=videoid)
    for video in examplesentence.examplevideo_set.order_by('version'):
        video.reversion(revert=True)
        if video.version == 0:
            video.make_small_video()
        log_entry = ExampleVideoHistory(action="delete", examplesentence=examplesentence, actor=request.user,
                                        uploadfile=os.path.basename(video.videofile.name),
                                        goal_location=video.videofile.path)
        log_entry.save()

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_http_methods(["POST"])
def deletevideo(request, glossid):
    """Remove the video for this gloss, if there is an older version
    then reinstate that as the current video (act like undo)"""
    gloss = get_object_or_404(Gloss, pk=glossid, archived=False)
    excluded_glossvideo_ids = [*GlossVideoNME.objects.filter(gloss=gloss).values_list('id', flat=True),
                               *GlossVideoPerspective.objects.filter(gloss=gloss).values_list('id', flat=True)]
    for video in GlossVideo.objects.filter(gloss=gloss).exclude(id__in=excluded_glossvideo_ids).order_by('version'):
        if video.version == 0:
            GlossVideoHistory.objects.create(action="delete", gloss=gloss, actor=request.user,
                                             uploadfile=os.path.basename(video.videofile.name),
                                             goal_location=video.videofile.path,)
        video.reversion(revert=True)

    DeletedGlossOrMedia.objects.create(item_type='video', idgloss=gloss.idgloss,
                                       annotation_idgloss=get_default_annotationidglosstranslation(gloss),
                                       old_pk=gloss.pk, filename=gloss.get_video_path())

    return redirect(request.META.get('HTTP_REFERER', '/'))
