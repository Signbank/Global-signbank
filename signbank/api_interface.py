import json

from signbank.dictionary.models import *
from django.db.models import FileField
from django.core.files.base import ContentFile, File
from tagging.models import Tag, TaggedItem
from signbank.dictionary.forms import *
from django.utils.translation import override, gettext_lazy as _, activate
from signbank.settings.server_specific import LANGUAGES, LEFT_DOUBLE_QUOTE_PATTERNS, RIGHT_DOUBLE_QUOTE_PATTERNS
from signbank.api_token import hash_token
from signbank.abstract_machine import get_interface_language_api

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
from signbank.zip_interface import *


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

    return api_fields_2023


def get_fields_data_json(request, datasetid):

    results = dict()
    auth_token_request = request.headers.get('Authorization', '')
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)
    if auth_token_request:
        auth_token = auth_token_request.split('Bearer ')[-1]
        hashed_token = hash_token(auth_token)
        signbank_token = SignbankAPIToken.objects.filter(api_token=hashed_token).first()
        if not signbank_token:
            results['errors'] = [gettext("Your Authorization Token does not match anything.")]
            return JsonResponse(results)
        username = signbank_token.signbank_user.username
        user = User.objects.get(username=username)
    else:
        user = request.user
        interface_language_code = get_interface_language_api(request, user)

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

    if user.has_perm('dictionary.change_gloss'):
        api_fields_2023 = api_fields(dataset, interface_language_code, advanced=True)
    else:
        api_fields_2023 = api_fields(dataset, interface_language_code, advanced=False)

    result = {'fields': api_fields_2023}

    return JsonResponse(result)


def get_gloss_data_json(request, datasetid, glossid):

    results = dict()
    auth_token_request = request.headers.get('Authorization', '')
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)
    if auth_token_request:
        auth_token = auth_token_request.split('Bearer ')[-1]
        hashed_token = hash_token(auth_token)
        signbank_token = SignbankAPIToken.objects.filter(api_token=hashed_token).first()
        if not signbank_token:
            results['errors'] = [gettext("Your Authorization Token does not match anything.")]
            return JsonResponse(results)
        username = signbank_token.signbank_user.username
        user = User.objects.get(username=username)
    else:
        user = request.user
        interface_language_code = get_interface_language_api(request, user)

    sequence_of_digits = True
    for i in datasetid:
        if not i.isdigit():
            sequence_of_digits = False
            break

    if not sequence_of_digits:
        return JsonResponse({})

    dataset_id = int(datasetid)
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not user.is_authenticated:
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
    gloss = Gloss.objects.filter(lemma__dataset=dataset, id=gloss_id).first()

    if not gloss:
        return JsonResponse({})

    if user.has_perm('dictionary.change_gloss'):
        api_fields_2023 = api_fields(dataset, interface_language_code, advanced=True)
    else:
        api_fields_2023 = api_fields(dataset, interface_language_code, advanced=False)

    gloss_data = dict()
    gloss_data[str(gloss.pk)] = gloss.get_fields_dict(api_fields_2023, interface_language_code)

    return JsonResponse(gloss_data, safe=False)


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
                    format = probe_format(video_file_path)
                    (filename_without_extension, extension) = os.path.splitext(file)
                    gloss = Gloss.objects.filter(lemma__dataset=dataset,
                                                 annotationidglosstranslation__language__language_code_3char=language3char,
                                                 annotationidglosstranslation__text__exact=filename_without_extension).first()
                    if format.startswith('h264'):
                        # the output of ffmpeg includes extra information following h264, so only check the prefix
                        list_of_video_gloss_status[language3char].append((file, True, gloss))
                    else:
                        list_of_video_gloss_status[language3char].append((file, False, gloss))

    return list_of_video_gloss_status


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
        # ignore the database in the url if necessary
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)

    videos_data = dict()
    videos_data['import_videos/'+dataset.acronym] = uploaded_video_files(dataset)

    return JsonResponse(videos_data)


