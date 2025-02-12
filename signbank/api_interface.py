import json
import urllib.request
import tempfile
import shutil
import os
import stat
import zipfile
import sys

from urllib.parse import quote
from urllib.error import URLError
from requests.exceptions import InvalidURL
from guardian.shortcuts import get_objects_for_user, get_user_perms
from tagging.models import Tag, TaggedItem

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group, User
from django.contrib.auth.decorators import permission_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import override, gettext_lazy as _, activate
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse, StreamingHttpResponse
from django.urls import reverse, reverse_lazy

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile, File

from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError
from django.db.models import FileField

import signbank.tools
from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from signbank.settings.server_specific import LANGUAGES, LEFT_DOUBLE_QUOTE_PATTERNS, RIGHT_DOUBLE_QUOTE_PATTERNS, VIDEOS_TO_IMPORT_FOLDER
from signbank.api_token import put_api_user_in_request
from signbank.abstract_machine import get_interface_language_api, get_human_readable_value_dict
from signbank.video.convertvideo import probe_format
from signbank.video.models import GlossVideo, GlossVideoHistory
from signbank.zip_interface import *


def check_api_dataset_manager_permissions(request, datasetid):

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        return None, {"error": "Dataset with given id does not exist."}, 400

    group_manager = Group.objects.filter(name='Dataset_Manager').first()
    if not group_manager:
        return None, {"error": "No group Dataset Manager found."}, 400

    groups_of_user = request.user.groups.all()
    if group_manager not in groups_of_user:
        return None, {"error": "You must be in group Dataset Manager to upload a zip video archive."}, 400

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)
    if dataset not in change_permit_datasets:
        return None, {"error": "No change permission for dataset."}, 400

    if not request.user.has_perm('dictionary.change_gloss'):
        return None, {"error": "No permission."}, 400

    return dataset, {}, 200


def check_api_file_storage(dataset):

    import_folder = os.path.join(WRITABLE_FOLDER, API_VIDEO_ARCHIVES)
    import_folder_exists = os.path.exists(import_folder)
    if not import_folder_exists:
        return {"error": "Upload zip archive: The folder API_VIDEO_ARCHIVES is missing."}, 400

    # Create the TEMP folder if needed
    temp_goal_directory = os.path.join(WRITABLE_FOLDER, API_VIDEO_ARCHIVES, 'TEMP')
    if not os.path.exists(temp_goal_directory):
        try:
            os.mkdir(temp_goal_directory, mode=0o775)
        except (OSError, PermissionError):
            return {"error": "Upload zip archive: The folder API_VIDEO_ARCHIVES/TEMP is missing."}, 400

    dataset_folder = os.path.join(WRITABLE_FOLDER, API_VIDEO_ARCHIVES, dataset.acronym)
    dataset_folder_exists = os.path.exists(dataset_folder)
    if not dataset_folder_exists:
        try:
            os.mkdir(dataset_folder, mode=0o775)
        except (OSError, PermissionError):
            return {"error": f"Upload zip archive: The folder API_VIDEO_ARCHIVES/{dataset.acronym} cannot be created."}, 400

    import_folder_exists = os.path.exists(VIDEOS_TO_IMPORT_FOLDER)
    if not import_folder_exists:
        return {"error": "Upload zip archive: The folder VIDEOS_TO_IMPORT_FOLDER is missing."}, 400

    lang3charcodes = [language.language_code_3char for language in dataset.translation_languages.all()]

    # Create the TEMP folder if needed
    temp_goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, 'TEMP')
    if not os.path.exists(temp_goal_directory):
        try:
            os.mkdir(temp_goal_directory, mode=0o775)
        except (OSError, PermissionError):
            return {
                "error": f"Upload zip archive: The folder VIDEOS_TO_IMPORT_FOLDER/TEMP cannot be created."}, 400

    dataset_folder = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym)
    dataset_folder_exists = os.path.exists(dataset_folder)
    if not dataset_folder_exists:
        try:
            os.mkdir(dataset_folder, mode=0o775)
        except (OSError, PermissionError):
            return {
                "error": f"Upload zip archive: The folder VIDEOS_TO_IMPORT_FOLDER/{dataset.acronym} cannot be created."}, 400

    for lang3char in lang3charcodes:
        dataset_lang3char_folder = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym, lang3char)
        if not os.path.exists(dataset_lang3char_folder):
            try:
                os.mkdir(dataset_lang3char_folder, mode=0o775)
            except (OSError, PermissionError):
                return {
                    "error": f"Upload zip archive: The folder VIDEOS_TO_IMPORT_FOLDER/{dataset.acronym}/{lang3char} cannot be created."}, 400

    return {}, 200


