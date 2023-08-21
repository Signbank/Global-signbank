from django.conf import empty
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.datastructures import MultiValueDictKeyError
from tagging.models import Tag, TaggedItem
from urllib.parse import quote
from django.contrib import messages
from pathlib import Path

import csv
import time
from signbank.dictionary.adminviews import order_queryset_by_sort_order

from signbank.dictionary.forms import *
from signbank.dictionary.models import *
from signbank.feedback.models import *
from signbank.dictionary.update import update_keywords, update_signlanguage, update_dialect, subst_relations, subst_foreignrelations, \
    update_sequential_morphology, update_simultaneous_morphology, update_tags, update_blend_morphology, subst_notes
import signbank.dictionary.forms
from signbank.video.models import GlossVideo, small_appendix, add_small_appendix

from signbank.video.forms import VideoUploadForObjectForm
from signbank.tools import save_media
from signbank.tools import get_selected_datasets_for_user, get_default_annotationidglosstranslation, \
    get_dataset_languages, \
    create_gloss_from_valuedict, compare_valuedict_to_gloss, compare_valuedict_to_lemma, construct_scrollbar, \
    get_interface_language_and_default_language_codes, split_csv_lines_header_body, \
    split_csv_lines_sentences_header_body, create_sentence_from_valuedict
from signbank.dictionary.field_choices import fields_to_fieldcategory_dict

from signbank.csv_interface import csv_create_senses, csv_update_sentences, csv_create_sentence
from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value, \
    check_value_to_translated_human_value

import signbank.settings
from signbank.settings.base import *
from django.utils.translation import override, gettext_lazy as _

from urllib.parse import urlencode, urlparse
from wsgiref.util import FileWrapper, request_uri
import datetime as DT
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import get_current_timezone

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist


def login_required_config(f):
    """like @login_required if the ALWAYS_REQUIRE_LOGIN setting is True"""

    if settings.ALWAYS_REQUIRE_LOGIN:
        return login_required(f)
    else:
        return f


