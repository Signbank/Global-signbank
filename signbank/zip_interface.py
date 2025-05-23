import shutil
import os

from django.core.files.base import File
from django.views.decorators.csrf import csrf_exempt
from django.db.transaction import atomic, TransactionManagementError, DatabaseError

from signbank.settings.server_specific import (WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, VIDEOS_TO_IMPORT_FOLDER,
                                               DEBUG_VIDEOS)
from signbank.dictionary.models import (Gloss, Language)
from signbank.video.models import GlossVideo, GlossVideoHistory
from signbank.tools import get_two_letter_dir

import zipfile


def import_folder(video_file_path):
    # this removes the WRITABLE_FOLDER from the path, so as not to show to user
    video_folder = os.path.dirname(video_file_path)
    path_units = video_folder.split('/')
    # import_path of form import_videos/NGT/nld
    import_path = os.path.join(path_units[-3], path_units[-2], path_units[-1])
    return import_path


def get_target_filepath(dataset, lang3charcodes, filepath_in_zip_archive):
    acronym = dataset.acronym
    lang3char = dataset.default_language.language_code_3char

    filepath_units = filepath_in_zip_archive.split('/')
    filename = filepath_units[-1]
    for unit in filepath_units:
        if unit in lang3charcodes:
            lang3char = unit
    target_path = os.path.join(acronym, lang3char, filename)
    return target_path


def get_filenames(path_to_zip):
    """ return list of filenames inside of the zip folder"""
    with zipfile.ZipFile(path_to_zip, 'r') as zipped:
        return zipped.namelist()


def get_filenames_with_filetype(path_to_zip):
    """ return list of filenames inside of the zip folder"""
    files_in_zip_archive = dict()
    with zipfile.ZipFile(path_to_zip, 'r') as zipped:
        for entry in zipped.infolist():
            if not entry.filename.endswith('.mp4'):
                # this can be an Apple .DS_Store file
                files_in_zip_archive[entry.filename] = (False, False)
                continue
            unique_gloss_match = check_zipfile_video_for_gloss_matches(entry.filename)
            files_in_zip_archive[entry.filename] = (True, unique_gloss_match)
        return files_in_zip_archive


def check_subfolders_for_unzipping(acronym, lang3charcodes, filenames):
    # the zip file possibly has an outer folder container
    # include both possible structures in the allowed structural paths
    commonprefix = os.path.commonprefix(filenames)
    common_prefix_paths = [acronym + '/' + lang3char + '/' for lang3char in lang3charcodes]
    if commonprefix != acronym + '/':
        # if the user has put the zip files inside another folder, e.g., NGT_videos/NGT/nld/
        subfolders = ([commonprefix] + [commonprefix + acronym + '/'] +
                      [commonprefix + acronym + '/' + lang3char + '/' for lang3char in lang3charcodes])
    else:
        subfolders = ([acronym + '/'] + common_prefix_paths)
    video_files = []
    for zipfilename in filenames:
        if zipfilename in subfolders:
            # skip directory nesting structures
            continue
        if '/' not in zipfilename:
            # this is not a path, for example, .DS_Store as for Apple
            continue
        file_dirname = os.path.dirname(zipfilename)
        # this is the path to the media file
        if file_dirname + '/' not in common_prefix_paths:
            # this path not an allowed nesting structure, ignore this
            continue
        video_files.append(zipfilename)
    return video_files


def check_subfolders_for_unzipping_ids(acronym, filenames):
    # the zip file possibly has an outer folder container
    # include both possible structures in the allowed structural paths
    commonprefix = os.path.commonprefix(filenames)
    if commonprefix != acronym + '/':
        # if the user has put the zip files inside another folder, e.g., NGT_videos/NGT/nld/
        subfolders = [commonprefix] + [commonprefix + acronym + '/']
    else:
        subfolders = [acronym + '/']
    video_files = []
    for zipfilename in filenames:
        if zipfilename in subfolders:
            # skip directory nesting structures
            continue
        if '/' not in zipfilename:
            # this is not a path, for example, .DS_Store as for Apple
            continue
        file_dirname = os.path.dirname(zipfilename)
        # this is the path to the media file
        if file_dirname + '/' not in subfolders:
            # this path not an allowed nesting structure, ignore this
            continue
        video_files.append(zipfilename)
    return video_files


def check_zipfile_video_for_gloss_matches(zipvideo):
    path_units = zipvideo.split('/')
    if len(path_units) < 3:
        # the pathname is not long enough
        return False
    filename = path_units[-1]
    filename_without_extension, _ = os.path.splitext(filename)
    lang3code = path_units[-2]
    acronym = path_units[-3]
    glosses = Gloss.objects.filter(lemma__dataset__acronym=acronym,
                                   annotationidglosstranslation__language__language_code_3char=lang3code,
                                   annotationidglosstranslation__text__exact=filename_without_extension)

    # return False if there is either no gloss found or multiple glosses found
    return glosses.count() == 1