def api_fields(dataset, language_code='en', advanced=False):
    activate(language_code)
    api_fields_2023 = []
    if not dataset:
        dataset = Dataset.objects.get(acronym=settings.DEFAULT_DATASET_ACRONYM)
    if advanced:
        for language in dataset.translation_languages.all():
            language_field = gettext("Lemma ID Gloss") + ": %s" % language.name
            api_fields_2023.append(language_field)
    for language in dataset.translation_languages.all():
        language_field = gettext("Annotation ID Gloss") + ": %s" % language.name
        api_fields_2023.append(language_field)
    for language in dataset.translation_languages.all():
        language_field = gettext("Senses") + ": %s" % language.name
        api_fields_2023.append(language_field)

    if not advanced:
        api_fields_2023.append(gettext("Handedness"))
        api_fields_2023.append(gettext("Strong Hand"))
        api_fields_2023.append(gettext("Weak Hand"))
        api_fields_2023.append(gettext("Location"))
        api_fields_2023.append(gettext("Semantic Field"))
        api_fields_2023.append(gettext("Word Class"))
        api_fields_2023.append(gettext("Named Entity"))
        api_fields_2023.append(gettext("Link"))
        api_fields_2023.append(gettext("Video"))
    else:
        api_fields_2023.append(gettext("Link"))
        api_fields_2023.append(gettext("Video"))
        api_fields_2023.append(gettext("Tags"))
        api_fields_2023.append(gettext("Notes"))
        api_fields_2023.append(gettext("Affiliation"))
        api_fields_2023.append(gettext("Sequential Morphology"))
        api_fields_2023.append(gettext("Simultaneous Morphology"))
        api_fields_2023.append(gettext("Blend Morphology"))

        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
        gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

        # TO DO
        extra_columns = ['Sign Languages', 'Dialects',
                         'Relations to other signs', 'Relations to foreign signs', 'Notes']

        # show advanced properties
        for field in gloss_fields:
            api_fields_2023.append(field.verbose_name.title())

        api_fields_2023.append(gettext("NME Videos"))

    return api_fields_2023


@csrf_exempt
@put_api_user_in_request
def get_fields_data_json(request, datasetid):
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)
    if request.user.is_authenticated:
        interface_language_code = get_interface_language_api(request, request.user)

    sequence_of_digits = True
    for i in datasetid:
        if not i.isdigit():
            sequence_of_digits = False
            break

    if not sequence_of_digits:
        return JsonResponse({})

    dataset_id = int(datasetid)
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        # ignore the database in the url if necessary
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)

    if request.user.has_perm('dictionary.change_gloss'):
        api_fields_2023 = api_fields(dataset, interface_language_code, advanced=True)
    else:
        api_fields_2023 = api_fields(dataset, interface_language_code, advanced=False)

    result = {'fields': api_fields_2023}

    return JsonResponse(result)


@csrf_exempt
@put_api_user_in_request
def get_gloss_data_json(request, datasetid, glossid):
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)
    if request.user.is_authenticated:
        interface_language_code = get_interface_language_api(request, request.user)

    sequence_of_digits = True
    for i in datasetid:
        if not i.isdigit():
            sequence_of_digits = False
            break

    if not sequence_of_digits:
        return JsonResponse({})

    dataset_id = int(datasetid)
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        # ignore the dataset in the url if necessary
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)

    sequence_of_digits = True
    for i in glossid:
        if not i.isdigit():
            sequence_of_digits = False
            break

    if not sequence_of_digits:
        return JsonResponse({})

    gloss_id = int(glossid)
    gloss = Gloss.objects.filter(lemma__dataset=dataset, id=gloss_id, archived=False).first()

    if not gloss:
        return JsonResponse({})

    if request.user.has_perm('dictionary.change_gloss'):
        api_fields_2023 = api_fields(dataset, interface_language_code, advanced=True)
    else:
        api_fields_2023 = api_fields(dataset, interface_language_code, advanced=False)

    gloss_data = dict()
    gloss_data[str(gloss.pk)] = gloss.get_fields_dict(api_fields_2023, interface_language_code)

    return JsonResponse(gloss_data, safe=False)


