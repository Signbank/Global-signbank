
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

    reverse_url = '/'

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return HttpResponseRedirect('/')

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        return HttpResponseRedirect(reverse_url)

    # make sure the user can write to this dataset
    from guardian.shortcuts import get_objects_for_user
    user_change_datasets = get_objects_for_user(request.user, 'change_dataset', Dataset,
                                                accept_global_perms=False)
    if not user_change_datasets or dataset not in user_change_datasets:
        messages.add_message(request, messages.ERROR, _('No permission to modify dataset permissions.'))
        return HttpResponseRedirect('/')

    import_folder_exists = os.path.exists(VIDEOS_TO_IMPORT_FOLDER)
    if not import_folder_exists:
        messages.add_message(request, messages.ERROR,
                             _("Upload videos media failed: The videos import folder is missing."))
        return HttpResponseRedirect('/')

    zipped_file = request.FILES.get('file')
    filename = zipped_file.name
    filetype = zipped_file.content_type

    if not filetype:
        # unrecognised file type has been uploaded
        messages.add_message(request, messages.ERROR, _("Upload videos media failed: The file has an unknown type."))
        return HttpResponseRedirect(reverse_url)

    norm_filename = os.path.normpath(filename)
    split_norm_filename = norm_filename.split('.')

    if len(split_norm_filename) == 1:
        # file has no extension
        messages.add_message(request, messages.ERROR, _("Upload videos media failed: The file has no extension."))
        return HttpResponseRedirect(reverse_url)

    extension = split_norm_filename[-1]
    filename_base = '.'.join(split_norm_filename[:-1])

    # Create the folder if needed
    temp_goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, 'TEMP')
    if not os.path.isdir(temp_goal_directory):
        os.mkdir(temp_goal_directory, mode=0o765)

    goal_directory = os.path.join(VIDEOS_TO_IMPORT_FOLDER, dataset.acronym)
    goal_zipped_file = temp_goal_directory + os.sep + norm_filename

    with open(goal_zipped_file, "wb+") as destination:
        for chunk in zipped_file.chunks():
            destination.write(chunk)
        destination.close()

    messages.add_message(request, messages.INFO, _("Upload zipped videos media was successful."))
    return HttpResponseRedirect('/')
