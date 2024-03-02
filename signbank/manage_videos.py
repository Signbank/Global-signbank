import json

from signbank.dictionary.models import *
from django.db.models import FileField
from django.core.files.base import ContentFile, File
from tagging.models import Tag, TaggedItem
from signbank.dictionary.forms import *
from django.utils.translation import override, gettext_lazy as _, activate
from signbank.settings.server_specific import LANGUAGES, LEFT_DOUBLE_QUOTE_PATTERNS, RIGHT_DOUBLE_QUOTE_PATTERNS

from django.contrib import messages

from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import permission_required
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from signbank.settings.server_specific import VIDEOS_TO_IMPORT_FOLDER
import zipfile
from django.urls import reverse, reverse_lazy
import urllib.request
import tempfile
import shutil
import os
from signbank.video.convertvideo import probe_format
from signbank.video.models import GlossVideo, GlossVideoHistory
from django.http import StreamingHttpResponse
from django.contrib.auth.models import Group, User


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
        settings.WRITABLE_FOLDER,
        settings.GLOSS_VIDEO_DIRECTORY,
        dataset_acronym,
        two_letter_dir
    )

    if not os.path.isdir(destination_folder):
        os.mkdir(destination_folder)

    glossid = str(gloss.id)

    video_file_name = annotation_text + '-' + glossid + extension
    goal = os.path.join(destination_folder, video_file_name)
    video_path = os.path.join(settings.GLOSS_VIDEO_DIRECTORY,
                              dataset_acronym,
                              two_letter_dir)
    return goal, video_file_name, video_path


def import_folder(video_file_path):
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
                files_in_zip_archive[entry.filename] = False
                continue
            files_in_zip_archive[entry.filename] = True
        return files_in_zip_archive


def check_subfolders_for_unzipping(acronym, lang3charcodes, filenames):
    # the zip file possibly has an outer folder container
    # include both possible structures in the allowed structural paths
    commonprefix = os.path.commonprefix(filenames)
    subfolders = ([commonprefix] +
                  [commonprefix + acronym + '/' + lang3char + '/' for lang3char in lang3charcodes] +
                  [acronym + '/' + lang3char + '/' for lang3char in lang3charcodes])
    video_files = []
    for zipfilename in filenames:
        if zipfilename in subfolders:
            # skip directory nesting structures
            continue
        if '/' not in zipfilename:
            # this is not a path
            continue
        file_dirname = os.path.dirname(zipfilename)
        if file_dirname + '/' not in subfolders:
            # this path not an allowed nesting structure, ignore this
            continue
        video_files.append(zipfilename)
    return video_files


def unzip_video_files(dataset, zipped_videos_file, destination):
    with zipfile.ZipFile(zipped_videos_file, "r") as zf:
        for name in zf.namelist():
            if not name.endswith('.mp4'):
                # this can be an Apple .DS_Store file
                continue
            # this is a video
            localfilepath = zf.extract(name, destination)
            path_units = localfilepath.split('/')
            filename = path_units[-1]
            lang3code = path_units[-2]
            new_location = os.path.join(destination, dataset.acronym, lang3code, filename)
            shutil.move(localfilepath, new_location)

    unzipped_filename = os.path.basename(zipped_videos_file)
    folder_name, extension = os.path.splitext(unzipped_filename)
    unzipped_folder = os.path.join(destination, folder_name)
    if os.path.exists(unzipped_folder):
        shutil.rmtree(unzipped_folder)

    return


