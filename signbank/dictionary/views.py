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
    update_sequential_morphology, update_simultaneous_morphology, update_tags
from signbank.dictionary.adminviews import choicelist_queryset_to_translated_dict
import signbank.dictionary.forms

from signbank.video.forms import VideoUploadForGlossForm
from signbank.tools import *
from signbank.tools import save_media, compare_valuedict_to_gloss, MachineValueNotFoundError

import signbank.settings
from signbank.settings.base import WRITABLE_FOLDER, URL
from django.utils.translation import override

from urllib.parse import urlencode, urlparse
from wsgiref.util import FileWrapper


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
                               'gloss': trans.gloss,
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
                               'SIGN_NAVIGATION' : settings.SIGN_NAVIGATION,
                               'DEFINITION_FIELDS' : settings.DEFINITION_FIELDS})

def gloss(request, idgloss):
    """View of a gloss - mimics the word view, really for admin use
       when we want to preview a particular gloss"""

    if 'feedbackmessage' in request.GET:
        feedbackmessage = request.GET['feedbackmessage']
    else:
        feedbackmessage = False

    # we should only be able to get a single gloss, but since the URL
    # pattern could be spoofed, we might get zero or many
    # so we filter first and raise a 404 if we don't get one
    glosses = Gloss.objects.filter(annotation_idgloss=idgloss)

    if len(glosses) != 1:
        raise Http404

    gloss = glosses[0]

    if not(request.user.has_perm('dictionary.search_gloss') or gloss.inWeb):
#        return render_to_response('dictionary/not_allowed.html')
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

    out = '<p>Imported</p><ul>'
    overwritten_files = '<p>Of these files, these were overwritten</p><ul>'
    errors = []

    if video:
        import_folder = settings.VIDEOS_TO_IMPORT_FOLDER
        goal_directory = settings.GLOSS_VIDEO_DIRECTORY
    else:
        import_folder = settings.IMAGES_TO_IMPORT_FOLDER
        goal_directory = settings.GLOSS_IMAGE_DIRECTORY


    for filename in os.listdir(import_folder):

        parts = filename.split('.')
        idgloss = '.'.join(parts[:-1])
        extension = parts[-1]

        try:
            gloss = Gloss.objects.get(annotation_idgloss=idgloss)
        except ObjectDoesNotExist:
            errors.append('Failed at '+filename+'. Could not find '+idgloss+'.')
            continue

        overwritten, was_allowed = save_media(import_folder,settings.WRITABLE_FOLDER+goal_directory+'/',gloss,extension)

        if not was_allowed:
            errors.append('Failed to move media file for '+gloss.annotation_idgloss+
                          '. Either the source could not be read or the destination could not be written.')
            continue

        out += '<li>'+filename+'</li>'

        # If it is a video also extract a still image and generate a thumbnail version
        if video:
            annotation_id = gloss.annotation_idgloss
            destination_folder = settings.WRITABLE_FOLDER+goal_directory+'/'+annotation_id[:2]+'/'
            video_filename = annotation_id+'-' + str(gloss.pk) + '.' + extension
            video_filepath_small = destination_folder + annotation_id+'-' + str(gloss.pk) + '_small.' + extension

            try:
                print("Trying to resize video " + destination_folder+video_filename)

                if os.path.isfile(video_filepath_small):
                    print("Making a backup of " + video_filepath_small)
                    # Make a backup
                    backup_id = 1
                    made_backup = False
                    while not made_backup:
                        if not os.path.isfile(video_filepath_small + '_' + str(backup_id)):
                            os.rename(video_filepath_small, video_filepath_small + '_' + str(backup_id))
                            made_backup = True
                        else:
                            backup_id += 1

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

    result = 'OK'

    # for gloss in Gloss.objects.all():
    #     for morphemePart in gloss.morphemePart.all():
    #         definition = SimultaneousMorphologyDefinition()
    #         definition.morpheme = morphemePart
    #         definition.parent_gloss = gloss
    #         definition.save()

    return HttpResponse(result)

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