def gloss(request, glossid):
    # this is public view of a gloss

    try:
        gloss = Gloss.objects.get(id=glossid)
    except ObjectDoesNotExist:
        raise Http404

    # set session variables for scroll bar
    if 'search_results' in request.session.keys():
        search_results = request.session['search_results']
    else:
        search_results = []
    if search_results and len(search_results) > 0:
        if request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme']:
            # if the results have the wrong type
            request.session['search_results'] = []
    if 'search_type' in request.session.keys():
        # check that the search type matches the results
        # the session variables are used by the ajax call
        if request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape']:
            # search type is not correct, see if the results were not erased in the last step
            if request.session['search_results']:
                # this was not set to None in the previous step, results have the right type
                # search type is set to handshape but there are glosses in the search results
                request.session['search_type'] = 'sign_or_morpheme'

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    if not(request.user.has_perm('dictionary.search_gloss') or gloss.inWeb):
        feedbackmessage = _('You are not allowed to see this sign.')

        messages.add_message(request, messages.ERROR, feedbackmessage)

        return render(request, "dictionary/word.html",
                      { 'sensetranslations_per_language': {},
                        'public_title': '',
                        'gloss_or_morpheme': 'gloss',
                        'notes_groupedby_role': {},
                        'translations_per_language': {},
                        'gloss': gloss,
                        'active_id': glossid,  # used by search_result_bar.html
                        'annotation_idgloss': {},
                        'dataset_languages': dataset_languages,
                        'selected_datasets': selected_datasets,
                        'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

    # Put translations (senses) per language in the context
    sensetranslations_per_language = dict()
    for language in gloss.lemma.dataset.translation_languages.all():
        sensetranslations_per_language[language] = dict()
        sensetranslations_for_language = dict()
        for sensei, sense in enumerate(gloss.ordered_senses().all(), 1):
            if sense.senseTranslations.filter(language=language).exists():
                sensetranslation = sense.senseTranslations.get(language=language)
                translations = sensetranslation.translations.all().order_by('index')
                if translations:
                    keywords_list = [trans.translation.text for trans in translations]
                    sensetranslations_for_language[sensei] = ', '.join(keywords_list)
        sensetranslations_per_language[language] = sensetranslations_for_language

    # Put annotation_idgloss per language in the context
    annotation_idgloss = {}
    if gloss.dataset:
        for language in gloss.dataset.translation_languages.all():
            annotation_idgloss[language] = gloss.annotationidglosstranslation_set.filter(language=language)
    else:
        language = Language.objects.get(id=get_default_language_id())
        annotation_idgloss[language] = gloss.annotationidglosstranslation_set.filter(language=language)

    default_language = Language.objects.get(id=get_default_language_id())
    public_title = gloss.annotation_idgloss(settings.LANGUAGE_CODE)

    # Regroup notes
    note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType')
    notes = gloss.definition_set.filter(published__exact=True)
    notes_groupedby_role = {}
    for note in notes:
        note_role_machine_value = note.role.machine_value if note.role else 0
        translated_note_role = machine_value_to_translated_human_value(note_role_machine_value, note_role_choices)
        role_id = (note.role, translated_note_role)
        if role_id not in notes_groupedby_role:
            notes_groupedby_role[role_id] = []
        notes_groupedby_role[role_id].append(note)

    return render(request,"dictionary/word.html",
                              {'sensetranslations_per_language': sensetranslations_per_language,
                               'public_title': public_title,
                               'gloss_or_morpheme': 'gloss',
                               'notes_groupedby_role': notes_groupedby_role,
                               'translations_per_language': {},
                               'gloss': gloss,
                               'active_id': glossid,  # used by search_result_bar.html
                               'annotation_idgloss': annotation_idgloss,
                               'dataset_languages': dataset_languages,
                               'selected_datasets': selected_datasets,
                               'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })


def morpheme(request, glossid):
    # this is public view of a morpheme

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    # we should only be able to get a single gloss, but since the URL
    # pattern could be spoofed, we might get zero or many
    # so we filter first and raise a 404 if we don't get one
    try:
        morpheme = Morpheme.objects.get(id=glossid)
    except ObjectDoesNotExist:
        raise Http404

    if not(request.user.has_perm('dictionary.search_gloss') or morpheme.inWeb):
        feedbackmessage = _('You are not allowed to see this morpheme.')

        messages.add_message(request, messages.ERROR, feedbackmessage)
        return render(request, "dictionary/word.html",
                      {'sensetranslations_per_language': {},
                       'public_title': '',
                       'gloss_or_morpheme': 'morpheme',
                       'notes_groupedby_role': {},
                       'translations_per_language': {},
                       'gloss': morpheme,
                       'active_id': glossid,  # used by search_result_bar.html
                       'annotation_idgloss': {},
                       'dataset_languages': dataset_languages,
                       'selected_datasets': selected_datasets,
                       'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface}
                      )

    # morphemes use translations not senses
    translations_per_language = {}
    if morpheme.lemma.dataset:
        for language in morpheme.dataset.translation_languages.all():
            translations_per_language[language] = morpheme.translation_set.filter(language=language).order_by(
                'translation__index')
    else:
        language = Language.objects.get(id=get_default_language_id())
        translations_per_language[language] = morpheme.translation_set.filter(language=language).order_by(
            'translation__index')

    videourl = morpheme.get_video_url()
    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, videourl)):
        videourl = None

    public_title = morpheme.annotation_idgloss(settings.LANGUAGE_CODE)

    annotation_idgloss = {}
    if morpheme.dataset:
        for language in morpheme.dataset.translation_languages.all():
            annotation_idgloss[language] = morpheme.annotationidglosstranslation_set.filter(language=language)
    else:
        language = Language.objects.get(id=get_default_language_id())
        annotation_idgloss[language] = morpheme.annotationidglosstranslation_set.filter(language=language)

    # Regroup notes
    note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType')
    notes = morpheme.definition_set.filter(published__exact=True)
    notes_groupedby_role = {}
    for note in notes:
        note_role_machine_value = note.role.machine_value if note.role else 0
        translated_note_role = machine_value_to_translated_human_value(note_role_machine_value, note_role_choices)
        role_id = (note.role, translated_note_role)
        if role_id not in notes_groupedby_role:
            notes_groupedby_role[role_id] = []
        notes_groupedby_role[role_id].append(note)

    return render(request,"dictionary/word.html",
                              {'sensetranslations_per_language': {},
                               'gloss_or_morpheme': 'morpheme',
                               'notes_groupedby_role': notes_groupedby_role,
                               'public_title': public_title,
                               'translations_per_language': translations_per_language,
                               'videofile': videourl,
                               'gloss': morpheme,
                               'annotation_idgloss': annotation_idgloss,
                               'active_id': glossid,  # used by search_result_bar.html
                               'DEFINITION_FIELDS' : settings.DEFINITION_FIELDS})


@login_required_config
def search(request):
    """Handle keyword search form submission"""

    form = UserSignSearchForm(request.GET.copy())

    if form.is_valid():

        glossQuery = form.cleaned_data['glossQuery']
        # Issue #153: make sure + and - signs are translated correctly into the search URL
        glossQuery = quote(glossQuery)
        term = form.cleaned_data['query']
        # Issue #153: do the same with the Translation, encoded by 'query'
        term = quote(term)

        return HttpResponseRedirect('../../signs/search/?search='+glossQuery+'&keyword='+term)


def missing_video_list():
    """A list of signs that don't have an
    associated video file"""

    glosses = Gloss.objects.filter(inWeb__exact=True)
    for gloss in glosses:
        if not gloss.has_video():
            yield gloss

def missing_video_view(request):
    """A view for the above list"""

    glosses = missing_video_list()

    return render(request, "dictionary/missingvideo.html",
                              {'glosses': glosses})

def import_media(request,video):
    """
    Importing media is done as follows:
    1. In the main folder for importing media all folders with names equal to dataset names are opened.
    2. In each folder with a dataset name all folders with name equal to a three letter language code of the dataset
    at hand are opened.
    3 In the folders with a three letter language code as name all media file are imported.
    
    E.g. view the following folder structure:
     <import folder>/ASL/eng/HOUSE.mp4
     
     where 'ASL' is the name of a dataset and 'eng' is the three letter language code of English which is one of the 
     dataset languages of the dataset 'ASL'.
    """

    overwritten_files = []
    errors = []

    if video:
        import_folder = settings.VIDEOS_TO_IMPORT_FOLDER
    else:
        import_folder = settings.IMAGES_TO_IMPORT_FOLDER

    # selected_datasets and dataset_languages are used by the Signbank header, these are passed to the view
    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = get_dataset_languages(selected_datasets)
    # gather the possible folder names for the selected datasets
    selected_datasets_folder_options = [ ds.acronym for ds in selected_datasets ] + [ ds.name for ds in selected_datasets ]
    # initialize data structures used while traversing the folders
    files_per_dataset_per_language = {}
    status_per_dataset_per_language = {}

    for dataset_folder_name in [name for name in os.listdir(import_folder) if os.path.isdir(os.path.join(import_folder, name))]:

        # only consider selected datasets to avoid feedback about other datasets
        if dataset_folder_name not in selected_datasets_folder_options:
            continue
        # Check whether the folder name is equal to a dataset name
        try:
            dataset = Dataset.objects.get(name=dataset_folder_name)
        except ObjectDoesNotExist:
            try:
                dataset = Dataset.objects.get(acronym=dataset_folder_name)
            except ObjectDoesNotExist:
                # this should not occur, we have already continued on non-selected folders
                print('import_media, unidentified dataset folder: '+dataset_folder_name)
                continue
        files_per_dataset_per_language[dataset_folder_name] = {}
        status_per_dataset_per_language[dataset_folder_name] = {}

        dataset_folder_path = os.path.join(import_folder, dataset_folder_name)
        for lang3code_folder_name in [name for name in os.listdir(dataset_folder_path) if os.path.isdir(os.path.join(dataset_folder_path, name))]:
            # Check whether the folder name is equal to a three letter code for language of the dataset at hand
            languages = dataset.translation_languages.filter(language_code_3char=lang3code_folder_name)
            if languages:
                language = languages[0]
            else:
                errors.append('Unidentified language folder for dataset '+dataset_folder_name+': '+lang3code_folder_name)
                continue
            files_per_dataset_per_language[dataset_folder_name][lang3code_folder_name] = []
            status_per_dataset_per_language[dataset_folder_name][lang3code_folder_name] = {}

            lang3code_folder_path = os.path.join(dataset_folder_path, lang3code_folder_name) + "/"
            for filename in os.listdir(lang3code_folder_path):
                files_per_dataset_per_language[dataset_folder_name][lang3code_folder_name].append(filename)
                status_per_dataset_per_language[dataset_folder_name][lang3code_folder_name][filename] = ''
                (filename_without_extension, extension) = os.path.splitext(filename)
                extension = extension[1:]  # Remove the dot
                glosses = Gloss.objects.filter(lemma__dataset=dataset, annotationidglosstranslation__language=language,
                                             annotationidglosstranslation__text__exact=filename_without_extension)
                if glosses:
                    gloss = glosses[0]
                    if glosses.count() > 1:
                        # not sure if this can happen
                        status_per_dataset_per_language[dataset_folder_name][lang3code_folder_name][filename] = _('Warning: Duplicate gloss found.')
                        continue
                else:
                    status_per_dataset_per_language[dataset_folder_name][lang3code_folder_name][filename] = _('Fail: Gloss Not Found')
                    continue

                default_annotationidgloss = get_default_annotationidglosstranslation(gloss)

                if not video:
                    overwritten, was_allowed = save_media(lang3code_folder_path, lang3code_folder_name,
                                                          GLOSS_IMAGE_DIRECTORY, gloss, extension)

                    if not was_allowed:
                        status_per_dataset_per_language[dataset_folder_name][lang3code_folder_name][filename] = _('Permission denied')

                        errors.append('Failed to move media file for '+default_annotationidgloss+
                                      '. Either the source could not be read or the destination could not be written.')
                        print('Failed to move media file for ',GLOSS_IMAGE_DIRECTORY,lang3code_folder_path,default_annotationidgloss)
                        continue

                    if overwritten:
                        status_per_dataset_per_language[dataset_folder_name][lang3code_folder_name][filename] = _('Success (Image File Overwritten)')
                    else:
                        status_per_dataset_per_language[dataset_folder_name][lang3code_folder_name][filename] = _('Success')

                else:
                    video_file_path = os.path.join(lang3code_folder_path, filename)
                    vfile = File(open(video_file_path, 'rb'))
                    video = gloss.add_video(request.user, vfile)
                    vfile.close()
                    overwritten = len(GlossVideo.objects.filter(gloss=gloss)) > 1
                    if overwritten:
                        status_per_dataset_per_language[dataset_folder_name][lang3code_folder_name][filename] = _('Success (Video File Overwritten)')
                    else:
                        status_per_dataset_per_language[dataset_folder_name][lang3code_folder_name][filename] = _('Success')

                    try:
                        os.remove(video_file_path)
                    except OSError as oserror:
                        errors.append("OSError: {}".format(oserror))

                if overwritten:
                    overwritten_files.append(filename)

    if overwritten_files:
        print('import_media, overwritten_files: ', overwritten_files)

    files_per_dataset_per_language_list = []
    for ds in files_per_dataset_per_language.keys():

        for lang3chr in files_per_dataset_per_language[ds].keys():

            mediapaths = []
            for mediapath in files_per_dataset_per_language[ds][lang3chr]:
                try:
                    status = status_per_dataset_per_language[ds][lang3chr][mediapath]
                except KeyError:
                    status = ''
                mediapaths.append((mediapath, status))
            import_media_body_row = { 'dataset': ds,
                                      'lang3chr': lang3chr,
                                      'mediapaths': mediapaths }
            files_per_dataset_per_language_list.append(import_media_body_row)

    if errors:
        print('import_media, errors: ', errors)

    return render(request,'dictionary/import_media.html',{'files_per_dataset_per_language':files_per_dataset_per_language_list,
                                                        'errors':errors,
                                                        'dataset_languages':dataset_languages,
                                                        'selected_datasets':selected_datasets,
                                                        'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


def try_code(request, pk):
    """A view for the developer to try out senses for a particular gloss"""
    context = {}

    selected_datasets = get_selected_datasets_for_user(request.user)

    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    context['dataset_languages'] = dataset_languages

    context['selected_datasets'] = selected_datasets

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

    try:
        gloss = get_object_or_404(Gloss, pk=pk)
    except ObjectDoesNotExist:
        gloss = None

    if not gloss or not (request.user.is_staff or request.user.is_superuser):
        translated_message = _('You do not have permission to use the try command.')
        return render(request, 'dictionary/warning.html',
                      {'warning': translated_message,
                       'dataset_languages': dataset_languages,
                       'selected_datasets': selected_datasets,
                       'SHOW_DATASET_INTERFACE_OPTIONS': SHOW_DATASET_INTERFACE_OPTIONS})

    context['gloss'] = gloss

    gloss_annotations = gloss.annotationidglosstranslation_set.all()
    if gloss_annotations:
        gloss_default_annotationidglosstranslation = gloss.annotationidglosstranslation_set.get(
            language=gloss.lemma.dataset.default_language).text
    else:
        gloss_default_annotationidglosstranslation = str(gloss.id)
    # Put annotation_idgloss per language in the context
    context['annotation_idgloss'] = {}
    for language in gloss.dataset.translation_languages.all():
        try:
            annotation_text = gloss.annotationidglosstranslation_set.get(language=language).text
        except (ObjectDoesNotExist):
            annotation_text = gloss_default_annotationidglosstranslation
        context['annotation_idgloss'][language] = annotation_text

    senses = gloss.senses.all().order_by('glosssense')
    context['senses'] = senses

    sense_to_similar_senses = dict()
    for sns in senses:
        sense_to_similar_senses[sns] = sns.get_senses_with_similar_sensetranslations_dict()
    context['sense_to_similar_senses'] = sense_to_similar_senses

    for sense in senses:
        print('sense.get_example_sentences()  (original): ', sense.get_example_sentences_orig())
        print('sense.get_example_sentences_alternative(): ', sense.get_example_sentences())
        print('sense.get_sense_translations_dict_with()  (original): ', sense.get_sense_translations_dict_with_orig())
        print('sense.get_sense_translations_dict_with_alternative(): ', sense.get_sense_translations_dict_with(', '))
        print('sense.get_sense_translations_dict_with_return()  (original): ', sense.get_sense_translations_dict_with_return())
        print('sense.get_sense_translations_dict_with_alternative(): ', sense.get_sense_translations_dict_with('\n'))

    return render(request, 'dictionary/try.html', context)


# this method is called from the Signbank menu bar
def add_new_sign(request):
    context = {}

    selected_datasets = get_selected_datasets_for_user(request.user)

    default_dataset_acronym = settings.DEFAULT_DATASET_ACRONYM
    default_dataset = Dataset.objects.get(acronym=default_dataset_acronym)

    if len(selected_datasets) == 1:
        last_used_dataset = selected_datasets[0].acronym
    elif 'last_used_dataset' in request.session.keys():
        last_used_dataset = request.session['last_used_dataset']
    else:
        last_used_dataset = None
    context['last_used_dataset'] = last_used_dataset

    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    context['dataset_languages'] = dataset_languages
    context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE

    context['selected_datasets'] = selected_datasets
    context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix
    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = False
    context['add_gloss_form'] = GlossCreateForm(request.GET, languages=dataset_languages, user=request.user, last_used_dataset=last_used_dataset)

    return render(request,'dictionary/add_gloss.html',context)


@login_required_config
def search_morpheme(request):
    """Handle morpheme search form submission"""

    form = UserMorphemeSearchForm(request.GET.copy())

    if form.is_valid():

        morphQuery = form.cleaned_data['morphQuery']
        # Issue #153: make sure + and - signs are translated correctly into the search URL
        morphQuery = quote(morphQuery)
        term = form.cleaned_data['query']
        # Issue #153: do the same with the Translation, encoded by 'query'
        term = quote(term)

        return HttpResponseRedirect('../../morphemes/search/?search='+morphQuery+'&keyword='+term)

def add_new_morpheme(request):

    context = {}

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    context['dataset_languages'] = dataset_languages
    context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE

    default_dataset_acronym = settings.DEFAULT_DATASET_ACRONYM
    default_dataset = Dataset.objects.get(acronym=default_dataset_acronym)

    if len(selected_datasets) == 1:
        last_used_dataset = selected_datasets[0].acronym
    elif 'last_used_dataset' in request.session.keys():
        last_used_dataset = request.session['last_used_dataset']
    else:
        last_used_dataset = None
    context['last_used_dataset'] = last_used_dataset

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

    form = MorphemeCreateForm(request.GET, languages=dataset_languages, user=request.user, last_used_dataset=last_used_dataset)
    context['add_morpheme_form'] = form

    context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

    return render(request,'dictionary/add_morpheme.html',context)


def import_csv_create(request):
    user = request.user
    import guardian
    user_datasets = guardian.shortcuts.get_objects_for_user(user,'change_dataset',Dataset)
    user_datasets_names = [ dataset.acronym for dataset in user_datasets ]

    selected_datasets = get_selected_datasets_for_user(user)
    dataset_languages = get_dataset_languages(selected_datasets)

    translation_languages_dict = {}
    # this dictionary is used in the template, it maps each dataset to a list of tuples (English name of dataset, language_code_2char)
    for dataset_object in user_datasets:
        translation_languages_dict[dataset_object] = []

        for language in dataset_object.translation_languages.all():
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            language_tuple = (language_name, language.language_code_2char)
            translation_languages_dict[dataset_object].append(language_tuple)

    seen_datasets = []
    seen_dataset_names = []

    # fatal errors are duplicate column headers, data in columns without headers
    # column headers that do not correspond to database fields
    # non-numerical gloss ids
    # non-existent dataset or no permission for dataset
    # attempt to create glosses in multiple datasets in the same csv
    # missing Dataset column
    # missing Lemma or Annotation translations required for the dataset during creation
    # extra columns during creation:
    # (although these are ignored, it is advised to remove them to make it clear the data is not being stored)

    encoding_error = False

    uploadform = signbank.dictionary.forms.CSVUploadForm
    changes = []
    error = []
    creation = []
    gloss_already_exists = []
    earlier_creation_same_csv = {}
    earlier_creation_annotationidgloss = {}
    earlier_creation_lemmaidgloss = {}

    #Propose changes
    if len(request.FILES) > 0:

        new_file = request.FILES['file']

        try:
            # files that will fail here include those renamed to .csv which are not csv
            # non UTF-8 encoded files also fail
            csv_text = new_file.read().decode('UTF-8-sig')
        except (UnicodeDecodeError, UnicodeError):
            new_file.seek(0)
            import magic
            magic_file_type = magic.from_buffer(new_file.read(2048), mime=True)

            if magic_file_type == 'text/plain':
                feedback_message = _('Unrecognised text encoding. Please export your file to UTF-8 format using e.g. LibreOffice.')
            else:
                feedback_message = _('Unrecognised format in selected CSV file.')

            messages.add_message(request, messages.ERROR, feedback_message)

            return render(request, 'dictionary/import_csv_create.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'creation': creation,
                           'gloss_already_exists': gloss_already_exists,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        fatal_error = False
        csv_lines = re.compile('[\r\n]+').split(csv_text) # split the csv text on any combination of new line characters

        # the following code allows for specifying a column delimiter in the import_csv_create.html template
        if 'delimiter' in request.POST:
            delimiter_radio = request.POST['delimiter']
            if delimiter_radio == 'tab':
                delimiter = '\t'
            elif delimiter_radio == 'comma':
                delimiter = ','
            elif delimiter_radio == 'semicolon':
                delimiter = ';'
            else:
                # this should not occur
                # perhaps only if the user is trying to fiddle without using the template
                # set to template default, print message for Admin
                print('Missing template default for delimiter_radio in import_csv_create.html')
                delimiter = ','
                delimiter_radio = 'comma'
        else:
            # this should not occur
            # perhaps only if the user is trying to fiddle without using the template
            # set to template default, print message for Admin
            print('Missing template default for delimiter_radio in import_csv_create.html')
            delimiter = ','
            delimiter_radio = 'comma'

        first_csv_line, rest_csv_lines = csv_lines[0], csv_lines[1:]

        keys = first_csv_line.strip().split(delimiter)
        if len(keys) < 2:
            feedback_message = _('Incorrect Delimiter: ') + delimiter_radio + '.'
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        elif '' in keys:
            feedback_message = _('Empty Column Header Found.')
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        elif len(keys) > len(list(set(keys))) :
            feedback_message = _('Duplicate Column Header Found.')
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        elif 'Signbank ID' in keys:
            feedback_message = _('Signbank ID column found.')
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        elif 'Dataset' not in keys:
            feedback_message = _('The Dataset column is required.')
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        if encoding_error:
            return render(request, 'dictionary/import_csv_create.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'creation': creation,
                           'gloss_already_exists': gloss_already_exists,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        # create a template for an empty row with the desired number of columns
        empty_row = [''] * len(keys)
        for nl, line in enumerate(rest_csv_lines):
            if len(line) == 0:
                # this happens at the end of the file
                continue
            values = csv.reader([line], delimiter=delimiter).__next__()
            if values == empty_row:
                continue

            # construct value_dict for row
            value_dict = {}
            for nv,value in enumerate(values):
                if nv >= len(keys):
                    # this has already been checked above
                    # it's here to avoid needing an exception on the subscript [nv]
                    continue
                value_dict[keys[nv]] = value

            # 'Dataset' in value_dict keys, checked above
            dataset_name = value_dict['Dataset'].strip()

            # Check whether the user may change the dataset of the current row
            if dataset_name not in seen_dataset_names:
                if seen_datasets:
                    # already seen a dataset
                    # this is a different dataset
                    e3 = 'Row '+str(nl + 1) + ': A different dataset is mentioned.'
                    e4 = 'You can only create glosses for one dataset at a time.'
                    e5 = 'To create glosses in multiple datasets, use a separate CSV file for each dataset.'
                    error.append(e3)
                    error.append(e4)
                    error.append(e5)
                    break

                # only process a dataset_name once for the csv file being imported
                # catch possible empty values for dataset, primarily for pretty printing error message
                if dataset_name == '' or dataset_name == None or dataset_name == 0 or dataset_name == 'NULL':
                    e_dataset_empty = 'Row '+str(nl + 1) + ': The Dataset is missing.'
                    error.append(e_dataset_empty)
                    break
                try:
                    dataset = Dataset.objects.get(acronym=dataset_name)
                except ObjectDoesNotExist:
                    # An error message should be returned here, the dataset does not exist
                    e_dataset_not_found = 'Row '+str(nl + 1) + ': Dataset %s' % value_dict['Dataset'].strip() + ' does not exist.'
                    error.append(e_dataset_not_found)
                    break

                if dataset_name not in user_datasets_names:
                    e3 = 'Row '+str(nl + 1) + ': You are not allowed to change dataset %s.' % value_dict['Dataset'].strip()
                    error.append(e3)
                    break
                if dataset not in selected_datasets:
                    e3 = 'Row '+str(nl + 1) + ': Please select the dataset %s.' % value_dict['Dataset'].strip()
                    error.append(e3)
                    break
                if seen_datasets:
                    # already seen a dataset
                    if dataset in seen_datasets:
                        pass
                    else:
                        # seen more than one dataset
                        # e4 = 'You are attempting to modify two datasets.'

                        e4 = 'You can only create glosses for one dataset at a time.'
                        e5 = 'To create glosses in multiple datasets, use a separate CSV file for each dataset.'
                        error.append(e4)
                        error.append(e5)
                        break

                else:
                    seen_datasets.append(dataset)
                    seen_dataset_names.append(dataset_name)

                    # saw the first dataset
                    # if creating glosses
                    # check the required columns for translations
                    # and make sure there are no extra columns which will be ignored

                    number_of_translation_languages_for_dataset = len(translation_languages_dict[dataset])
                    # there should be columns for Dataset + Lemma ID Gloss per dataset + Annotation ID Gloss per dataset
                    number_of_required_columns = 1 + 2 * number_of_translation_languages_for_dataset
                    required_columns = ['Dataset']
                    for language in dataset.translation_languages.all():
                        language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                        lemma_column_name = "Lemma ID Gloss (%s)" % language_name
                        required_columns.append(lemma_column_name)
                        if lemma_column_name not in value_dict:
                            e1 = 'To create glosses in dataset ' + dataset_name + ', column ' + lemma_column_name + ' is required.'
                            error.append(e1)
                        annotation_column_name = "Annotation ID Gloss (%s)" % language_name
                        required_columns.append(annotation_column_name)
                        if annotation_column_name not in value_dict:
                            e1 = 'To create glosses in dataset ' + dataset_name + ', column ' + annotation_column_name + ' is required.'
                            error.append(e1)
                    if len(value_dict) > number_of_required_columns:
                        # print an error message about extra columns
                        # if already found an error, the extra column might be a different language
                        extra_column_headers = []
                        for col in keys:
                            if col not in required_columns:
                                extra_column_headers.append(col)

                        e_extra_columns = 'Extra columns found for gloss creation: ' + ', '.join(extra_column_headers)
                        error.append(e_extra_columns)
                        e_extra_columns_create = 'Use a separate CSV file to update glosses after creation.'
                        error.append(e_extra_columns_create)
                        e_create_or_update = 'To update existing glosses, the Signbank ID column is required.'
                        error.append(e_create_or_update)

                    if len(error) > 0:
                        break

            empty_lemma_translation = False
            # The Lemma ID Gloss may already exist.
            # store the lemma translations for the current row in dict lemmaidglosstranslations
            # for those translations, look up existing lemmas with (one of) those translations
            lemmaidglosstranslations = {}
            existing_lemmas = {}
            existing_lemmas_list = []
            new_lemmas = {}
            contextual_error_messages_lemmaidglosstranslations = []
            annotationidglosstranslations = {}
            try:
                dataset = seen_datasets[0]
            except (KeyError, IndexError):
                # this is kind of stupid, we already made sure a dataset was found, but python can't tell if it's been initialised
                # dataset is a local variable above and we put it into the (singleton) list seen_datasets
                break
            translation_languages = dataset.translation_languages.all()

            # check annotation translations
            for language in translation_languages:
                language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                annotationidglosstranslation_text = value_dict["Annotation ID Gloss (%s)" % (language_name) ]
                annotationidglosstranslations[language] = annotationidglosstranslation_text

                annotationtranslation_for_this_text_language = AnnotationIdglossTranslation.objects.filter(gloss__lemma__dataset=dataset,
                                                                                   language=language, text__exact=annotationidglosstranslation_text)

                if annotationtranslation_for_this_text_language:
                    error_string = 'Row ' + str(nl + 1) + ' contains a duplicate Annotation ID Gloss for '+ language_name +'.'
                    error.append(error_string)

            # check lemma translations
            for language in translation_languages:
                language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                column_name = "Lemma ID Gloss (%s)" % language_name
                lemmaidglosstranslation_text = value_dict[column_name].strip()
                # also stores empty values
                lemmaidglosstranslations[language] = lemmaidglosstranslation_text

                lemmatranslation_for_this_text_language = LemmaIdglossTranslation.objects.filter(lemma__dataset=dataset,
                                                                                   language=language, text__exact=lemmaidglosstranslation_text)
                if lemmatranslation_for_this_text_language:
                    one_lemma = lemmatranslation_for_this_text_language[0].lemma
                    existing_lemmas[language.language_code_2char] = one_lemma
                    if not one_lemma in existing_lemmas_list:
                        existing_lemmas_list.append(one_lemma)
                        help = 'Row ' + str(nl + 1) + ": Existing Lemma ID Gloss (" + language_name + '): ' + lemmaidglosstranslation_text
                        contextual_error_messages_lemmaidglosstranslations.append(help)
                elif not lemmaidglosstranslation_text:
                    # lemma translation is empty, determine if existing lemma is also empty for this language
                    if existing_lemmas_list:
                        lemmatranslation_for_this_text_language = LemmaIdglossTranslation.objects.filter(
                            lemma__dataset=dataset, lemma=existing_lemmas_list[0],
                            language=language)
                        if lemmatranslation_for_this_text_language:
                            help = 'Row ' + str(nl + 1) + ': Lemma ID Gloss (' + language_name + ') is empty'
                            contextual_error_messages_lemmaidglosstranslations.append(help)
                            empty_lemma_translation = True
                    else:
                        empty_lemma_translation = True
                else:
                    new_lemmas[language.language_code_2char] = lemmaidglosstranslation_text
                    help = 'Row ' + str(nl + 1) + ': New Lemma ID Gloss (' + language_name + '): ' + lemmaidglosstranslation_text
                    contextual_error_messages_lemmaidglosstranslations.append(help)

            if len(existing_lemmas_list) > 0:
                if len(existing_lemmas_list) > 1:
                    e1 = 'Row '+str(nl + 1)+': The Lemma translations refer to different lemmas.'
                    error.append(e1)
                elif empty_lemma_translation:
                    e1 = 'Row '+str(nl + 1)+': Exactly one lemma matches, but one of the translations in the csv is empty.'
                    error.append(e1)
                if len(new_lemmas.keys()) and len(existing_lemmas.keys()):
                    e1 = 'Row '+str(nl + 1)+': Combination of existing and new lemma translations.'
                    error.append(e1)
            elif not len(new_lemmas.keys()):
                e1 = 'Row '+str(nl + 1)+': No lemma translations provided.'
                error.append(e1)

            if error:
                # these are feedback errors, don't bother comparing the new gloss to existing values, we already found an error
                continue

            # put creation of value_dict for the new gloss inside an exception to catch any unexpected errors
            # errors are kept track of as user feedback, but the code needs to be safe
            try:
                (new_gloss, already_exists, error_create, earlier_creation_same_csv, earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss) \
                    = create_gloss_from_valuedict(value_dict,dataset,nl, earlier_creation_same_csv, earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss)
            except (KeyError, ValueError):
                print('import csv create: got this far in processing loop before exception in row ', str(nl+1))
                break
            if len(error_create):
                errors_found_string = '\n'.join(error_create)
                error.append(errors_found_string)
            else:
                creation += new_gloss
            # whether or not glosses mentioned in the csv file already exist is accummulated in gloss_already_exists
            # one version of the template also shows these with the errors, so the user might remove extra data from the csv to reduce its size
            gloss_already_exists += already_exists
            continue

        stage = 1

    #Do changes
    elif len(request.POST) > 0:

        glosses_to_create = dict()

        for key, new_value in request.POST.items():

            # obtain tuple values for each proposed gloss
            # pk is the row number in the import file!
            try:
                pk, fieldname = key.split('.')

                if pk not in glosses_to_create.keys():
                    glosses_to_create[pk] = dict()
                glosses_to_create[pk][fieldname] = new_value

            #In case there's no dot, this is not a value we set at the previous page
            except ValueError:
                # when the database token csrfmiddlewaretoken is passed, there is no dot
                continue

        # these should be error free based on the django template import_csv_create.html
        for row in glosses_to_create.keys():
            dataset = glosses_to_create[row]['dataset']

            try:
                dataset_id = Dataset.objects.get(acronym=dataset)
            except:
                # this is an error, this should have already been caught
                e1 = 'Dataset not found: ' + dataset
                error.append(e1)
                continue

            lemmaidglosstranslations = {}
            for language in dataset_id.translation_languages.all():
                lemma_id_gloss = glosses_to_create[row]['lemma_id_gloss_' + language.language_code_2char]
                if lemma_id_gloss:
                    lemmaidglosstranslations[language] = lemma_id_gloss
            # Check whether it is an existing one (correct, make a reference), ...
            existing_lemmas = []
            for language, term in lemmaidglosstranslations.items():
                try:
                    existing_lemmas.append(LemmaIdglossTranslation.objects.get(lemma__dataset=dataset_id,
                                                                               language=language,
                                                                               text=term).lemma)
                except ObjectDoesNotExist as e:
                    # New lemma will be created
                    pass
            existing_lemmas_set = set(existing_lemmas)

            if len(existing_lemmas) == len(lemmaidglosstranslations) and len(existing_lemmas_set) == 1:
                lemma_for_gloss = existing_lemmas[0]
            elif len(existing_lemmas) == 0:
                with atomic():
                    lemma_for_gloss = LemmaIdgloss(dataset=dataset_id)
                    lemma_for_gloss.save()
                    for language, term in lemmaidglosstranslations.items():
                        new_lemmaidglosstranslation = LemmaIdglossTranslation(lemma=lemma_for_gloss,
                                                                              language=language, text=term)
                        new_lemmaidglosstranslation.save()
            else:
                # This case should not happen, it should have been caught in stage 1
                e1 = 'To create glosses in dataset ' + dataset_id.acronym + \
                     ', the combination of Lemma ID Gloss translations should either refer ' \
                     'to an existing Lemma ID Gloss or make up a completely new Lemma ID gloss.'
                error.append(e1)
                continue

            new_gloss = Gloss()
            new_gloss.lemma = lemma_for_gloss
            # Save the new gloss before updating it
            new_gloss.save()
            new_gloss.creationDate = DT.datetime.now()
            new_gloss.creator.add(request.user)
            new_gloss.excludeFromEcv = False
            new_gloss.save()

            for language in dataset_languages:
                annotation_id_gloss = glosses_to_create[row]['annotation_id_gloss_' + language.language_code_2char]
                if annotation_id_gloss:
                    annotationidglosstranslation = AnnotationIdglossTranslation()
                    annotationidglosstranslation.language = language
                    annotationidglosstranslation.gloss = new_gloss
                    annotationidglosstranslation.text = annotation_id_gloss
                    annotationidglosstranslation.save()

        stage = 2

    #Show uploadform
    else:

        stage = 0

    return render(request,'dictionary/import_csv_create.html',{'form':uploadform,'stage':stage,'changes':changes,
                                                        'creation':creation,
                                                        'gloss_already_exists':gloss_already_exists,
                                                        'error':error,
                                                        'dataset_languages':dataset_languages,
                                                        'selected_datasets':selected_datasets,
                                                        'translation_languages_dict': translation_languages_dict,
                                                        'seen_datasets': seen_datasets,
                                                        'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


def import_csv_update(request):
    user = request.user
    import guardian
    user_datasets = guardian.shortcuts.get_objects_for_user(user,'change_dataset',Dataset)
    user_datasets_names = [ dataset.acronym for dataset in user_datasets ]

    selected_datasets = get_selected_datasets_for_user(user)
    dataset_languages = get_dataset_languages(selected_datasets)
    translation_languages_dict = {}
    # this dictionary is used in the template, it maps each dataset to a list of tuples (English name of dataset, language_code_2char)
    for dataset_object in user_datasets:
        translation_languages_dict[dataset_object] = []

        for language in dataset_object.translation_languages.all():
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            language_tuple = (language_name, language.language_code_2char)
            translation_languages_dict[dataset_object].append(language_tuple)

    seen_datasets = []
    seen_dataset_names = []

    # fatal errors are duplicate column headers, data in columns without headers
    # column headers that do not correspond to database fields
    # non-numerical gloss ids
    # non-existent dataset or no permission for dataset
    # attempt to create glosses in multiple datasets in the same csv
    # missing Dataset column
    # missing Lemma or Annotation translations required for the dataset during creation
    # extra columns during creation:
    # (although these are ignored, it is advised to remove them to make it clear the data is not being stored)

    uploadform = signbank.dictionary.forms.CSVUploadForm
    changes = []
    error = []
    creation = []
    gloss_already_exists = []
    earlier_updates_same_csv = []
    earlier_updates_lemmaidgloss = {}

    encoding_error = False

    # this is needed in case the user has exported the csv first and not removed the frequency columns
    # this code retrieves the column headers in English

    gloss_fields = [Gloss.get_field(fname) for fname in Gloss.get_field_names()]
    with override(LANGUAGE_CODE):
        columns_to_skip = {field.verbose_name: field for field in gloss_fields if field.name in FIELDS['frequency']}

    # Process Input File
    if len(request.FILES) > 0:

        new_file = request.FILES['file']

        try:
            # files that will fail here include those renamed to .csv which are not csv
            # non UTF-8 encoded files also fail
            csv_text = new_file.read().decode('UTF-8-sig')
        except (UnicodeDecodeError, UnicodeError):
            new_file.seek(0)
            import magic
            magic_file_type = magic.from_buffer(new_file.read(2048), mime=True)

            if magic_file_type == 'text/plain':
                feedback_message = _('Unrecognised text encoding. Please export your file to UTF-8 format using e.g. LibreOffice.')
            else:
                feedback_message = _('Unrecognised format in selected CSV file.')

            messages.add_message(request, messages.ERROR, feedback_message)

            return render(request, 'dictionary/import_csv_update.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'creation': creation,
                           'gloss_already_exists': gloss_already_exists,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        fatal_error = False
        csv_lines = re.compile('[\r\n]+').split(csv_text) # split the csv text on any combination of new line characters

        # the following code allows for specifying a column delimiter in the import_csv_update.html template
        if 'delimiter' in request.POST:
            delimiter_radio = request.POST['delimiter']
            if delimiter_radio == 'tab':
                delimiter = '\t'
            elif delimiter_radio == 'comma':
                delimiter = ','
            elif delimiter_radio == 'semicolon':
                delimiter = ';'
            else:
                # this should not occur
                # perhaps only if the user is trying to fiddle without using the template
                # set to template default, print message for Admin
                print('Missing template default for delimiter_radio in import_csv_update.html')
                delimiter = ','
                delimiter_radio = 'comma'
        else:
            # this should not occur
            # perhaps only if the user is trying to fiddle without using the template
            # set to template default, print message for Admin
            print('Missing template default for delimiter_radio in import_csv_update.html')
            delimiter = ','
            delimiter_radio = 'comma'

        # the obtains the notes togggle
        notes_toggle = 'keep'
        if 'toggle_notes' in request.POST:
            notes_radio = request.POST['toggle_notes']
            if notes_radio == 'erase':
                notes_toggle = 'erase'

        # the obtains the notes assign togggle
        notes_assign_toggle = 'replace'
        if 'toggle_notes_assign' in request.POST:
            notes_radio = request.POST['toggle_notes_assign']
            if notes_radio == 'update':
                notes_assign_toggle = 'update'

        # the obtains the tags togggle
        tags_toggle = 'keep'
        if 'toggle_tags' in request.POST:
            tags_radio = request.POST['toggle_tags']
            if tags_radio == 'erase':
                tags_toggle = 'erase'

        first_csv_line, rest_csv_lines = csv_lines[0], csv_lines[1:]

        keys = first_csv_line.strip().split(delimiter)
        if len(keys) < 2:
            feedback_message = _('Incorrect Delimiter: ') + delimiter_radio + '.'
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        elif '' in keys:
            feedback_message = _('Empty Column Header Found.')
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        elif len(keys) > len(list(set(keys))) :
            feedback_message = _('Duplicate Column Header Found.')
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        elif 'Signbank ID' not in keys:
            feedback_message = _('The Signbank ID column is required.')
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        elif 'Dataset' not in keys:
            feedback_message = _('The Dataset column is required.')
            messages.add_message(request, messages.ERROR, feedback_message)
            encoding_error = True
        if encoding_error:
            return render(request, 'dictionary/import_csv_update.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'creation': creation,
                           'gloss_already_exists': gloss_already_exists,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        # create a template for an empty row with the desired number of columns
        empty_row = [''] * len(keys)
        for nl, line in enumerate(rest_csv_lines):
            if len(line) == 0:
                # this happens at the end of the file
                continue
            values = csv.reader([line], delimiter=delimiter).__next__()
            if values == empty_row:
                continue

            # construct value_dict for row
            value_dict = {}
            for nv,value in enumerate(values):
                if nv >= len(keys):
                    # this has already been checked above
                    # it's here to avoid needing an exception on the subscript [nv]
                    continue
                elif keys[nv] in columns_to_skip.keys():
                    continue
                value_dict[keys[nv]] = value

            # 'Signbank ID' in value_dict keys, checked above
            try:
                pk = int(value_dict['Signbank ID'])
            except (ValueError, KeyError):
                # the ID is not a number
                e = 'Row '+str(nl + 1) + ': Signbank ID must be numerical: ' + str(value_dict['Signbank ID'])
                error.append(e)
                fatal_error = True
                break

            # 'Dataset' in value_dict keys, checked above
            dataset_name = value_dict['Dataset'].strip()

            if dataset_name not in seen_dataset_names:
                # catch possible empty values for dataset, primarily for pretty printing error message
                if dataset_name == '' or dataset_name == None or dataset_name == 0 or dataset_name == 'NULL':
                    e_dataset_empty = 'Row '+str(nl + 1) + ': The Dataset is missing.'
                    error.append(e_dataset_empty)
                    break
                try:
                    dataset = Dataset.objects.get(acronym=dataset_name)
                except ObjectDoesNotExist:
                    # The dataset does not exist
                    e_dataset_not_found = 'Row '+str(nl + 1) + ': Dataset %s' % value_dict['Dataset'].strip() + ' does not exist.'
                    error.append(e_dataset_not_found)
                    fatal_error = True
                    break
                if dataset_name not in user_datasets_names:
                    # Check whether the user may change the dataset of the current row
                    e3 = 'Row '+str(nl + 1) + ': You are not allowed to change dataset %s.' % value_dict['Dataset'].strip()
                    error.append(e3)
                    fatal_error = True
                    break
                if dataset not in selected_datasets:
                    e3 = 'Row '+str(nl + 1) + ': Please select the dataset %s.' % value_dict['Dataset'].strip()
                    error.append(e3)
                    fatal_error = True
                    break
                if seen_datasets:
                    # already seen a dataset
                    if dataset in seen_datasets:
                        pass
                    else:
                        # seen more than one dataset
                        seen_datasets.append(dataset)
                        seen_dataset_names.append(dataset_name)
                else:
                    seen_datasets.append(dataset)
                    seen_dataset_names.append(dataset_name)
                    # saw the first dataset

            if fatal_error or encoding_error:
                # break out of enumerate csv lines
                # Dataset or Signbank ID data for configuring updates in the next step is compromised
                break
            # The Lemma ID Gloss may already exist.
            lemmaidglosstranslations = {}
            contextual_error_messages_lemmaidglosstranslations = []
            for language in dataset.translation_languages.all():
                language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                column_name = "Lemma ID Gloss (%s)" % language_name
                if column_name in value_dict:
                    lemma_idgloss_value = value_dict[column_name].strip()
                    # also stores empty values
                    lemmaidglosstranslations[language] = lemma_idgloss_value

            # updating glosses
            try:
                gloss = Gloss.objects.select_related().get(pk=pk)
            except ObjectDoesNotExist as e:

                e = 'Row '+ str(nl + 1) + ': Could not find gloss for Signbank ID '+str(pk)
                error.append(e)
                continue

            if gloss.lemma.dataset != dataset:
                e1 = 'Row '+ str(nl + 1) + ': The Dataset column (' + dataset.acronym + ') does not correspond to that of the Signbank ID (' \
                                                    + str(pk) + ').'
                error.append(e1)
                # ignore the rest of the row
                continue
            # dataset is the same

            # If there are changes in the LemmaIdglossTranslation, the changes should refer to another LemmaIdgloss
            current_lemmaidglosstranslations = {}
            for language in gloss.lemma.dataset.translation_languages.all():
                try:
                    lemma_translation = LemmaIdglossTranslation.objects.get(language=language, lemma=gloss.lemma)
                    current_lemmaidglosstranslations[language] = lemma_translation.text
                except:
                    current_lemmaidglosstranslations[language] = ''
            if lemmaidglosstranslations \
                    and current_lemmaidglosstranslations != lemmaidglosstranslations:

                help = 'Row '+ str(nl + 1) + ': Attempt to update Lemma ID Gloss translations for Signbank ID (' + str(pk) + ")."
                error.append(help)
                messages.add_message(request, messages.ERROR, ('Attempt to update Lemma ID Gloss translations for Signbank ID.'))
                continue

            try:
                (changes_found, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss) = \
                            compare_valuedict_to_gloss(value_dict,gloss.id,user_datasets_names, nl,
                                                       earlier_updates_same_csv, earlier_updates_lemmaidgloss,
                                                       notes_toggle, notes_assign_toggle, tags_toggle)
                changes += changes_found

                if len(errors_found):
                    # more than one error found
                    errors_found_string = '\n'.join(errors_found)
                    error.append(errors_found_string)

            except KeyError as e:

                e_string = str(e)
                error.append(e_string)
        stage = 1

    # Do changes
    elif len(request.POST) > 0:
        gloss_fields = Gloss.get_field_names()

        lemmaidglosstranslations_per_gloss = {}
        for key, new_value in request.POST.items():

            try:
                pk, fieldname = key.split('.')

            #In case there's no dot, this is not a value we set at the previous page
            except ValueError:
                # when the database token csrfmiddlewaretoken is passed, there is no dot
                continue

            gloss = Gloss.objects.select_related().get(pk=pk)

            # This is no longer allowed. The column is skipped.
            # Updating the lemma idgloss is a special procedure, not only because it has relations to other parts of
            # the database, but also because it only can be evaluated after reviewing all lemma idgloss translations
            lemma_idgloss_key_prefix = "Lemma ID Gloss ("
            if fieldname.startswith(lemma_idgloss_key_prefix):
                language_name = fieldname[len(lemma_idgloss_key_prefix):-1]
                if gloss not in lemmaidglosstranslations_per_gloss:
                    lemmaidglosstranslations_per_gloss[gloss] = {}
                lemmaidglosstranslations_per_gloss[gloss][language_name] = new_value

                # compare new value to existing value
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                languages = Language.objects.filter(**{language_name_column:language_name})
                if languages:
                    language = languages[0]
                    lemma_idglosses = gloss.lemma.lemmaidglosstranslation_set.filter(language=language)
                    if lemma_idglosses:
                        lemma_idgloss_string = lemma_idglosses[0].text
                    else:
                        # lemma not set
                        lemma_idgloss_string = ''
                    if lemma_idgloss_string != new_value and new_value != 'None' and new_value != '':
                        error_string = 'ERROR: Attempt to update Lemma ID Gloss translations: ' + new_value
                        if error:
                            error.append(error_string)
                        else:
                            error = [error_string]
                        messages.add_message(request, messages.ERROR, ('Attempt to update Lemma ID Gloss translations.'))

                continue   # avoid default field update

            # Updating the annotation idgloss is a special procedure, because it has relations to other parts of the
            # database
            annotation_idgloss_key_prefix = "Annotation ID Gloss ("
            if fieldname.startswith(annotation_idgloss_key_prefix):
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = fieldname[len(annotation_idgloss_key_prefix):-1]
                languages = Language.objects.filter(**{language_name_column:language_name})
                if languages:
                    language = languages.first()
                    annotation_idglosses = gloss.annotationidglosstranslation_set.filter(language=language)
                    if annotation_idglosses:
                        annotation_idgloss = annotation_idglosses.first()
                        annotation_idgloss.text = new_value
                        annotation_idgloss.save()
                continue

            keywords_key_prefix = "Senses ("
            # Updating the keywords is a special procedure, because it has relations to other parts of the database
            if fieldname.startswith(keywords_key_prefix):
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = fieldname[len(keywords_key_prefix):-1]
                language = Language.objects.filter(**{language_name_column: language_name}).first()
                if language:
                    csv_create_senses(request, gloss, language, new_value, create=True)
                continue

            example_sentences_key_prefix = "Example Sentences ("
            if fieldname.startswith(example_sentences_key_prefix):
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = fieldname[len(example_sentences_key_prefix):-1]
                language = Language.objects.filter(**{language_name_column: language_name}).first()
                if language:
                    csv_update_sentences(request, gloss, language, new_value, update=True)
                continue

            if fieldname == 'SignLanguages':

                new_human_value_list = [v.strip() for v in new_value.split(',')]

                update_signlanguage(gloss,'signlanguage',new_human_value_list)
                gloss.save()
                continue

            if fieldname == 'Dialects':

                new_human_value_list = [v.strip() for v in new_value.split(',')]

                update_dialect(gloss,None,new_human_value_list)
                gloss.save()
                continue

            if fieldname == 'Dataset':

                # this has already been checked for existence and permission in the previous step
                # get dataset identifier
                if new_value == 'None':
                    # don't allow the user to erase the current dataset, this should have already been caught
                    print('csv import make changes error: gloss ', gloss.id, ' attempt to set dataset to empty')
                    continue
                else:
                    # the existence of the new dataset should have already been tested
                    new_dataset = Dataset.objects.get(acronym=new_value)
                try:
                    gloss_lemma = gloss.lemma
                except:
                    # this error should not happen
                    print('csv import make changes error: gloss ', gloss.id, ' gloss.lemma is empty, cannot set dataset')
                    continue

                # this could have an unwanted side effect on the Lemma translations?
                gloss_lemma.dataset = new_dataset
                gloss_lemma.save()
                continue

            if fieldname == 'Sequential Morphology':

                new_human_value_list = [v.strip() for v in new_value.split(',')]
                # get the gloss ids out of the input
                # the input is a sequence of role:id values
                # these have already been parsed at the previous stage
                glosses = [int(component.split(':')[1]) for component in new_human_value_list]

                update_sequential_morphology(gloss, None, glosses)

                continue

            if fieldname == 'Simultaneous Morphology':

                new_human_value_list = [v.strip() for v in new_value.split(',')]

                update_simultaneous_morphology(gloss,None,new_human_value_list)

                continue

            if fieldname == 'Blend Morphology':

                new_human_value_list = [v.strip() for v in new_value.split(',')]

                update_blend_morphology(gloss,None,new_human_value_list)

                continue

            if fieldname == 'Relations to other signs':

                new_human_value_list = [v.strip() for v in new_value.split(',')]

                subst_relations(gloss,None,new_human_value_list)
                continue

            if fieldname == 'Relations to foreign signs':

                new_human_value_list = [v.strip() for v in new_value.split(',')]

                subst_foreignrelations(gloss,None,new_human_value_list)
                continue

            if fieldname == 'Tags':

                new_human_value_list = [v.strip().replace(' ','_') for v in new_value.split(',')]

                update_tags(gloss,None,new_human_value_list)
                continue

            if fieldname == 'Notes':

                subst_notes(gloss,None,new_value)
                continue

            with override(settings.LANGUAGE_CODE):
                if fieldname not in gloss_fields:
                    continue
                field = Gloss.get_field(fieldname)
                # Replace the value for bools
                if field.__class__.__name__ == 'BooleanField':

                    if new_value in ['true','True', 'TRUE']:
                        new_value = True
                    elif new_value == 'None' or new_value == 'Neutral':
                        new_value = None
                    else:
                        new_value = False
                elif isinstance(field, models.ForeignKey) and field.related_model == Handshape:
                    new_value = Handshape.objects.get(machine_value=int(new_value))
                elif hasattr(field, 'field_choice_category'):
                    new_value = FieldChoice.objects.get(machine_value=int(new_value),
                                                        field=Gloss.get_field(fieldname).field_choice_category)
                # Remember this for renaming the video later
                if fieldname == 'idgloss':
                    video_path_before = settings.WRITABLE_FOLDER+gloss.get_video_path()

                # The normal change and save procedure
                # the new value machine value of Handshape or FieldChoice has been replaced with an object reference above
                setattr(gloss, fieldname, new_value)
                gloss.save()

                #Also update the video if needed
                if fieldname == 'idgloss':
                    video_path_after = settings.WRITABLE_FOLDER+gloss.get_video_path()
                    if os.path.isfile(video_path_before):
                        os.rename(video_path_before,video_path_after)

        stage = 2

    #Show uploadform
    else:

        stage = 0
    if encoding_error:
        # Go back to upload page
        stage = 0

    elif stage == 1 and not changes and not error:
        # no changes were found in the input file. print a message as feedback
        # this is needed in order to have output that can be tested for in the unit tests
        messages.add_message(request, messages.INFO, ('No changes were found.'))

    return render(request,'dictionary/import_csv_update.html',{'form':uploadform,'stage':stage,'changes':changes,
                                                        'creation':creation,
                                                        'gloss_already_exists':gloss_already_exists,
                                                        'error':error,
                                                        'dataset_languages':dataset_languages,
                                                        'selected_datasets':selected_datasets,
                                                        'translation_languages_dict': translation_languages_dict,
                                                        'seen_datasets': seen_datasets,
                                                        'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


def import_csv_lemmas(request):
    user = request.user
    import guardian
    user_datasets = guardian.shortcuts.get_objects_for_user(user, 'change_dataset', Dataset)
    user_datasets_names = [dataset.acronym for dataset in user_datasets]

    selected_datasets = get_selected_datasets_for_user(user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    translation_languages_dict = {}
    # this dictionary is used in the template
    # it maps each dataset to a list of tuples (English name of dataset, language_code_2char)
    for dataset_object in user_datasets:
        translation_languages_dict[dataset_object] = []

        for language in dataset_object.translation_languages.all():
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            language_tuple = (language_name, language.language_code_2char)
            translation_languages_dict[dataset_object].append(language_tuple)

    # fatal errors are duplicate column headers, data in columns without headers
    # column headers that do not correspond to database fields
    # non-numerical lemma ids
    # non-existent dataset or no permission for dataset
    # attempt to update lemmas in multiple datasets in the same csv
    # missing Dataset column
    # missing Lemma required for the dataset

    uploadform = signbank.dictionary.forms.CSVUploadForm
    seen_datasets = []
    changes = []
    error = []
    earlier_updates_same_csv = []
    earlier_updates_lemmaidgloss = {}

    if not selected_datasets or selected_datasets.count() > 1:
        feedback_message = _('Please select a single dataset for which you have change permission.')
        messages.add_message(request, messages.ERROR, feedback_message)

        return render(request, 'dictionary/import_csv_update_lemmas.html',
                      {'form': uploadform, 'stage': 0, 'changes': changes,
                       'error': error,
                       'dataset_languages': dataset_languages,
                       'selected_datasets': selected_datasets,
                       'translation_languages_dict': translation_languages_dict,
                       'seen_datasets': seen_datasets,
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

    # set the allowed dataset names to selected dataset, which must have change permission (checked below)
    dataset = selected_datasets.first()
    seen_dataset_names = [dataset.acronym]

    if dataset not in user_datasets:
        feedback_message = _('You do not have change permission for the chosen dataset.')
        messages.add_message(request, messages.ERROR, feedback_message)

        return render(request, 'dictionary/import_csv_update_lemmas.html',
                      {'form': uploadform, 'stage': 0, 'changes': changes,
                       'error': error,
                       'dataset_languages': dataset_languages,
                       'selected_datasets': selected_datasets,
                       'translation_languages_dict': translation_languages_dict,
                       'seen_datasets': seen_datasets,
                       'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

    # Process Input File
    if len(request.FILES) > 0:
        # the multipurpose template is at stage 0

        new_file = request.FILES['file']

        try:
            # files that will fail here include those renamed to .csv which are not csv
            # non UTF-8 encoded files also fail
            csv_text = new_file.read().decode('UTF-8-sig')
        except (UnicodeDecodeError, UnicodeError):
            feedback_message = _('Unrecognised text encoding. Please export your file to UTF-8 format using e.g. LibreOffice.')
            messages.add_message(request, messages.ERROR, feedback_message)

            return render(request, 'dictionary/import_csv_update_lemmas.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        fatal_error = False
        csv_lines = re.compile('[\r\n]+').split(csv_text)  # split the csv text on new line characters

        # the following code allows for specifying a column delimiter in the import_csv_update_lemmas.html template
        if 'delimiter' in request.POST:
            delimiter_radio = request.POST['delimiter']
            if delimiter_radio == 'tab':
                delimiter = '\t'
            elif delimiter_radio == 'comma':
                delimiter = ','
            elif delimiter_radio == 'semicolon':
                delimiter = ';'
            else:
                # this should not occur
                # perhaps only if the user is trying to fiddle without using the template
                # set to template default, print message for Admin
                print('Missing template default for delimiter_radio in import_csv_update_lemmas.html')
                delimiter = ','
                delimiter_radio = 'comma'
        else:
            # this should not occur
            # perhaps only if the user is trying to fiddle without using the template
            # set to template default, print message for Admin
            print('Missing template default for delimiter_radio in import_csv_update_lemmas.html')
            delimiter = ','
            delimiter_radio = 'comma'

        keys_found, extra_keys, csv_header, csv_body = split_csv_lines_header_body(dataset_languages, csv_lines,
                                                                                   delimiter)

        if not keys_found:
            # this is intended to assist the user in the case that a wrong file was selected
            feedback_message = _('The required column headers are missing.')
            messages.add_message(request, messages.ERROR, feedback_message)
            return render(request, 'dictionary/import_csv_update_lemmas.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        if extra_keys:
            # this is intended to assist the user in the case that a wrong file was selected
            feedback_message = _('Extra columns were found.')
            messages.add_message(request, messages.ERROR, feedback_message)
            return render(request, 'dictionary/import_csv_update_lemmas.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        # create a template for an empty row with the desired number of columns
        empty_row = [''] * len(csv_header)
        for nl, line in enumerate(csv_body):
            if len(line) == 0:
                # this happens at the end of the file
                continue
            values = csv.reader([line], delimiter=delimiter).__next__()
            if values == empty_row:
                continue

            # construct value_dict for row
            value_dict = {}
            for nv, value in enumerate(values):
                if nv >= len(csv_header):
                    # this has already been checked above
                    # it's here to avoid needing an exception on the subscript [nv]
                    continue
                value_dict[csv_header[nv]] = value

            try:
                pk = int(value_dict['Lemma ID'])
            except ValueError:
                e = 'Row '+str(nl + 1) + ': Lemma ID must be numerical: ' + str(value_dict['Lemma ID'])
                error.append(e)
                fatal_error = True
                break

            dataset_name = value_dict['Dataset'].strip()

            # catch possible empty values for dataset, primarily for pretty printing error message
            if dataset_name == '' or dataset_name is None or dataset_name == 0 or dataset_name == 'NULL':
                e_dataset_empty = 'Row ' + str(nl + 1) + ': The Dataset is missing.'
                error.append(e_dataset_empty)
                fatal_error = True
                break
            if dataset_name not in seen_dataset_names:
                # seen more than one dataset
                e3 = 'Row ' + str(nl + 1) + ': Dataset not in selected datasets: %s.' % dataset_name
                error.append(e3)
                fatal_error = True
                break

            # The Lemma ID Gloss may already exist.
            lemmaidglosstranslations = {}
            for language in dataset.translation_languages.all():
                language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                column_name = "Lemma ID Gloss (%s)" % language_name
                if column_name in value_dict:
                    lemma_idgloss_value = value_dict[column_name]
                    # also stores empty values
                    lemmaidglosstranslations[language] = lemma_idgloss_value

            # if we get to here, the Lemma ID, Dataset, and Lemma ID Gloss columns have been checked
            # determine if any extra columns were found
            for key in value_dict.keys():
                if key not in csv_header:
                    # too many columns found
                    e = 'Extra column found: ' + key
                    error.append(e)
                    # use a Boolean to catch all extra columns
                    fatal_error = True
                    break

            # # updating lemmas, propose changes (make dict)
            try:
                lemma = LemmaIdgloss.objects.select_related().get(pk=pk)
            except ObjectDoesNotExist as e:

                e = 'Row ' + str(nl + 1) + ': Could not find lemma for Lemma ID '+str(pk)
                error.append(e)
                continue

            if lemma.dataset.acronym != dataset_name:
                e1 = 'Row ' + str(nl + 1) + ': The Dataset column (' + dataset.acronym \
                     + ') does not correspond to that of the Lemma ID (' + str(pk) + ').'
                error.append(e1)
                # ignore the rest of the row
                continue
            # dataset is the same

            # If there are changes in the LemmaIdglossTranslation, the changes should refer to another LemmaIdgloss
            current_lemmaidglosstranslations = {}
            for language in lemma.dataset.translation_languages.all():
                try:
                    lemma_translation = LemmaIdglossTranslation.objects.get(language=language, lemma=lemma)
                    current_lemmaidglosstranslations[language] = lemma_translation.text
                except (KeyError, IndexError, ValueError, ObjectDoesNotExist, MultipleObjectsReturned):
                    current_lemmaidglosstranslations[language] = ''

            try:
                (changes_found, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss) = \
                            compare_valuedict_to_lemma(value_dict, lemma.id, user_datasets_names, nl,
                                                       lemmaidglosstranslations, current_lemmaidglosstranslations,
                                                       earlier_updates_same_csv, earlier_updates_lemmaidgloss)
                changes += changes_found

                if len(errors_found):
                    # more than one error found
                    errors_found_string = '\n'.join(errors_found)
                    error.append(errors_found_string)

            except KeyError as e:

                e_string = str(e)
                error.append(e_string)
        stage = 1

    # Do changes
    elif len(request.POST) > 0:

        for key, new_value in request.POST.items():

            try:
                pk, fieldname = key.split('.')

            #In case there's no dot, this is not a value we set in the proposed changes
            except ValueError:
                # when the database token csrfmiddlewaretoken is passed, there is no dot
                continue

            lemma = LemmaIdgloss.objects.select_related().get(pk=pk)

            with override(settings.LANGUAGE_CODE):

                # when we do the changes, it has already been confirmed
                # that changes to the translations ensure that there is at least one translation
                lemma_idgloss_key_prefix = "Lemma ID Gloss ("
                if fieldname.startswith(lemma_idgloss_key_prefix):
                    language_name = fieldname[len(lemma_idgloss_key_prefix):-1]

                    # compare new value to existing value
                    language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                    languages = Language.objects.filter(**{language_name_column: language_name})
                    if languages:
                        language = languages[0]
                        lemma_idglosses = lemma.lemmaidglosstranslation_set.filter(language=language)
                        if lemma_idglosses:
                            # update the lemma translation
                            lemma_translation = lemma_idglosses.first()
                            if new_value:
                                setattr(lemma_translation, 'text', new_value)
                                lemma_translation.save()
                            else:
                                # setting a translation to empty deletes the translation
                                # in the previous stage when proposing changes we have already checked to prevent all translations from being deleted
                                lemma_translation.delete()
                        elif new_value:
                            # this is a new lemma translation for the language
                            lemma_translation = LemmaIdglossTranslation(lemma=lemma, language=language)
                            setattr(lemma_translation, 'text', new_value)
                            lemma_translation.save()
                        # else:
                            # this case should not occur, there is no translation for the language and the user wants to make an empty one

        stage = 2

    # Show uploadform
    else:

        stage = 0

    return render(request, 'dictionary/import_csv_update_lemmas.html',
                  {'form': uploadform, 'stage': stage, 'changes': changes,
                   'error': error,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'translation_languages_dict': translation_languages_dict,
                   'seen_datasets': seen_datasets,
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})



def switch_to_language(request,language):

    user_profile = request.user.user_profile_user
    user_profile.last_used_language = language
    user_profile.save()

    return HttpResponse('OK')

def recently_added_glosses(request):
    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    from signbank.settings.server_specific import RECENTLY_ADDED_SIGNS_PERIOD

    (interface_language, interface_language_code,
     default_language, default_language_code) = get_interface_language_and_default_language_codes(request)

    dataset_display_languages = []
    for lang in dataset_languages:
        dataset_display_languages.append(lang.language_code_2char)
    if interface_language_code in dataset_display_languages:
        lang_attr_name = interface_language_code
    else:
        lang_attr_name = default_language_code

    recently_added_signs_since_date = DT.datetime.now(tz=get_current_timezone()) - RECENTLY_ADDED_SIGNS_PERIOD
    recent_glosses = Gloss.objects.filter(morpheme=None, lemma__dataset__in=selected_datasets).filter(
        creationDate__range=[recently_added_signs_since_date, DT.datetime.now(tz=get_current_timezone())]).order_by(
        'creationDate').reverse()

    items = construct_scrollbar(recent_glosses, 'sign', lang_attr_name)
    request.session['search_results'] = items
    request.session['search_type'] = 'sign'
    request.session.modified = True

    return render(request, 'dictionary/recently_added_glosses.html',
                  {'glosses': recent_glosses,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'language': interface_language,
                   'number_of_days': RECENTLY_ADDED_SIGNS_PERIOD.days,
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


def proposed_new_signs(request):
    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    proposed_or_new_signs = (Gloss.objects.filter(isNew=True) |
                             TaggedItem.objects.get_intersection_by_model(Gloss, "sign:_proposed")).order_by('creationDate').reverse()
    return render(request, 'dictionary/recently_added_glosses.html',
                  {'glosses': proposed_or_new_signs,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'number_of_days': RECENTLY_ADDED_SIGNS_PERIOD.days,
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})


def create_citation_image(request, pk):
    gloss = get_object_or_404(Gloss, pk=pk)
    try:
        gloss.create_citation_image()
    except:
        print("Citation image for gloss {} could not be created.".format(gloss.id))

    # return to referer
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)

def add_image(request):

    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'

    if request.method == 'POST':

        form = ImageUploadForGlossForm(request.POST, request.FILES)

        if form.is_valid():

            gloss_id = form.cleaned_data['gloss_id']
            gloss = get_object_or_404(Gloss, pk=gloss_id)

            imagefile = form.cleaned_data['imagefile']
            extension = '.'+imagefile.name.split('.')[-1]

            if extension not in settings.SUPPORTED_CITATION_IMAGE_EXTENSIONS:

                feedback_message = _('File extension not supported! Please convert to png or jpg')

                messages.add_message(request, messages.ERROR, feedback_message)

                return redirect(url)

            elif imagefile.size > settings.MAXIMUM_UPLOAD_SIZE:

                feedback_message = _('Uploaded file too large!')
                messages.add_message(request, messages.ERROR, feedback_message)

                return redirect(url)

            # construct a filename for the image, use sn
            # if present, otherwise use idgloss+gloss id
            if gloss.sn != None:
                imagefile.name = str(gloss.sn) + extension
            else:
                imagefile.name = gloss.idgloss + "-" + str(gloss.pk) + extension

            redirect_url = form.cleaned_data['redirect']

            # deal with any existing image for this sign
            goal_path = os.path.join(
                WRITABLE_FOLDER,
                GLOSS_IMAGE_DIRECTORY,
                gloss.lemma.dataset.acronym,
                signbank.tools.get_two_letter_dir(gloss.idgloss)
            )
            goal_location_str = os.path.join(goal_path, gloss.idgloss + '-' + str(gloss.pk) + extension)

            try:
                exists = os.path.exists(goal_path)
            except:
                exists = False

            #First make the dir if needed
            if not exists:
                try:
                    os.makedirs(goal_path)
                except OSError as ose:
                    print(ose)

            #Remove previous video
            if gloss.get_image_path():
                os.remove(settings.WRITABLE_FOLDER+gloss.get_image_path())

            try:
                f = open(goal_location_str.encode(sys.getfilesystemencoding()), 'wb+')
                destination = File(f)
            except:
                quoted_filename = quote(gloss.idgloss, safe='')
                filename = quoted_filename + '-' + str(gloss.pk) + extension
                goal_location_str = os.path.join(goal_path, filename)
                try:
                    f = open(goal_location_str.encode(sys.getfilesystemencoding()), 'wb+')
                    destination = File(f)
                except:
                    print('add_image, failed to open destintation: ', goal_location_str)
                    return redirect(redirect_url)
            # if we get to here, destination has been opened
            for chunk in imagefile.chunks():
                destination.write(chunk)
            destination.close()

            return redirect(redirect_url)

    # if we can't process the form, just redirect back to the
    # referring page, should just be the case of hitting
    # Upload without choosing a file but could be
    # a malicious request, if no referrer, go back to root
    return redirect(url)

def delete_image(request, pk):

    if request.method == "POST":

        # deal with any existing video for this sign
        gloss = get_object_or_404(Gloss, pk=pk)
        image_path = gloss.get_image_path()
        full_image_path = settings.WRITABLE_FOLDER + os.sep + image_path
        default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)
        if os.path.exists(full_image_path.encode('utf-8')):
            os.remove(full_image_path.encode('utf-8'))
        else:
            print('delete_image: wrong type for image path, file does not exist')
        deleted_image = DeletedGlossOrMedia()
        deleted_image.item_type = 'image'
        deleted_image.idgloss = gloss.idgloss
        deleted_image.annotation_idgloss = default_annotationidglosstranslation
        deleted_image.old_pk = gloss.pk
        deleted_image.filename = image_path
        deleted_image.save()

    # return to referer
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)


def add_handshape_image(request):

    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'

    if not settings.USE_HANDSHAPE:
        return redirect(url)

    if request.method == 'POST':

        form = ImageUploadForHandshapeForm(request.POST, request.FILES)

        if form.is_valid():

            handshape_id = form.cleaned_data['handshape_id']
            handshape = get_object_or_404(Handshape, machine_value=handshape_id)

            imagefile = form.cleaned_data['imagefile']
            extension = '.'+imagefile.name.split('.')[-1]

            if extension not in settings.SUPPORTED_CITATION_IMAGE_EXTENSIONS:

                feedback_message = _('File extension not supported! Please convert to png or jpg')
                messages.add_message(request, messages.ERROR, feedback_message)

                return redirect(url)

            elif imagefile.size > settings.MAXIMUM_UPLOAD_SIZE:

                feedback_message = _('Uploaded file too large!')
                messages.add_message(request, messages.ERROR, feedback_message)
                return redirect(url)

            # construct a filename for the image, use sn
            # if present, otherwise use idgloss+gloss id
            imagefile.name = "handshape_" + str(handshape.machine_value) + extension

            redirect_url = form.cleaned_data['redirect']

            # deal with any existing image for this sign
            goal_path = settings.WRITABLE_FOLDER+settings.HANDSHAPE_IMAGE_DIRECTORY + '/' + str(handshape.machine_value) + '/'
            goal_location = goal_path + 'handshape_' + str(handshape.machine_value) + extension
            # First make the dir if needed
            try:
                os.mkdir(goal_path)
            except OSError:
                pass

            # Remove previous video
            if handshape.get_image_path():
                os.remove(settings.WRITABLE_FOLDER+handshape.get_image_path())

            # create the destination file
            try:
                f = open(goal_location, 'wb+')
            except (UnicodeEncodeError, IOError, OSError):
                feedback_message = _('Error uploading handshape image. Please consult the administrator.')
                messages.add_message(request, messages.ERROR, feedback_message)
                return redirect(redirect_url)

            destination = File(f)
            # Save the file
            for chunk in request.FILES['imagefile'].chunks():
                destination.write(chunk)
            destination.close()

            return redirect(redirect_url)

    # if we can't process the form, just redirect back to the
    # referring page, should just be the case of hitting
    # Upload without choosing a file but could be
    # a malicious request, if no referrer, go back to root
    return redirect(url)


def gloss_annotations(this_gloss):
    # this function is used for display of the annotations in the find_and_save_variants template
    # if more than one translation language is available, the language prefixes the annotation translation text
    # a comma-separated string of the translations is returned
    translations = []
    count_dataset_languages = this_gloss.lemma.dataset.translation_languages.all().count() \
        if this_gloss.lemma and this_gloss.lemma.dataset else 0
    for translation in this_gloss.annotationidglosstranslation_set.all():
        if settings.SHOW_DATASET_INTERFACE_OPTIONS and count_dataset_languages > 1:
            translations.append("{}: {}".format(translation.language, translation.text))
        else:
            translations.append("{}".format(translation.text))
    return ", ".join(translations)


def find_and_save_variants(request):

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    gloss_pattern_table = dict()

    if selected_datasets.count() > 1:
        # because of the way the variant suffixes are computed, we only want to allow this over one dataset
        # since the variants are obtained indirectly via a Gloss method for each gloss
        # and these are syntactic patterns
        # we don't want to accidentally have variants from different datasets
        return render(request, 'dictionary/find_and_save_variants.html',
                      {'gloss_pattern_table': gloss_pattern_table,
                       'dataset_languages': dataset_languages,
                       'selected_datasets': selected_datasets,
                       'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface,
                       'too_many_datasets': True
                       })

    # first get all the glosses from the (single) selected dataset that match the syntactical variant pattern
    variant_pattern_glosses = Gloss.objects.filter(lemma__dataset__in=selected_datasets,
                                                   annotationidglosstranslation__text__regex=r"^(.*)\-([A-Z])$").distinct().order_by('lemma')

    # each of these, called the focus gloss, will have a row in a table in the template
    # if the focus gloss has syntactic variants
    # construct here the columns for the focus gloss row
    for focus_gloss in variant_pattern_glosses:
        dict_key = focus_gloss.id

        # the first row shows the annotations of the focus gloss (optionally prefaced by language)
        # these will have the variant pattern (for at least one of the languages)
        col1 = gloss_annotations(focus_gloss)

        # obtain any other relations the focus gloss is involved in
        other_relations_of_sign = focus_gloss.other_relations()

        # variants may also exist as saved relations (rather than syntactic patterns)
        # these are put in a column in the table
        variant_relations_of_sign = [r.target for r in focus_gloss.variant_relations()]

        if variant_relations_of_sign:
            col3 = ' || '.join(gloss_annotations(g) for g in variant_relations_of_sign)
        else:
            col3 = ' '

        # both of these need to be excluded from any matches below
        other_relation_objects = [x.target.id for x in other_relations_of_sign]
        variant_relation_objects = [x.id for x in variant_relations_of_sign]

        # now look for other glosses in the dataset that match the stem of the variant
        # (i.e., remove the -A, -B, -C, ... and look for the first part (stem), but with a different suffix)
        # exclude other relations and saved variant relations
        # Build query
        this_sign_stems = focus_gloss.get_stems()
        if not this_sign_stems:
            continue
        queries = []
        for this_sign_stem in this_sign_stems:
            # the stems are multilingual, for each language of the dataset
            # stored as (language, text) tuples
            this_matches = r'^' + re.escape(this_sign_stem[1]) + r'\-[A-Z]$'
            queries.append(Q(annotationidglosstranslation__text__regex=this_matches,
                             lemma__dataset=focus_gloss.lemma.dataset,
                             annotationidglosstranslation__language=this_sign_stem[0]))
        query = queries.pop()
        for q in queries:
            query |= q
        candidate_variants = Gloss.objects.filter(query).distinct().exclude(id=focus_gloss.id).exclude(
            id__in=other_relation_objects).exclude(id__in=variant_relation_objects)

        if not candidate_variants:
            # if no syntactical variants were found, do not put this gloss in the table
            continue

        # for each of the variants, display its annotations (possibly with language)
        col4 = ' || '.join(gloss_annotations(x) for x in candidate_variants)

        gloss_pattern_table[dict_key] = (dict_key, col1, col3, col4)

    return render(request, 'dictionary/find_and_save_variants.html',
                  {'gloss_pattern_table': gloss_pattern_table,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface,
                   'too_many_datasets': False
                   })


def get_unused_videos(request):

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    selected_dataset_acronyms = [ ds.acronym for ds in selected_datasets ]
    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    file_not_in_glossvideo_object = []
    gloss_video_dir = os.path.join(settings.WRITABLE_FOLDER, settings.GLOSS_VIDEO_DIRECTORY)
    for acronym in os.listdir(gloss_video_dir):
        if acronym not in selected_dataset_acronyms:
            continue
        if os.path.isdir(os.path.join(gloss_video_dir, acronym)):
            for folder in os.listdir(os.path.join(gloss_video_dir, acronym)):
                if os.path.isdir(os.path.join(gloss_video_dir, acronym, folder)):
                    for filename in os.listdir(os.path.join(gloss_video_dir, acronym, folder)):
                        if small_appendix in filename:
                            filename = add_small_appendix(filename, reverse=True)
                        gloss_video_path = os.path.join(settings.GLOSS_VIDEO_DIRECTORY, acronym, folder, filename)
                        gloss_videos = GlossVideo.objects.filter(videofile=gloss_video_path, version=0)
                        if not gloss_videos:
                            file_not_in_glossvideo_object.append((acronym, folder, filename))

    return render(request, "dictionary/unused_videos.html",
                  {'file_not_in_glossvideo_object': file_not_in_glossvideo_object,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface
                   })


@login_required_config
def package(request):

    # :)
    first_part_of_file_name = 'signbank_pa'

    timestamp_part_of_file_name = str(int(time.time()))

    if 'since_timestamp' in request.GET:
        first_part_of_file_name += 'tch'
        since_timestamp = int(request.GET['since_timestamp'])
        timestamp_part_of_file_name = request.GET['since_timestamp']+'-'+timestamp_part_of_file_name
    else:
        first_part_of_file_name += 'ckage'
        since_timestamp = 0

    if 'dataset_name' in request.GET:
        dataset = Dataset.objects.get(acronym=request.GET['dataset_name'])
    else:
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)


    video_folder_name = 'glossvideo'
    image_folder_name = 'glossimage'

    try:
        if request.GET['small_videos'] not in [0,False,'false']:
            video_folder_name+= '_small'
    except KeyError:
        pass

    archive_file_name = '.'.join([first_part_of_file_name,timestamp_part_of_file_name,'zip'])
    archive_file_path = settings.SIGNBANK_PACKAGES_FOLDER + archive_file_name

    video_urls = {os.path.splitext(os.path.basename(gv.videofile.name))[0]:
                      reverse('dictionary:protected_media', args=[gv.small_video(use_name=True) or gv.videofile.name])
                  for gv in GlossVideo.objects.filter(gloss__lemma__dataset=dataset)
                  if os.path.exists(str(gv.videofile.path))
                  and os.path.getmtime(str(gv.videofile.path)) > since_timestamp}
    image_urls = {os.path.splitext(os.path.basename(gv.videofile.name))[0]:
                       reverse('dictionary:protected_media', args=[gv.poster_file()])
                  for gv in GlossVideo.objects.filter(gloss__lemma__dataset=dataset)
                  if os.path.exists(str(gv.videofile.path))
                     and os.path.getmtime(str(gv.videofile.path)) > since_timestamp}

    collected_data = {'video_urls':video_urls,
                      'image_urls':image_urls,
                      'glosses':signbank.tools.get_gloss_data(since_timestamp, dataset)}

    if since_timestamp != 0:
        collected_data['deleted_glosses'] = signbank.tools.get_deleted_gloss_or_media_data('gloss',since_timestamp)
        collected_data['deleted_videos'] = signbank.tools.get_deleted_gloss_or_media_data('video',since_timestamp)
        collected_data['deleted_images'] = signbank.tools.get_deleted_gloss_or_media_data('image',since_timestamp)

    signbank.tools.create_zip_with_json_files(collected_data,archive_file_path)

    response = HttpResponse(FileWrapper(open(archive_file_path,'rb')), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename='+archive_file_name
    return response


def info(request):
    import guardian
    user_datasets = guardian.shortcuts.get_objects_for_user(request.user, 'change_dataset', Dataset)
    user_datasets_names = [dataset.acronym for dataset in user_datasets]

    # Put the default dataset in first position
    if settings.DEFAULT_DATASET_ACRONYM in user_datasets_names:
        user_datasets_names.insert(0, user_datasets_names.pop(user_datasets_names.index(settings.DEFAULT_DATASET_ACRONYM)))

    if user_datasets_names:
        return HttpResponse(json.dumps(user_datasets_names), content_type='application/json')
    else:
        return HttpResponse(json.dumps([settings.LANGUAGE_NAME, settings.COUNTRY_NAME]),
                            content_type='application/json')


def protected_media(request, filename, document_root=WRITABLE_FOLDER, show_indexes=False):

    if not request.user.is_authenticated:

        # If we are not logged in, try to find if this maybe belongs to a gloss that is free to see for everbody?
        (name, ext) = os.path.splitext(os.path.basename(filename))
        if 'handshape' in name:
            # handshape images are allowed to be seen in Show All Handshapes
            pass
        else:
            gloss_pk = int(filename.split('.')[-2].split('-')[-1])

            try:
                if not Gloss.objects.get(pk=gloss_pk).inWeb:
                    return HttpResponse(status=401)
            except Gloss.DoesNotExist:
                return HttpResponse(status=401)

        #If we got here, the gloss was found and in the web dictionary, so we can continue

    filename = os.path.normpath(filename)

    dir_path = WRITABLE_FOLDER
    path = dir_path.encode('utf-8') + filename.encode('utf-8')
    try:
        exists = os.path.exists(path)
    except:
        exists = False
    if not exists:
        # quote the filename instead to resolve special characters in the url
        (head, tail) = os.path.split(filename)
        quoted_filename = quote(tail, safe='')
        quoted_path = os.path.join(dir_path, head, quoted_filename)
        exists = os.path.exists(quoted_path)
        if not exists:
            raise Http404("File does not exist.")
        else:
            filename = quoted_filename
            path = quoted_path

    if not hasattr(settings, 'USE_X_SENDFILE') or settings.USE_X_SENDFILE:
        if filename.split('.')[-1] == 'mp4':
            response = HttpResponse(content_type='video/mp4')
        elif filename.split('.')[-1] == 'png':
            response = HttpResponse(content_type='image/png')
        elif filename.split('.')[-1] == 'jpg':
            response = HttpResponse(content_type='image/jpg')
        else:
            response = HttpResponse()

        response['Content-Disposition'] = 'inline;filename='+filename+';filename*=UTF-8'
        response['X-Sendfile'] = path

        return response

    else:
        from django.views.static import serve
        return serve(request, filename, document_root, show_indexes)

def show_glosses_with_no_lemma(request):

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    glosses_without_lemma = Gloss.objects.filter(lemma=None)
    gloss_tuples = []
    for g in glosses_without_lemma:
        gloss_annotations = AnnotationIdglossTranslation.objects.filter(gloss=g)
        gloss_annotation_languages = [ann.language.name for ann in gloss_annotations]
        language_names = ', '.join(gloss_annotation_languages)
        gloss_tuples.append((g, gloss_annotations, language_names))

    all_datasets = Dataset.objects.all()
    dummies_to_create = []
    for this_dataset in all_datasets:
        dataset_languages_this_dataset = this_dataset.translation_languages.all()
        for lang in dataset_languages_this_dataset:
            dummy_lemma_name = 'DUMMY_LEMMA_' + this_dataset.acronym.replace(' ', '') + '_' + lang.language_code_2char.upper()
            dummy_lemma = LemmaIdgloss.objects.filter(dataset=this_dataset,
                                                      lemmaidglosstranslation__text=dummy_lemma_name)
            if not dummy_lemma.count():
                if this_dataset not in dummies_to_create:
                    dummies_to_create.append(this_dataset)

    for dataset_to_dummy in dummies_to_create:
        dataset_languages_this_dataset = dataset_to_dummy.translation_languages.all()
        new_lemma = LemmaIdgloss(dataset=dataset_to_dummy)
        new_lemma.save()
        for lang in dataset_languages_this_dataset:
            dummy_lemma_name = 'DUMMY_LEMMA_' + dataset_to_dummy.acronym.replace(' ', '') + '_' + lang.language_code_2char.upper()
            dummy_translation = LemmaIdglossTranslation(text=dummy_lemma_name, lemma=new_lemma, language=lang)
            dummy_translation.save()

    dummy_lemma_name = 'DUMMY_LEMMA_'
    dummy_lemmas = LemmaIdgloss.objects.filter(lemmaidglosstranslation__text__icontains=dummy_lemma_name).distinct()
    lemma_choices = []
    for dummy in dummy_lemmas:
        dummy_translations = [t.language.name for t in dummy.lemmaidglosstranslation_set.all()]
        select_string = ', '.join(dummy_translations)
        lemma_choices.append((dummy, dummy.dataset.acronym + ': ' + select_string))

    return render(request, "dictionary/glosses_with_no_lemma.html", {
        'dataset_languages': dataset_languages,
        'selected_datasets': selected_datasets,
        'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface,
        'glosses_without_lemma': gloss_tuples,
        'dummy_lemmas': lemma_choices
    })

@login_required_config
def show_unassigned_glosses(request):
    if request.method == 'POST':
        dataset_select_prefix = "sign-language__"
        for key, new_value in request.POST.items():
            if key.startswith(dataset_select_prefix) and new_value != "":
                try:
                    signlanguage_id = key[len(dataset_select_prefix):]
                    dataset_id = int(new_value)
                    dataset = Dataset.objects.get(pk=int(dataset_id))
                    print("Signlanguage: %s; dataset: %s" % (signlanguage_id, dataset_id))
                    if signlanguage_id == "":
                        glosses_to_be_assigned = Gloss.objects.filter(
                            signlanguage=None,
                            dataset=None
                        )
                    else:
                        glosses_to_be_assigned = Gloss.objects.filter(
                            signlanguage__pk=signlanguage_id,
                            dataset=None
                        )
                    for gloss in glosses_to_be_assigned:
                        gloss.dataset = dataset
                        gloss.save()
                except ObjectDoesNotExist as objectDoesNotExist:
                    print('Assigning glosses to a dataset resulted in an error: ' + objectDoesNotExist.message)

        return HttpResponseRedirect(reverse('show_unassigned_glosses'))
    else:
        from django.db.models import OuterRef, Subquery, Count, Prefetch
        unassigned_glosses = Gloss.objects.filter(
                    lemma__dataset=None,
                    signlanguage=OuterRef('pk')
                ).order_by().values('signlanguage')
        count_unassigned_glosses = unassigned_glosses.annotate(cnt=Count('pk')).values('cnt')
        signlanguages = SignLanguage.objects.prefetch_related(
            Prefetch(
                'dataset_set',
                queryset=Dataset.objects.all(),
                to_attr='datasets'
            )
        ).annotate(
            num_unassigned_glosses=Subquery(
                count_unassigned_glosses,
                output_field=models.IntegerField()
            )
        )

        number_of_unassigned_glosses_without_signlanguage = Gloss.objects.filter(
            lemma__dataset=None,
            signlanguage=None
        ).count()

        all_datasets = Dataset.objects.all()

        return render(request,"dictionary/unassigned_glosses.html", {
                        "signlanguages":signlanguages,
                        "number_of_unassigned_glosses_without_signlanguage":number_of_unassigned_glosses_without_signlanguage,
                        "all_datasets":all_datasets
                      })

from django.db import models

def choice_lists(request):

    selected_datasets = get_selected_datasets_for_user(request.user)
    all_choice_lists = {}

    if 'dataset' in request.GET:
        choices_to_exclude = Dataset.objects.get(acronym=request.GET['dataset']).exclude_choices.all()
    else:
        choices_to_exclude = None

    fields_with_choices = fields_to_fieldcategory_dict()

    for (field, fieldchoice_category) in fields_with_choices.items():
        # Get and save the choice list for this field
        if fieldchoice_category in CATEGORY_MODELS_MAPPING.keys():
            choice_list = CATEGORY_MODELS_MAPPING[fieldchoice_category].objects.all()
        else:
            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)

        if len(choice_list) == 0:
            continue

        all_choice_lists[field] = choicelist_queryset_to_translated_dict(choice_list,
                                                                         choices_to_exclude=choices_to_exclude)

        #Also concatenate the frequencies of all values
        if 'include_frequencies' in request.GET and request.GET['include_frequencies']:
            for choicefield in choice_list:
                machine_value = choicefield.machine_value
                choice_list_field = '_' + str(choicefield.machine_value)
                if fieldchoice_category == 'SemField':
                    null_field = 'semField'
                    filter = 'semField__machine_value__in'
                    value = [machine_value]
                elif fieldchoice_category == 'derivHist':
                    null_field = 'derivHist'
                    filter = 'derivHist__machine_value__in'
                    value = [machine_value]
                else:
                    null_field = field
                    filter = field + '__machine_value'
                    value = machine_value

                if machine_value == 0:
                    frequency_for_field = Gloss.objects.filter(Q(lemma__dataset__in=selected_datasets),
                                                               Q(**{null_field + '__isnull': True}) |
                                                               Q(**{null_field: 0})).count()

                else:
                    frequency_for_field = Gloss.objects.filter(
                        lemma__dataset__in=selected_datasets).filter(**{filter: value}).count()

                if choice_list_field in all_choice_lists[field].keys():
                    all_choice_lists[field][choice_list_field] += ' ['+str(frequency_for_field)+']'

    # Add morphology to choice lists
    all_choice_lists['morphology_role'] = choicelist_queryset_to_translated_dict(
        FieldChoice.objects.filter(field__iexact='MorphologyType'))

    # all_choice_lists['morph_type'] = choicelist_queryset_to_translated_dict(
    #     FieldChoice.objects.filter(field__iexact='MorphemeType'))
    # print(all_choice_lists['morph_type'])
    return HttpResponse(json.dumps(all_choice_lists), content_type='application/json')


def gloss_revision_history(request,gloss_pk):

    gloss = Gloss.objects.get(pk=gloss_pk)

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    if hasattr(settings, 'SHOW_QUERY_PARAMETERS_AS_BUTTON') and settings.SHOW_QUERY_PARAMETERS_AS_BUTTON:
        show_query_parameters_as_button = settings.SHOW_QUERY_PARAMETERS_AS_BUTTON
    else:
        show_query_parameters_as_button = False

    revisions = []
    for revision in GlossRevision.objects.filter(gloss=gloss):
        if revision.field_name in Gloss.get_field_names():
            revision_verbose_fieldname = _(Gloss.get_field(revision.field_name).verbose_name)
        else:
            revision_verbose_fieldname = _(revision.field_name)

        # field name qualification is stored separately here
        # Django was having a bit of trouble translating it when embeded in the field_name string below
        if revision.field_name == 'Tags':
            if revision.old_value:
                # this translation exists in the interface of Gloss Edit View
                delete_command = str(_('delete this tag'))
                field_name_qualification = ' (' + delete_command + ')'
            elif revision.new_value:
                # this translation exists in the interface of Gloss Edit View
                add_command = str(_('Add Tag'))
                field_name_qualification = ' (' + add_command + ')'
            else:
                # this shouldn't happen
                field_name_qualification = ''
        elif revision.field_name == 'Sense':
            if revision.old_value and not revision.new_value:
                # this translation exists in the interface of Gloss Edit View
                delete_command = str(_('Delete'))
                field_name_qualification = ' (' + delete_command + ')'
            elif revision.new_value and not revision.old_value:
                # this translation exists in the interface of Gloss Edit View
                add_command = str(_('Create'))
                field_name_qualification = ' (' + add_command + ')'
            else:
                # this translation exists in the interface of Gloss Edit View
                add_command = str(_('Update'))
                field_name_qualification = ' (' + add_command + ')'
        elif revision.field_name == 'Sentence':
            if revision.old_value and not revision.new_value:
                # this translation exists in the interface of Gloss Edit View
                delete_command = str(_('Delete'))
                field_name_qualification = ' (' + delete_command + ')'
            elif revision.new_value and not revision.old_value:
                # this translation exists in the interface of Gloss Edit View
                add_command = str(_('Create'))
                field_name_qualification = ' (' + add_command + ')'
            else:
                # this translation exists in the interface of Gloss Edit View
                add_command = str(_('Update'))
                field_name_qualification = ' (' + add_command + ')'
        else:
            field_name_qualification = ' (' + revision.field_name + ')'
        revision_dict = {
            'is_tag': revision.field_name == 'Tags',
            'gloss' : revision.gloss,
            'user' : revision.user,
            'time' : revision.time,
            'field_name' : revision_verbose_fieldname,
            'field_name_qualification' : field_name_qualification,
            'old_value' : check_value_to_translated_human_value(revision.field_name, revision.old_value),
            'new_value' : check_value_to_translated_human_value(revision.field_name, revision.new_value) }
        revisions.append(revision_dict)

    return render(request, 'dictionary/gloss_revision_history.html',
                  {'gloss': gloss, 'revisions':revisions,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'active_id': gloss_pk,
                   'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface,
                   'SHOW_QUERY_PARAMETERS_AS_BUTTON': show_query_parameters_as_button
                   })


def find_interesting_frequency_examples(request):

    INTERESTING_FREQUENCY_THRESHOLD = 25

    interesting_gloss_pks = []

    debug_str = ''

    for gloss in Gloss.objects.all():

        speaker_data = gloss.speaker_data()

        if speaker_data['Male'] > 0:
            debug_str += str(speaker_data['Male']) + ' '

        if speaker_data['Male'] + speaker_data['Female'] < INTERESTING_FREQUENCY_THRESHOLD:
            continue

        try:
            variants = gloss.pattern_variants()
        except:
            try:
                variants = gloss.has_variants()
            except:
                variants = []

        if len(variants) == 0:
            continue

        found_interesting_variant = False

        for variant in variants:

            speaker_data = variant.speaker_data()

            if speaker_data['Male'] + speaker_data['Female'] >= INTERESTING_FREQUENCY_THRESHOLD:
                found_interesting_variant = True
                break

        if not found_interesting_variant:
            continue

        interesting_gloss_pks.append(gloss.pk)

        if len(interesting_gloss_pks) > 100: #This prevents this code from running too long
            break

        if len(debug_str) > 1000:
            break

    return HttpResponse(' '.join(['<a href="/dictionary/gloss/'+str(i)+'">'+str(i)+'</a>' for i in interesting_gloss_pks]))

def gif_prototype(request):

    return render(request,'dictionary/gif_prototype.html')


@csrf_exempt
def gloss_api_get_sign_name_and_media_info(request):
    """
    API endpoint for the sign app that returns a json object with all the signs names and urls
    """

    dataset = 0
    max_number_of_results = 100

    # Make sure that other request options then the intended one are blocked
    if request.method not in ('GET', 'POST'):
        return HttpResponseNotAllowed(
                json.dumps({"Error": "Tried anohter request methoded then GET or POST, please only use GET or POST for this endpoint."}),
                content_type="application/json")

    # Get all glosses that are in the given list
    if request.method == 'POST':
        id_list = json.loads(request.body.decode('utf-8'))

        glosses = Gloss.objects \
            .filter(id__in=id_list) \
            .filter(inWeb=True) \
            .order_by('id').distinct()[0:max_number_of_results]

    elif request.method == 'GET':

        # Get the dataset that is used to return the sign of the right signlanguage like NGT
        try:
            dataset = request.GET['dataset']
        except MultiValueDictKeyError:
            return HttpResponseBadRequest(json.dumps({"Error": "No dataset selected"}), content_type="application/json")

        # Try to get the results data for the query. This variable dictates how many results are allowed to be return
        # If the results variable is not set in the GET request return a error
        try:
            max_number_of_results = int(request.GET['results'])
        except MultiValueDictKeyError:
            return HttpResponseBadRequest(json.dumps({"Error": "No amount of search results given"}), content_type="application/json")

        # Get the search item. This is the name of the sign that the user wants to find
        try:
            search = request.GET['search']
        except MultiValueDictKeyError:
            return HttpResponseBadRequest(json.dumps({"Error": "No search term found"}), content_type="application/json")

        # Run the query to get all the gloss data in a list
        glosses = Gloss.objects \
            .filter(inWeb=True) \
            .filter(lemma__lemmaidglosstranslation__text__startswith=search) \
            .filter(lemma__dataset=dataset) \
            .order_by('lemma__lemmaidglosstranslation__text')[0:max_number_of_results]

    response = [
            {
                'id': gloss.id,
                'sign_name': str(gloss),
                'video_url': gloss.get_video_url(),
                'image_url': gloss.get_image_url()}
            for gloss in glosses if gloss.get_video_url()]

    return HttpResponse(json.dumps(response), content_type="application/json")


def import_csv_create_sentences(request):
    user = request.user
    import guardian
    user_datasets = guardian.shortcuts.get_objects_for_user(user, 'change_dataset', Dataset)
    user_datasets_names = [dataset.acronym for dataset in user_datasets]

    selected_datasets = get_selected_datasets_for_user(user)
    dataset_languages = get_dataset_languages(selected_datasets)

    translation_languages_dict = {}
    # this dictionary is used in the template, it maps each dataset to a list of tuples (English name of dataset, language_code_2char)
    for dataset_object in user_datasets:
        translation_languages_dict[dataset_object] = []

        for language in dataset_object.translation_languages.all():
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            language_tuple = (language_name, language.language_code_2char)
            translation_languages_dict[dataset_object].append(language_tuple)

    seen_datasets = []
    seen_dataset_names = []

    encoding_error = False

    uploadform = signbank.dictionary.forms.CSVUploadForm
    changes = []
    error = []
    creation = []
    gloss_already_exists = []
    earlier_creation_same_csv = {}
    earlier_creation_annotationidgloss = {}
    earlier_creation_lemmaidgloss = {}

    # Propose changes
    if len(request.FILES) > 0:

        new_file = request.FILES['file']

        try:
            # files that will fail here include those renamed to .csv which are not csv
            # non UTF-8 encoded files also fail
            csv_text = new_file.read().decode('UTF-8-sig')
        except (UnicodeDecodeError, UnicodeError):
            new_file.seek(0)
            import magic
            magic_file_type = magic.from_buffer(new_file.read(2048), mime=True)

            if magic_file_type == 'text/plain':
                feedback_message = _('Unrecognised text encoding. Please export your file to UTF-8 format using e.g. LibreOffice.')
            else:
                feedback_message = _('Unrecognised format in selected CSV file.')

            messages.add_message(request, messages.ERROR, feedback_message)

            return render(request, 'dictionary/import_csv_create_sentences.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'creation': creation,
                           'gloss_already_exists': gloss_already_exists,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        fatal_error = False
        csv_lines = re.compile('[\r\n]+').split(csv_text)  # split the csv text on any combination of newline characters

        # the following code allows for specifying a column delimiter in the import_csv_create_sentences.html template
        if 'delimiter' in request.POST:
            delimiter_radio = request.POST['delimiter']
            if delimiter_radio == 'tab':
                delimiter = '\t'
            elif delimiter_radio == 'comma':
                delimiter = ','
            elif delimiter_radio == 'semicolon':
                delimiter = ';'
            else:
                # this should not occur
                # perhaps only if the user is trying to fiddle without using the template
                # set to template default, print message for Admin
                print('Missing template default for delimiter_radio in import_csv_create_sentences.html')
                delimiter = ','
                delimiter_radio = 'comma'
        else:
            # this should not occur
            # perhaps only if the user is trying to fiddle without using the template
            # set to template default, print message for Admin
            print('Missing template default for delimiter_radio in import_csv_create_sentences.html')
            delimiter = ','
            delimiter_radio = 'comma'

        keys_found, extra_keys, csv_header, csv_body = split_csv_lines_sentences_header_body(dataset_languages, csv_lines,
                                                                                   delimiter)

        if not keys_found:
            # this is intended to assist the user in the case that a wrong file was selected
            feedback_message = _('The required column headers are missing.')
            messages.add_message(request, messages.ERROR, feedback_message)
            return render(request, 'dictionary/import_csv_create_sentences.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        if extra_keys:
            # this is intended to assist the user in the case that a wrong file was selected
            feedback_message = _('Extra columns were found.')
            messages.add_message(request, messages.ERROR, feedback_message)
            return render(request, 'dictionary/import_csv_create_sentences.html',
                          {'form': uploadform, 'stage': 0, 'changes': changes,
                           'error': error,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'translation_languages_dict': translation_languages_dict,
                           'seen_datasets': seen_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

        # create a template for an empty row with the desired number of columns
        empty_row = [''] * len(csv_header)
        for nl, line in enumerate(csv_body):
            if len(line) == 0:
                # this happens at the end of the file
                continue
            values = csv.reader([line], delimiter=delimiter).__next__()
            if values == empty_row:
                continue

            # construct value_dict for row
            value_dict = {}
            for nv, value in enumerate(values):
                if nv >= len(csv_header):
                    # this has already been checked above
                    # it's here to avoid needing an exception on the subscript [nv]
                    continue
                value_dict[csv_header[nv]] = value

            # 'Dataset' in value_dict keys, checked above
            dataset_name = value_dict['Dataset'].strip()

            # Check whether the user may change the dataset of the current row
            if dataset_name not in seen_dataset_names:
                if seen_datasets:
                    # already seen a dataset
                    # this is a different dataset
                    e3 = 'Row '+str(nl + 1) + ': A different dataset is mentioned.'
                    e4 = 'You can only create glosses for one dataset at a time.'
                    e5 = 'To create glosses in multiple datasets, use a separate CSV file for each dataset.'
                    error.append(e3)
                    error.append(e4)
                    error.append(e5)
                    break

                # only process a dataset_name once for the csv file being imported
                # catch possible empty values for dataset, primarily for pretty printing error message
                if dataset_name in ['', None, 0, 'NULL']:
                    e_dataset_empty = 'Row '+str(nl + 1) + ': The Dataset is missing.'
                    error.append(e_dataset_empty)
                    break
                try:
                    dataset = Dataset.objects.get(acronym=dataset_name)
                except ObjectDoesNotExist:
                    # An error message should be returned here, the dataset does not exist
                    e_dataset_not_found = 'Row '+str(nl + 1) + ': Dataset %s' % value_dict['Dataset'].strip() + ' does not exist.'
                    error.append(e_dataset_not_found)
                    break

                if dataset_name not in user_datasets_names:
                    e3 = 'Row '+str(nl + 1) + ': You are not allowed to change dataset %s.' % value_dict['Dataset'].strip()
                    error.append(e3)
                    break
                if dataset not in selected_datasets:
                    e3 = 'Row '+str(nl + 1) + ': Please select the dataset %s.' % value_dict['Dataset'].strip()
                    error.append(e3)
                    break
                if seen_datasets:
                    # already seen a dataset
                    if dataset in seen_datasets:
                        pass
                    else:
                        # seen more than one dataset
                        # e4 = 'You are attempting to modify two datasets.'

                        e4 = 'You can only create sentences for one dataset at a time.'
                        e5 = 'To create sentences in multiple datasets, use a separate CSV file for each dataset.'
                        error.append(e4)
                        error.append(e5)
                        break

                else:
                    seen_datasets.append(dataset)
                    seen_dataset_names.append(dataset_name)

            translation_languages = dataset.translation_languages.all()

            sentence_translations = dict()
            # check sentence translations
            for language in translation_languages:
                language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                column_name = "Example Sentences (%s)" % language_name
                sentence_text = value_dict[column_name].strip()
                # also stores empty values
                sentence_translations[language] = sentence_text

            # put creation of value_dict for the new gloss inside an exception to catch any unexpected errors
            # errors are kept track of as user feedback, but the code needs to be safe
            try:
                (new_gloss, already_exists, error_create, earlier_creation_same_csv, earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss) \
                    = create_sentence_from_valuedict(value_dict,dataset,nl, earlier_creation_same_csv, earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss)
            except (KeyError, ValueError):
                print('import csv create sentences: got this far in processing loop before exception in row ', str(nl+1))
                break
            if len(error_create):
                errors_found_string = '\n'.join(error_create)
                error.append(errors_found_string)
            else:
                creation += new_gloss
            # whether or not glosses mentioned in the csv file already exist is accumulated in gloss_already_exists
            # one version of the template also shows these with the errors, so the user might remove extra data
            # from the csv to reduce its size
            gloss_already_exists += already_exists
            continue

        stage = 1

    # Do changes
    elif len(request.POST) > 0:

        glosses_to_create = dict()

        for key, new_value in request.POST.items():

            # obtain tuple values for each proposed gloss
            # pk is the row number in the import file!
            try:
                pk, fieldname = key.split('.')

                if pk not in glosses_to_create.keys():
                    glosses_to_create[pk] = dict()
                glosses_to_create[pk][fieldname] = new_value

            except ValueError:
                # when the database token csrfmiddlewaretoken is passed, there is no dot
                continue

        # these should be error free based on the django template import_csv_create_sentences.html
        for row in glosses_to_create.keys():
            gloss_id = glosses_to_create[row]['gloss_pk']

            try:
                gloss = Gloss.objects.get(id=int(gloss_id))
            except ObjectDoesNotExist:
                # this is an error, this should have already been caught
                e1 = 'Gloss not found: ' + gloss_id
                error.append(e1)
                continue

            dataset_acronym = glosses_to_create[row]['dataset']

            try:
                dataset = Dataset.objects.get(acronym=dataset_acronym)
            except ObjectDoesNotExist:
                # this is an error, this should have already been caught
                e1 = 'Dataset not found: ' + dataset_acronym
                error.append(e1)
                continue

            csv_create_sentence(request, gloss, dataset_languages, glosses_to_create[row], create=True)

        stage = 2

    # Show uploadform
    else:

        stage = 0

    return render(request,'dictionary/import_csv_create_sentences.html',{'form':uploadform,'stage':stage,'changes':changes,
                                                        'creation':creation,
                                                        'gloss_already_exists':gloss_already_exists,
                                                        'error':error,
                                                        'dataset_languages':dataset_languages,
                                                        'selected_datasets':selected_datasets,
                                                        'translation_languages_dict': translation_languages_dict,
                                                        'seen_datasets': seen_datasets,
                                                        'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})