@csrf_exempt
@put_api_user_in_request
def get_annotated_sentences_of_gloss_json(request, datasetid, glossid):

    from django.utils.translation import gettext_lazy as _, activate, gettext
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)
    if request.user.is_authenticated:
        interface_language_code = get_interface_language_api(request, request.user)

    dataset_id = int(datasetid)
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        return JsonResponse({"error": "No dataset found or no permission."}, status=400)
    dataset_languages = dataset.translation_languages.all()

    gloss_id = int(glossid)
    gloss = Gloss.objects.filter(lemma__dataset=dataset, id=gloss_id, archived=False).first()

    if not gloss:
        return JsonResponse({"error": "No gloss found or no permission."}, status=400)

    if not request.user.has_perm('dictionary.change_gloss'):
        return JsonResponse({"error": "No permission to change this gloss."}, status=400)

    annotated_sentences = []
    related_sentences = AnnotatedSentence.objects.filter(annotated_glosses__gloss = gloss).distinct()
    for sentence in related_sentences.all():
        sentence_dict = dict()
        sentence_dict["id"] = sentence.id
        for language in dataset_languages:
            translations_name = gettext("Translation") + " (" + language.name + ")"
            contexts_name = gettext("Context") + " (" + language.name + ")"
            translation = sentence.annotated_sentence_translations.filter(language=language).first()
            if translation:
                sentence_dict[translations_name] = translation.text
            else:
                sentence_dict[translations_name] = ""
            context = sentence.annotated_sentence_contexts.filter(language=language).first()
            if context:
                sentence_dict[contexts_name] = context.text
            else:
                sentence_dict[contexts_name] = ""
        if sentence.annotatedvideo.source:
            sentence_dict["Source"] = sentence.annotatedvideo.source.id
        else:
            sentence_dict["Source"] = ""
        if sentence.annotatedvideo.url:
            sentence_dict["Url"] = sentence.annotatedvideo.url
        else:
            sentence_dict["Url"] = ""
        repr_gloss_list = []
        unrepr_gloss_list = []
        for annotated_gloss in sentence.annotated_glosses.all():
            if annotated_gloss.isRepresentative and str(annotated_gloss.gloss.id) not in repr_gloss_list:
                repr_gloss_list.append(str(annotated_gloss.gloss.id))
            if not annotated_gloss.isRepresentative and str(annotated_gloss.gloss.id) not in unrepr_gloss_list:
                unrepr_gloss_list.append(str(annotated_gloss.gloss.id))
        sentence_dict["Representative glosses"] = repr_gloss_list
        sentence_dict["Unrepresentative glosses"] = unrepr_gloss_list
        annotated_sentences.append(sentence_dict)
    return JsonResponse(annotated_sentences, safe=False)


def check_gloss_existence_for_uploaded_video(dataset):
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
                    (filename_without_extension, extension) = os.path.splitext(file)
                    gloss = Gloss.objects.filter(lemma__dataset=dataset, archived=False,
                                                 annotationidglosstranslation__language__language_code_3char=language3char,
                                                 annotationidglosstranslation__text__exact=filename_without_extension).first()
                    list_of_video_gloss_status[language3char].append((file, True, gloss))

    return list_of_video_gloss_status