def unzip_video_files(dataset, zipped_videos_file, destination):
    lang3charcodes = [language.language_code_3char for language in dataset.translation_languages.all()]
    with zipfile.ZipFile(zipped_videos_file, "r") as zf:
        for name in zf.namelist():
            if not name.endswith('.mp4'):
                # this can be an Apple .DS_Store file
                continue
            # this is a video
            # check that the path is correct before extracting
            filename = os.path.basename(name)
            folder_name = os.path.dirname(name)
            path_units = folder_name.split('/')
            if len(path_units) != 2:
                # path does not have form dataset/lang3char/annotation.mp4
                continue
            lang3code = path_units[-1]
            acronym = path_units[-2]
            if acronym != str(dataset.acronym) or lang3code not in lang3charcodes:
                # path is not correct, ignore
                continue
            localfilepath = zf.extract(name, destination)
            new_location = os.path.join(destination, str(dataset.acronym), lang3code, filename)
            shutil.move(localfilepath, new_location)

    unzipped_filename = os.path.basename(zipped_videos_file)
    folder_name, extension = os.path.splitext(unzipped_filename)
    unzipped_folder = os.path.join(destination, folder_name)

    # originally there was a cleanup here
    return


def unzip_video_files_ids(dataset, zipped_videos_file, destination):

    with zipfile.ZipFile(zipped_videos_file, "r") as zf:
        for name in zf.namelist():
            if not name.endswith('.mp4'):
                # this can be an Apple .DS_Store file
                continue
            # this is a video
            filename = os.path.basename(name)

            # The ZipFile module does not like os.path.join paths
            # The zip file needs to be unzipped in the same location as itself, then files are moved
            unzip_location = WRITABLE_FOLDER + destination + 'TEMP'
            new_location = WRITABLE_FOLDER + destination + str(dataset.acronym) + '/' + filename
            try:
                localfilepath = zf.extract(name, unzip_location)

                shutil.move(localfilepath, new_location)
            except (OSError, PermissionError):
                print('File system error unzipping')
                continue


def uploaded_zip_archives(dataset):
    # find the uploaded zip archives in TEMP that include the dataset
    zip_archive = dict()
    zipped_archive_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, 'TEMP')
    if os.path.isdir(zipped_archive_directory):
        for file_or_folder in os.listdir(zipped_archive_directory):
            file_or_folder_path = os.path.join(zipped_archive_directory, file_or_folder)
            if os.path.isdir(file_or_folder_path):
                continue
            if not zipfile.is_zipfile(file_or_folder_path):
                continue
            archive_contents = get_filenames(file_or_folder_path)
            common_prefix = os.path.commonprefix(archive_contents)
            if dataset.acronym not in common_prefix:
                continue
            zipfilename = os.path.basename(file_or_folder_path)
            zip_archive[zipfilename] = get_filenames_with_filetype(file_or_folder_path)
    return zip_archive


def get_gloss_filepath(video_file_path, gloss):

    filename = os.path.basename(video_file_path)
    filename_without_extension, _ = os.path.splitext(filename)
    filepath, extension = os.path.splitext(video_file_path)
    file_folder_path = os.path.dirname(video_file_path)
    path_units = file_folder_path.split('/')
    language_code_3char = path_units[-1]
    dataset_acronym = path_units[-2]

    # get language of import_videos path
    language = Language.objects.filter(language_code_3char=language_code_3char).first()
    if not language:
        return "", "", ""
    # get the annotation text of the gloss
    annotationidglosstranslation = gloss.annotationidglosstranslation_set.all().filter(language=language)
    if not annotationidglosstranslation:
        # the gloss has no annotations for the language
        return "", "", ""
    annotation_text = annotationidglosstranslation.first().text
    if annotation_text != filename_without_extension:
        # gloss annotation does not match zip file name
        return "", "", ""
    two_letter_dir = get_two_letter_dir(gloss.idgloss)
    destination_folder = os.path.join(
        WRITABLE_FOLDER,
        GLOSS_VIDEO_DIRECTORY,
        dataset_acronym,
        two_letter_dir
    )

    if not os.path.exists(destination_folder):
        os.mkdir(destination_folder, mode=0o775)

    idgloss = gloss.idgloss
    glossid = str(gloss.id)

    video_file_name = idgloss + '-' + glossid + extension
    goal = os.path.join(destination_folder, video_file_name)
    video_path = os.path.join(GLOSS_VIDEO_DIRECTORY,
                              dataset_acronym,
                              two_letter_dir)
    return goal, video_file_name, video_path