def add_new_sign(request):
    context = {}
    selected_datasets = get_selected_datasets_for_user(request.user)
    context['selected_datasets'] = selected_datasets
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    context['dataset_languages'] = dataset_languages
    context['add_gloss_form'] = GlossCreateForm(request.GET, languages=dataset_languages)

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
    oContext['morph_fields'] = []
    oChoiceLists = {}
    oContext['choice_lists'] = oChoiceLists

    selected_datasets = get_selected_datasets_for_user(request.user)
    oContext['selected_datasets'] = selected_datasets
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
    oContext['dataset_languages'] = dataset_languages
    oContext['add_morpheme_form'] = MorphemeCreateForm(request.GET, languages=dataset_languages)

    field = 'mrpType'
    # Get and save the choice list for this field
    field_category = fieldname_to_category(field)
    choice_list = FieldChoice.objects.filter(field__iexact=field_category)

    if len(choice_list) > 0:
        ordered_dict = choicelist_queryset_to_translated_dict(choice_list, request.LANGUAGE_CODE)
        oChoiceLists[field] = ordered_dict
        oContext['choice_lists'] = oChoiceLists
        oContext['mrp_list'] = json.dumps(ordered_dict)
    else:
        oContext['mrp_list'] = {}

    oContext['choice_lists'] = json.dumps(oContext['choice_lists'])

    # And add the kind of field
    kind = 'list';

    oContext['morph_fields'].append(['(Make a choice)', field, "Morpheme type", kind])

    # Continue
    oBack = render(request,'dictionary/add_morpheme.html', oContext)
    return oBack


