import io
import json
from urllib.error import URLError

from django.views.decorators.csrf import csrf_exempt
from requests.exceptions import InvalidURL

from signbank.dictionary.models import *
from django.db.models import FileField
from django.core.files.base import ContentFile, File
from tagging.models import Tag, TaggedItem
from signbank.dictionary.forms import *
from django.utils.translation import override, gettext_lazy as _, activate
from signbank.settings.server_specific import LANGUAGES, LEFT_DOUBLE_QUOTE_PATTERNS, RIGHT_DOUBLE_QUOTE_PATTERNS
from signbank.api_token import put_api_user_in_request
from signbank.abstract_machine import get_interface_language_api

from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import permission_required
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from signbank.settings.server_specific import VIDEOS_TO_IMPORT_FOLDER, API_VIDEO_ARCHIVES
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
import base64


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


def uploaded_video_files(dataset):

    dataset_acronym = str(dataset.acronym)
    goal_directory = os.path.join(API_VIDEO_ARCHIVES, dataset_acronym)
    list_of_videos = dict()

    if os.path.isdir(goal_directory):
        for file in os.listdir(goal_directory):
            list_of_videos[dataset_acronym].append(file)
    return list_of_videos


def uploaded_video_filepaths(dataset):

    dataset_acronym = str(dataset.acronym)
    goal_directory = os.path.join(API_VIDEO_ARCHIVES, dataset_acronym)
    list_of_video_paths = []

    if os.path.isdir(goal_directory):
        for file in os.listdir(goal_directory):
            video_path = os.path.join(goal_directory, file)
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
    videos_data[API_VIDEO_ARCHIVES+dataset.acronym] = uploaded_video_files(dataset)

    return JsonResponse(videos_data, safe=False)


def get_dataset_zipfile_value_dict(request):
    post_data = json.loads(request.body.decode('utf-8'))

    value_dict = dict()

    file_key = gettext("File")
    if file_key in post_data.keys():
        # a file may be included in the json data
        # if there are problems decoding it, the value_dict without it is returned
        try:
            #'data:application/zip;base64,
            uploaded_file = post_data[file_key]
            uploaded_file_contents = uploaded_file[28:]
            filename = 'video_archive.zip'
            goal_path = os.path.join(settings.TMP_DIR, filename)
            f = open(goal_path, 'wb+')
            inputbytes = base64.b64decode(uploaded_file_contents, validate=False, altchars=None)
            f.write(inputbytes)
            tempfile = File(f)
            value_dict[file_key] = tempfile
        except (OSError, EncodingWarning, UnicodeDecodeError):
            pass

    return value_dict