def upload_zipped_videos_folder_json(request, datasetid):

    status_request = dict()

    if not request.user.is_authenticated:
        status_request['errors'] = 'Please login to use this functionality.'
        return JsonResponse(status_request)

    # check if the user can manage this dataset
    try:
        group_manager = Group.objects.get(name='Dataset_Manager')
    except ObjectDoesNotExist:
        status_request['errors'] = 'No group Dataset Manager found.'
        return JsonResponse(status_request)

    groups_of_user = request.user.groups.all()
    if group_manager not in groups_of_user:
        status_request['errors'] = 'You must be in group Dataset Manager to upload a zip video archive.'
        return JsonResponse(status_request)

    sequence_of_digits = True
    for i in datasetid:
        if not i.isdigit():
            sequence_of_digits = False
            break

    if not sequence_of_digits:
        status_request['errors'] = 'The dataset ID must be numerical.'
        return JsonResponse(status_request)

    dataset_id = int(datasetid)
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        # ignore the database in the url if necessary
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)

    import_folder_exists = os.path.exists(VIDEOS_TO_IMPORT_FOLDER)
    if not import_folder_exists:
        status_request['errors'] = "Upload zip archive: The folder VIDEOS_TO_IMPORT_FOLDER is missing."
        return JsonResponse(status_request)

    lang3charcodes = [language.language_code_3char for language in dataset.translation_languages.all()]

    # Create the TEMP folder if needed
    temp_goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, 'TEMP')
    if not os.path.exists(temp_goal_directory):
        os.mkdir(temp_goal_directory, mode=0o775)

    dataset_folder = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym)
    dataset_folder_exists = os.path.exists(dataset_folder)
    if not dataset_folder_exists:
        os.mkdir(dataset_folder, mode=0o775)

    for lang3char in lang3charcodes:
        dataset_lang3char_folder = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym, lang3char)
        if not os.path.exists(dataset_lang3char_folder):
            os.mkdir(dataset_lang3char_folder, mode=0o775)

    # get file as a url parameter: /dictionary/upload_zipped_videos_folder_json/5/?file=file:///path/to/zipfile.zip
    
    zipped_file_url = request.GET['file']
    file_path_units = zipped_file_url.split('/')
    file_name = file_path_units[-1]

    goal_zipped_file = os.path.join(temp_goal_directory, file_name)

    with urllib.request.urlopen(zipped_file_url) as response:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_zipped_file:
            shutil.copyfileobj(response, tmp_zipped_file)

    chunk_size = 4096
    temp_zipped = open(tmp_zipped_file.name, 'rb')
    zipped_file = open(goal_zipped_file, 'wb')
    with open(goal_zipped_file, "wb+") as destination:
        while True:
            chunk = temp_zipped.read(chunk_size)
            if chunk == b"":
                break  # end of file
            destination.write(chunk)
        destination.close()

    shutil.copyfileobj(temp_zipped, zipped_file)

    if not zipfile.is_zipfile(goal_zipped_file):
        # unrecognised file type has been uploaded
        status_request['filename'] = file_name
        status_request['errors'] = "Upload zip archive: The file is not a zip file."
        return JsonResponse(status_request)

    norm_filename = os.path.normpath(goal_zipped_file)
    split_norm_filename = norm_filename.split('.')

    if len(split_norm_filename) == 1:
        # file has no extension
        status_request['filename'] = file_name
        status_request['errors'] = "Upload zip archive: The file has no extension."
        return JsonResponse(status_request)

    filenames = get_filenames(goal_zipped_file)
    video_paths_okay = check_subfolders_for_unzipping(dataset.acronym, lang3charcodes, filenames)
    if not video_paths_okay:
        default_language_3char = dataset.default_language.language_code_3char
        error_feedback = ("The zip archive has the wrong structure. It should be: "
                          + str(dataset.acronym) + '/' + default_language_3char + "/annotation.mp4")
        status_request['filename'] = file_name
        status_request['errors'] = error_feedback
        status_request['zippedfiles'] = filenames
        return JsonResponse(status_request)

    with atomic():
        unzip_video_files(dataset, goal_zipped_file, VIDEOS_TO_IMPORT_FOLDER)

    unzipped_files = uploaded_video_files(dataset)

    videos_data = dict()
    videos_data['filename'] = file_name
    videos_data['unzippedvideos'] = unzipped_files

    return JsonResponse(videos_data)


