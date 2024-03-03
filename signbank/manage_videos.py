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
from signbank.zip_interface import *


def upload_zipped_videos_folder(request):
    # this is a button in the DatasetMediaView
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

    with atomic():
        unzip_video_files(dataset, goal_zipped_file, VIDEOS_TO_IMPORT_FOLDER)

    messages.add_message(request, messages.INFO, _("Upload zipped videos media was successful."))
    return HttpResponseRedirect(reverse('admin_dataset_media', args=[dataset.id]))


def listing_uploaded_videos(dataset):
    # this is used in the context of the DatasetMediaView template

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


def import_video_to_gloss_manager(request, video_file_path):
    # this sets dictionary data to be used in the DatasetMediaView template

    import_video_data = dict()
    filename = os.path.basename(video_file_path)
    file_folder_path = os.path.dirname(video_file_path)
    path_units = file_folder_path.split('/')
    language_3_code = path_units[-1]
    dataset_acronym = path_units[-2]
    videopath = 'import_videos/' + dataset_acronym + '/' + language_3_code + '/' + filename
    (filename_without_extension, extension) = os.path.splitext(filename)
    gloss = Gloss.objects.filter(lemma__dataset__acronym=dataset_acronym,
                                 annotationidglosstranslation__language__language_code_3char=language_3_code,
                                 annotationidglosstranslation__text__exact=filename_without_extension).first()
    if not gloss:
        errors = "Gloss not found. for " + filename_without_extension
        import_video_data["gloss"] = ""
        import_video_data["videopath"] = videopath
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
        import_video_data["videopath"] = videopath
        import_video_data["videofile"] = filename
        import_video_data["videolink"] = settings.URL + settings.PREFIX_URL + '/dictionary/protected_media/' + video_path
        import_video_data["uploadstatus"] = "Success"
        import_video_data["errors"] = errors
    else:
        import_video_data["gloss"] = str(gloss.id)
        import_video_data["videopath"] = videopath
        import_video_data["videofile"] = filename
        import_video_data["videolink"] = ""
        import_video_data["uploadstatus"] = "Wrong video format."
        import_video_data["errors"] = "Video file is not h264."
    return import_video_data


def import_video_to_gloss_json(request):
    # this is an ajax call in the DatasetMediaView template
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

    import_folder_exists = os.path.exists(VIDEOS_TO_IMPORT_FOLDER)
    if not import_folder_exists:
        return JsonResponse({})

    # make sure the user can write to this dataset
    from guardian.shortcuts import get_objects_for_user
    user_change_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset,
                                                accept_global_perms=False)
    if not user_change_datasets or dataset not in user_change_datasets:
        return JsonResponse({})

    videofile = request.POST.get('videofile', '')
    if not videofile:
        return JsonResponse({})

    video_data = import_video_to_gloss_manager(request, videofile)
    return JsonResponse(video_data)