def import_csv(request):

    if not(request.user.is_staff) and len(request.user.groups.filter(name="Publisher")) == 0:
        return HttpResponse('You are not allowed to see this page.')

    user = request.user
    import guardian
    qs = guardian.shortcuts.get_objects_for_user(user,'view_dataset',Dataset)

    my_datasets = [ dataset.name for dataset in qs ]

    # print('datasets: ', my_datasets)

    uploadform = signbank.dictionary.forms.CSVUploadForm
    changes = []
    error = False
    creation = []
    gloss_already_exists = []
    gloss_already_exists_dutch = []
    gloss_already_exists_english = []

    #Propose changes
    if len(request.FILES) > 0:

        changes = []
        gloss_already_exists = []
        gloss_already_exists_dutch = []
        gloss_already_exists_english = []

        csv_text = request.FILES['file'].read().decode('UTF-8')
        csv_lines = re.compile('[\r\n]+').split(csv_text) # split the csv text on any combination of new line characters
        creation = []

        # print('import CSV: csv_lines: ', csv_lines)

        for nl, line in enumerate(csv_lines):

            #The first line contains the keys
            if nl == 0:
                keys = line.strip().split(',')
                num_keys = len(keys)
                # print("number of keys: ", num_keys, ', keys: ', keys)
                continue
            elif len(line) == 0:
                continue

            values = csv.reader([line]).__next__()
            value_dict = {}

            for nv,value in enumerate(values):
                # print('try import csv: line number: ', nv, ', value: ', value)

                try:
                    if keys[nv] != '':
                        value_dict[keys[nv]] = value
                    else:
                        if value != '':
                            # empty column header
                            e = 'Extra data found in column without header, row ' + str(nl) + ', column ' + str(nv) + ': ' + value

                            if not error:
                                error = [e]
                            else:
                                error.append(e)
                        pass
                except IndexError:
                    print('index error import csv: line number: ', nv, ', value: ', value)
                    pass

            # print("import CSV: value_dict: ", value_dict)
            try:
                if 'Signbank ID' in value_dict:
                    pk = int(value_dict['Signbank ID'])
                # no column Signbank ID
                elif not ('Lemma ID Gloss' in value_dict
                          and 'Annotation ID Gloss: Dutch' in value_dict
                          and 'Annotation ID Gloss: English' in value_dict
                          and 'Dataset' in value_dict):
                    # not enough columns for creating glosses, input file needs fixing
                    e1 = 'To create glosses, the following columns are required: ' \
                        + 'Dataset, Lemma ID Gloss, Annotation ID Gloss: Dutch, Annotation ID Gloss: English.'
                    e2 = 'To update glosses, column Signbank ID is required.'

                    if not error:
                        error = [e1, e2]
                    else:
                        error.append(e1).append(e2)
                    break

                else:
                    (new_gloss, already_exists, already_exists_dutch, already_exists_english, error_create) \
                        = create_gloss_from_valuedict(value_dict,my_datasets,nl)
                    creation += new_gloss
                    gloss_already_exists += already_exists
                    gloss_already_exists_dutch += already_exists_dutch
                    gloss_already_exists_english += already_exists_english
                    if len(error_create):
                        # more than one error found
                        errors_found_string = '\n'.join(error_create)
                        # print("errors found string: ", errors_found_string)

                        if not error:
                            error = [errors_found_string]
                        else:
                            error.append(errors_found_string)
                    continue
            except ValueError:
                e = 'Signbank ID must be numerical: '+ str(value_dict['Signbank ID'])

                if not error:
                    error = [e]
                else:
                    error.append(e)

                continue

            try:
                gloss = Gloss.objects.get(pk=pk)
            except ObjectDoesNotExist as e:

                e = 'Could not find gloss for ID '+str(pk)

                if not error:
                    error = [e]
                else:
                    error.append(e)

                print('import_csv gloss does not exist, line ', str(nl), ' gloss id ', str(pk))
                continue

            # print('line after gloss does not exist, line ', str(nl))
            try:
                (changes_found, errors_found) = compare_valuedict_to_gloss(value_dict,gloss,my_datasets)
                changes += changes_found
                # changes += compare_valuedict_to_gloss(value_dict,gloss)

                if len(errors_found):
                    # more than one error found
                    errors_found_string = '\n'.join(errors_found)
                    # print("errors found string: ", errors_found_string)

                    if not error:
                        error = [errors_found_string]
                    else:
                        error.append(errors_found_string)

            except MachineValueNotFoundError as e:

                # print('exception changes: ', e)

                s = str(e)

                # allow for returning multiple error messages via the exception
                if not error:
                    error = [e]
                else:
                    # print('else case')
                    error.append(e)

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
            for key, new_value in request.POST.items():

                try:
                    pk, fieldname = key.split('.')

                #In case there's no dot, this is not a value we set at the previous page
                except ValueError:
                    # when the database token csrfmiddlewaretoken is passed, there is no dot
                    # print("no dot in key error")
                    continue

                gloss = Gloss.objects.get(pk=pk)

                #Updating the keywords is a special procedure, because it has relations to other parts of the database
                if fieldname == 'Keywords':

                    update_keywords(gloss,None,new_value)
                    gloss.save()
                    continue

                if fieldname == 'SignLanguages':

                    # print('update SignLanguages')

                    new_human_value_list = [v.strip() for v in new_value.split(',')]
                    # print('Sign languages new list: ', new_human_value_list)

                    update_signlanguage(gloss,None,new_human_value_list)
                    gloss.save()
                    continue

                if fieldname == 'Dialects':

                    # print('update Dialects')

                    new_human_value_list = [v.strip() for v in new_value.split(',')]
                    # print('Dialects new list: ', new_human_value_list)

                    update_dialect(gloss,None,new_human_value_list)
                    gloss.save()
                    continue

                if fieldname == 'Dataset':

                    # this has already been checked for existance and permission in the previous step
                    # get dataset identifier
                    if new_value == 'None':
                        dataset_id = None
                    else:
                        dataset_id = Dataset.objects.get(name=new_value)
                    setattr(gloss,'dataset',dataset_id)
                    gloss.save()
                    continue

                if fieldname == 'Sequential Morphology':

                    new_human_value_list = [v.strip() for v in new_value.split(',')]
                    # print('Sequential Morphology new list: ', new_human_value_list)

                    update_sequential_morphology(gloss,None,new_human_value_list)

                    continue

                if fieldname == 'Simultaneous Morphology':

                    new_human_value_list = [v.strip() for v in new_value.split(',')]
                    # print('Sequential Simultaneous new list: ', new_human_value_list)

                    update_simultaneous_morphology(gloss,None,new_human_value_list)

                    continue

                if fieldname == 'Relations to other signs':

                    # print('update Relations to other signs')

                    new_human_value_list = [v.strip() for v in new_value.split(',')]
                    # print('Relations to other signs new list: ', new_human_value_list)

                    subst_relations(gloss,None,new_human_value_list)
                    gloss.save()    # is this needed?
                    continue

                if fieldname == 'Relations to foreign signs':

                    # print('update Relations to foreign signs')

                    new_human_value_list = [v.strip() for v in new_value.split(',')]
                    # print('Relations to foreign signs new list: ', new_human_value_list)

                    subst_foreignrelations(gloss,None,new_human_value_list)
                    gloss.save()    # is this needed?
                    continue

                if fieldname == 'Tags':

                    new_human_value_list = [v.strip().replace(' ','_') for v in new_value.split(',')]
                    # print('Tags list: ', new_human_value_list)

                    update_tags(gloss,None,new_human_value_list)
                    gloss.save()    # is this needed?
                    continue

                with override(settings.LANGUAGE_CODE):

                    #Replace the value for bools
                    if gloss._meta.get_field(fieldname).__class__.__name__ == 'NullBooleanField':

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
                        os.rename(video_path_before,video_path_after)
            stage = 2

        elif csv_create:
            # print('create glosses')

            glosses_to_create = dict()

            for key, new_value in request.POST.items():

                # print('key, new value: ', key, ', ', new_value)

                # obtain tuple values for each proposed gloss

                try:
                    pk, fieldname = key.split('.')
                    # print('field name: ', fieldname)

                    if pk not in glosses_to_create.keys():
                        glosses_to_create[pk] = dict()
                    glosses_to_create[pk][fieldname] = new_value

                #In case there's no dot, this is not a value we set at the previous page
                except ValueError:
                    # when the database token csrfmiddlewaretoken is passed, there is no dot
                    continue
            # print('dictionary: ', glosses_to_create)

            # these should be error free based on the django template import_csv.html
            for row in glosses_to_create.keys():
                lemma_id_gloss = glosses_to_create[row]['lemma_id_gloss']
                dataset = glosses_to_create[row]['dataset']
                annotation_id_gloss = glosses_to_create[row]['annotation_id_gloss']
                annotation_id_gloss_en = glosses_to_create[row]['annotation_id_gloss_en']

                if dataset == 'None':
                    dataset_id = None
                else:
                    dataset_id = Dataset.objects.get(name=dataset)
                new_gloss = Gloss()
                new_gloss.idgloss = lemma_id_gloss
                new_gloss.dataset = dataset_id
                new_gloss.annotation_idgloss = annotation_id_gloss
                new_gloss.annotation_idgloss_en = annotation_id_gloss_en
                new_gloss.save()
                # print('new gloss created: ', new_gloss.idgloss)

            stage = 2
        else:
            stage = 0

    #Show uploadform
    else:

        stage = 0

    # print('before return creation: ', creation)
    # print('before return changes: ', changes)

    return render(request,'dictionary/import_csv.html',{'form':uploadform,'stage':stage,'changes':changes,
                                                        'creation':creation,
                                                        'gloss_already_exists':gloss_already_exists,
                                                        'gloss_already_exists_dutch':gloss_already_exists_dutch,
                                                        'gloss_already_exists_english':gloss_already_exists_english,
                                                        'error':error})

