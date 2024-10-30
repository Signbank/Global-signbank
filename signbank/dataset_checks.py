

from signbank.dictionary.models import *
from signbank.video.models import GlossVideo, GlossVideoHistory
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse


def gloss_annotations_check(dataset):

    translation_languages = dataset.translation_languages.all()
    results = dict()
    glosses_with_too_many_annotations = []
    glosses_missing_annotations = []

    all_glosses = Gloss.objects.filter(lemma__dataset=dataset)
    for gloss in all_glosses:
        annotations = AnnotationIdglossTranslation.objects.filter(gloss=gloss)
        for language in translation_languages:
            num_translations_per_language = annotations.filter(language=language).count()
            if num_translations_per_language > 1:
                glosses_with_too_many_annotations.append((gloss, language))
            elif not num_translations_per_language:
                glosses_missing_annotations.append((gloss, language))

    results['glosses_with_too_many_annotations'] = glosses_with_too_many_annotations
    results['glosses_missing_annotations'] = glosses_missing_annotations
    return results


def gloss_videos_check(dataset):

    results = dict()
    glosses_with_too_many_videos = []
    gloss_videos = []

    default_language = dataset.default_language

    all_glosses = Gloss.objects.filter(lemma__dataset=dataset,
                                       lemma__lemmaidglosstranslation__language=default_language).order_by(
        'lemma__lemmaidglosstranslation__text').distinct()
    for gloss in all_glosses:
        glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                                glossvideonme=None,
                                                glossvideoperspective=None).order_by('version')
        num_videos = glossvideos.count()
        dubble_version_0 = glossvideos.filter(version=0)
        if dubble_version_0.count() > 1:
            list_videos = ', '.join([str(gv.version)+': '+str(gv.videofile) for gv in dubble_version_0])
            glosses_with_too_many_videos.append((gloss, list_videos))
        if num_videos > 0:
            list_videos = ', '.join([str(gv.version)+': '+str(gv.videofile) for gv in glossvideos])
            gloss_videos.append((gloss, list_videos))
        # elif not num_videos:
        #     glosses_missing_video.append((gloss, num_videos))

    results['glosses_with_too_many_videos'] = glosses_with_too_many_videos
    results['gloss_videos'] = gloss_videos

    return results


def gloss_video_filename_check(dataset):

    results = dict()
    glosses_with_weird_filenames = []
    non_mp4_videos = []

    default_language = dataset.default_language

    all_glosses = Gloss.objects.filter(lemma__dataset=dataset,
                                       lemma__lemmaidglosstranslation__language=default_language).order_by(
        'lemma__lemmaidglosstranslation__text').distinct()
    for gloss in all_glosses:
        glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                                glossvideonme=None,
                                                glossvideoperspective=None).order_by('version')
        weird_pattern = '-' + str(gloss.id) + '_'
        pattern_in_filename = [gv for gv in glossvideos if weird_pattern in str(gv.videofile)]
        if pattern_in_filename:
            list_videos = ', '.join([str(gv.version)+': '+str(gv.videofile) for gv in pattern_in_filename])
            glosses_with_weird_filenames.append((gloss, list_videos))
        version_0_videos = glossvideos.filter(version=0)
        mp4_pattern = '.mp4'
        mp4_in_filename = [gv for gv in version_0_videos if not str(gv.videofile).endswith(mp4_pattern)]
        if mp4_in_filename:
            list_videos = ', '.join([str(gv.version)+': '+str(gv.videofile) for gv in mp4_in_filename])
            non_mp4_videos.append((gloss, list_videos))

    results['glosses_with_weird_filenames'] = glosses_with_weird_filenames
    results['non_mp4_videos'] = non_mp4_videos

    return results


def check_consistency_gloss_translations(request):
    # this is an ajax call in the DatasetConstraintsView template
    if not request.user.is_authenticated:
        return JsonResponse({})

    from django.contrib.auth.models import Group
    try:
        group_manager = Group.objects.get(name='Dataset_Manager')
    except ObjectDoesNotExist:
        return JsonResponse({})

    groups_of_user = request.user.groups.all()
    if group_manager not in groups_of_user:
        return JsonResponse({})

    datasetid = request.POST.get('dataset', '')
    if not datasetid:
        return JsonResponse({})

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return JsonResponse({})

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        return JsonResponse({})

    # make sure the user can write to this dataset
    from guardian.shortcuts import get_objects_for_user
    user_change_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset,
                                                accept_global_perms=False)
    if not user_change_datasets or dataset not in user_change_datasets:
        return JsonResponse({})

    results = gloss_annotations_check(dataset)

    return JsonResponse(results)
