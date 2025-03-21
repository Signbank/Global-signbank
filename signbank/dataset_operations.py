import os.path
from django.contrib.auth.decorators import permission_required
from signbank.dictionary.models import *
from signbank.video.models import GlossVideo, GlossVideoNME, GlossVideoPerspective
from signbank.video.convertvideo import video_file_type_extension
from signbank.tools import get_two_letter_dir
import re
from django.http import JsonResponse


def video_type(glossvideo):
    # if the file exists, this will obtain the type of video as an extension

    video_file_full_path = os.path.join(WRITABLE_FOLDER, str(glossvideo.videofile))
    return video_file_type_extension(video_file_full_path)


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


def gloss_backup_videos(gloss):

    backup_videos = GlossVideo.objects.filter(gloss=gloss,
                                              glossvideonme=None,
                                              glossvideoperspective=None,
                                              version__gt=0).order_by('version', 'id')
    return backup_videos


def renumber_backup_videos(gloss):
    # this method accounts for poorly enumerated or missing version numbers
    # it renumbers the existing backup videos starting with 1
    glossvideos = gloss_backup_videos(gloss)
    for inx, gloss_video in enumerate(glossvideos, 1):
        current_version = gloss_video.version
        if inx == current_version:
            continue

        if settings.DEBUG_VIDEOS:
            print('dataset_operations:renumber_backup_videos: change version ', current_version, inx)

        gloss_video.version = inx
        gloss_video.save()


def rename_backup_videos(gloss):
    glossvideos = gloss_backup_videos(gloss)
    idgloss = gloss.idgloss
    glossid = str(gloss.id)
    two_letter_dir = get_two_letter_dir(idgloss)
    dataset_dir = gloss.lemma.dataset.acronym
    for inx, glossvideo in enumerate(glossvideos, 1):
        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(glossvideo.videofile))
        video_extension = video_file_type_extension(video_file_full_path)
        desired_filename_without_extension = f'{idgloss}-{glossid}{video_extension}'
        _, bak = os.path.splitext(glossvideo.videofile.name)
        desired_extension = '.bak' + str(glossvideo.id)
        desired_filename = desired_filename_without_extension + desired_extension
        desired_relative_path = os.path.join(settings.GLOSS_VIDEO_DIRECTORY,
                                             dataset_dir, two_letter_dir, desired_filename)
        current_relative_path = str(glossvideo.videofile)
        if current_relative_path == desired_relative_path:
            continue
        source = os.path.join(settings.WRITABLE_FOLDER, current_relative_path)
        destination = os.path.join(WRITABLE_FOLDER, desired_relative_path)
        if settings.DEBUG_VIDEOS:
            print('dataset_operations:rename_backup_videos:rename: ', source, destination)
            print('desired_relative_path: ', desired_relative_path)
        # if the file exists, rename it, otherwise only modify the filename of the object
        if os.path.exists(source):
            os.rename(source, destination)
        glossvideo.videofile.name = desired_relative_path
        glossvideo.save()


def gloss_has_videos_with_extra_chars_in_filename(gloss):
    glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                            glossvideonme=None,
                                            glossvideoperspective=None).order_by('version')
    weird_pattern = '-' + str(gloss.id) + '_'
    pattern_in_filename = [gv for gv in glossvideos if weird_pattern in str(gv.videofile)]
    return len(pattern_in_filename) > 0


def path_exists(relativepath):

    fullpath = os.path.join(WRITABLE_FOLDER, relativepath)
    return os.path.exists(fullpath)


def weed_out_duplicate_version_0_videos(gloss):
    # make sure there is only one version 0 video
    # retrieve the gloss video objects, ordered by most recent first
    glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                            glossvideonme=None,
                                            glossvideoperspective=None,
                                            version=0).order_by('-id')

    if glossvideos.count() <= 1:
        return

    # first delete the objects that do not have a video
    if settings.DEBUG_VIDEOS:
        print('dataset_operations:weed_out_duplicate_version_0_videos:more than one version 0 ', glossvideos)
    for gv in glossvideos:
        # delete the objects with no video
        gv_full_path = os.path.join(WRITABLE_FOLDER, str(gv.videofile))
        if not path_exists(gv_full_path):
            gv.delete()

    glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                            glossvideonme=None,
                                            glossvideoperspective=None,
                                            version=0).order_by('-id')

    if glossvideos.count() <= 1:
        return

    glossvideo = glossvideos.first()

    # there are still more than one
    # delete everybody except the most recent
    for gv in glossvideos:
        if gv == glossvideo:
            continue
        gv_full_path = os.path.join(WRITABLE_FOLDER, str(gv.videofile))
        try:
            os.unlink(gv.videofile.path)
            os.remove(gv_full_path)
            gv.delete()
            if settings.DEBUG_VIDEOS:
                print('dataset_operations:weed_out_duplicate_version_0_videos:remove: ', gv_full_path)
        except (OSError, PermissionError):
            if settings.DEBUG_VIDEOS:
                print('Exception dataset_operations:weed_out_duplicate_version_0_videos:remove: ', gv_full_path)