def uploaded_video_files(dataset, useid=False):

    dataset_acronym = str(dataset.acronym)
    if useid:
        list_of_videos = []
        goal_directory = os.path.join(WRITABLE_FOLDER, API_VIDEO_ARCHIVES, dataset_acronym)
    else:
        list_of_videos = dict()
        goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset_acronym)

    if not os.path.isdir(goal_directory):
        return list_of_videos

    if useid:
        for file in os.listdir(goal_directory):
            list_of_videos.append(file)
    else:
        for language3char in os.listdir(goal_directory):
            if language3char not in list_of_videos.keys():
                list_of_videos[language3char] = []
            language_subfolder = os.path.join(goal_directory, language3char)
            if os.path.isdir(language_subfolder):
                for file in os.listdir(language_subfolder):
                    list_of_videos[language3char].append(file)
    return list_of_videos


def uploaded_video_filepaths(dataset, useid=False):

    dataset_acronym = str(dataset.acronym)
    if useid:
        goal_directory = os.path.join(WRITABLE_FOLDER, API_VIDEO_ARCHIVES, dataset_acronym)
    else:
        goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset_acronym)
    list_of_video_paths = []

    if not os.path.isdir(goal_directory):
        return list_of_video_paths

    if useid:
        for file in os.listdir(goal_directory):
            video_path = os.path.join(goal_directory, file)
            list_of_video_paths.append(video_path)
    else:
        for language3char in os.listdir(goal_directory):
            language_subfolder = os.path.join(goal_directory, language3char)
            if os.path.isdir(language_subfolder):
                for file in os.listdir(language_subfolder):
                    video_path = os.path.join(goal_directory, language3char, file)
                    list_of_video_paths.append(video_path)
    return list_of_video_paths


@csrf_exempt
@put_api_user_in_request
def get_unzipped_video_files_json(request, datasetid):

    sequence_of_digits = True
    for i in datasetid:
        if not i.isdigit():
            sequence_of_digits = False
            break

    if not sequence_of_digits:
        return JsonResponse({})

    dataset_id = int(datasetid)
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        return JsonResponse({})

    videos_data = dict()
    videos_data[API_VIDEO_ARCHIVES+dataset.acronym] = uploaded_video_files(dataset, useid=True)

    return JsonResponse(videos_data, safe=False)