def get_gloss_filepath_glossid(video_file_path, gloss):

    filename = os.path.basename(video_file_path)
    filename_without_extension, _ = os.path.splitext(filename)
    filepath, extension = os.path.splitext(video_file_path)
    file_folder_path = os.path.dirname(video_file_path)
    path_units = file_folder_path.split('/')
    dataset_acronym = path_units[-1]

    if not gloss.lemma or not gloss.lemma.dataset:
        return "", "", ""

    idgloss = gloss.idgloss
    glossid = str(gloss.id)
    if glossid != filename_without_extension:
        # gloss id does not match zip file name
        return "", "", ""

    two_letter_dir = get_two_letter_dir(gloss.idgloss)
    destination_folder = os.path.join(
        WRITABLE_FOLDER,
        GLOSS_VIDEO_DIRECTORY,
        dataset_acronym,
        two_letter_dir
    )

    if not os.path.exists(destination_folder):
        os.mkdir(destination_folder, mode=0o775)

    video_file_name = idgloss + '-' + glossid + extension
    goal = os.path.join(destination_folder, video_file_name)
    video_path = os.path.join(GLOSS_VIDEO_DIRECTORY,
                              dataset_acronym,
                              two_letter_dir)
    return goal, video_file_name, video_path


def remove_video_file_from_import_videos(video_file_path):
    errors = ""
    if not os.path.exists(video_file_path):
        return errors
    try:
        os.remove(video_file_path)
        errors = ""
    except OSError:
        errors = "Cannot delete the source video: " + video_file_path
    return errors


def remove_zip_file_from_archive(path_to_zip):
    errors = ""
    if not os.path.exists(path_to_zip):
        return errors
    try:
        os.remove(path_to_zip)
        errors = ""
    except OSError:
        errors = "Cannot delete the zip file: " + path_to_zip
    return errors


def save_video(video_file_path, goal):
    # this is called inside an atomic block

    try:
        shutil.copyfile(video_file_path, goal)
        return True, ""
    except IOError as e:
        feedback_message = getattr(e, 'message', repr(e))
        return False, feedback_message


@csrf_exempt
def import_video_file(request, gloss, video_file_path, useid=False):
    # request is needed as a parameter to the GlossVideoHistory
    try:
        with atomic():
            if useid:
                goal_gloss_file_path, video_file_name, video_path = get_gloss_filepath_glossid(video_file_path, gloss)
            else:
                goal_gloss_file_path, video_file_name, video_path = get_gloss_filepath(video_file_path, gloss)
            if not goal_gloss_file_path:
                errors = "Incorrect gloss path for import."
                errors_deleting = remove_video_file_from_import_videos(video_file_path)
                if errors_deleting and DEBUG_VIDEOS:
                    print('import_video_file: ', errors_deleting)
                return "Failed", errors
            existing_videos = GlossVideo.objects.filter(gloss=gloss, glossvideonme=None, glossvideoperspective=None, version=0)
            if existing_videos.count():
                # overwrite existing video using shutil
                success, feedback = save_video(video_file_path, goal_gloss_file_path)
                if success:
                    # make sure the video name stored in GlossVideo matches the uploaded video
                    existing_glossvideo = existing_videos.first()
                    vidfile_folder = os.path.dirname(existing_glossvideo.videofile.name)
                    new_glossvideo_name = os.path.join(vidfile_folder, video_file_name)
                    existing_glossvideo.videofile.name = new_glossvideo_name
                    existing_glossvideo.save()
                    # refresh poster image
                    existing_videos.first().make_poster_image()
                    glossvideohistory = GlossVideoHistory(action="import",
                                                          gloss=gloss,
                                                          actor=request.user,
                                                          uploadfile=video_file_name,
                                                          goal_location=goal_gloss_file_path)
                    glossvideohistory.save()
                    status, errors = 'Success', ""
                else:
                    status, errors = 'Failed', feedback

            else:
                # make new GlossVideo object for new video
                video = GlossVideo(gloss=gloss, glossvideonme=None, glossvideoperspective=None,
                                   version=0)
                new_glossvideo_name = os.path.join(video_path, video_file_name)
                with open(video_file_path, 'rb') as f:
                    video.videofile.save(new_glossvideo_name, File(f), save=True)
                video.save()
                video.make_poster_image()
                glossvideohistory = GlossVideoHistory(action="import",
                                                      gloss=gloss,
                                                      actor=request.user,
                                                      uploadfile=video_file_name,
                                                      goal_location=goal_gloss_file_path)
                glossvideohistory.save()
                status, errors = 'Success', ""
    except (DatabaseError, TransactionManagementError, OSError):
        status, errors = "Failed", "Failed"

    errors_deleting = remove_video_file_from_import_videos(video_file_path)
    if errors_deleting and DEBUG_VIDEOS:
        print('import_video_file: ', errors_deleting)

    return status, errors