def rename_gloss_video(gloss):

    weed_out_duplicate_version_0_videos(gloss)

    glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                            glossvideonme=None,
                                            glossvideoperspective=None,
                                            version=0).order_by('-id')
    # grab the most recent
    glossvideo = glossvideos.first()

    if not glossvideo:
        return
    idgloss = gloss.idgloss
    glossid = str(gloss.id)
    two_letter_dir = get_two_letter_dir(idgloss)
    dataset_dir = gloss.lemma.dataset.acronym
    video_file_full_path = os.path.join(WRITABLE_FOLDER, str(glossvideo.videofile))
    video_extension = video_file_type_extension(video_file_full_path)
    desired_filename = f'{idgloss}-{glossid}{video_extension}'
    desired_relative_path = os.path.join(settings.GLOSS_VIDEO_DIRECTORY,
                                         dataset_dir, two_letter_dir, desired_filename)
    current_relative_path = str(glossvideo.videofile)
    if current_relative_path == desired_relative_path:
        return
    source = os.path.join(settings.WRITABLE_FOLDER, current_relative_path)
    destination = os.path.join(WRITABLE_FOLDER, desired_relative_path)
    if settings.DEBUG_VIDEOS:
        print('dataset_operations:rename_backup_videos:rename: ', source, destination)
        print('desired_relative_path: ', desired_relative_path)
    # if the file exists, rename it, otherwise only modify the filename of the object
    if os.path.exists(source):
        os.rename(source, destination)
    glossvideo.videofile.name = desired_relative_path
    glossvideo.save()


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
            gloss_videos.append((gloss, num_videos, gloss_has_videos_with_extra_chars_in_filename(gloss), list_videos))

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
            list_videos = [(gv.version, str(gv.videofile), path_exists(str(gv.videofile))) for gv in folder_not_in_filename]
            wrong_folder.append((gloss, list_videos))

    results['glosses_with_weird_filenames'] = glosses_with_weird_filenames
    results['non_mp4_videos'] = non_mp4_videos
    results['wrong_folder'] = wrong_folder

    return results


def find_unlinked_video_files(dataset, linked_file_names):
    """Return list of file_names that are not found in file list of db"""

    dataset_folder = os.path.join(settings.WRITABLE_FOLDER, settings.GLOSS_VIDEO_DIRECTORY, dataset.acronym)

    unlinked_video_filenames = []

    for subdir, dirs, files in os.walk(dataset_folder):
        for file in files:
            filename_string = str(file)
            if filename_string in ['.DS_Store'] or filename_string.endswith('.icloud'):
                # Signbank is running on MacOS
                # this is a MacOS icons file or an iCloud sync file, ignore it
                continue
            if filename_string.endswith('.bak') or re.search(r"\.bak\d+$", filename_string):
                # ignore backup files since they aren't viewable as protected media
                continue
            filename, ext = os.path.splitext(file)
            filename_without_extension = str(filename)
            # ignore small and subclass videos
            if (filename_without_extension.endswith('_small')
                    or filename_without_extension.endswith('_left')
                    or filename_without_extension.endswith('_right')
                    or re.search(r"\_nme_\d+$", filename_without_extension)):
                continue
            two_char_folder = os.path.basename(subdir)
            # obtain a relative path using os.path.join
            relative_path = str(os.path.join(settings.GLOSS_VIDEO_DIRECTORY, dataset.acronym, two_char_folder, file))
            if relative_path not in linked_file_names:
                unlinked_video_filenames.append(relative_path)

    return unlinked_video_filenames


def find_unlinked_video_files_for_dataset(dataset):

    filenames_of_dataset = [str(gv.videofile) for gv in GlossVideo.objects.filter(gloss__lemma__dataset=dataset)]

    unlinked_video_filenames = find_unlinked_video_files(dataset, filenames_of_dataset)

    return unlinked_video_filenames


@permission_required('dictionary.change_gloss')
def update_gloss_video_backups(request, glossid):

    if not request.user.is_authenticated:
        return JsonResponse({})

    gloss_id = int(glossid)
    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        return JsonResponse({})

    rename_gloss_video(gloss)
    rename_backup_videos(gloss)
    renumber_backup_videos(gloss)

    glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                            glossvideonme=None,
                                            glossvideoperspective=None).order_by('version')
    list_videos = ', '.join([str(gv.version) + ': ' + str(gv.videofile) for gv in glossvideos])

    return JsonResponse({'videos': list_videos})
