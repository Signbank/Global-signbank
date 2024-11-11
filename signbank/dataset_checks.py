

from signbank.dictionary.models import *
from signbank.video.models import GlossVideo, GlossVideoHistory, GlossVideoNME, GlossVideoPerspective
from signbank.tools import get_two_letter_dir


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


def gloss_backup_videos(dataset):
    backup_videos = []
    default_language = dataset.default_language

    all_glosses = Gloss.objects.filter(lemma__dataset=dataset,
                                       lemma__lemmaidglosstranslation__language=default_language).order_by(
        'lemma__lemmaidglosstranslation__text').distinct()
    for gloss in all_glosses:
        glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                                glossvideonme=None,
                                                glossvideoperspective=None).order_by('version')
        backup_videos_ordered = glossvideos.filter(version__gt=0).order_by('version')
        if backup_videos_ordered.count() > 1:
            gloss_videos = [gv for gv in backup_videos_ordered]
            backup_videos.append((gloss, gloss_videos))
    return backup_videos


def rename_backup_videos(gloss, glossvideos):

    idgloss = gloss.idgloss
    desired_filename_without_extension = idgloss + '-' + str(gloss.id) + '.mp4'
    for inx, gloss_video in enumerate(glossvideos, 1):
        _, bak = os.path.splitext(gloss_video.videofile.name)
        desired_extension = '.bak' + str(gloss_video.id)
        current_version = gloss_video.version
        desired_filename = desired_filename_without_extension + desired_extension
        current_filename = str(gloss_video.videofile)
        if bak == desired_extension and inx == current_version:
            continue
        if bak != desired_extension:
            source = os.path.join(settings.WRITABLE_FOLDER, current_filename)
            destination = os.path.join(settings.WRITABLE_FOLDER, desired_filename)
            print('rename_backup_videos move ', source, destination)
            os.rename(source, destination)
            gloss_video.videofile.name = desired_filename
        if inx != current_version:
            print('rename_backup_videos change version ', current_version, inx)
            gloss_video.version = inx
        gloss_video.save()


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

    results['glosses_with_too_many_videos'] = glosses_with_too_many_videos
    results['gloss_videos'] = gloss_videos

    return results


def gloss_subclass_videos_check(dataset):

    results = dict()
    gloss_nme_videos = []
    gloss_perspective_videos = []

    default_language = dataset.default_language

    all_glosses = Gloss.objects.filter(lemma__dataset=dataset,
                                       lemma__lemmaidglosstranslation__language=default_language).order_by(
        'lemma__lemmaidglosstranslation__text').distinct()
    for gloss in all_glosses:
        glossnmevideos = GlossVideoNME.objects.filter(gloss=gloss).order_by('offset')
        num_nme_videos = glossnmevideos.count()
        if num_nme_videos > 0:
            list_videos = ', '.join([str(gv.offset)+': '+str(gv.videofile) for gv in glossnmevideos])
            gloss_nme_videos.append((gloss, list_videos))

        glossperspvideos = GlossVideoPerspective.objects.filter(gloss=gloss)
        num_persp_videos = glossperspvideos.count()
        if num_persp_videos > 0:
            list_videos = ', '.join([str(gv.perspective) + ': ' + str(gv.videofile) for gv in glossperspvideos])
            gloss_perspective_videos.append((gloss, list_videos))

    results['gloss_nme_videos'] = gloss_nme_videos
    results['gloss_perspective_videos'] = gloss_perspective_videos

    return results


def gloss_video_filename_check(dataset):

    results = dict()
    glosses_with_weird_filenames = []
    non_mp4_videos = []
    wrong_folder = []

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
        idgloss = gloss.idgloss
        two_letter_dir = get_two_letter_dir(idgloss)
        folder_pattern = settings.GLOSS_VIDEO_DIRECTORY + os.sep + dataset.acronym + os.sep + two_letter_dir
        folder_not_in_filename = [gv for gv in glossvideos if folder_pattern not in str(gv.videofile)]
        if folder_not_in_filename:
            list_videos = ', '.join([str(gv.version)+': '+str(gv.videofile) for gv in mp4_in_filename])
            wrong_folder.append((gloss, list_videos))

    results['glosses_with_weird_filenames'] = glosses_with_weird_filenames
    results['non_mp4_videos'] = non_mp4_videos
    results['wrong_folder'] = wrong_folder

    return results
