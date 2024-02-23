import os.path

from signbank.dictionary.models import *
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


def api_fields(dataset, advanced=False):

    api_fields_2023 = []
    if not dataset:
        dataset = Dataset.objects.get(acronym=settings.DEFAULT_DATASET_ACRONYM)
    if advanced:
        for language in dataset.translation_languages.all():
            language_field = _("Lemma ID Gloss") + ": %s" % language.name
            api_fields_2023.append(language_field)
    for language in dataset.translation_languages.all():
        language_field = _("Annotation ID Gloss") + ": %s" % language.name
        api_fields_2023.append(language_field)
    for language in dataset.translation_languages.all():
        language_field = _("Senses") + ": %s" % language.name
        api_fields_2023.append(language_field)

    if not advanced:
        api_fields_2023.append("Handedness")
        api_fields_2023.append("Strong Hand")
        api_fields_2023.append("Weak Hand")
        api_fields_2023.append("Location")
        api_fields_2023.append("Semantic Field")
        api_fields_2023.append("Word Class")
        api_fields_2023.append("Named Entity")
        api_fields_2023.append("Link")
        api_fields_2023.append("Video")
    else:
        api_fields_2023.append("Link")
        api_fields_2023.append("Video")

        activate(LANGUAGES[0][0])
        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
        gloss_fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

        # TO DO
        extra_columns = ['Sign Languages', 'Dialects', 'Sequential Morphology', 'Simultaneous Morphology',
                         'Blend Morphology', 'Relations to other signs', 'Relations to foreign signs', 'Tags', 'Notes']

        # show advanced properties
        for field in gloss_fields:
            api_fields_2023.append(field.verbose_name.title())

    return api_fields_2023


def get_fields_data_json(request, datasetid):
    try:
        dataset_id = int(datasetid)
    except TypeError:
        return JsonResponse({})

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        # ignore the database in the url if necessary
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)

    if request.user.has_perm('dictionary.change_gloss'):
        api_fields_2023 = api_fields(dataset, advanced=True)
    else:
        api_fields_2023 = api_fields(dataset, advanced=False)

    result = {'fields': api_fields_2023}

    return JsonResponse(result)


def get_gloss_data_json(request, datasetid, glossid):

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return JsonResponse({})

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        # ignore the database in the url if necessary
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)

    try:
        gloss_id = int(glossid)
    except TypeError:
        return JsonResponse({})

    gloss = Gloss.objects.filter(lemma__dataset=dataset, id=gloss_id).first()

    if not gloss:
        return JsonResponse({})

    if request.user.has_perm('dictionary.change_gloss'):
        api_fields_2023 = api_fields(dataset, advanced=True)
    else:
        api_fields_2023 = api_fields(dataset, advanced=False)

    gloss_data = dict()
    gloss_data[str(gloss.pk)] = gloss.get_fields_dict(api_fields_2023)

    return JsonResponse(gloss_data)


def get_filenames(path_to_zip):
    """ return list of filenames inside of the zip folder"""
    with zipfile.ZipFile(path_to_zip, 'r') as zipped:
        return zipped.namelist()


def check_subfolders_for_unzipping(acronym, lang3charcodes, filenames):
    commonprefix = os.path.commonprefix(filenames)
    if commonprefix != acronym + '/':
        return []
    subfolders = [acronym + '/' + lang3char + '/' for lang3char in lang3charcodes]
    video_files = []
    for zipfilename in filenames:
        if zipfilename == commonprefix:
            continue
        if zipfilename in subfolders:
            continue
        file_dirname = os.path.dirname(zipfilename)
        if file_dirname + '/' not in subfolders:
            return []
        video_files.append(zipfilename)
    return video_files


def unzip_video_files(zipped_videos_file, destination):
    with zipfile.ZipFile(zipped_videos_file) as zipped_file:
        for zip_info in zipped_file.infolist():
            if zip_info.is_dir():
                continue
            # zip_folder = os.path.dirname(zip_info.filename)
            # target_folder = os.path.join(destination, zip_folder)
            zipped_file.extract(zip_info, destination)
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

    extension = split_norm_filename[-1]
    filename_base = '.'.join(split_norm_filename[:-1])

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

    unzip_video_files(goal_zipped_file, VIDEOS_TO_IMPORT_FOLDER)

    messages.add_message(request, messages.INFO, _("Upload zipped videos media was successful."))
    return HttpResponseRedirect(reverse('admin_dataset_media', args=[dataset.id]))