def get_dataset_zipfile_value_dict(request):

    value_dict = dict()
    try:
        uploaded_file = request.FILES.get('File')
    except (AttributeError, KeyError):
        return value_dict

    try:
        filename = uploaded_file.name
        goal_path = os.path.join(settings.TMP_DIR, filename)
        f = open(goal_path, 'wb+')
        for chunk in uploaded_file.chunks():
            if not chunk:
                break
            f.write(chunk)
        f.close()
        os.chmod(goal_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

        tempfile = File(f)
        value_dict['File'] = tempfile
    except (OSError, EncodingWarning, UnicodeDecodeError) as e:
        feedback_message = getattr(e, 'message', repr(e))
        print('exception: ', feedback_message)
        pass

    return value_dict


@csrf_exempt
@put_api_user_in_request
def upload_zipped_videos_folder_json(request, datasetid):

    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    # check if the user can manage this dataset
    dataset, errors, status = check_api_dataset_manager_permissions(request, datasetid)
    if not dataset:
        return JsonResponse(errors, status=status)

    errors, status = check_api_file_storage(dataset)
    if errors:
        return JsonResponse(errors, status=status)

    value_dict = get_dataset_zipfile_value_dict(request)

    file_key = gettext("File")
    if file_key not in value_dict.keys():
        return JsonResponse({"error": "Error processing the zip file."}, status=400)

    zip_file = value_dict[file_key]
    file_name = zip_file.name
    goal_zipped_file = os.path.join(VIDEOS_TO_IMPORT_FOLDER, 'TEMP', file_name)
    basename = os.path.basename(file_name)

    try:
        shutil.move(zip_file.name, str(goal_zipped_file))
    except (OSError, PermissionError):
        return JsonResponse({"error": "Could not copy the zip file to the destination folder."}, status=400)

    if not zipfile.is_zipfile(goal_zipped_file):
        # unrecognised file type has been uploaded
        return JsonResponse({"error": "Upload zip archive: The file is not a zip file."}, status=400)

    norm_filename = os.path.normpath(goal_zipped_file)
    split_norm_filename = norm_filename.split('.')

    if len(split_norm_filename) == 1:
        # file has no extension
        return JsonResponse({"error": "Upload zip archive: The file has no extension."}, status=400)

    lang3charcodes = [language.language_code_3char for language in dataset.translation_languages.all()]

    filenames = get_filenames(goal_zipped_file)
    video_paths_okay = check_subfolders_for_unzipping(dataset.acronym, lang3charcodes, filenames)
    if not video_paths_okay:
        default_language_3char = dataset.default_language.language_code_3char
        return JsonResponse({"error": f"The zip archive has the wrong structure. It should be: {dataset.acronym}/{default_language_3char}/annotation.mp4"}, status=400)

    with atomic():
        unzip_video_files(dataset, goal_zipped_file, VIDEOS_TO_IMPORT_FOLDER)

    unzipped_files = uploaded_video_files(dataset, useid=False)

    return JsonResponse({"success": f"Zip archive {basename} uploaded successfully.",
                         "unzippedvideos": unzipped_files}, status=200, safe=False)


@csrf_exempt
@put_api_user_in_request
def upload_zipped_videos_archive(request, datasetid):

    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    # check if the user can manage this dataset
    dataset, errors, status = check_api_dataset_manager_permissions(request, datasetid)
    if not dataset:
        return JsonResponse(errors, status=status)

    errors, status = check_api_file_storage(dataset)
    if errors:
        return JsonResponse(errors, status=status)

    value_dict = get_dataset_zipfile_value_dict(request)

    file_key = gettext("File")
    if file_key not in value_dict.keys():
        return JsonResponse({"error": "Error processing the zip file."}, status=400)

    zip_file = value_dict[file_key]
    file_name = zip_file.name
    goal_zipped_file = os.path.join(WRITABLE_FOLDER, API_VIDEO_ARCHIVES, 'TEMP', file_name)
    basename = os.path.basename(file_name)

    try:
        shutil.move(zip_file.name, str(goal_zipped_file))
    except (OSError, PermissionError):
        return JsonResponse({"error": "Could not copy the zip file to the destination folder."}, status=400)

    if not zipfile.is_zipfile(goal_zipped_file):
        # unrecognised file type has been uploaded
        return JsonResponse({"error": "Upload zip archive: The file is not a zip file."}, status=400)

    norm_filename = os.path.normpath(goal_zipped_file)
    split_norm_filename = norm_filename.split('.')

    if len(split_norm_filename) == 1:
        # file has no extension
        return JsonResponse({"error": "Upload zip archive: The file has no extension."}, status=400)

    filenames = get_filenames(goal_zipped_file)
    video_paths_okay = check_subfolders_for_unzipping_ids(dataset.acronym, filenames)
    if not video_paths_okay:
        return JsonResponse({"error": f"The zip archive has the wrong structure. It should be: {dataset.acronym}/GLOSSID.mp4"}, status=400)

    with atomic():
        unzip_video_files_ids(dataset, goal_zipped_file, API_VIDEO_ARCHIVES)

    unzipped_files = uploaded_video_files(dataset, useid=True)

    return JsonResponse({"success": f"Zip archive {basename} uploaded successfully.",
                         "unzippedvideos": unzipped_files}, status=200, safe=False)


def import_video_to_gloss(request, video_file_path):
    # request is included as a parameter to add to the GlossVideoHistory in the called functions

    import_video_data = dict()
    filename = os.path.basename(video_file_path)
    file_folder_path = os.path.dirname(video_file_path)
    path_units = file_folder_path.split('/')
    if len(path_units) > 1:
        useid = False
        language_3_code = path_units[-1]
        dataset_acronym = path_units[-2]
        json_path_key = dataset_acronym + '/' + language_3_code + '/' + filename
        (filename_without_extension, extension) = os.path.splitext(filename)
        gloss = Gloss.objects.filter(lemma__dataset__acronym=dataset_acronym, archived=False,
                                     annotationidglosstranslation__language__language_code_3char=language_3_code,
                                     annotationidglosstranslation__text__exact=filename_without_extension).first()
    else:
        useid = True
        dataset_acronym = path_units[-1]
        json_path_key = dataset_acronym + '/' + filename
        (filename_without_extension, extension) = os.path.splitext(filename)
        gloss = Gloss.objects.filter(id=int(filename_without_extension), archived=False).first()

    import_video_data[json_path_key] = dict()

    if not gloss:
        errors_deleting = remove_video_file_from_import_videos(video_file_path)
        if errors_deleting and settings.DEBUG_VIDEOS:
            print('import_video_to_gloss: ', errors_deleting)
        import_video_data[json_path_key]["gloss"] = ''
        import_video_data[json_path_key]["videofile"] = filename
        import_video_data[json_path_key]["errors"] = f"Gloss not found for {filename_without_extension}."
        import_video_data[json_path_key]["Video"] = ''
        import_video_data[json_path_key]["importstatus"] = 'Failed'
        return import_video_data

    status, errors = import_video_file(request, gloss, video_file_path, useid=useid)
    if status == 'Success':
        video_path = gloss.get_video_url()
        import_video_data[json_path_key]["Video"] = settings.URL + settings.PREFIX_URL + '/dictionary/protected_media/' + video_path
    else:
        import_video_data[json_path_key]["Video"] = ''
    import_video_data[json_path_key]["gloss"] = str(gloss.id)
    import_video_data[json_path_key]["videofile"] = filename
    import_video_data[json_path_key]["importstatus"] = status
    import_video_data[json_path_key]["errors"] = errors

    return import_video_data


class VideoImporter:
    """An object that implements just the write method of the file-like
    interface. This is based on an example in the Django 4.2 documentation
    """
    line = 0

    def write(self, request, value):
        """Write the value by returning it, instead of storing in a buffer."""
        if value == "start":
            value_json = "{ \"imported_videos\": ["
        elif value == "finish":
            value_json = "]}"
        else:
            video_data = import_video_to_gloss(request, value)
            if self.line > 1:
                value_json = "," + json.dumps(video_data)
            else:
                value_json = json.dumps(video_data)
        self.line += 1
        return value_json


# json.dumps( {key: val} {key: val}, separators=('}', ':'))
def json_start():
    return ["start"]


def json_finish():
    return ["finish"]


@csrf_exempt
@put_api_user_in_request
def upload_videos_to_glosses(request, datasetid):
    # Do this AFTER uploading a zip archive using: /dictionary/upload_videos_to_glosses/5

    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        return JsonResponse({"error": gettext("Dataset not found.")}, status=400)

    if 'change_dataset' not in get_user_perms(request.user, dataset):
        return JsonResponse({"error": gettext("No permission to change dataset")}, status=400)

    # check if the user can manage this dataset
    group_manager = Group.objects.get(name='Dataset_Manager')
    groups_of_user = request.user.groups.all()
    if group_manager not in groups_of_user:
        return JsonResponse({"error": gettext('You must be in group Dataset Manager to import gloss videos.')}, status=400)

    video_file_paths_with_ids = uploaded_video_filepaths(dataset, useid=True)
    video_file_paths_with_annotations = uploaded_video_filepaths(dataset, useid=False)

    pseudo_buffer = VideoImporter()
    return StreamingHttpResponse(
        (pseudo_buffer.write(request, vg) for vg in json_start() + video_file_paths_with_ids + video_file_paths_with_annotations + json_finish()),
        content_type="application/json",
        headers={"Content-Disposition": 'attachment; filename='+'glosses.json'},
    )

def verify_conditions_for_file_upload(request, gloss_id):

    if not request.user:
        return JsonResponse({'error': 'User not found'}, status=401)

    gloss = Gloss.objects.filter(id=gloss_id).first()
    if not gloss:
        return JsonResponse({'error': 'Gloss not found'}, status=404)

    if gloss.archived:
        return JsonResponse({'error': 'Gloss is archived'}, status=403)

    if not gloss.lemma:
        return JsonResponse({'error': 'Gloss has no lemma'}, status=404)

    if not gloss.lemma.dataset:
        return JsonResponse({'error': 'Gloss has no dataset'}, status=404)

    if not request.user.has_perm('dictionary.change_gloss'):
        return JsonResponse({'error': 'No change gloss permission'}, status=403)

    change_permit_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset)

    if gloss.lemma.dataset not in change_permit_datasets:
        return JsonResponse({'error': 'No change permission for dataset'}, status=403)

    if len(gloss.idgloss) < 2:
        return JsonResponse({'error': 'This gloss has no idgloss'}, status=400)

    if len(request.FILES) == 0:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

