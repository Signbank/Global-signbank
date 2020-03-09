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
from django.contrib import messages
from django.core.files import File
from pathlib import Path

import os
import shutil
import csv
import time
import re

from signbank.dictionary.translate_choice_list import choicelist_queryset_to_translated_dict
from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from signbank.feedback.models import *
from signbank.dictionary.update import update_keywords, update_signlanguage, update_dialect, subst_relations, subst_foreignrelations, \
    update_sequential_morphology, update_simultaneous_morphology, update_tags, update_blend_morphology, subst_notes
import signbank.dictionary.forms
from signbank.video.models import GlossVideo, small_appendix, add_small_appendix

from signbank.video.forms import VideoUploadForGlossForm
from signbank.tools import *
from signbank.tools import save_media, compare_valuedict_to_gloss, MachineValueNotFoundError
from signbank.tools import get_selected_datasets_for_user, gloss_from_identifier

import signbank.settings
from signbank.settings.base import *
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
                               'gloss_or_morpheme': 'gloss',
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
    # this is public view of a gloss

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

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    if not(request.user.has_perm('dictionary.search_gloss') or gloss.inWeb):
        return render(request,"dictionary/word.html",{'feedbackmessage': 'You are not allowed to see this sign.',
                                                       'dataset_languages': dataset_languages,
                                                       'selected_datasets': selected_datasets,
                                                       'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

    allkwds = gloss.translation_set.all()
    if len(allkwds) == 0:
        trans = None  # this seems to cause problems in the template, the title of the page ends up empty
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

    default_language = Language.objects.get(id=get_default_language_id())
    if not trans:
        # this prevents an empty title in the template
        # this essentially overrides the "gloss.idgloss" method to prevent it from putting translations between parentheses
        # print('trans was None, set it to annotation id gloss of default language')
        trans = gloss.annotationidglosstranslation_set.get(language=default_language).text
    # print('word trans: ', trans)

    # Regroup notes
    note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType')
    notes = gloss.definition_set.all()
    notes_groupedby_role = {}
    for note in notes:
        # print('note: ', note.id, ', ', note.role, ', ', note.published, ', ', note.text, ', ', note.count)
        translated_note_role = machine_value_to_translated_human_value(note.role, note_role_choices,
                                                                       request.LANGUAGE_CODE)
        role_id = (note.role, translated_note_role)
        if role_id not in notes_groupedby_role:
            notes_groupedby_role[role_id] = []
        notes_groupedby_role[role_id].append(note)

    # get the last match keyword if there is one passed along as a form variable
    if 'lastmatch' in request.GET:
        lastmatch = request.GET['lastmatch']
        print('lastmatch: ', lastmatch)
        if lastmatch == "None":
            # this looks weird, comparing to None in quotes
            lastmatch = False
    else:
        lastmatch = False

    return render(request,"dictionary/word.html",
                              {'translation': trans,
                               'definitions': gloss.definitions(),
                               'gloss_or_morpheme': 'gloss',
                               'allkwds': allkwds,
                               'notes_groupedby_role': notes_groupedby_role,
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
                               'DEFINITION_FIELDS' : settings.DEFINITION_FIELDS,
                               'dataset_languages': dataset_languages,
                               'selected_datasets': selected_datasets,
                               'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })


def morpheme(request, glossid):
    # this is public view of a morpheme

    if 'feedbackmessage' in request.GET:
        feedbackmessage = request.GET['feedbackmessage']
    else:
        feedbackmessage = False

    # we should only be able to get a single gloss, but since the URL
    # pattern could be spoofed, we might get zero or many
    # so we filter first and raise a 404 if we don't get one
    try:
        morpheme = Morpheme.objects.get(id=glossid)
    except ObjectDoesNotExist:
        raise Http404

    if not(request.user.has_perm('dictionary.search_gloss') or morpheme.inWeb):
        return render(request,"dictionary/word.html",{'feedbackmessage': 'You are not allowed to see this sign.'})

    allkwds = morpheme.translation_set.all().order_by('translation__text')
    if len(allkwds) == 0:
        trans = None
    else:
        trans = allkwds[0]

    videourl = morpheme.get_video_url()
    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, videourl)):
        videourl = None

    if morpheme.sn != None:
        if request.user.has_perm('dictionary.search_gloss'):
            glosscount = Morpheme.objects.count()
            glossposn = Morpheme.objects.filter(sn__lt=morpheme.sn).count()+1
        else:
            glosscount = Morpheme.objects.filter(inWeb__exact=True).count()
            glossposn = Morpheme.objects.filter(inWeb__exact=True, sn__lt=morpheme.sn).count()+1
    else:
        glosscount = 0
        glossposn = 0

    # navigation gives us the next and previous signs
    nav = morpheme.navigation(request.user.has_perm('dictionary.search_gloss'))

    # the gloss update form for staff
    update_form = None

    if request.user.has_perm('dictionary.search_gloss'):
        update_form = GlossModelForm(instance=morpheme)
        video_form = VideoUploadForGlossForm(initial={'gloss_id': morpheme.pk,
                                                      'redirect': request.get_full_path()})
    else:
        update_form = None
        video_form = None


    # Put annotation_idgloss per language in the context
    annotation_idgloss = {}
    if morpheme.dataset:
        for language in morpheme.dataset.translation_languages.all():
            annotation_idgloss[language] = morpheme.annotationidglosstranslation_set.filter(language=language)
    else:
        language = Language.objects.get(id=get_default_language_id())
        annotation_idgloss[language] = morpheme.annotationidglosstranslation_set.filter(language=language)


    # get the last match keyword if there is one passed along as a form variable
    if 'lastmatch' in request.GET:
        lastmatch = request.GET['lastmatch']
        print('lastmatch: ', lastmatch)
        if lastmatch == "None":
            # this looks weird, comparing to None in quotes
            lastmatch = False
    else:
        lastmatch = False

    return render(request,"dictionary/word.html",
                              {'translation': trans,
                               'definitions': morpheme.definitions(),
                               'gloss_or_morpheme': 'morpheme',
                               'allkwds': allkwds,
                               'dialect_image': map_image_for_dialects(morpheme.dialect.all()),
                               'lastmatch': lastmatch,
                               'videofile': videourl,
                               'viewname': word,
                               'feedback': None,
                               'gloss': morpheme,
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
    out = '<p>Imported</p><ul>'
    overwritten_files = '<p>Of these files, these were overwritten</p><ul>'
    errors = []
    print("video: ", video)

    if video:
        import_folder = settings.VIDEOS_TO_IMPORT_FOLDER
    else:
        import_folder = settings.IMAGES_TO_IMPORT_FOLDER

    print("Import folder: %s" % import_folder)

    for dataset_folder_name in [name for name in os.listdir(import_folder) if os.path.isdir(os.path.join(import_folder, name))]:
        # Check whether the folder name is equal to a dataset name
        print("Dataset folder name: %s " % dataset_folder_name)
        try:
            dataset = Dataset.objects.get(name=dataset_folder_name)
        except:
            dataset = Dataset.objects.get(acronym=dataset_folder_name)

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
                    glosses = Gloss.objects.filter(lemma__dataset=dataset, annotationidglosstranslation__language=language,
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

                if not video:
                    overwritten, was_allowed = save_media(lang3code_folder_path, lang3code_folder_name,
                                                          GLOSS_IMAGE_DIRECTORY, gloss, extension)

                    if not was_allowed:
                        errors.append('Failed to move media file for '+default_annotationidgloss+
                                      '. Either the source could not be read or the destination could not be written.')
                        continue

                    out += '<li>'+filename+'</li>'

                else:
                    video_file_path = os.path.join(lang3code_folder_path, filename)
                    vfile = File(open(video_file_path, 'rb'))
                    video = gloss.add_video(request.user, vfile)
                    vfile.close()

                    try:
                        os.remove(video_file_path)
                    except OSError as oserror:
                        errors.append("OSError: {}".format(oserror))

                    overwritten = False

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

    from collections import Counter

    encountered_lemmata = []
    lemmata_nr_of_glosses = {}
    lemmata_frequency = {}

    dataset = Dataset.objects.get(pk=5)

    for gloss in Gloss.objects.filter(lemma__dataset=5):

        if gloss.lemma == None:
            continue

        translations = [translation.text for translation in LemmaIdglossTranslation.objects.filter(lemma = gloss.lemma)]
        name = ','.join(translations)

        if gloss.lemma not in encountered_lemmata:
            encountered_lemmata.append(gloss.lemma)
            lemmata_nr_of_glosses[name] = 0
            lemmata_frequency[name] = 0

        lemmata_nr_of_glosses[name] += 1

        try:
            lemmata_frequency[name] += gloss.tokNo
        except TypeError:
            pass

    interesting_lemmata = [(name,lemmata_frequency[name]) for name, freq in lemmata_nr_of_glosses.items() if freq > 1]
    interesting_lemmata.sort(key=lambda x: x[1], reverse=True)

    return HttpResponse(str(interesting_lemmata))

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
    print('inside views add_new_sign')
    context = {}

    selected_datasets = get_selected_datasets_for_user(request.user)

    default_dataset_acronym = settings.DEFAULT_DATASET_ACRONYM
    default_dataset = Dataset.objects.get(acronym=default_dataset_acronym)

    if len(selected_datasets) == 1:
        last_used_dataset = selected_datasets[0]
    elif 'last_used_dataset' in request.session.keys():
        last_used_dataset = request.session['last_used_dataset']
    else:
        last_used_dataset = default_dataset
    context['last_used_dataset'] = last_used_dataset
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    context['dataset_languages'] = dataset_languages
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
        morphQuery = urlquote(morphQuery)
        term = form.cleaned_data['query']
        # Issue #153: do the same with the Translation, encoded by 'query'
        term = urlquote(term)

        return HttpResponseRedirect('../../morphemes/search/?search='+morphQuery+'&keyword='+term)

def add_new_morpheme(request):

    context = {}
    choicelists = {}

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    context['dataset_languages'] = dataset_languages

    default_dataset_acronym = settings.DEFAULT_DATASET_ACRONYM
    default_dataset = Dataset.objects.get(acronym=default_dataset_acronym)

    if len(selected_datasets) == 1:
        last_used_dataset = selected_datasets[0]
    elif 'last_used_dataset' in request.session.keys():
        last_used_dataset = request.session['last_used_dataset']
    else:
        last_used_dataset = default_dataset
    context['last_used_dataset'] = last_used_dataset

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = False
    context['add_morpheme_form'] = MorphemeCreateForm(request.GET, languages=dataset_languages, user=request.user, last_used_dataset=last_used_dataset)

    # Get and save the choice list for mrpType
    try:
        field_mrpType = Morpheme._meta.get_field('mrpType')
        field_category = field_mrpType.field_choice_category
        choice_list = FieldChoice.objects.filter(field__iexact=field_category)
    except:
        print('add_new_morpheme request: error getting field category for mrpType, set to empty list. Check models.py for attribute field_choice_category.')
        choice_list = []
    if len(choice_list) > 0:
        ordered_dict = choicelist_queryset_to_translated_dict(choice_list, request.LANGUAGE_CODE)
        choicelists['mrpType'] = ordered_dict

    context['choice_lists'] = json.dumps(choicelists)

    context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

    return render(request,'dictionary/add_morpheme.html',context)



def import_csv_create(request):
    user = request.user
    import guardian
    user_datasets = guardian.shortcuts.get_objects_for_user(user,'change_dataset',Dataset)
    user_datasets_names = [ dataset.acronym for dataset in user_datasets ]

    selected_datasets = get_selected_datasets_for_user(user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

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

    fatal_error = False

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

        csv_text = request.FILES['file'].read().decode('UTF-8')
        csv_lines = re.compile('[\r\n]+').split(csv_text) # split the csv text on any combination of new line characters

        delimiter = ','

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
                print('Unknown delimiter found during import_csv_create: ', delimiter_radio)

        creation = []
        keys = {}   # in case something goes wrong in header row
        for nl, line in enumerate(csv_lines):

            #The first line contains the keys
            if nl == 0:
                keys = line.strip().split(delimiter)
                num_keys = len(keys)
                continue
            elif len(line) == 0:
                continue

            values = csv.reader([line], delimiter=delimiter).__next__()
            value_dict = {}

            for nv,value in enumerate(values):

                try:
                    if keys[nv]:
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
                # fatal errors so far are having incorrect columns or poorly formatted csv
                break

            if 'Signbank ID' in value_dict:
                e = 'Signbank ID column found.'
                error.append(e)
                break

            # Check whether the user may change the dataset of the current row
            if 'Dataset' in value_dict:
                dataset_name = value_dict['Dataset'].strip()
            else:
                e1 = 'The Dataset column is required.'
                error.append(e1)
                break
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
                except:
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
            except:
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
            except:
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
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
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
                    dataset = Dataset.objects.get(acronym=dataset_name)
                except:
                    print('exception trying to get dataset object')
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
                        # print('error string: ', error_string)
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
                    language = languages[0]
                    annotation_idglosses = gloss.annotationidglosstranslation_set.filter(language=language)
                    if annotation_idglosses:
                        annotation_idgloss = annotation_idglosses[0]
                        annotation_idgloss.text = new_value
                        annotation_idgloss.save()
                continue

            keywords_key_prefix = "Keywords ("
            # Updating the keywords is a special procedure, because it has relations to other parts of the database
            if fieldname.startswith(keywords_key_prefix):
                language_name_column = settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English']
                language_name = fieldname[len(keywords_key_prefix):-1]
                languages = Language.objects.filter(**{language_name_column:language_name})
                if languages:
                    language = languages[0]
                    language_code_2char = language.language_code_2char
                    update_keywords(gloss, "keywords_" + language_code_2char, new_value)
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

    if stage and not changes and not error:
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
    user_datasets = guardian.shortcuts.get_objects_for_user(user,'change_dataset',Dataset)
    user_datasets_names = [ dataset.acronym for dataset in user_datasets ]

    selected_datasets = get_selected_datasets_for_user(user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
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
    # non-numerical lemma ids
    # non-existent dataset or no permission for dataset
    # attempt to update lemmas in multiple datasets in the same csv
    # missing Dataset column
    # missing Lemma required for the dataset

    uploadform = signbank.dictionary.forms.CSVUploadForm
    changes = []
    error = []
    earlier_updates_same_csv = []
    earlier_updates_lemmaidgloss = {}

    #Propose changes
    if len(request.FILES) > 0:
        fatal_error = False
        csv_text = request.FILES['file'].read().decode('UTF-8')
        csv_lines = re.compile('[\r\n]+').split(csv_text) # split the csv text on any combination of new line characters
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

            if 'Lemma ID' in value_dict:
                try:
                    pk = int(value_dict['Lemma ID'])
                except ValueError:
                    e = 'Row '+str(nl + 1) + ': Lemma ID must be numerical: ' + str(value_dict['Lemma ID'])
                    error.append(e)
                    fatal_error = True
            else:
                e = 'Lemma ID required to update lemmas.'
                error.append(e)
                fatal_error = True

            if fatal_error:
                break

            if 'Dataset' not in value_dict:
                e1 = 'The Dataset column is required.'
                error.append(e1)
                break

            # construct list of allowed columns
            required_columns = ['Lemma ID', 'Dataset']

            dataset_name = value_dict['Dataset'].strip()

            # catch possible empty values for dataset, primarily for pretty printing error message
            if dataset_name == '' or dataset_name == None or dataset_name == 0 or dataset_name == 'NULL':
                e_dataset_empty = 'Row ' + str(nl + 1) + ': The Dataset is missing.'
                error.append(e_dataset_empty)
                break
            if dataset_name not in seen_dataset_names:

                try:
                    dataset = Dataset.objects.get(acronym=dataset_name)
                except:
                    print('exception trying to get dataset object')
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
                        e3 = 'Row ' + str(nl + 1) + ': Seen more than one dataset: %s.' % value_dict['Dataset'].strip()
                        error.append(e3)
                        fatal_error = True
                        break
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
                language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
                column_name = "Lemma ID Gloss (%s)" % language_name
                required_columns.append(column_name)
                if column_name in value_dict:
                    lemma_idgloss_value = value_dict[column_name].strip()
                    # also stores empty values
                    lemmaidglosstranslations[language] = lemma_idgloss_value

            # if we get to here, the Lemma ID, Dataset, and Lemma ID Gloss columns have been checked
            # determine if any extra columns were found
            for key in value_dict.keys():
                if key not in required_columns:
                    # too many columns found
                    e = 'Extra column found: ' + key
                    error.append(e)
                    # use a Boolean to catch all extra columns
                    fatal_error = True
            if fatal_error:
                break

            # # updating lemmas, propose changes (make dict)
            try:
                lemma = LemmaIdgloss.objects.select_related().get(pk=pk)
            except ObjectDoesNotExist as e:

                e = 'Row '+ str(nl + 1) + ': Could not find lemma for Lemma ID '+str(pk)
                error.append(e)
                continue
            #
            if lemma.dataset.acronym != dataset_name:
                e1 = 'Row '+ str(nl + 1) + ': The Dataset column (' + dataset.acronym + ') does not correspond to that of the Lemma ID (' \
                                                    + str(pk) + ').'
                error.append(e1)
                # ignore the rest of the row
                continue
            # # dataset is the same

            # If there are changes in the LemmaIdglossTranslation, the changes should refer to another LemmaIdgloss
            current_lemmaidglosstranslations = {}
            for language in lemma.dataset.translation_languages.all():
                try:
                    lemma_translation = LemmaIdglossTranslation.objects.get(language=language, lemma=lemma)
                    current_lemmaidglosstranslations[language] = lemma_translation.text
                except:
                    current_lemmaidglosstranslations[language] = ''

            try:
                (changes_found, errors_found, earlier_updates_same_csv, earlier_updates_lemmaidgloss) = \
                            compare_valuedict_to_lemma(value_dict,lemma.id,user_datasets_names, nl,
                                                       lemmaidglosstranslations, current_lemmaidglosstranslations,
                                                       earlier_updates_same_csv, earlier_updates_lemmaidgloss)
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
                    languages = Language.objects.filter(**{language_name_column:language_name})
                    if languages:
                        language = languages[0]
                        lemma_idglosses = lemma.lemmaidglosstranslation_set.filter(language=language)
                        if lemma_idglosses:
                            # update the lemma translation
                            lemma_translation = lemma_idglosses.first()
                            if new_value:
                                setattr(lemma_translation,'text',new_value)
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
                            # print('Lemma ', str(lemma.pk), ': No existing translation for language (', language_name, ') and no new value: ', new_value)


        stage = 2

    #Show uploadform
    else:

        stage = 0

    return render(request,'dictionary/import_csv_update_lemmas.html',{'form':uploadform,'stage':stage,'changes':changes,
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
    from signbank.settings.server_specific import RECENTLY_ADDED_SIGNS_PERIOD

    try:
        recently_added_signs_since_date = DT.datetime.now() - RECENTLY_ADDED_SIGNS_PERIOD
        recent_glosses = Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(
                          creationDate__range=[recently_added_signs_since_date, DT.datetime.now()]).order_by(
                          'creationDate').reverse()
        return render(request, 'dictionary/recently_added_glosses.html',
                      {'glosses': recent_glosses,
                       'dataset_languages': dataset_languages,
                        'selected_datasets':selected_datasets,
                        'number_of_days': RECENTLY_ADDED_SIGNS_PERIOD.days,
                        'SHOW_DATASET_INTERFACE_OPTIONS' : settings.SHOW_DATASET_INTERFACE_OPTIONS})

    except:
        return render(request,'dictionary/recently_added_glosses.html',
                      {'glosses':Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(isNew=True).order_by('creationDate').reverse(),
                       'dataset_languages': dataset_languages,
                        'selected_datasets':selected_datasets,
                        'number_of_days': RECENTLY_ADDED_SIGNS_PERIOD.days,
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
                   'number_of_days': RECENTLY_ADDED_SIGNS_PERIOD.days,
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
            goal_path = os.path.join(
                WRITABLE_FOLDER,
                GLOSS_IMAGE_DIRECTORY,
                gloss.lemma.dataset.acronym,
                signbank.tools.get_two_letter_dir(gloss.idgloss)
            )
            goal_location_str = os.path.join(goal_path, gloss.idgloss + '-' + str(gloss.pk) + extension)

            #First make the dir if needed
            try:
                os.mkdir(goal_path)
            except OSError:
                pass

            #Remove previous video
            if gloss.get_image_path():
                os.remove(settings.WRITABLE_FOLDER+gloss.get_image_path())

            try:
                f = open(goal_location_str.encode(sys.getfilesystemencoding()), 'wb+')
                destination = File(f)
            except:
                import urllib.parse
                quoted_filename = urllib.parse.quote(gloss.idgloss, safe='')
                filename = quoted_filename + '-' + str(gloss.pk) + extension
                goal_location_str = goal_path + filename
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

    if not settings.USE_HANDSHAPE:
        return HttpResponse(output_string + '<p>Handshapes are not supported by your Signbank configuration.</p>' + output_string_suffix)
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

def configure_speakers(request):

    if request.user.has_perm('dictionary.change_gloss'):

        import_corpus_speakers()

        return HttpResponse('<p>Speakers have been configured.</p>')

    else:

        return HttpResponse('<p>You do not have permission to configure speakers.</p>')

def configure_corpus_documents_ngt(request):

    if request.user.has_perm('dictionary.change_gloss'):

        configure_corpus_documents()

        return HttpResponse('<p>Corpus NGT has been configured.</p>')

    else:

        return HttpResponse('<p>You do not have permission to configure the corpus NGT.</p>')

def get_unused_videos(request):
    file_not_in_glossvideo_object = []
    gloss_video_dir = os.path.join(settings.WRITABLE_FOLDER, settings.GLOSS_VIDEO_DIRECTORY)
    all_files = [str(file) for file in Path(gloss_video_dir).glob('**/*') if file.is_file()]

    for file in all_files:
        full_file_path = file
        file = file[len(settings.WRITABLE_FOLDER):]
        if file.startswith('/'):
            file = file[1:]
        if small_appendix in file:
            file = add_small_appendix(file, reverse=True)

        gloss_videos = GlossVideo.objects.filter(videofile=file)
        if not gloss_videos:
            file_not_in_glossvideo_object.append(full_file_path)

    return render(request, "dictionary/unused_videos.html",
                  {'file_not_in_glossvideo_object': file_not_in_glossvideo_object})


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

    if not request.user.is_authenticated():

        # If we are not logged in, try to find if this maybe belongs to a gloss that is free to see for everbody?
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
    exists = os.path.exists(path)
    if not exists:
        # quote the filename instead to resolve special characters in the url
        (head, tail) = os.path.split(filename)
        import urllib.parse
        quoted_filename = urllib.parse.quote(tail, safe='')
        quoted_path = os.path.join(dir_path, head, quoted_filename)
        exists = os.path.exists(quoted_path)
        if not exists:
            raise Http404("File does not exist.")
        else:
            filename = quoted_filename
            path = quoted_path

    USE_NEW_X_SENDFILE_APPROACH = True

    if USE_NEW_X_SENDFILE_APPROACH:

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

    selected_datasets = get_selected_datasets_for_user(request.user)
    all_choice_lists = {}

    if 'dataset' in request.GET:
        choices_to_exclude = Dataset.objects.get(acronym=request.GET['dataset']).exclude_choices.all()
    else:
        choices_to_exclude = None

    # Translate the machine values to human values in the correct language, and save the choice lists along the way
    for topic in ['main', 'phonology', 'semantics', 'frequency']:

        fields_with_choices = [(field.name, field.field_choice_category) for field in Gloss._meta.fields if field.name in FIELDS[topic] and hasattr(field, 'field_choice_category') ]

        for (field, fieldchoice_category) in fields_with_choices:

            # Get and save the choice list for this field
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

def gloss_revision_history(request,gloss_pk):

    gloss = Gloss.objects.get(pk=gloss_pk)

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    return render(request, 'dictionary/gloss_revision_history.html',
                  {'gloss': gloss, 'revisions':GlossRevision.objects.filter(gloss=gloss),
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface
                   })

def gloss_frequency(request,gloss_pk):

    gloss = Gloss.objects.get(pk=gloss_pk)

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    if gloss.lemma.dataset.acronym != 'NGT':

        return render(request, 'dictionary/gloss_frequency.html',
                      {'gloss': gloss,
                       'has_frequency_data': False,
                       'variants': [],
                       'variants_data': [],
                       'variants_data_quick_access': {},
                       'variants_age_distribution_data': {},
                       'variants_age_distribution_cat_data': {},
                       'variants_age_distribution_cat_percentage': {},
                       'frequency_regions': settings.FREQUENCY_REGIONS,
                       'data_datasets': gloss.data_datasets(),
                       'speaker_age_data': {},
                       'speaker_data': {},
                       'variant_labels': [],
                       'variants_sex_distribution_data': {},
                       'variants_sex_distribution_data_percentage': {},
                       'view_type': 'percentage',
                       'dataset_languages': dataset_languages,
                       'selected_datasets': selected_datasets,
                       'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface
                       })

    speakers_summary = gloss.speaker_age_data()
    speaker_age_data = []
    for i in range(1, 100):
        i_key = str(i)
        if i_key in speakers_summary.keys():
            i_value = speakers_summary[i_key]
            speaker_age_data.append(i_value)
        else:
            speaker_age_data.append(0)

    speaker_data = gloss.speaker_data()

    # incorporates legacy relations
    # a variant pattern is only a variant if there are no other relations between the focus gloss and other glosses under consideration
    # variants might be explictly stored as relations to other glosses
    # the has_variants method only catches explicitly stored variants
    # the pattern variants method excludes glosses with explictly stored relations (including variant relations) to the focus gloss
    # therefore we first try pattern variants

    # for the purposes of frequency charts in the template, the focus gloss is included in the variants
    # this simplifies generating tables for variants inside of a loop in the javascript
    try:
        variants = gloss.pattern_variants()
    except:
        try:
            variants = gloss.has_variants()
        except:
            variants = []
    if gloss not in variants:
        variants.append(gloss)
    variants_with_keys = []
    for gl in variants:
        # get the annotation explicitly
        # do not use the __str__ property idgloss
        gl_idgloss = gl.annotationidglosstranslation_set.get(language=gloss.lemma.dataset.default_language).text
        variants_with_keys.append((gl_idgloss, gl))
    sorted_variants_with_keys = sorted(variants_with_keys, key=lambda tup: tup[0])
    sorted_variant_keys = sorted( [ og_idgloss for (og_idgloss, og) in variants_with_keys] )
    variants_data_quick_access = {}
    variants_data = []
    for (og_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        variants_speaker_data = variant_of_gloss.speaker_data()
        variants_data.append( (og_idgloss, variants_speaker_data ))
        variants_data_quick_access[og_idgloss] = variants_speaker_data

    variants_age_distribution_data = {}
    for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        variant_speaker_age_data_v = variant_of_gloss.speaker_age_data()

        speaker_age_data_v = []
        for i in range(1, 100):
            i_key = str(i)
            if i_key in variant_speaker_age_data_v.keys():
                i_value = variant_speaker_age_data_v[i_key]
                speaker_age_data_v.append(i_value)
            else:
                speaker_age_data_v.append(0)

        variants_age_distribution_data[variant_idgloss] = speaker_age_data_v

    variants_sex_distribution_data = {}
    variants_sex_distribution_data_percentage = {}
    variants_sex_distribution_data_totals = {}
    variants_sex_distribution_data_totals['Female'] = 0
    variants_sex_distribution_data_totals['Male'] = 0

    for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        for i_key in ['Female', 'Male']:
            variants_sex_distribution_data_totals[i_key] += variants_data_quick_access[variant_idgloss][i_key]
            variants_sex_distribution_data[i_key] = {}
            variants_sex_distribution_data_percentage[i_key] = {}

    for i_key in ['Female', 'Male']:
        total_gender_across_variants = variants_sex_distribution_data_totals[i_key]
        for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
            variant_speaker_data_v = variant_of_gloss.speaker_data()
            i_value = variant_speaker_data_v[i_key]

            # print('variant idgloss ', variant_idgloss, ' i key ', i_key, ' total across variants: ', total_gender_across_variants, ' key value: ', i_value)

            speaker_data_v = i_value
            if total_gender_across_variants > 0:
                speaker_data_p = i_value/total_gender_across_variants
            else:
                speaker_data_p = 0

            variants_sex_distribution_data[i_key][variant_idgloss] = speaker_data_v
            variants_sex_distribution_data_percentage[i_key][variant_idgloss] = speaker_data_p

    # print('variants_sex_distribution_data: ', variants_sex_distribution_data)
    # print('variants_sex_distribution_data_percentage: ', variants_sex_distribution_data_percentage)

    variants_age_distribution_cat_data = {}
    variants_age_distribution_cat_percentage = {}
    variants_age_distribution_cat_totals = {}
    variants_age_distribution_cat_totals['< 25'] = 0
    variants_age_distribution_cat_totals['25 - 35'] = 0
    variants_age_distribution_cat_totals['36 - 65'] = 0
    variants_age_distribution_cat_totals['> 65'] = 0

    for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        for i_key in ['< 25', '25 - 35', '36 - 65', '> 65']:
            variants_age_distribution_cat_totals[i_key] += variants_data_quick_access[variant_idgloss][i_key]
            variants_age_distribution_cat_data[i_key] = {}
            variants_age_distribution_cat_percentage[i_key] = {}

    for i_key in ['< 25', '25 - 35', '36 - 65', '> 65']:
        total_age_across_variants = variants_age_distribution_cat_totals[i_key]
        for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:

            variant_age_data_v = variant_of_gloss.speaker_data()
            i_value = variant_age_data_v[i_key]

            # print('variant idgloss ', variant_idgloss, ' i key ', i_key, ' total across variants: ', total_age_across_variants, ' key value: ', i_value)

            speaker_data_v = i_value
            if total_age_across_variants > 0:
                speaker_data_p = i_value/total_age_across_variants
            else:
                speaker_data_p = i_value
            variants_age_distribution_cat_data[i_key][variant_idgloss] = speaker_data_v
            variants_age_distribution_cat_percentage[i_key][variant_idgloss] = speaker_data_p

    # print('variants_age_distribution_cat_data: ', variants_age_distribution_cat_data)
    # print('variants_age_distribution_cat_percentage: ', variants_age_distribution_cat_percentage)

    variant_labels = []
    for og_igloss in sorted_variant_keys:
        if og_igloss not in variant_labels:
            variant_labels.append(og_igloss)

    return render(request, 'dictionary/gloss_frequency.html',
                  {'gloss': gloss,
                   'has_frequency_data': gloss.has_frequency_data(),
                   'variants': variants,
                   'variants_data': variants_data,
                   'variants_data_quick_access': variants_data_quick_access,
                   'variants_age_distribution_data': variants_age_distribution_data,
                   'variants_age_distribution_cat_data': variants_age_distribution_cat_data,
                   'variants_age_distribution_cat_percentage': variants_age_distribution_cat_percentage,
                   'frequency_regions': settings.FREQUENCY_REGIONS,
                   'data_datasets': gloss.data_datasets(),
                   'speaker_age_data': speaker_age_data,
                   'speaker_data': speaker_data,
                   'variant_labels' : variant_labels,
                   'variants_sex_distribution_data': variants_sex_distribution_data,
                   'variants_sex_distribution_data_percentage': variants_sex_distribution_data_percentage,
                   'view_type': 'percentage',
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface
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