def switch_to_language(request,language):

    user_profile = request.user.user_profile_user
    user_profile.last_used_language = language
    user_profile.save()

    return HttpResponse('OK')

def recently_added_glosses(request):
    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

    try:
        from signbank.settings.base import RECENTLY_ADDED_SIGNS_PERIOD
        import datetime as DT
        recently_added_signs_since_date = DT.datetime.now() - RECENTLY_ADDED_SIGNS_PERIOD
        return render(request, 'dictionary/recently_added_glosses.html',
                      {'glosses': Gloss.objects.filter(
                          creationDate__range=(recently_added_signs_since_date, DT.datetime.now())).order_by(
                          'creationDate').reverse(),
                       'dataset_languages': dataset_languages})

    except:
        return render(request,'dictionary/recently_added_glosses.html',
                      {'glosses':Gloss.objects.filter(isNew=True).order_by('creationDate').reverse(),
                       'dataset_languages': dataset_languages})


def proposed_new_signs(request):
    proposed_or_new_signs = (Gloss.objects.filter(isNew=True) |
                             TaggedItem.objects.get_intersection_by_model(Gloss, "sign:_proposed"))\
                             .order_by('creationDate').reverse()
    return render(request, 'dictionary/recently_added_glosses.html',
                  {'glosses': proposed_or_new_signs})


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

        os.remove(settings.WRITABLE_FOLDER+image_path)

        deleted_image = DeletedGlossOrMedia()
        deleted_image.item_type = 'image'
        deleted_image.idgloss = gloss.idgloss
        deleted_image.annotation_idgloss = gloss.annotation_idgloss
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