@csrf_exempt
@put_api_user_in_request
def api_add_video(request, gloss_id):

    CENTER_VIDEO_LABELS = ['center', 'centered', 'mid', 'default', 'file', 'video']
    LEFT_VIDEO_LABELS = ['left', 'l']
    RIGHT_VIDEO_LABELS = ['right', 'r']

    error_response = verify_conditions_for_file_upload(request, gloss_id)

    if error_response:
        return error_response

    gloss = Gloss.objects.filter(id=gloss_id).first()

    for label in request.FILES.keys():
        if label not in CENTER_VIDEO_LABELS and label not in LEFT_VIDEO_LABELS and label not in RIGHT_VIDEO_LABELS:
            return JsonResponse({'error': f"Unrecognized file label '{label}'. Use 'file', 'center', 'left' or 'right'."}, status=400)

    dataset = gloss.lemma.dataset
    nr_of_videos = 0

    for label in CENTER_VIDEO_LABELS:

        if label not in request.FILES.keys():
            continue

        vfile = request.FILES[label]
        gloss.add_video(request.user, vfile, False)
        nr_of_videos += 1

    for label in LEFT_VIDEO_LABELS:

        if label not in request.FILES.keys():
            continue

        vfile = request.FILES[label]
        gloss.add_perspective_video(request.user, vfile, 'left', False)
        nr_of_videos += 1

    for label in RIGHT_VIDEO_LABELS:

        if label not in request.FILES.keys():
            continue

        vfile = request.FILES[label]
        gloss.add_perspective_video(request.user, vfile, 'right', False)
        nr_of_videos += 1

    return JsonResponse({'message': f'Uploaded {nr_of_videos} videos to dataset {dataset}.' }, status=200)


