from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader
from django.http import Http404
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from tagging.models import Tag, TaggedItem
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import urlquote
from collections import OrderedDict

import os
import shutil
import csv
import time
import re

from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from signbank.feedback.models import *
from signbank.dictionary.update import update_keywords, update_signlanguage, update_dialect, subst_relations, subst_foreignrelations, \
    update_sequential_morphology, update_simultaneous_morphology, update_tags, update_blend_morphology, subst_notes
from signbank.dictionary.adminviews import choicelist_queryset_to_translated_dict
import signbank.dictionary.forms

from signbank.video.forms import VideoUploadForGlossForm
from signbank.tools import *
from signbank.tools import save_media, compare_valuedict_to_gloss, MachineValueNotFoundError
from signbank.tools import get_selected_datasets_for_user, gloss_from_identifier

import signbank.settings
from signbank.settings.base import WRITABLE_FOLDER, URL
from django.utils.translation import override

from urllib.parse import urlencode, urlparse
from wsgiref.util import FileWrapper
import datetime as DT



def login_required_config(f):
    """like @login_required if the ALWAYS_REQUIRE_LOGIN setting is True"""

    if settings.ALWAYS_REQUIRE_LOGIN:
        return login_required(f)
    else:
        return f



@login_required_config
def index(request):
    """Default view showing a browse/search entry
    point to the dictionary"""


    return render(request,"dictionary/search_result.html",
                              {'form': UserSignSearchForm(),
                               'language': settings.LANGUAGE_NAME,
                               'query': ''})


STATE_IMAGES = {'auslan_all': "images/maps/allstates.gif",
                'auslan_nsw_act_qld': "images/maps/nsw-act-qld.gif",
                'auslan_nsw': "images/maps/nsw.gif",
                'auslan_nt':  "images/maps/nt.gif",
                'auslan_qld': "images/maps/qld.gif",
                'auslan_sa': "images/maps/sa.gif",
                'auslan_tas': "images/maps/tas.gif",
                'auslan_south': "images/maps/vic-wa-tas-sa-nt.gif",
                'auslan_vic': "images/maps/vic.gif",
                'auslan_wa': "images/maps/wa.gif",
                }

def map_image_for_dialects(dialects):
    """Get the right map image for this dialect set


    Relies on database contents, which is bad. This should
    be in the database
    """
    # we only work for Auslan just now
    dialects = dialects.filter(signlanguage__name__exact="Auslan")

    if len(dialects) == 0:
        return

    # all states
    if dialects.filter(name__exact="Australia Wide"):
        return STATE_IMAGES['auslan_all']

    if dialects.filter(name__exact="Southern Dialect"):
        return STATE_IMAGES['auslan_south']

    if dialects.filter(name__exact="Northern Dialect"):
        return STATE_IMAGES['auslan_nsw_act_qld']

    if dialects.filter(name__exact="New South Wales"):
        return STATE_IMAGES['auslan_nsw']

    if dialects.filter(name__exact="Queensland"):
        return STATE_IMAGES['auslan_qld']

    if dialects.filter(name__exact="Western Australia"):
        return STATE_IMAGES['auslan_wa']

    if dialects.filter(name__exact="South Australia"):
        return STATE_IMAGES['auslan_sa']

    if dialects.filter(name__exact="Tasmania"):
        return STATE_IMAGES['auslan_tas']

    if dialects.filter(name__exact="Victoria"):
        return STATE_IMAGES['auslan_vic']

    return None


@login_required_config
def word(request, keyword, n):
    """View of a single keyword that may have more than one sign"""

    n = int(n)

    if 'feedbackmessage' in request.GET:
        feedbackmessage = request.GET['feedbackmessage']
    else:
        feedbackmessage = False

    word = get_object_or_404(Keyword, text=keyword)

    # returns (matching translation, number of matches)
    (trans, total) =  word.match_request(request, n, )

    # and all the keywords associated with this sign
    allkwds = trans.gloss.translation_set.all()

    videourl = trans.gloss.get_video_url()
    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, videourl)):
        videourl = None

    trans.homophones = trans.gloss.relation_sources.filter(role='homophone')

    # work out the number of this gloss and the total number
    gloss = trans.gloss
    if gloss.sn != None:
        if request.user.has_perm('dictionary.search_gloss'):
            glosscount = Gloss.objects.count()
            glossposn = Gloss.objects.filter(sn__lt=gloss.sn).count()+1
        else:
            glosscount = Gloss.objects.filter(inWeb__exact=True).count()
            glossposn = Gloss.objects.filter(inWeb__exact=True, sn__lt=gloss.sn).count()+1
    else:
        glosscount = 0
        glossposn = 0

    # navigation gives us the next and previous signs
    nav = gloss.navigation(request.user.has_perm('dictionary.search_gloss'))

    # the gloss update form for staff

    if request.user.has_perm('dictionary.search_gloss'):
        update_form = GlossModelForm(instance=trans.gloss)
        video_form = VideoUploadForGlossForm(initial={'gloss_id': trans.gloss.pk,
                                                      'redirect': request.path})
    else:
        update_form = None
        video_form = None

    return render(request,"dictionary/word.html",
                              {'translation': trans.translation.text.encode('utf-8'),
                               'viewname': 'words',
                               'definitions': trans.gloss.definitions(),
                               'allkwds': allkwds,
                               'n': n,
                               'total': total,
                               'matches': range(1, total+1),
                               'navigation': nav,
                               'dialect_image': map_image_for_dialects(gloss.dialect.all()),
                               # lastmatch is a construction of the url for this word
                               # view that we use to pass to gloss pages
                               # could do with being a fn call to generate this name here and elsewhere
                               'lastmatch': trans.translation.text.encode('utf-8')+"-"+str(n),
                               'videofile': videourl,
                               'update_form': update_form,
                               'videoform': video_form,
                               'gloss': gloss,
                               'glosscount': glosscount,
                               'glossposn': glossposn,
                               'feedback' : True,
                               'feedbackmessage': feedbackmessage,
                               'tagform': TagUpdateForm(),
                               'annotation_idgloss': {},
                               'SIGN_NAVIGATION' : settings.SIGN_NAVIGATION,
                               'DEFINITION_FIELDS' : settings.DEFINITION_FIELDS})

def gloss(request, glossid):
    """View of a gloss - mimics the word view, really for admin use
       when we want to preview a particular gloss"""

    if 'feedbackmessage' in request.GET:
        feedbackmessage = request.GET['feedbackmessage']
    else:
        feedbackmessage = False

    # we should only be able to get a single gloss, but since the URL
    # pattern could be spoofed, we might get zero or many
    # so we filter first and raise a 404 if we don't get one
    try:
        gloss = Gloss.objects.get(id=glossid)
    except ObjectDoesNotExist:
        raise Http404

    if not(request.user.has_perm('dictionary.search_gloss') or gloss.inWeb):
        return render(request,"dictionary/word.html",{'feedbackmessage': 'You are not allowed to see this sign.'})

    allkwds = gloss.translation_set.all()
    if len(allkwds) == 0:
        trans = Translation()
    else:
        trans = allkwds[0]

    videourl = gloss.get_video_url()
    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, videourl)):
        videourl = None

    if gloss.sn != None:
        if request.user.has_perm('dictionary.search_gloss'):
            glosscount = Gloss.objects.count()
            glossposn = Gloss.objects.filter(sn__lt=gloss.sn).count()+1
        else:
            glosscount = Gloss.objects.filter(inWeb__exact=True).count()
            glossposn = Gloss.objects.filter(inWeb__exact=True, sn__lt=gloss.sn).count()+1
    else:
        glosscount = 0
        glossposn = 0

    # navigation gives us the next and previous signs
    nav = gloss.navigation(request.user.has_perm('dictionary.search_gloss'))

    # the gloss update form for staff
    update_form = None

    if request.user.has_perm('dictionary.search_gloss'):
        update_form = GlossModelForm(instance=gloss)
        video_form = VideoUploadForGlossForm(initial={'gloss_id': gloss.pk,
                                                      'redirect': request.get_full_path()})
    else:
        update_form = None
        video_form = None


    # Put annotation_idgloss per language in the context
    annotation_idgloss = {}
    if gloss.dataset:
        for language in gloss.dataset.translation_languages.all():
            annotation_idgloss[language] = gloss.annotationidglosstranslation_set.filter(language=language)
    else:
        language = Language.objects.get(id=get_default_language_id())
        annotation_idgloss[language] = gloss.annotationidglosstranslation_set.filter(language=language)


    # get the last match keyword if there is one passed along as a form variable
    if 'lastmatch' in request.GET:
        lastmatch = request.GET['lastmatch']
        if lastmatch == "None":
            lastmatch = False
    else:
        lastmatch = False

    return render(request,"dictionary/word.html",
                              {'translation': trans,
                               'definitions': gloss.definitions(),
                               'allkwds': allkwds,
                               'dialect_image': map_image_for_dialects(gloss.dialect.all()),
                               'lastmatch': lastmatch,
                               'videofile': videourl,
                               'viewname': word,
                               'feedback': None,
                               'gloss': gloss,
                               'glosscount': glosscount,
                               'glossposn': glossposn,
                               'navigation': nav,
                               'update_form': update_form,
                               'videoform': video_form,
                               'tagform': TagUpdateForm(),
                               'feedbackmessage': feedbackmessage,
                               'annotation_idgloss': annotation_idgloss,
                               'SIGN_NAVIGATION' : settings.SIGN_NAVIGATION,
                               'DEFINITION_FIELDS' : settings.DEFINITION_FIELDS})