@csrf_exempt
@put_api_user_in_request
def upload_zipped_videos_folder_json(request, datasetid):

    results = dict()
    interface_language_code = request.headers.get('Accept-Language', 'en')
    if interface_language_code not in settings.MODELTRANSLATION_LANGUAGES:
        interface_language_code = 'en'
    activate(interface_language_code)

    # check if the user can manage this dataset
    try:
        group_manager = Group.objects.get(name='Dataset_Manager')
    except ObjectDoesNotExist:
        results['errors'] = 'No group Dataset Manager found.'
        results['unzippedvideos'] = []
        return JsonResponse(results)

    groups_of_user = request.user.groups.all()
    if group_manager not in groups_of_user:
        results['errors'] = 'You must be in group Dataset Manager to upload a zip video archive.'
        results['unzippedvideos'] = []
        return JsonResponse(results, safe=False)

    dataset = Dataset.objects.filter(id=int(datasetid)).first()
    if not dataset:
        results['errors'] = gettext("Dataset ID does not exist.")
        results['updatestatus'] = "Failed"
        return JsonResponse(results, safe=False)

    import_folder = os.path.join(WRITABLE_FOLDER, API_VIDEO_ARCHIVES)
    import_folder_exists = os.path.exists(import_folder)
    if not import_folder_exists:
        results['errors'] = "Upload zip archive: The folder API_VIDEO_ARCHIVES is missing."
        results['unzippedvideos'] = []
        return JsonResponse(results)

    # Create the TEMP folder if needed
    temp_goal_directory = os.path.join(WRITABLE_FOLDER, API_VIDEO_ARCHIVES, 'TEMP')
    if not os.path.exists(temp_goal_directory):
        try:
            os.mkdir(temp_goal_directory, mode=0o775)
        except (OSError, PermissionError):
            results['errors'] = "Upload zip archive: The folder API_VIDEO_ARCHIVES/TEMP is missing."
            results['unzippedvideos'] = []
            return JsonResponse(results)

    dataset_folder = os.path.join(WRITABLE_FOLDER, API_VIDEO_ARCHIVES, dataset.acronym)
    dataset_folder_exists = os.path.exists(dataset_folder)
    if not dataset_folder_exists:
        try:
            os.mkdir(dataset_folder, mode=0o775)
        except (OSError, PermissionError):
            results['errors'] = "Upload zip archive: The folder API_VIDEO_ARCHIVES/" + dataset.acronym + " cannot be created."
            results['unzippedvideos'] = []
            return JsonResponse(results)

    value_dict = get_dataset_zipfile_value_dict(request)

    file_key = gettext("File")
    if file_key not in value_dict.keys():
        results['errors'] = "Error processing the zip file."
        results['unzippedvideos'] = []
        return JsonResponse(results)

    zip_file = value_dict[file_key]
    file_name = zip_file.name

    goal_zipped_file = os.path.join(temp_goal_directory, file_name)

    # with urllib.request.urlopen(zipped_file_url) as response:
    #     with tempfile.NamedTemporaryFile(delete=False) as tmp_zipped_file:
    #         shutil.copyfileobj(response, tmp_zipped_file)

    chunk_size = 4096
    temp_zipped = open(zip_file.name, 'rb')
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
        results['filename'] = file_name
        results['errors'] = "Upload zip archive: The file is not a zip file."
        results['unzippedvideos'] = []
        return JsonResponse(results)

    norm_filename = os.path.normpath(goal_zipped_file)
    split_norm_filename = norm_filename.split('.')

    if len(split_norm_filename) == 1:
        # file has no extension
        results['filename'] = file_name
        results['errors'] = "Upload zip archive: The file has no extension."
        results['unzippedvideos'] = []
        return JsonResponse(results, safe=False)

    filenames = get_filenames(goal_zipped_file)
    video_paths_okay = check_subfolders_for_unzipping_ids(dataset.acronym, filenames)
    if not video_paths_okay:
        error_feedback = ("The zip archive has the wrong structure. It should be: "
                          + str(dataset.acronym) + '/' + "GLOSSID.mp4")
        results['filename'] = file_name
        results['errors'] = error_feedback
        results['unzippedvideos'] = filenames
        return JsonResponse(results, safe=False)

    with atomic():
        unzip_video_files(dataset, goal_zipped_file, API_VIDEO_ARCHIVES)

    unzipped_files = uploaded_video_files(dataset)

    videos_data = dict()
    videos_data['filename'] = file_name
    videos_data['errors'] = ""
    videos_data['unzippedvideos'] = unzipped_files

    return JsonResponse(videos_data, safe=False)


def import_video_to_gloss_api(request, video_file_path):
    # request is included as a parameter to add to the GlossVideoHistory in the called functions

    import_video_data = dict()
    filename = os.path.basename(video_file_path)
    file_folder_path = os.path.dirname(video_file_path)
    path_units = file_folder_path.split('/')
    dataset_acronym = path_units[-1]
    json_path_key = settings.API_VIDEO_ARCHIVES + dataset_acronym + '/' + filename
    import_video_data[json_path_key] = dict()
    (filename_without_extension, extension) = os.path.splitext(filename)
    gloss = Gloss.objects.filter(id=filename_without_extension).first()
    if not gloss:
        errors_deleting = remove_video_file_from_import_videos(video_file_path)
        if errors_deleting:
            print('import_video_to_gloss: ', errors_deleting)
        import_video_data[json_path_key]["gloss"] = ''
        import_video_data[json_path_key]["videofile"] = filename
        import_video_data[json_path_key]["errors"] = "Gloss not found for ID " + filename_without_extension + ". "
        import_video_data[json_path_key]["Video"] = ''
        import_video_data[json_path_key]["importstatus"] = 'Failed'
        return import_video_data

    status, errors = import_video_file(request, gloss, video_file_path)
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
            value_json = "{ \"import_videos_status\": ["
        elif value == "finish":
            value_json = "]}"
        else:
            video_data = import_video_to_gloss_api(request, value)
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