@csrf_exempt
@put_api_user_in_request
def api_add_image(request, gloss_id):
    """
    Handles the upload of an image file for a specific gloss via the API, and saves it to the correct location.
    """

    error_response = verify_conditions_for_file_upload(request, gloss_id)

    if error_response:
        return error_response

    gloss = Gloss.objects.filter(id=gloss_id).first()
    image_file = list(request.FILES.values())[0]

    # Construct a filename for the image, use sn if present, otherwise use idgloss+gloss id
    file_extension = os.path.splitext(image_file.name)[1].lower()
    if file_extension not in settings.SUPPORTED_CITATION_IMAGE_EXTENSIONS:
        return JsonResponse({'error': 'File extension not supported! Please convert to png or jpg'}, status=400)

    image_file.name = f'{gloss.sn}{file_extension}' if gloss.sn is not None else f'{gloss.idgloss}-{gloss.pk}{file_extension}'

    # Prepare the file's new path and name
    goal_path = os.path.join(WRITABLE_FOLDER, settings.GLOSS_IMAGE_DIRECTORY, gloss.lemma.dataset.acronym, signbank.tools.get_two_letter_dir(gloss.idgloss))
    goal_location = os.path.join(goal_path, quote(image_file.name, safe=''))

    if not os.path.exists(goal_path):
        try:
            os.makedirs(goal_path)
        except OSError as ose:
            return JsonResponse({'error': f'Failed to create directory {goal_path}: {ose}'}, status=500)

    # Save the file
    try:
        destination = File(open(goal_location.encode(sys.getfilesystemencoding()), 'wb+'))
    except (SystemError, OSError, IOError):
        return JsonResponse({'error': f'Failed to open file {goal_location} for writing.'}, status=500)

    for chunk in image_file.chunks():
        destination.write(chunk)

    destination.close()

    return JsonResponse({'message': 'Image upload successful.'}, status=200) 