def upload_zipped_videos_folder(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, _('Please login to use this functionality.'))
        return HttpResponseRedirect('/')

    # check if the user can manage this dataset
    from django.contrib.auth.models import Group, User

    try:
        group_manager = Group.objects.get(name='Dataset_Manager')
    except ObjectDoesNotExist:
        messages.add_message(request, messages.ERROR, _('No group Dataset_Manager found.'))
        return HttpResponseRedirect('/')

    groups_of_user = request.user.groups.all()
    if group_manager not in groups_of_user:
        messages.add_message(request, messages.ERROR,
                             _('You must be in group Dataset Manager to upload a zip video archive.'))
        return HttpResponseRedirect('/')

    if 'dataset' in request.POST and request.POST['dataset'] is not None:
        datasetid = request.POST['dataset']
    else:
        datasetid = settings.DEFAULT_DATASET_PK

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return HttpResponseRedirect('/')

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        return HttpResponseRedirect('/')

    lang3charcodes = [language.language_code_3char for language in dataset.translation_languages.all()]

    # make sure the user can write to this dataset
    from guardian.shortcuts import get_objects_for_user
    user_change_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset,
                                                accept_global_perms=False)
    if not user_change_datasets or dataset not in user_change_datasets:
        messages.add_message(request, messages.ERROR, _('No change dataset permission.'))
        return HttpResponseRedirect('/')

    import_folder_exists = os.path.exists(VIDEOS_TO_IMPORT_FOLDER)
    if not import_folder_exists:
        messages.add_message(request, messages.ERROR,
                             _("Upload zip archive: The folder VIDEOS_TO_IMPORT_FOLDER is missing."))
        return HttpResponseRedirect(reverse('admin_dataset_media', args=[dataset.id]))

    zipped_file = request.FILES.get('file')
    filename = zipped_file.name
    filetype = zipped_file.content_type

    if not filetype:
        # unrecognised file type has been uploaded
        messages.add_message(request, messages.ERROR, _("Upload zip archive: The file has an unknown type."))
        return HttpResponseRedirect(reverse('admin_dataset_media', args=[dataset.id]))

    if not zipfile.is_zipfile(zipped_file):
        # unrecognised file type has been uploaded
        messages.add_message(request, messages.ERROR, _("Upload zip archive: The file is not a zip file."))
        return HttpResponseRedirect(reverse('admin_dataset_media', args=[dataset.id]))

    norm_filename = os.path.normpath(filename)
    split_norm_filename = norm_filename.split('.')

    if len(split_norm_filename) == 1:
        # file has no extension
        messages.add_message(request, messages.ERROR, _("Upload zip archive: The file has no extension."))
        return HttpResponseRedirect(reverse('admin_dataset_media', args=[dataset.id]))

    # Create the folder if needed
    temp_goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, 'TEMP')
    if not os.path.isdir(temp_goal_directory):
        os.mkdir(temp_goal_directory, mode=0o777)

    goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym)
    if not os.path.isdir(goal_directory):
        os.mkdir(temp_goal_directory, mode=0o777)
    goal_zipped_file = temp_goal_directory + os.sep + norm_filename

    with open(goal_zipped_file, "wb+") as destination:
        for chunk in zipped_file.chunks():
            destination.write(chunk)
        destination.close()

    for lang3char in lang3charcodes:
        dataset_subfolder = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym, lang3char)
        if not os.path.isdir(dataset_subfolder):
            os.mkdir(dataset_subfolder, mode=0o777)

    filenames = get_filenames(goal_zipped_file)
    video_paths_okay = check_subfolders_for_unzipping(dataset.acronym, lang3charcodes, filenames)
    if not video_paths_okay:
        messages.add_message(request, messages.ERROR, _("Upload zip archive: The zip archive has the wrong structure."))
        return HttpResponseRedirect(reverse('admin_dataset_media', args=[dataset.id]))

    unzip_video_files(dataset, goal_zipped_file, VIDEOS_TO_IMPORT_FOLDER)

    messages.add_message(request, messages.INFO, _("Upload zipped videos media was successful."))
    return HttpResponseRedirect(reverse('admin_dataset_media', args=[dataset.id]))


def listing_uploaded_videos(dataset):
    dataset_acronym = str(dataset.acronym)
    goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset_acronym)
    list_of_video_gloss_status = dict()

    if os.path.isdir(goal_directory):
        for language3char in os.listdir(goal_directory):
            if language3char not in list_of_video_gloss_status.keys():
                list_of_video_gloss_status[language3char] = []
            language_subfolder = os.path.join(goal_directory, language3char)
            if os.path.isdir(language_subfolder):
                for file in os.listdir(language_subfolder):
                    video_file_path = os.path.join(goal_directory, language3char, file)
                    import_folder = os.path.join(dataset_acronym, language3char, file)
                    format = probe_format(video_file_path)
                    (filename_without_extension, extension) = os.path.splitext(file)
                    gloss = Gloss.objects.filter(lemma__dataset=dataset,
                                                 annotationidglosstranslation__language__language_code_3char=language3char,
                                                 annotationidglosstranslation__text__exact=filename_without_extension).first()
                    if format.startswith('h264'):
                        # the output of ffmpeg includes extra information following h264, so only check the prefix
                        list_of_video_gloss_status[language3char].append((video_file_path, import_folder, file, True, gloss))
                    else:
                        list_of_video_gloss_status[language3char].append((video_file_path, import_folder, file, False, gloss))

    return list_of_video_gloss_status


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


def uploaded_video_files(dataset):
    dataset_acronym = str(dataset.acronym)
    goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset_acronym)
    list_of_videos = dict()

    if os.path.isdir(goal_directory):
        for language3char in os.listdir(goal_directory):
            if language3char not in list_of_videos.keys():
                list_of_videos[language3char] = []
            language_subfolder = os.path.join(goal_directory, language3char)
            if os.path.isdir(language_subfolder):
                for file in os.listdir(language_subfolder):
                    list_of_videos[language3char].append(file)
    return list_of_videos


def uploaded_video_filepaths(dataset):
    dataset_acronym = str(dataset.acronym)
    goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset_acronym)
    list_of_video_paths = []

    if os.path.isdir(goal_directory):
        for language3char in os.listdir(goal_directory):
            language_subfolder = os.path.join(goal_directory, language3char)
            if os.path.isdir(language_subfolder):
                for file in os.listdir(language_subfolder):
                    video_path = os.path.join(goal_directory, language3char, file)
                    list_of_video_paths.append(video_path)
    return list_of_video_paths


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