def uploaded_video_files(dataset):

    goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym)
    list_of_videos = []

    if os.path.isdir(goal_directory):
        for language3char in os.listdir(goal_directory):
            language_subfolder = os.path.join(goal_directory, language3char)
            if os.path.isdir(language_subfolder):
                for file in os.listdir(language_subfolder):
                    file_path = os.path.join('import_videos', dataset.acronym, language3char, file)
                    list_of_videos.append(file_path)
    return list_of_videos


def get_unzipped_video_files_json(request, datasetid):

    sequence_of_digits = True
    for i in datasetid:
        if not i.isdigit():
            sequence_of_digits = False
            break

    if not sequence_of_digits:
        return JsonResponse({})

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return JsonResponse({})

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
        status_request['errors'] = _('Please login to use this functionality.')
        return JsonResponse(status_request)

    # check if the user can manage this dataset
    from django.contrib.auth.models import Group, User

    try:
        group_manager = Group.objects.get(name='Dataset_Manager')
    except ObjectDoesNotExist:
        status_request['errors'] = _('No group Dataset Manager found.')
        return JsonResponse(status_request)

    groups_of_user = request.user.groups.all()
    if group_manager not in groups_of_user:
        status_request['errors'] = _('You must be in group Dataset Manager to upload a zip video archive.')
        return JsonResponse(status_request)

    sequence_of_digits = True
    for i in datasetid:
        if not i.isdigit():
            sequence_of_digits = False
            break

    if not sequence_of_digits:
        status_request['errors'] = _('The dataset ID must be numerical.')
        return JsonResponse(status_request)

    dataset_id = int(datasetid)
    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        # ignore the database in the url if necessary
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)

    import_folder_exists = os.path.exists(VIDEOS_TO_IMPORT_FOLDER)
    if not import_folder_exists:
        status_request['errors'] = _("Upload zip archive: The folder VIDEOS_TO_IMPORT_FOLDER is missing.")
        return JsonResponse(status_request)

    lang3charcodes = [language.language_code_3char for language in dataset.translation_languages.all()]

    # Create the TEMP folder if needed
    temp_goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, 'TEMP')
    if not os.path.isdir(temp_goal_directory):
        os.mkdir(temp_goal_directory, mode=0o777)

    goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym)
    if not os.path.isdir(goal_directory):
        os.mkdir(temp_goal_directory, mode=0o777)

    for lang3char in lang3charcodes:
        dataset_subfolder = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym, lang3char)
        if not os.path.isdir(dataset_subfolder):
            os.mkdir(dataset_subfolder, mode=0o777)

    # get file as a url parameter: /dictionary/upload_zipped_videos_folder_json/5/?file=file:///path/to/zipfile.zip
    
    zipped_file_url = request.GET['file']
    file_path_units = zipped_file_url.split('/')
    file_name = file_path_units[-1]

    goal_zipped_file = temp_goal_directory + os.sep + file_name

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
        status_request['errors'] = _("Upload zip archive: The file is not a zip file.")
        return JsonResponse(status_request)

    norm_filename = os.path.normpath(goal_zipped_file)
    split_norm_filename = norm_filename.split('.')

    if len(split_norm_filename) == 1:
        # file has no extension
        status_request['errors'] = _("Upload zip archive: The file has no extension.")
        return JsonResponse(status_request)

    filenames = get_filenames(goal_zipped_file)
    video_paths_okay = check_subfolders_for_unzipping(dataset.acronym, lang3charcodes, filenames)
    if not video_paths_okay:
        status_request['errors'] = _("Upload zip archive: The zip archive has the wrong structure.")
        return JsonResponse(status_request)

    with atomic():
        unzip_video_files(goal_zipped_file, VIDEOS_TO_IMPORT_FOLDER)

    unzipped_files = uploaded_video_files(dataset)

    videos_data = dict()
    videos_data['filename'] = VIDEOS_TO_IMPORT_FOLDER + '/TEMP/' + norm_filename
    videos_data['unzipped videos'] = unzipped_files

    return JsonResponse(videos_data)