def update_cngt_counts(request,folder_index=None):

    #Run the counter script
    try:
        from CNGT_scripts.python.signCounter import SignCounter
    except ImportError:
        return HttpResponse('Counter script not present')

    folder_paths = []

    for foldername in os.listdir(settings.CNGT_EAF_FILES_LOCATION):
        if '.xml' not in foldername:
            folder_paths.append(settings.CNGT_EAF_FILES_LOCATION+foldername+'/')

    if folder_index != None:
        folder_paths = [folder_paths[int(folder_index)]]

    eaf_file_paths = []

    for folder_path in folder_paths:
        eaf_file_paths += [folder_path + f for f in os.listdir(folder_path)]

    sign_counter = SignCounter(settings.CNGT_METADATA_LOCATION,
                               eaf_file_paths,
                               settings.MINIMUM_OVERLAP_BETWEEN_SIGNING_HANDS_IN_CNGT)

    sign_counter.run()
    counts = sign_counter.get_result()

    #Save the results to Signbank
    location_to_fieldname_letter = {'Amsterdam': 'A', 'Voorburg': 'V', 'Rotterdam': 'R',
                                    'St. Michielsgestel': 'Ge', 'Groningen': 'Gr', 'Other': 'O'}

    glosses_not_in_signbank = []
    updated_glosses = []

    for idgloss, frequency_info in counts.items():

        #Collect the gloss needed
        try:
            gloss = Gloss.objects.get(annotation_idgloss=idgloss)
        except ObjectDoesNotExist:

            if idgloss != None:
                glosses_not_in_signbank.append(idgloss)

            continue

        #Save general frequency info
        gloss.tokNo = frequency_info['frequency']
        gloss.tokNoSgnr = frequency_info['numberOfSigners']
        updated_glosses.append(gloss.idgloss+' (tokNo,tokNoSgnr)')

        #Data for Mixed and Other should be added (1/3)
        otherFrequency = 0
        otherNumberofSigners = 0

        #Iterate to them, and add to gloss
        for region, data in frequency_info['frequenciesPerRegion'].items():

            frequency = data['frequency']
            numberOfSigners = data['numberOfSigners']

            #Data for Mixed and Other should be added (2/3)
            if region in ('Mixed', 'Other'):
                otherFrequency += frequency
                otherNumberofSigners += numberOfSigners
            else:
                try:
                    attribute_name = 'tokNo' + location_to_fieldname_letter[region]
                    setattr(gloss,attribute_name,frequency)
                    updated_glosses.append(gloss.idgloss + ' ('+attribute_name+')')

                    attribute_name = 'tokNoSgnr' + location_to_fieldname_letter[region]
                    setattr(gloss,attribute_name,numberOfSigners)
                    updated_glosses.append(gloss.idgloss + ' (' + attribute_name + ')')

                except KeyError:
                    continue

        #Data for Mixed and Other should be added (3/3)
        try:
            attribute_name = 'tokNo' + location_to_fieldname_letter['Other']
            setattr(gloss,attribute_name,otherFrequency)
            updated_glosses.append(gloss.idgloss + ' ('+attribute_name+')')

            attribute_name = 'tokNoSgnr' + location_to_fieldname_letter['Other']
            setattr(gloss,attribute_name,otherNumberofSigners)
            updated_glosses.append(gloss.idgloss + ' (' + attribute_name + ')')

        except KeyError:
            continue

        gloss.save()

    glosses_not_in_signbank_str = '</li><li>'.join(glosses_not_in_signbank)
    updated_glosses = '</li><li>'.join(updated_glosses)
    return HttpResponse('<p>No glosses were found for these names:</p><ul><li>'+glosses_not_in_signbank_str+'</li></ul>'+\
                        '<p>Updated glosses</p><ul><li>'+updated_glosses+'</li></ul>')