@login_required_config
def search(request):
    """Handle keyword search form submission"""

    form = UserSignSearchForm(request.GET.copy())

    if form.is_valid():

        glossQuery = form.cleaned_data['glossQuery']
        # Issue #153: make sure + and - signs are translated correctly into the search URL
        glossQuery = urlquote(glossQuery)
        term = form.cleaned_data['query']
        # Issue #153: do the same with the Translation, encoded by 'query'
        term = urlquote(term)

        return HttpResponseRedirect('../../signs/search/?search='+glossQuery+'&keyword='+term)

def keyword_value_list(request, prefix=None):
    """View to generate a list of possible values for
    a keyword given a prefix."""


    kwds = Keyword.objects.filter(text__startswith=prefix)
    kwds_list = [k.text for k in kwds]
    return HttpResponse("\n".join(kwds_list), content_type='text/plain')


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

    return render_to_response("dictionary/missingvideo.html",
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
    out = '<p>Imported</p><ul>'
    overwritten_files = '<p>Of these files, these were overwritten</p><ul>'
    errors = []

    if video:
        import_folder = settings.VIDEOS_TO_IMPORT_FOLDER
        goal_directory = settings.GLOSS_VIDEO_DIRECTORY
    else:
        import_folder = settings.IMAGES_TO_IMPORT_FOLDER
        goal_directory = settings.GLOSS_IMAGE_DIRECTORY

    print("Import folder: %s" % import_folder)

    for dataset_folder_name in [name for name in os.listdir(import_folder) if os.path.isdir(os.path.join(import_folder, name))]:
        # Check whether the folder name is equal to a dataset name
        print("Dataset folder name: %s " % dataset_folder_name)
        dataset = Dataset.objects.get(name=dataset_folder_name)
        if not dataset:
            continue

        dataset_folder_path = os.path.join(import_folder, dataset_folder_name)
        for lang3code_folder_name in [name for name in os.listdir(dataset_folder_path) if os.path.isdir(os.path.join(dataset_folder_path, name))]:
            # Check whether the folder name is equal to a three letter code for language of the dataset at hand
            print("Lang3code folder name: %s " % lang3code_folder_name)
            languages = dataset.translation_languages.filter(language_code_3char=lang3code_folder_name)
            if languages:
                language = languages[0]
            else:
                continue

            lang3code_folder_path = os.path.join(dataset_folder_path, lang3code_folder_name) + "/"
            for filename in os.listdir(lang3code_folder_path):

                (filename_without_extension, extension) = os.path.splitext(filename)
                extension = extension[1:]  # Remove the dot

                try:
                    glosses = Gloss.objects.filter(dataset=dataset, annotationidglosstranslation__language=language,
                                                 annotationidglosstranslation__text__exact=filename_without_extension)
                    if glosses:
                        gloss = glosses[0]
                    else:
                        errors.append(
                            'Failed at ' + filename + '. Could not find ' + filename_without_extension + ' (it should be a gloss ID).')
                        continue
                except ObjectDoesNotExist:
                    errors.append('Failed at '+filename+'. Could not find '+filename_without_extension+' (it should be a gloss ID).')
                    continue

                default_annotationidgloss = get_default_annotationidglosstranslation(gloss)

                overwritten, was_allowed = save_media(lang3code_folder_path,lang3code_folder_name,
                                                      settings.WRITABLE_FOLDER+goal_directory+'/',gloss,extension)

                if not was_allowed:
                    errors.append('Failed to move media file for '+default_annotationidgloss+
                                  '. Either the source could not be read or the destination could not be written.')
                    continue

                out += '<li>'+filename+'</li>'

                # If it is a video also extract a still image and generate a thumbnail version
                if video:
                    annotation_id = default_annotationidgloss
                    destination_folder = settings.WRITABLE_FOLDER+goal_directory+'/'+annotation_id[:2]+'/'
                    video_filename = annotation_id+'-' + str(gloss.pk) + '.' + extension
                    video_filepath_small = destination_folder + annotation_id+'-' + str(gloss.pk) + '_small.' + extension

                    try:
                        print("Trying to resize video " + destination_folder+video_filename)
                        from CNGT_scripts.python.resizeVideos import VideoResizer
                        from signbank.settings.server_specific import FFMPEG_PROGRAM
                        resizer = VideoResizer([destination_folder+video_filename], FFMPEG_PROGRAM, 180, 0, 0)
                        resizer.run()
                    except ImportError as i:
                        print(i.message)
                    except IOError as io:
                        print(io.message)

                    # Issue #255: generate still image
                    try:
                        print("Trying to generate still images for " + destination_folder+video_filename)
                        from signbank.tools import generate_still_image
                        generate_still_image(annotation_id[:2],
                                             destination_folder,
                                             video_filename)
                    except ImportError as i:
                        print(i.message)

                if overwritten:
                    overwritten_files += '<li>'+filename+'</li>'

    overwritten_files += '</ul>'
    out += '</ul>'+overwritten_files

    if len(errors) > 0:
        out += '<p>Errors</p><ul>'

        for error in errors:
            out += '<li>'+error+'</li>'

        out += '</ul>'

    return HttpResponse(out)

def import_other_media(request):

    errors = []

    #First do some checks
    if not os.path.isfile(settings.OTHER_MEDIA_TO_IMPORT_FOLDER+'index.csv'):
        errors.append('The required file index.csv is not present')
    else:

        for n,row in enumerate(csv.reader(open(settings.OTHER_MEDIA_TO_IMPORT_FOLDER+'index.csv'))):

            #Skip the header
            if n == 0:
                if row == ['Idgloss','filename','type','alternative_gloss']:
                    continue
                else:
                    errors.append('The header of index.csv is not Idgloss,filename,type,alternative_gloss')
                    continue

            #Create an other video for this
            try:
                idgloss, file_name, other_media_type, alternative_gloss = row
            except ValueError:
                errors.append('Line '+str(n)+' does not seem to have the correct amount of items')
                continue

            for field_choice in FieldChoice.objects.filter(field='OtherMediaType'):
                if field_choice.english_name == other_media_type:
                    other_media_type_machine_value = field_choice.machine_value

            parent_gloss = Gloss.objects.filter(idgloss=idgloss)[0]

            other_media = OtherMedia()
            other_media.parent_gloss = parent_gloss
            other_media.alternative_gloss = alternative_gloss
            other_media.path = settings.STATIC_URL+'othermedia/'+str(parent_gloss.pk)+'/'+file_name

            try:
                other_media.type = other_media_type_machine_value
            except UnboundLocalError:
                pass

            #Copy the file
            goal_folder = settings.OTHER_MEDIA_DIRECTORY+str(parent_gloss.pk)+'/'

            try:
                os.mkdir(goal_folder)
            except OSError:
                pass #Do nothing if the folder exists already

            source = settings.OTHER_MEDIA_TO_IMPORT_FOLDER+file_name

            try:
                shutil.copyfile(source,goal_folder+file_name)
            except IOError:
                errors.append('File '+source+' not present')

            #Copy at the end, so it only goes through if there was no crash before
            other_media.save()

            try:
                os.remove(source)
            except OSError:
                pass

    if len(errors) == 0:
        return HttpResponse('OK')
    else:
        output = '<p>Errors</p><ul>'

        for error in errors:
            output += '<li>'+error+'</li>'

        output += '</ul>'

        return HttpResponse(output)

def try_code(request):

    """A view for the developer to try out things"""

    return render(request,'dictionary/try.html',{})

def import_authors(request):

    """In a few cases the authors were delivered separately; this imports a json file and adds it to the correct glossess"""

    import json

    JSON_FILE_LOCATION = '/scratch2/www/ASL-signbank/repo/NGT-signbank/signbank/dictionary/migrations/asl_authors.json'
    author_data = json.load(open(JSON_FILE_LOCATION))
    result = ''

    for gloss in Gloss.objects.all():

        #Try to find an author for this gloss
        try:
            author_names = author_data[gloss.idgloss]
        except KeyError:
            continue

        for author_name in author_names:
            author = User.objects.filter(username=author_name)[0]
            result += str(author)

            gloss.creator.add(author)

    return HttpResponse('OKS')

# this method is called from the Signbank menu bar
def add_new_sign(request):
    context = {}

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    context['dataset_languages'] = dataset_languages
    context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix
    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = False
    if 'last_used_dataset' in request.session.keys():
        context['add_gloss_form'] = GlossCreateForm(request.GET, languages=dataset_languages, user=request.user, last_used_dataset=request.session['last_used_dataset'])
    else:
        context['add_gloss_form'] = GlossCreateForm(request.GET, languages=dataset_languages, user=request.user, last_used_dataset=None)

    return render(request,'dictionary/add_gloss.html',context)


@login_required_config
def search_morpheme(request):
    """Handle morpheme search form submission"""

    form = UserMorphemeSearchForm(request.GET.copy())

    if form.is_valid():

        morphQuery = form.cleaned_data['morphQuery']
        # Issue #153: make sure + and - signs are translated correctly into the search URL
        morphQuery = urlquote(morphQuery)
        term = form.cleaned_data['query']
        # Issue #153: do the same with the Translation, encoded by 'query'
        term = urlquote(term)

        return HttpResponseRedirect('../../morphemes/search/?search='+morphQuery+'&keyword='+term)

def add_new_morpheme(request):

    oContext = {}

    # Add essential information to the context
    oChoiceLists = {}
    oContext['choice_lists'] = oChoiceLists

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    oContext['dataset_languages'] = dataset_languages
    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        oContext['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        oContext['SHOW_DATASET_INTERFACE_OPTIONS'] = False
    if 'last_used_dataset' in request.session.keys():
        oContext['add_morpheme_form'] = MorphemeCreateForm(request.GET, languages=dataset_languages, user=request.user, last_used_dataset=request.session['last_used_dataset'])
    else:
        oContext['add_morpheme_form'] = MorphemeCreateForm(request.GET, languages=dataset_languages, user=request.user, last_used_dataset=None)

    # Get and save the choice list for this field
    field_category = fieldname_to_category('mrpType')
    choice_list = FieldChoice.objects.filter(field__iexact=field_category)

    if len(choice_list) > 0:
        ordered_dict = choicelist_queryset_to_translated_dict(choice_list, request.LANGUAGE_CODE)
        oChoiceLists['mrpType'] = ordered_dict
        oContext['choice_lists'] = oChoiceLists

    oContext['choice_lists'] = json.dumps(oContext['choice_lists'])

    oContext['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

    # Continue
    oBack = render(request,'dictionary/add_morpheme.html', oContext)
    return oBack




def import_csv_create(request):
    user = request.user
    import guardian
    user_datasets = guardian.shortcuts.get_objects_for_user(user,'change_dataset',Dataset)
    user_datasets_names = [ dataset.name for dataset in user_datasets ]

    selected_datasets = get_selected_datasets_for_user(user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    translation_languages_dict = {}
    for dataset_object in user_datasets:
        translation_languages_dict[dataset_object] = []

        for language in dataset_object.translation_languages.all():
            translation_languages_dict[dataset_object].append(language)

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

    fatal_error = False

    uploadform = signbank.dictionary.forms.CSVUploadForm
    changes = []
    error = []
    creation = []
    gloss_already_exists = []
    earlier_creation_same_csv = {}
    earlier_creation_annotationidgloss = {}
    earlier_creation_lemmaidgloss = {}

    columns_to_skip = {field.verbose_name: field for field in Gloss._meta.fields if field.name in FIELDS['frequency']}

    #Propose changes
    if len(request.FILES) > 0:

        csv_text = request.FILES['file'].read().decode('UTF-8')
        csv_lines = re.compile('[\r\n]+').split(csv_text) # split the csv text on any combination of new line characters
        creation = []
        keys = {}   # in case something goes wrong in header row
        for nl, line in enumerate(csv_lines):

            #The first line contains the keys
            if nl == 0:
                keys = line.strip().split(',')
                num_keys = len(keys)
                continue
            elif len(line) == 0:
                continue

            values = csv.reader([line]).__next__()
            value_dict = {}

            for nv,value in enumerate(values):

                try:
                    if keys[nv]:
                        if keys[nv] in value_dict.keys():
                            e = 'Duplicate header column found: ' + keys[nv]
                            error.append(e)
                            fatal_error = True
                            break
                        if keys[nv] not in columns_to_skip:
                            value_dict[keys[nv]] = value
                    elif value:
                        # empty column header
                        e = 'Row '+str(nl + 1) + ': Extra data found in column without header: ' + value
                        error.append(e)
                        fatal_error = True
                        break
                except IndexError:
                    e = 'Row '+str(nl + 1) + ': Index error in column: ' + str(nv)
                    error.append(e)
                    fatal_error = True
                    break

            if fatal_error:
                break

            if 'Signbank ID' in value_dict:
                e = 'Signbank ID column found.'
                error.append(e)
                fatal_error = True
                break

            # Check whether the user may change the dataset of the current row
            if 'Dataset' in value_dict:
                dataset_name = value_dict['Dataset'].strip()
            else:
                e1 = 'The Dataset column is required.'
                error.append(e1)
                fatal_error = True
                break
            if dataset_name not in seen_dataset_names:
                # catch possible empty values for dataset, primarily for pretty printing error message
                if dataset_name == '' or dataset_name == None or dataset_name == 0 or dataset_name == 'NULL':
                    e_dataset_empty = 'Row '+str(nl + 1) + ': The Dataset is missing.'
                    error.append(e_dataset_empty)
                    break
                try:
                    dataset = Dataset.objects.get(name=dataset_name)
                except:
                    # An error message should be returned here, the dataset does not exist
                    e_dataset_not_found = 'Row '+str(nl + 1) + ': Dataset %s' % value_dict['Dataset'].strip() + ' does not exist.'
                    error.append(e_dataset_not_found)
                    fatal_error = True
                    break

                if dataset_name not in user_datasets_names:
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
                        # e4 = 'You are attempting to modify two datasets.'

                        e4 = 'You can only create glosses for one dataset at a time.'
                        e5 = 'To create glosses in multiple datasets, use a separate CSV file for each dataset.'
                        error.append(e4)
                        error.append(e5)
                        fatal_error = True
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
                        lemma_column_name = "Lemma ID Gloss (%s)" % language.name_en
                        required_columns.append(lemma_column_name)
                        if lemma_column_name not in value_dict:
                            e1 = 'To create glosses in dataset ' + dataset_name + ', column ' + lemma_column_name + ' is required.'
                            error.append(e1)
                        annotation_column_name = "Annotation ID Gloss (%s)" % language.name_en
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
                        fatal_error = True
                        break


            if fatal_error:
                break

            # The Lemma ID Gloss may already exist.
            lemmaidglosstranslations = {}
            contextual_error_messages_lemmaidglosstranslations = []
            for language in dataset.translation_languages.all():
                column_name = "Lemma ID Gloss (%s)" % language.name_en
                lemma_idgloss_value = value_dict[column_name].strip()
                # also stores empty values
                lemmaidglosstranslations[language] = lemma_idgloss_value

            # if we get to here, the dataset and required permissions are okay.
            # check that the required columns are available, and check that
            # values are present in the row for these column
            # Checks if all columns for creating a gloss are there.
            fatal_error = False
            row_error = False

            existing_lemmas = []
            for language, term in lemmaidglosstranslations.items():
                try:
                    existing_lemmas.append(LemmaIdglossTranslation.objects.get(lemma__dataset=dataset,
                                                                               language=language,
                                                                               text=term).lemma)
                    help = 'Row ' + str(nl + 1) + ": Existing Lemma ID Gloss (" + language.name_en + '): ' + term
                    contextual_error_messages_lemmaidglosstranslations.append(help)
                except ObjectDoesNotExist as e:
                    if term:
                        other_language_for_term = LemmaIdgloss.objects.filter(dataset=dataset,
                                                                              lemmaidglosstranslation__text=term)
                        if other_language_for_term and lemmaidglosstranslations[language]:
                            help = 'Row ' + str(nl + 1) + ': Wrong lemma translation for Lemma ID Gloss (' + language.name_en + '): ' + term
                            row_error = True
                            contextual_error_messages_lemmaidglosstranslations.append(help)
                        else:
                            help = 'Row ' + str(nl + 1) + ': New Lemma ID Gloss (' + language.name_en + '): ' + term
                            contextual_error_messages_lemmaidglosstranslations.append(help)
                    else:
                        row_error = True
                        help = 'Row ' + str(nl + 1) + ': Lemma ID Gloss (' + language.name_en + ') is empty'
                        contextual_error_messages_lemmaidglosstranslations.append(help)
                    # pass
            existing_lemmas_set = set(existing_lemmas)

            if row_error:
                # everything is either new or empty
                # after processing all lemma translations, determine if an existing lemma has an empty translation
                # and matches an empty column
                for (lang, term) in lemmaidglosstranslations.items():
                    for lem in existing_lemmas_set:

                        lem_trans = lem.lemmaidglosstranslation_set.filter(language=lang, text=term)
                        if lem_trans:
                            # the lemma gloss translation matches the column
                            row_error = False
                        else:
                            if term:
                                # no matching translation found
                                row_error = True
                            else:
                                # term is empty and lemma has empty translation, it's okay
                                row_error = False

            if row_error:
                # row error is still true if not enough matches were found for existing lemmas
                # there is still a row error
                number_of_new_lemmas = len(re.findall('New', ' '.join(contextual_error_messages_lemmaidglosstranslations)))
                number_of_empty_lemmas = len(re.findall('empty', ' '.join(contextual_error_messages_lemmaidglosstranslations)))
                if number_of_new_lemmas and number_of_empty_lemmas:
                    addendum = 'Row '+str(nl + 1)+': The Lemma translations may refer to different lemmas.'
                    contextual_error_messages_lemmaidglosstranslations.append(addendum)

                error += contextual_error_messages_lemmaidglosstranslations

            if len(existing_lemmas_set) == 1:
                existing_lemma = existing_lemmas[0]
            elif len(existing_lemmas):
                e1 = 'Row '+str(nl + 1)+': To create glosses in dataset ' + dataset_name + \
                     ', the combination of Lemma ID Gloss translations should either refer ' \
                     'to an existing Lemma ID Gloss or make up a completely new Lemma ID gloss.'
                fatal_error = True
                error.append(e1)
                if contextual_error_messages_lemmaidglosstranslations:
                    number_of_existing_lemmas = len(re.findall('Existing', ' '.join(contextual_error_messages_lemmaidglosstranslations)))
                    if number_of_existing_lemmas > 1:
                        addendum = 'The Lemma translations refer to different lemmas.'
                        contextual_error_messages_lemmaidglosstranslations.append(addendum)
                    error += contextual_error_messages_lemmaidglosstranslations

            # Annotation ID Gloss needs to be checked dynamically for each dataset language.
            for language in dataset.translation_languages.all():
                column_name = "Annotation ID Gloss (%s)" % language.name_en
                if column_name not in value_dict:
                    e1 = 'To create glosses in dataset ' + dataset_name + ', column ' + column_name + ' is required.'
                    fatal_error = True
                    error.append(e1)
                    break

            # break at this level to get out of iteration over csv lines in case of missing column
            if fatal_error:
                break

            (new_gloss, already_exists, error_create, earlier_creation_same_csv, earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss) \
                = create_gloss_from_valuedict(value_dict,dataset,nl, earlier_creation_same_csv, earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss)
            creation += new_gloss
            gloss_already_exists += already_exists
            if len(error_create):
                # more than one error found
                errors_found_string = '\n'.join(error_create)
                error.append(errors_found_string)
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

        # these should be error free based on the django template import_csv.html
        for row in glosses_to_create.keys():
            dataset = glosses_to_create[row]['dataset']

            try:
                dataset_id = Dataset.objects.get(name=dataset)
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
                    # print("Error: {}".format(e))
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
                e1 = 'To create glosses in dataset ' + dataset_id.name + \
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
    user_datasets_names = [ dataset.name for dataset in user_datasets ]

    selected_datasets = get_selected_datasets_for_user(user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    translation_languages_dict = {}
    for dataset_object in user_datasets:
        translation_languages_dict[dataset_object] = []

        for language in dataset_object.translation_languages.all():
            translation_languages_dict[dataset_object].append(language)

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

    fatal_error = False

    uploadform = signbank.dictionary.forms.CSVUploadForm
    changes = []
    error = []
    creation = []
    gloss_already_exists = []
    earlier_updates_same_csv = []
    earlier_updates_lemmaidgloss = {}

    # this is needed in case the user has exported the csv first and not removed the frequency columns
    # this code retrieves the column headers in English
    with override(LANGUAGE_CODE):
        columns_to_skip = {field.verbose_name: field for field in Gloss._meta.fields if field.name in FIELDS['frequency']}

    #Propose changes
    if len(request.FILES) > 0:
        fatal_error = False
        csv_text = request.FILES['file'].read().decode('UTF-8')
        csv_lines = re.compile('[\r\n]+').split(csv_text) # split the csv text on any combination of new line characters
        creation = []
        keys = {}   # in case something goes wrong in header row
        for nl, line in enumerate(csv_lines):

            #The first line contains the keys
            if nl == 0:
                keys = line.strip().split(',')
                num_keys = len(keys)
                continue
            elif len(line) == 0:
                continue

            values = csv.reader([line]).__next__()
            value_dict = {}

            for nv,value in enumerate(values):

                try:
                    if keys[nv]:
                        if keys[nv] in columns_to_skip.keys():
                            continue
                        if keys[nv] in value_dict.keys():
                            e = 'Duplicate header column found: ' + keys[nv]
                            error.append(e)
                            fatal_error = True
                            break
                        value_dict[keys[nv]] = value
                    elif value:
                        # empty column header
                        e = 'Row '+str(nl + 1) + ': Extra data found in column without header: ' + value
                        error.append(e)
                        fatal_error = True
                        break
                except IndexError:
                    e = 'Row '+str(nl + 1) + ': Index error in column: ' + str(nv)
                    error.append(e)
                    fatal_error = True
                    break

            if fatal_error:
                break

            if 'Signbank ID' in value_dict:
                try:
                    pk = int(value_dict['Signbank ID'])
                except ValueError:
                    e = 'Row '+str(nl + 1) + ': Signbank ID must be numerical: ' + str(value_dict['Signbank ID'])
                    error.append(e)
                    fatal_error = True
            else:
                e = 'Signbank ID required to update glosses.'
                error.append(e)
                fatal_error = True

            if fatal_error:
                break

            # Check whether the user may change the dataset of the current row
            if 'Dataset' in value_dict:
                dataset_name = value_dict['Dataset'].strip()
            else:
                e1 = 'The Dataset column is required.'
                error.append(e1)
                fatal_error = True
                break
            if dataset_name not in seen_dataset_names:
                # catch possible empty values for dataset, primarily for pretty printing error message
                if dataset_name == '' or dataset_name == None or dataset_name == 0 or dataset_name == 'NULL':
                    e_dataset_empty = 'Row '+str(nl + 1) + ': The Dataset is missing.'
                    error.append(e_dataset_empty)
                    break
                try:
                    dataset = Dataset.objects.get(name=dataset_name)
                except:
                    # An error message should be returned here, the dataset does not exist
                    e_dataset_not_found = 'Row '+str(nl + 1) + ': Dataset %s' % value_dict['Dataset'].strip() + ' does not exist.'
                    error.append(e_dataset_not_found)
                    fatal_error = True
                    break

                if dataset_name not in user_datasets_names:
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

            if fatal_error:
                break

            # The Lemma ID Gloss may already exist.
            lemmaidglosstranslations = {}
            contextual_error_messages_lemmaidglosstranslations = []
            for language in dataset.translation_languages.all():
                column_name = "Lemma ID Gloss (%s)" % language.name_en
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
                e1 = 'Row '+ str(nl + 1) + ': The Dataset column (' + dataset.name + ') does not correspond to that of the Signbank ID (' \
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
                continue

            try:
                (changes_found, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss) = \
                            compare_valuedict_to_gloss(value_dict,gloss.id,user_datasets_names, nl, earlier_updates_same_csv, earlier_updates_lemmaidgloss)
                changes += changes_found

                if len(errors_found):
                    # more than one error found
                    errors_found_string = '\n'.join(errors_found)
                    error.append(errors_found_string)

            except MachineValueNotFoundError as e:

                e_string = str(e)
                error.append(e_string)
        stage = 1

    #Do changes
    elif len(request.POST) > 0:

        lemmaidglosstranslations_per_gloss = {}
        for key, new_value in request.POST.items():

            try:
                pk, fieldname = key.split('.')

            #In case there's no dot, this is not a value we set at the previous page
            except ValueError:
                # when the database token csrfmiddlewaretoken is passed, there is no dot
                # print('no dot found')
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
                continue   # avoid default field update

            # Updating the annotation idgloss is a special procedure, because it has relations to other parts of the
            # database
            annotation_idgloss_key_prefix = "Annotation ID Gloss ("
            if fieldname.startswith(annotation_idgloss_key_prefix):
                language_name = fieldname[len(annotation_idgloss_key_prefix):-1]
                languages = Language.objects.filter(name_en=language_name)
                if languages:
                    language = languages[0]
                    annotation_idglosses = gloss.annotationidglosstranslation_set.filter(language=language)
                    if annotation_idglosses:
                        annotation_idgloss = annotation_idglosses[0]
                        annotation_idgloss.text = new_value
                        annotation_idgloss.save()
                continue

            # Updating the keywords is a special procedure, because it has relations to other parts of the database
            if fieldname == 'Keywords':
                # The following is necessary to process keywords for multiple languages
                keywords_dict = {}
                for keyword_string in new_value.split(", "):
                    (keyword, language_code_2char) = keyword_string.split(":")
                    if language_code_2char in keywords_dict:
                        keywords_dict[language_code_2char] += ", " + keyword
                    else:
                        keywords_dict[language_code_2char] = keyword
                for language_code_2char, keywords in keywords_dict.items():
                    update_keywords(gloss, "keywords_" + language_code_2char, keywords)
                gloss.save()
                continue

            if fieldname == 'SignLanguages':

                new_human_value_list = [v.strip() for v in new_value.split(',')]

                update_signlanguage(gloss,None,new_human_value_list)
                gloss.save()
                continue

            if fieldname == 'Dialects':

                new_human_value_list = [v.strip() for v in new_value.split(',')]

                update_dialect(gloss,None,new_human_value_list)
                gloss.save()
                continue

            if fieldname == 'Dataset':

                # this has already been checked for existance and permission in the previous step
                # get dataset identifier
                if new_value == 'None':
                    # don't allow the user to erase the current dataset, this should have already been caught
                    print('csv import make changes error: gloss ', gloss.id, ' attempt to set dataset to empty')
                    continue
                else:
                    # the existence of the new dataset should have already been tested
                    new_dataset = Dataset.objects.get(name=new_value)
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

                update_sequential_morphology(gloss,None,new_human_value_list)

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

                #Replace the value for bools
                if fieldname in Gloss._meta.get_fields() and Gloss._meta.get_field(fieldname).__class__.__name__ == 'NullBooleanField':

                    if new_value in ['true','True', 'TRUE']:
                        new_value = True
                    elif new_value == 'None' or new_value == 'Neutral':
                        new_value = None
                    else:
                        new_value = False

                #Remember this for renaming the video later
                if fieldname == 'idgloss':
                    video_path_before = settings.WRITABLE_FOLDER+gloss.get_video_path()

                #The normal change and save procedure
                setattr(gloss,fieldname,new_value)
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

    return render(request,'dictionary/import_csv_update.html',{'form':uploadform,'stage':stage,'changes':changes,
                                                        'creation':creation,
                                                        'gloss_already_exists':gloss_already_exists,
                                                        'error':error,
                                                        'dataset_languages':dataset_languages,
                                                        'selected_datasets':selected_datasets,
                                                        'translation_languages_dict': translation_languages_dict,
                                                        'seen_datasets': seen_datasets,
                                                        'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})



def import_csv(request):
    user = request.user
    import guardian
    user_datasets = guardian.shortcuts.get_objects_for_user(user,'change_dataset',Dataset)
    user_datasets_names = [ dataset.name for dataset in user_datasets ]

    selected_datasets = get_selected_datasets_for_user(user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    translation_languages_dict = {}
    for dataset_object in user_datasets:
        translation_languages_dict[dataset_object] = []

        for language in dataset_object.translation_languages.all():
            translation_languages_dict[dataset_object].append(language)

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

    fatal_error = False

    uploadform = signbank.dictionary.forms.CSVUploadForm
    changes = []
    error = []
    creation = []
    gloss_already_exists = []
    earlier_creation_same_csv = {}
    earlier_creation_annotationidgloss = {}
    earlier_creation_lemmaidgloss = {}
    earlier_updates_same_csv = []
    earlier_updates_lemmaidgloss = {}

    columns_to_skip = {field.verbose_name: field for field in Gloss._meta.fields if field.name in FIELDS['frequency']}

    #Propose changes
    if len(request.FILES) > 0:

        csv_text = request.FILES['file'].read().decode('UTF-8')
        csv_lines = re.compile('[\r\n]+').split(csv_text) # split the csv text on any combination of new line characters
        creation = []
        keys = {}   # in case something goes wrong in header row
        for nl, line in enumerate(csv_lines):

            #The first line contains the keys
            if nl == 0:
                keys = line.strip().split(',')
                num_keys = len(keys)
                continue
            elif len(line) == 0:
                continue

            values = csv.reader([line]).__next__()
            value_dict = {}

            for nv,value in enumerate(values):

                try:
                    if keys[nv]:
                        if keys[nv] in value_dict.keys():
                            e = 'Duplicate header column found: ' + keys[nv]
                            error.append(e)
                            fatal_error = True
                            break
                        if keys[nv] not in columns_to_skip:
                            value_dict[keys[nv]] = value
                    elif value:
                        # empty column header
                        e = 'Row '+str(nl + 1) + ': Extra data found in column without header: ' + value
                        error.append(e)
                        fatal_error = True
                        break
                except IndexError:
                    e = 'Row '+str(nl + 1) + ': Index error in column: ' + nv
                    error.append(e)
                    fatal_error = True
                    break

            if fatal_error:
                break

            creating_glosses = True
            if 'Signbank ID' in value_dict:
                creating_glosses = False
                try:
                    pk = int(value_dict['Signbank ID'])
                except ValueError:
                    e = 'Row '+str(nl + 1) + ': Signbank ID must be numerical: ' + str(value_dict['Signbank ID'])
                    error.append(e)
                    fatal_error = True
                    break

            # Check whether the user may change the dataset of the current row
            if 'Dataset' in value_dict:
                dataset_name = value_dict['Dataset'].strip()
            else:
                e1 = 'The Dataset column is required.'
                error.append(e1)
                fatal_error = True
                break
            if dataset_name not in seen_dataset_names:
                # catch possible empty values for dataset, primarily for pretty printing error message
                if dataset_name == '' or dataset_name == None or dataset_name == 0 or dataset_name == 'NULL':
                    e_dataset_empty = 'Row '+str(nl + 1) + ': The Dataset is missing.'
                    error.append(e_dataset_empty)
                    break
                try:
                    dataset = Dataset.objects.get(name=dataset_name)
                except:
                    # An error message should be returned here, the dataset does not exist
                    e_dataset_not_found = 'Row '+str(nl + 1) + ': Dataset %s' % value_dict['Dataset'].strip() + ' does not exist.'
                    error.append(e_dataset_not_found)
                    fatal_error = True
                    break

                if dataset_name not in user_datasets_names:
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
                        # e4 = 'You are attempting to modify two datasets.'
                        if creating_glosses:
                            e4 = 'You can only create glosses for one dataset at a time.'
                            e5 = 'To create glosses in multiple datasets, use a separate CSV file for each dataset.'
                            error.append(e4)
                            error.append(e5)
                            fatal_error = True
                            break
                        else:
                            seen_datasets.append(dataset)
                            seen_dataset_names.append(dataset_name)
                else:
                    seen_datasets.append(dataset)
                    seen_dataset_names.append(dataset_name)

                    # saw the first dataset
                    # if creating glosses
                    # check the required columns for translations
                    # and make sure there are no extra columns which will be ignored
                    if creating_glosses:

                        number_of_translation_languages_for_dataset = len(translation_languages_dict[dataset])
                        # there should be columns for Dataset + Lemma ID Gloss per dataset + Annotation ID Gloss per dataset
                        number_of_required_columns = 1 + 2 * number_of_translation_languages_for_dataset
                        required_columns = ['Dataset']
                        for language in dataset.translation_languages.all():
                            lemma_column_name = "Lemma ID Gloss (%s)" % language.name_en
                            required_columns.append(lemma_column_name)
                            if lemma_column_name not in value_dict:
                                e1 = 'To create glosses in dataset ' + dataset_name + ', column ' + lemma_column_name + ' is required.'
                                error.append(e1)
                            annotation_column_name = "Annotation ID Gloss (%s)" % language.name_en
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
                            fatal_error = True
                            break


            if fatal_error:
                break

            # The Lemma ID Gloss may already exist.
            lemmaidglosstranslations = {}
            contextual_error_messages_lemmaidglosstranslations = []
            for language in dataset.translation_languages.all():
                column_name = "Lemma ID Gloss (%s)" % language.name_en
                lemma_idgloss_value = value_dict[column_name].strip()
                # also stores empty values
                lemmaidglosstranslations[language] = lemma_idgloss_value

            # if we get to here, the dataset and required permissions are okay.
            if creating_glosses:
                # check that the required columns are available, and check that
                # values are present in the row for these column
                # Checks if all columns for creating a gloss are there.
                fatal_error = False
                row_error = False

                existing_lemmas = []
                for language, term in lemmaidglosstranslations.items():
                    try:
                        existing_lemmas.append(LemmaIdglossTranslation.objects.get(lemma__dataset=dataset,
                                                                                   language=language,
                                                                                   text=term).lemma)
                        help = 'Row ' + str(nl + 1) + ": Existing Lemma ID Gloss (" + language.name_en + '): ' + term
                        contextual_error_messages_lemmaidglosstranslations.append(help)
                    except ObjectDoesNotExist as e:
                        if term:
                            other_language_for_term = LemmaIdgloss.objects.filter(dataset=dataset,
                                                                                  lemmaidglosstranslation__text=term)
                            if other_language_for_term and lemmaidglosstranslations[language]:
                                help = 'Row ' + str(nl + 1) + ': Wrong lemma translation for Lemma ID Gloss (' + language.name_en + '): ' + term
                                row_error = True
                                contextual_error_messages_lemmaidglosstranslations.append(help)
                            else:
                                help = 'Row ' + str(nl + 1) + ': New Lemma ID Gloss (' + language.name_en + '): ' + term
                                contextual_error_messages_lemmaidglosstranslations.append(help)
                        else:
                            row_error = True
                            help = 'Row ' + str(nl + 1) + ': Lemma ID Gloss (' + language.name_en + ') is empty'
                            contextual_error_messages_lemmaidglosstranslations.append(help)
                        # pass
                existing_lemmas_set = set(existing_lemmas)

                if row_error:
                    # everything is either new or empty
                    # after processing all lemma translations, determine if an existing lemma has an empty translation
                    # and matches an empty column
                    for (lang, term) in lemmaidglosstranslations.items():
                        for lem in existing_lemmas_set:

                            lem_trans = lem.lemmaidglosstranslation_set.filter(language=lang, text=term)
                            if lem_trans:
                                # the lemma gloss translation matches the column
                                row_error = False
                            else:
                                if term:
                                    # no matching translation found
                                    row_error = True
                                else:
                                    # term is empty and lemma has empty translation, it's okay
                                    row_error = False

                if row_error:
                    # row error is still true if not enough matches were found for existing lemmas
                    # there is still a row error
                    number_of_new_lemmas = len(re.findall('New', ' '.join(contextual_error_messages_lemmaidglosstranslations)))
                    number_of_empty_lemmas = len(re.findall('empty', ' '.join(contextual_error_messages_lemmaidglosstranslations)))
                    if number_of_new_lemmas and number_of_empty_lemmas:
                        addendum = 'Row '+str(nl + 1)+': The Lemma translations may refer to different lemmas.'
                        contextual_error_messages_lemmaidglosstranslations.append(addendum)

                    error += contextual_error_messages_lemmaidglosstranslations

                if len(existing_lemmas_set) == 1:
                    existing_lemma = existing_lemmas[0]
                elif len(existing_lemmas):
                    e1 = 'Row '+str(nl + 1)+': To create glosses in dataset ' + dataset_name + \
                         ', the combination of Lemma ID Gloss translations should either refer ' \
                         'to an existing Lemma ID Gloss or make up a completely new Lemma ID gloss.'
                    fatal_error = True
                    error.append(e1)
                    if contextual_error_messages_lemmaidglosstranslations:
                        number_of_existing_lemmas = len(re.findall('Existing', ' '.join(contextual_error_messages_lemmaidglosstranslations)))
                        if number_of_existing_lemmas > 1:
                            addendum = 'The Lemma translations refer to different lemmas.'
                            contextual_error_messages_lemmaidglosstranslations.append(addendum)
                        error += contextual_error_messages_lemmaidglosstranslations

                # Annotation ID Gloss needs to be checked dynamically for each dataset language.
                for language in dataset.translation_languages.all():
                    column_name = "Annotation ID Gloss (%s)" % language.name_en
                    if column_name not in value_dict:
                        e1 = 'To create glosses in dataset ' + dataset_name + ', column ' + column_name + ' is required.'
                        fatal_error = True
                        error.append(e1)
                        break

                # break at this level to get out of iteration over csv lines in case of missing column
                if fatal_error:
                    break

            if creating_glosses:
                (new_gloss, already_exists, error_create, earlier_creation_same_csv, earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss) \
                    = create_gloss_from_valuedict(value_dict,dataset,nl, earlier_creation_same_csv, earlier_creation_annotationidgloss, earlier_creation_lemmaidgloss)
                creation += new_gloss
                gloss_already_exists += already_exists
                if len(error_create):
                    # more than one error found
                    errors_found_string = '\n'.join(error_create)
                    error.append(errors_found_string)
                continue


            # updating glosses
            try:
                gloss = Gloss.objects.select_related().get(pk=pk)
            except ObjectDoesNotExist as e:

                e = 'Could not find gloss for Signbank ID '+str(pk)
                error.append(e)
                continue

            if gloss.lemma.dataset != dataset:
                e1 = 'Row '+ str(nl + 1) + ': The Dataset column (' + dataset.name + ') does not correspond to that of the Signbank ID (' \
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

                help = 'Signbank ID (' + str(pk) + "): Attempt to update Lemma ID Gloss translations."
                error.append(help)
                continue

            try:
                (changes_found, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss) = \
                            compare_valuedict_to_gloss(value_dict,gloss.id,user_datasets_names, nl, earlier_updates_same_csv, earlier_updates_lemmaidgloss)
                changes += changes_found

                if len(errors_found):
                    # more than one error found
                    errors_found_string = '\n'.join(errors_found)
                    error.append(errors_found_string)

            except MachineValueNotFoundError as e:

                e_string = str(e)
                error.append(e_string)
        stage = 1

    #Do changes
    elif len(request.POST) > 0:

        csv_update = False
        csv_create = False

        for key, new_value in request.POST.items():

            if key == 'update_or_create' and new_value == 'update':
                csv_update = True
            elif key == 'update_or_create' and new_value == 'create':
                csv_create = True
            else:
                pass

        if csv_update:
            lemmaidglosstranslations_per_gloss = {}
            for key, new_value in request.POST.items():

                try:
                    pk, fieldname = key.split('.')

                #In case there's no dot, this is not a value we set at the previous page
                except ValueError:
                    # when the database token csrfmiddlewaretoken is passed, there is no dot
                    # print('no dot found')
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
                    continue   # avoid default field update

                # Updating the annotation idgloss is a special procedure, because it has relations to other parts of the
                # database
                annotation_idgloss_key_prefix = "Annotation ID Gloss ("
                if fieldname.startswith(annotation_idgloss_key_prefix):
                    language_name = fieldname[len(annotation_idgloss_key_prefix):-1]
                    languages = Language.objects.filter(name_en=language_name)
                    if languages:
                        language = languages[0]
                        annotation_idglosses = gloss.annotationidglosstranslation_set.filter(language=language)
                        if annotation_idglosses:
                            annotation_idgloss = annotation_idglosses[0]
                            annotation_idgloss.text = new_value
                            annotation_idgloss.save()
                    continue

                # Updating the keywords is a special procedure, because it has relations to other parts of the database
                if fieldname == 'Keywords':
                    # The following is necessary to process keywords for multiple languages
                    keywords_dict = {}
                    for keyword_string in new_value.split(", "):
                        (keyword, language_code_2char) = keyword_string.split(":")
                        if language_code_2char in keywords_dict:
                            keywords_dict[language_code_2char] += ", " + keyword
                        else:
                            keywords_dict[language_code_2char] = keyword
                    for language_code_2char, keywords in keywords_dict.items():
                        update_keywords(gloss, "keywords_" + language_code_2char, keywords)
                    gloss.save()
                    continue

                if fieldname == 'SignLanguages':

                    new_human_value_list = [v.strip() for v in new_value.split(',')]

                    update_signlanguage(gloss,None,new_human_value_list)
                    gloss.save()
                    continue

                if fieldname == 'Dialects':

                    new_human_value_list = [v.strip() for v in new_value.split(',')]

                    update_dialect(gloss,None,new_human_value_list)
                    gloss.save()
                    continue

                if fieldname == 'Dataset':

                    # this has already been checked for existance and permission in the previous step
                    # get dataset identifier
                    if new_value == 'None':
                        # don't allow the user to erase the current dataset, this should have already been caught
                        print('csv import make changes error: gloss ', gloss.id, ' attempt to set dataset to empty')
                        continue
                    else:
                        # the existence of the new dataset should have already been tested
                        new_dataset = Dataset.objects.get(name=new_value)
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

                    update_sequential_morphology(gloss,None,new_human_value_list)

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

                    #Replace the value for bools
                    if fieldname in Gloss._meta.get_fields() and Gloss._meta.get_field(fieldname).__class__.__name__ == 'NullBooleanField':

                        if new_value in ['true','True', 'TRUE']:
                            new_value = True
                        elif new_value == 'None' or new_value == 'Neutral':
                            new_value = None
                        else:
                            new_value = False

                    #Remember this for renaming the video later
                    if fieldname == 'idgloss':
                        video_path_before = settings.WRITABLE_FOLDER+gloss.get_video_path()

                    #The normal change and save procedure
                    setattr(gloss,fieldname,new_value)
                    gloss.save()

                    #Also update the video if needed
                    if fieldname == 'idgloss':
                        video_path_after = settings.WRITABLE_FOLDER+gloss.get_video_path()
                        if os.path.isfile(video_path_before):
                            os.rename(video_path_before,video_path_after)

            stage = 2

        elif csv_create:

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

            # these should be error free based on the django template import_csv.html
            for row in glosses_to_create.keys():
                dataset = glosses_to_create[row]['dataset']

                try:
                    dataset_id = Dataset.objects.get(name=dataset)
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
                        # print("Error: {}".format(e))
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
                    e1 = 'To create glosses in dataset ' + dataset_id.name + \
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
        else:
            stage = 0

    #Show uploadform
    else:

        stage = 0

    return render(request,'dictionary/import_csv.html',{'form':uploadform,'stage':stage,'changes':changes,
                                                        'creation':creation,
                                                        'gloss_already_exists':gloss_already_exists,
                                                        'error':error,
                                                        'dataset_languages':dataset_languages,
                                                        'selected_datasets':selected_datasets,
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

    try:
        from signbank.settings.server_specific import RECENTLY_ADDED_SIGNS_PERIOD
        recently_added_signs_since_date = DT.datetime.now() - RECENTLY_ADDED_SIGNS_PERIOD
        recent_glosses = Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(
                          creationDate__range=[recently_added_signs_since_date, DT.datetime.now()]).order_by(
                          'creationDate').reverse()
        return render(request, 'dictionary/recently_added_glosses.html',
                      {'glosses': recent_glosses,
                       'dataset_languages': dataset_languages,
                        'selected_datasets':selected_datasets,
                        'SHOW_DATASET_INTERFACE_OPTIONS' : settings.SHOW_DATASET_INTERFACE_OPTIONS})

    except:
        return render(request,'dictionary/recently_added_glosses.html',
                      {'glosses':Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(isNew=True).order_by('creationDate').reverse(),
                       'dataset_languages': dataset_languages,
                        'selected_datasets':selected_datasets,
                        'SHOW_DATASET_INTERFACE_OPTIONS' : settings.SHOW_DATASET_INTERFACE_OPTIONS})


def proposed_new_signs(request):
    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    proposed_or_new_signs = (Gloss.objects.filter(isNew=True) |
                             TaggedItem.objects.get_intersection_by_model(Gloss, "sign:_proposed")).order_by('creationDate').reverse()
    return render(request, 'dictionary/recently_added_glosses.html',
                  {'glosses': proposed_or_new_signs,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

def add_params_to_url(url,params):
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url = urlparse.urlunparse(url_parts)

    url_parts[4] = urlencode(query)
    return urlparse.urlunparse(url_parts)

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

                params = {'warning':'File extension not supported! Please convert to png or jpg'}
                return redirect(add_params_to_url(url,params))

            elif imagefile._size > settings.MAXIMUM_UPLOAD_SIZE:

                params = {'warning':'Uploaded file too large!'}
                return redirect(add_params_to_url(url,params))

            # construct a filename for the image, use sn
            # if present, otherwise use idgloss+gloss id
            if gloss.sn != None:
                imagefile.name = str(gloss.sn) + extension
            else:
                imagefile.name = gloss.idgloss + "-" + str(gloss.pk) + extension

            redirect_url = form.cleaned_data['redirect']

            # deal with any existing image for this sign
            goal_path =  settings.WRITABLE_FOLDER+settings.GLOSS_IMAGE_DIRECTORY + '/' + gloss.idgloss[:2] + '/'
            goal_location = goal_path + gloss.idgloss + '-' + str(gloss.pk) + extension

            #First make the dir if needed
            try:
                os.mkdir(goal_path)
            except OSError:
                pass

            #Remove previous video
            if gloss.get_image_path():
                os.remove(settings.WRITABLE_FOLDER+gloss.get_image_path())

            with open(goal_location, 'wb+') as destination:
                for chunk in imagefile.chunks():
                    destination.write(chunk)

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

        default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

        os.remove(settings.WRITABLE_FOLDER+image_path)

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

    if request.method == 'POST':

        form = ImageUploadForHandshapeForm(request.POST, request.FILES)

        if form.is_valid():

            handshape_id = form.cleaned_data['handshape_id']
            handshape = get_object_or_404(Handshape, machine_value=handshape_id)

            imagefile = form.cleaned_data['imagefile']
            extension = '.'+imagefile.name.split('.')[-1]

            if extension not in settings.SUPPORTED_CITATION_IMAGE_EXTENSIONS:

                params = {'warning':'File extension not supported! Please convert to png or jpg'}
                return redirect(add_params_to_url(url,params))

            elif imagefile._size > settings.MAXIMUM_UPLOAD_SIZE:

                params = {'warning':'Uploaded file too large!'}
                return redirect(add_params_to_url(url,params))

            # construct a filename for the image, use sn
            # if present, otherwise use idgloss+gloss id
            imagefile.name = "handshape_" + str(handshape.machine_value) + extension

            redirect_url = form.cleaned_data['redirect']

            # deal with any existing image for this sign
            goal_path =  settings.WRITABLE_FOLDER+settings.HANDSHAPE_IMAGE_DIRECTORY + '/' + str(handshape.machine_value) + '/'
            goal_location = goal_path + 'handshape_' + str(handshape.machine_value) + extension

            #First make the dir if needed
            try:
                os.mkdir(goal_path)
            except OSError:
                pass

            #Remove previous video
            if handshape.get_image_path():
                os.remove(settings.WRITABLE_FOLDER+handshape.get_image_path())

            with open(goal_location, 'wb+') as destination:
                for chunk in imagefile.chunks():
                    destination.write(chunk)

            return redirect(redirect_url)

    # if we can't process the form, just redirect back to the
    # referring page, should just be the case of hitting
    # Upload without choosing a file but could be
    # a malicious request, if no referrer, go back to root
    return redirect(url)


def find_and_save_variants(request):

    variant_pattern_glosses = Gloss.objects.filter(annotationidglosstranslation__text__regex=r"^(.*)\-([A-Z])$").distinct().order_by('lemma')[:10]

    gloss_table_prefix = '<!DOCTYPE html>\n' \
                         '<html>\n' \
                         '<body>\n' \
                         '<table style="font-size: 11px; border-collapse:separate; border-spacing: 2px;" border="1">\n' \
                         '<thead>\n' \
                         '<tr>\n' \
                         '<th style="width:10em; text-align:left;">Focus Gloss</th>\n' \
                         '<th style="width:15em; text-align:left;">Other Relations</th>\n' \
                         '<th style="width:20em; text-align:left;">Variant Relations (PRE)</th>\n' \
                         '<th style="width:20em; text-align:left;">Candidate Variants</th>\n' \
                         '<th style="width:25em; text-align:left;">Variant Relations (POST)</th>\n' \
                          '</tr>\n' \
                         '</thead>\n' \
                         '<tbody>\n'
    gloss_table_suffix = '</tbody>\n' \
                         '</table>\n' \
                         '</body>\n' \
                         '</html>'

    gloss_pattern_table = dict()
    gloss_table_rows = ''

    for gloss in variant_pattern_glosses:

        dict_key = int(gloss.id)
        gloss_pattern_table[dict_key] = '<td>' + str(gloss.idgloss) + '</td>'
        other_relations_of_sign = gloss.other_relations()

        if other_relations_of_sign:

            gloss_pattern_table[dict_key] += '<td>'

            for x in other_relations_of_sign:
                gloss_pattern_table[dict_key] += str(x.target) + '&nbsp;(' + str(x.role) + ') '

            gloss_pattern_table[dict_key] += '</td>'

        else:
            gloss_pattern_table[dict_key] += '<td>&nbsp;</td>'

        variant_relations_of_sign = gloss.variant_relations()

        if variant_relations_of_sign:

            gloss_pattern_table[dict_key] += '<td>'

            for x in variant_relations_of_sign:
                gloss_pattern_table[dict_key] += str(x.target) + '&nbsp;(' + str(x.role) + ') '

            gloss_pattern_table[dict_key] += '</td>'

        else:
            gloss_pattern_table[dict_key] += '<td>&nbsp;</td>'


        other_relation_objects = [x.target for x in other_relations_of_sign]
        variant_relation_objects = [x.target for x in variant_relations_of_sign]

        # Build query
        this_sign_stems = gloss.get_stems()
        queries = []
        for this_sign_stem in this_sign_stems:
            this_matches = r'^' + re.escape(this_sign_stem[1]) + r'\-[A-Z]$'
            queries.append(Q(annotationidglosstranslation__text__regex=this_matches,
                             dataset=gloss.dataset, annotationidglosstranslation__language=this_sign_stem[0]))
        query = queries.pop()
        for q in queries:
            query |= q

        candidate_variants = Gloss.objects.filter(query).distinct().exclude(idgloss=gloss).exclude(
            idgloss__in=other_relation_objects).exclude(idgloss__in=variant_relation_objects)

        if candidate_variants:
            gloss_pattern_table[dict_key] += '<td>'

            for x in candidate_variants:
                gloss_pattern_table[dict_key] += str(x.idgloss) + ' '

            gloss_pattern_table[dict_key] += '</td>'

        else:
            gloss_pattern_table[dict_key] += '<td>&nbsp;</td>'


        for target in candidate_variants:

            rel = Relation(source=gloss, target=target, role='variant')
            rel.save()

        updated_variants = gloss.variant_relations()

        if updated_variants:

            gloss_pattern_table[dict_key] += '<td>'

            for x in updated_variants:
                gloss_pattern_table[dict_key] += str(x.target) + '&nbsp;(' + str(x.role) + ') '

            gloss_pattern_table[dict_key] += '</td>'

        else:
            gloss_pattern_table[dict_key] += '<td>&nbsp;</td>'

        gloss_table_rows = gloss_table_rows + '<tr>' + gloss_pattern_table[dict_key] + '</tr>\n'


    return HttpResponse(gloss_table_prefix+gloss_table_rows+gloss_table_suffix)



def configure_handshapes(request):

    output_string = '<!DOCTYPE html>\n' \
                         '<html>\n' \
                         '<body>\n'
    handshapes_table_pre = '<table style="font-size: 11px; border-collapse:separate; border-spacing: 2px;" border="1">\n' \
                         '<thead>\n' \
                         '<tr>\n' \
                         '<th style="width:20em; text-align:left;">Machine Value</th>\n' \
                         '<th style="width:25em; text-align:left;">English Name</th>\n' \
                         '<th style="width:40em; text-align:left;">Dutch Name</th>\n' \
                         '<th style="width:40em; text-align:left;">Chinese Name</th>\n' \
                         '</tr>\n' \
                         '</thead>\n' \
                         '<tbody>\n'

    handshapes_table_suffix = '</tbody>\n' \
                         '</table>\n'

    output_string_suffix = '</body>\n' \
                         '</html>'

    # check if the Handshape table has been filled, if so don't do anything
    already_filled_handshapes = Handshape.objects.count()
    if already_filled_handshapes:
        return HttpResponse(output_string + '<p>Handshapes are already configured.</p>' + output_string_suffix)
    else:

        output_string += handshapes_table_pre

        handshapes = FieldChoice.objects.filter(field__iexact='Handshape')

        for o in handshapes:

            new_id = o.machine_value
            new_machine_value = o.machine_value
            new_english_name = o.english_name
            new_dutch_name = o.dutch_name
            new_chinese_name = o.chinese_name

            new_handshape = Handshape(machine_value=new_machine_value, english_name=new_english_name, dutch_name=new_dutch_name, chinese_name=new_chinese_name)
            new_handshape.save()

            output_string += '<tr><td>' + str(new_machine_value) + '</td><td>' + new_english_name + '</td><td>' + new_dutch_name + '</td><td>' + new_chinese_name + '</td></tr>\n'

        output_string += handshapes_table_suffix

        # Add FieldChoice types for Handshape objects
        # output_string += values_Quantity()

        output_string += output_string_suffix

        return HttpResponse(output_string)

def get_unused_videos(request):

    videos_with_unused_pk = []
    videos_where_pk_does_match_idgloss = []
    videos_with_unusual_file_names = []

    for dir_name in os.listdir(settings.WRITABLE_FOLDER+settings.GLOSS_VIDEO_DIRECTORY):

        dir_path = settings.WRITABLE_FOLDER+settings.GLOSS_VIDEO_DIRECTORY+'/'+dir_name+'/'

        for file_name in os.listdir(dir_path):

            try:
                items = file_name.replace('.mp4','').split('-')
                pk = int(items[-1])
                idgloss = '-'.join(items[:-1])
            except ValueError:
                videos_with_unusual_file_names.append(file_name)
                continue

            try:
                if Gloss.objects.get(pk=pk).idgloss != idgloss:
                    videos_where_pk_does_match_idgloss.append(file_name)
            except ObjectDoesNotExist:
                videos_with_unused_pk.append(file_name)
                continue

    result = '<p>For these videos, the pk does not match the idgloss:</p><ul>'
    result += ''.join(['<li>'+video+'</li>' for video in videos_where_pk_does_match_idgloss])
    result += '</ul></p>'

    result += '<p>These videos have unusual file names:</p><ul>'
    result += ''.join(['<li>'+video+'</li>' for video in videos_with_unusual_file_names])
    result += '</ul></p>'

    result += '<p>These videos have unused pks:</p><ul>'
    result += ''.join(['<li>'+video+'</li>' for video in videos_with_unused_pk])
    result += '</ul></p>'

    return HttpResponse(result)

def list_all_fieldchoice_names(request):

    content = ''
    for fieldchoice in FieldChoice.objects.all():
        columns = []

        for column in [fieldchoice.field,fieldchoice.english_name,fieldchoice.dutch_name,fieldchoice.chinese_name]:
            if column not in [None,'']:
                columns.append(column)
            else:
                columns.append('[empty]')

        content += '\t'.join(columns)+'\n'

    return HttpResponse(content)

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

    dataset = None
    if 'dataset_name' in request.GET:
        dataset = Dataset.objects.get(name=request.GET['dataset_name'])


    video_folder_name = 'glossvideo'
    image_folder_name = 'glossimage'

    try:
        if request.GET['small_videos'] not in [0,False,'false']:
            video_folder_name+= '_small'
    except KeyError:
        pass

    archive_file_name = '.'.join([first_part_of_file_name,timestamp_part_of_file_name,'zip'])
    archive_file_path = settings.SIGNBANK_PACKAGES_FOLDER + archive_file_name

    video_urls = signbank.tools.get_static_urls_of_files_in_writable_folder(video_folder_name,since_timestamp, dataset)
    image_urls = signbank.tools.get_static_urls_of_files_in_writable_folder(image_folder_name,since_timestamp, dataset)
    # Filter out all backup files
    video_urls = dict([(gloss_id, url) for (gloss_id, url) in video_urls.items() if not re.match('.*_\d+', url)])
    image_urls = dict([(gloss_id, url) for (gloss_id, url) in image_urls.items() if not re.match('.*_\d+', url)])

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
    user_datasets_names = [dataset.name for dataset in user_datasets]

    # Put the default dataset in first position
    if DEFAULT_DATASET in user_datasets_names:
        user_datasets_names.insert(0, user_datasets_names.pop(user_datasets_names.index(DEFAULT_DATASET)))

    if user_datasets_names:
        return HttpResponse(json.dumps(user_datasets_names), content_type='application/json')
    else:
        return HttpResponse(json.dumps([settings.LANGUAGE_NAME, settings.COUNTRY_NAME]),
                            content_type='application/json')


def protected_media(request, filename, document_root=WRITABLE_FOLDER, show_indexes=False):

    if not request.user.is_authenticated():

        # If we are not logged in, try to find if this maybe belongs to a gloss that is free to see for everbody?
        gloss_pk = int(filename.split('.')[-2].split('-')[-1])

        try:
            if not Gloss.objects.get(pk=gloss_pk).inWeb:
                return HttpResponse(status=401)
        except Gloss.DoesNotExist:
            return HttpResponse(status=401)

        #If we got here, the gloss was found and in the web dictionary, so we can continue

    path = WRITABLE_FOLDER + filename
    exists = os.path.exists(path)

    if not exists:
        raise Http404("File does not exist.")

    USE_NEW_X_SENDFILE_APPROACH = True

    if USE_NEW_X_SENDFILE_APPROACH:

        if filename.split('.')[-1] == 'mp4':
            response = HttpResponse(content_type='video/mp4')
        elif filename.split('.')[-1] == 'png':
            response = HttpResponse(content_type='image/png')
        else:
            response = HttpResponse()

        response['Content-Disposition'] = 'inline;filename='+filename
        response['X-Sendfile'] = WRITABLE_FOLDER + filename

        return response

    else:
        from django.views.static import serve
        return serve(request, filename, document_root, show_indexes)

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
                    dataset=None,
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
            dataset=None,
            signlanguage=None
        ).count()

        all_datasets = Dataset.objects.all()

        return render(request,"dictionary/unassigned_glosses.html", {
                        "signlanguages":signlanguages,
                        "number_of_unassigned_glosses_without_signlanguage":number_of_unassigned_glosses_without_signlanguage,
                        "all_datasets":all_datasets
                      })

def choice_lists(request):

    FIELDS_TO_EXCLUDE = ['weakprop', 'weakdrop', 'domhndsh_number', 'domhndsh_letter', 'subhndsh_number',
                             'subhndsh_letter']

    selected_datasets = get_selected_datasets_for_user(request.user)
    all_choice_lists = {}

    if 'dataset' in request.GET:
        choices_to_exclude = Dataset.objects.get(name=request.GET['dataset']).exclude_choices.all()
    else:
        choices_to_exclude = None

    # Translate the machine values to human values in the correct language, and save the choice lists along the way
    for topic in ['main', 'phonology', 'semantics', 'frequency']:
        for field in FIELDS[topic]:

            if field in FIELDS_TO_EXCLUDE:
                continue

            # Get and save the choice list for this field
            fieldchoice_category = fieldname_to_category(field)
            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)

            if len(choice_list) > 0:
                all_choice_lists[field] = choicelist_queryset_to_translated_dict(choice_list,request.LANGUAGE_CODE,
                                                                                 choices_to_exclude=choices_to_exclude)
                choice_list_machine_values = choicelist_queryset_to_machine_value_dict(choice_list)

                #Also concatenate the frequencies of all values
                if 'include_frequencies' in request.GET and request.GET['include_frequencies']:
                    for choice_list_field, machine_value in choice_list_machine_values:

                        if machine_value == 0:
                            frequency_for_field = Gloss.objects.filter(Q(lemma__dataset__in=selected_datasets),
                                                                       Q(**{field + '__isnull': True}) |
                                                                       Q(**{field: 0})).count()

                        else:
                            variable_column = field
                            search_filter = 'exact'
                            filter = variable_column + '__' + search_filter
                            frequency_for_field = Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(**{filter: machine_value}).count()

                        try:
                            all_choice_lists[field][choice_list_field] += ' ['+str(frequency_for_field)+']'
                        except KeyError: #This might an excluded field
                            continue

    # Add morphology to choice lists
    all_choice_lists['morphology_role'] = choicelist_queryset_to_translated_dict(
        FieldChoice.objects.filter(field__iexact='MorphologyType'),request.LANGUAGE_CODE)

    all_choice_lists['morph_type'] = choicelist_queryset_to_translated_dict(
        FieldChoice.objects.filter(field__iexact='MorphemeType'),request.LANGUAGE_CODE)

    return HttpResponse(json.dumps(all_choice_lists), content_type='application/json')