def get_two_letter_dir(idgloss):
    foldername = idgloss[:2]

    if len(foldername) == 1:
        foldername += '-'

    return foldername


def save_video(video_file_path, goal):
    # this is called inside an atomic block

    try:
        shutil.copyfile(video_file_path, goal)
        return True
    except IOError:
        return False


def import_video_file(request, gloss, video_file_path):
    # request is included as a parameter to add to the GlossVideoHistory
    with atomic():
        goal_gloss_file_path, video_file_name, video_path = get_gloss_filepath(video_file_path, gloss)
        if not goal_gloss_file_path:
            return "Failed", "Incorrect gloss path for import"
        existing_videos = GlossVideo.objects.filter(gloss=gloss)
        if existing_videos.count():
            for video_object in existing_videos:
                video_object.reversion(revert=False)

        # overwritten should not happen because we already backed up the original videos
        success = save_video(video_file_path, goal_gloss_file_path)

        if success:
            # make new GlossVideo object for new video
            video = GlossVideo(gloss=gloss,
                               version=0)
            with open(video_file_path, 'rb') as f:
                f.seek(0)
                video.videofile.save(os.path.basename(video_file_path), File(f), save=False)
            video.save()
            # video.make_poster_image()
            glossvideohistory = GlossVideoHistory(action="import",
                                                  gloss=gloss,
                                                  actor=request.user,
                                                  uploadfile=video_file_path,
                                                  goal_location=goal_gloss_file_path)
            glossvideohistory.save()
            status = 'Success'
        else:
            # import failed to copy new video, put originals back
            if existing_videos.count():
                for video_object in existing_videos:
                    video_object.reversion(revert=True)
            status = 'Failed'

        # errors are if the import_videos video can not be removed
        # errors = remove_video_file_from_import_videos(video_file_path)
        errors = ""
        return status, errors


def import_video_to_gloss_manage(request, video_file_path):
    # request is included as a parameter to add to the GlossVideoHistory in the called functions

    import_video_data = dict()
    filename = os.path.basename(video_file_path)
    file_folder_path = os.path.dirname(video_file_path)
    path_units = file_folder_path.split('/')
    language_3_code = path_units[-1]
    dataset_acronym = path_units[-2]
    json_path_key = 'import_videos/' + dataset_acronym + '/' + language_3_code + '/' + filename
    (filename_without_extension, extension) = os.path.splitext(filename)
    gloss = Gloss.objects.filter(lemma__dataset__acronym=dataset_acronym,
                                 annotationidglosstranslation__language__language_code_3char=language_3_code,
                                 annotationidglosstranslation__text__exact=filename_without_extension).first()
    if not gloss:
        errors = "Gloss not found. for " + filename_without_extension
        import_video_data["gloss"] = ""
        import_video_data["videopath"] = json_path_key
        import_video_data["videofile"] = filename
        import_video_data["videolink"] = ""
        import_video_data["uploadstatus"] = "Gloss not found."
        errors_deleting = remove_video_file_from_import_videos(video_file_path)
        if errors_deleting:
            errors = errors + errors_deleting
            import_video_data["errors"] = errors + errors_deleting
        else:
            import_video_data["errors"] = errors
        return import_video_data
    format = probe_format(video_file_path)
    if format.startswith('h264'):
        # the output of ffmpeg includes extra information following h264, so only check the prefix
        status, errors = import_video_file(request, gloss, video_file_path)
        video_path = gloss.get_video_url()
        import_video_data["gloss"] = str(gloss.id)
        import_video_data["videopath"] = json_path_key
        import_video_data["videofile"] = filename
        import_video_data["videolink"] = settings.URL + settings.PREFIX_URL + '/dictionary/protected_media/' + video_path
        import_video_data["uploadstatus"] = "Success"
        import_video_data["errors"] = errors
    else:
        import_video_data["gloss"] = str(gloss.id)
        import_video_data["videopath"] = json_path_key
        import_video_data["videofile"] = filename
        import_video_data["videolink"] = ""
        import_video_data["uploadstatus"] = "Wrong video format."
        import_video_data["errors"] = "Video file is not h264."
    return import_video_data


def import_video_to_gloss_json(request):
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

    if 'dataset' in request.POST and request.POST['dataset'] is not None:
        datasetid = request.POST['dataset']
    else:
        datasetid = settings.DEFAULT_DATASET_PK

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return JsonResponse({})

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset:
        return JsonResponse({})

    import_folder_exists = os.path.exists(VIDEOS_TO_IMPORT_FOLDER)
    if not import_folder_exists:
        return JsonResponse({})

    # make sure the user can write to this dataset
    from guardian.shortcuts import get_objects_for_user
    user_change_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset,
                                                accept_global_perms=False)
    if not user_change_datasets or dataset not in user_change_datasets:
        return JsonResponse({})

    videofile = request.POST.get('videofile')
    video_data = import_video_to_gloss_manage(request, videofile)
    return JsonResponse(video_data)