def find_and_save_variants(request):

    variant_pattern_glosses = Gloss.objects.filter(annotation_idgloss__regex=r"^(.*)\-([A-Z])$").order_by('annotation_idgloss')

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
#        print(gloss.id, '\t', str(gloss.idgloss))
        other_relations_of_sign = gloss.other_relations()

        if other_relations_of_sign:

            gloss_pattern_table[dict_key] += '<td>'

            for x in other_relations_of_sign:
                gloss_pattern_table[dict_key] += str(x.target) + '&nbsp;(' + str(x.role) + ') '

            gloss_pattern_table[dict_key] += '</td>'

        else:
            gloss_pattern_table[dict_key] += '<td>&nbsp;</td>'

        #        if (len(other_relations_of_sign) > 0):
        #            print('Other relations: ', other_relation_objects )

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
        this_sign_stem = gloss.has_stem()
        length_this_sign_stem = len(this_sign_stem)
        this_matches = r'^' + re.escape(this_sign_stem) + r'\-[A-Z]$'
        candidate_variants = Gloss.objects.filter(annotation_idgloss__regex=this_matches).exclude(idgloss=gloss).exclude(
            idgloss__in=other_relation_objects).exclude(idgloss__in=variant_relation_objects)

        if candidate_variants:
            gloss_pattern_table[dict_key] += '<td>'

            for x in candidate_variants:
                gloss_pattern_table[dict_key] += str(x.idgloss) + ' '

            gloss_pattern_table[dict_key] += '</td>'

        else:
            gloss_pattern_table[dict_key] += '<td>&nbsp;</td>'


        for target in candidate_variants:

 #           print('UPDATE REL: source=', gloss, ', target=', target)
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

#        print('Dictionary key: ', dict_key, ', ', gloss_pattern_table[dict_key])
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

    video_folder_name = 'glossvideo'
    image_folder_name = 'glossimage'

    try:
        if request.GET['small_videos'] not in [0,False,'false']:
            video_folder_name+= '_small'
    except KeyError:
        pass

    archive_file_name = '.'.join([first_part_of_file_name,timestamp_part_of_file_name,'zip'])
    archive_file_path = settings.SIGNBANK_PACKAGES_FOLDER + archive_file_name

    video_urls = signbank.tools.get_static_urls_of_files_in_writable_folder(video_folder_name,since_timestamp)
    image_urls = signbank.tools.get_static_urls_of_files_in_writable_folder(image_folder_name,since_timestamp)
    # Filter out all backup files
    video_urls = dict([(gloss_id, url) for (gloss_id, url) in video_urls.items() if not re.match('.*_\d+', url)])
    image_urls = dict([(gloss_id, url) for (gloss_id, url) in image_urls.items() if not re.match('.*_\d+', url)])

    collected_data = {'video_urls':video_urls,
                      'image_urls':image_urls,
                      'glosses':signbank.tools.get_gloss_data(since_timestamp)}

    if since_timestamp != 0:
        collected_data['deleted_glosses'] = signbank.tools.get_deleted_gloss_or_media_data('gloss',since_timestamp)
        collected_data['deleted_videos'] = signbank.tools.get_deleted_gloss_or_media_data('video',since_timestamp)
        collected_data['deleted_images'] = signbank.tools.get_deleted_gloss_or_media_data('image',since_timestamp)

    signbank.tools.create_zip_with_json_files(collected_data,archive_file_path)

    response = HttpResponse(FileWrapper(open(archive_file_path,'rb')), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename='+archive_file_name
    return response


def info(request):
    return HttpResponse(json.dumps([ settings.LANGUAGE_NAME, settings.COUNTRY_NAME ]), content_type='application/json')


def protected_media(request, filename, document_root=WRITABLE_FOLDER, show_indexes=False):

    if not request.user.is_authenticated():

        # If we are not logged in, try to find if this maybe belongs to a gloss that is free to see for everbody?
        gloss_string = filename.split('/')[-1].split('-')[0]

        try:
            if not Gloss.objects.get(idgloss=gloss_string).inWeb:
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
                # print("Signlanguage: %s; dataset: %s" % (key, new_value))
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
                except ObjectDoesNotExist as e:
                    print('Assigning glosses to a dataset resulted in an error: ' + o.message)

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
        # print(signlanguages.query)

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