def import_video_to_gloss(request, video_file_path):
    # request is included as a parameter to add to the GlossVideoHistory in the called functions

    import_video_data = dict()
    filename = os.path.basename(video_file_path)
    file_folder_path = os.path.dirname(video_file_path)
    path_units = file_folder_path.split('/')
    language_3_code = path_units[-1]
    dataset_acronym = path_units[-2]
    json_path_key = 'import_videos/' + dataset_acronym + '/' + language_3_code + '/' + filename
    import_video_data[json_path_key] = dict()
    (filename_without_extension, extension) = os.path.splitext(filename)
    gloss = Gloss.objects.filter(lemma__dataset__acronym=dataset_acronym,
                                 annotationidglosstranslation__language__language_code_3char=language_3_code,
                                 annotationidglosstranslation__text__exact=filename_without_extension).first()
    if not gloss:
        errors_deleting = remove_video_file_from_import_videos(video_file_path)
        import_video_data[json_path_key]["errors"] = "Gloss not found for " + filename_without_extension + ". "
        return import_video_data
    format = probe_format(video_file_path)
    if format.startswith('h264'):
        # the output of ffmpeg includes extra information following h264, so only check the prefix
        status, errors = import_video_file(request, gloss, video_file_path)
        video_path = gloss.get_video_url()
        import_video_data[json_path_key]["gloss"] = str(gloss.id)
        import_video_data[json_path_key]["videofile"] = filename
        import_video_data[json_path_key]["Video"] = settings.URL + settings.PREFIX_URL + '/dictionary/protected_media/' + video_path
        import_video_data[json_path_key]["status"] = status
        import_video_data[json_path_key]["errors"] = errors
    else:
        import_video_data[json_path_key]["gloss"] = str(gloss.id)
        import_video_data[json_path_key]["videofile"] = filename
        import_video_data[json_path_key]["status"] = "Wrong video format."
        import_video_data[json_path_key]["errors"] = "Video file is not h264."

    return import_video_data


class VideoImporter:
    """An object that implements just the write method of the file-like
    interface. This is based on an example in the Django 4.2 documentation
    """
    line = 0

    def write(self, request, value):
        """Write the value by returning it, instead of storing in a buffer."""
        if value == "start":
            value_json = "{ \"import_videos_status\": ["
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


def upload_videos_to_glosses(request, datasetid):
    # get file as a url parameter: /dictionary/upload_videos_to_glosses/5

    has_permission = True
    errors = ""

    if not request.user.is_authenticated:
        has_permission = False
        errors = 'Please login to use the requested functionality.'

    # check if the user can manage this dataset
    try:
        group_manager = Group.objects.get(name='Dataset_Manager')
    except ObjectDoesNotExist:
        group_manager = None
        has_permission = False
        errors = 'No group Dataset_Manager found.'

    groups_of_user = request.user.groups.all()
    if has_permission and group_manager not in groups_of_user:
        has_permission = False
        errors = 'You must be in group Dataset Manager to upload a zip video archive.'

    if has_permission and not errors:
        dataset_id = int(datasetid)
        dataset = Dataset.objects.filter(id=dataset_id).first()
        # get paths of uploaded videos to import
        video_file_paths = uploaded_video_filepaths(dataset)
    else:
        # if the user does not have permission, an empty file is generated
        video_file_paths = []

    pseudo_buffer = VideoImporter()
    return StreamingHttpResponse(
        (pseudo_buffer.write(request, vg) for vg in json_start() + video_file_paths + json_finish()),
        content_type="application/json",
        headers={"Content-Disposition": 'attachment; filename='+'glosses.json'},
    )

