from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from tagging.models import Tag, TaggedItem
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import urlquote
from django.utils.encoding import smart_unicode

import os
import shutil
import csv

from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from signbank.feedback.models import *
from signbank.dictionary.update import update_keywords
import forms

from signbank.video.forms import VideoUploadForGlossForm
from signbank.tools import video_to_signbank, compare_valuedict_to_gloss, MachineValueNotFoundError

import signbank.settings
from django.utils.translation import override

import urlparse
from urllib import urlencode

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


    return render_to_response("dictionary/search_result.html",
                              {'form': UserSignSearchForm(),
                               'language': settings.LANGUAGE_NAME,
                               'query': '',
                               },
                               context_instance=RequestContext(request))



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
    dialects = dialects.filter(language__name__exact="Auslan")

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

    if request.GET.has_key('feedbackmessage'):
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

    return render_to_response("dictionary/word.html",
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
                               'DEFINITION_FIELDS' : settings.DEFINITION_FIELDS,
                               },
                               context_instance=RequestContext(request))

@login_required_config
def gloss(request, idgloss):
    """View of a gloss - mimics the word view, really for admin use
       when we want to preview a particular gloss"""

    if request.GET.has_key('feedbackmessage'):
        feedbackmessage = request.GET['feedbackmessage']
    else:
        feedbackmessage = False

    # we should only be able to get a single gloss, but since the URL
    # pattern could be spoofed, we might get zero or many
    # so we filter first and raise a 404 if we don't get one
    glosses = Gloss.objects.filter(idgloss=idgloss)

    if len(glosses) != 1:
        raise Http404

    gloss = glosses[0]

    # and all the keywords associated with this sign
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
    if request.GET.has_key('lastmatch'):
        lastmatch = request.GET['lastmatch']
        if lastmatch == "None":
            lastmatch = False
    else:
        lastmatch = False

    return render_to_response("dictionary/word.html",
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
                               'DEFINITION_FIELDS' : settings.DEFINITION_FIELDS,
                               },
                               context_instance=RequestContext(request))



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

from django.db.models.loading import get_model, get_apps, get_models
from django.core import serializers

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

def import_videos(request):

    out = '<p>Imported</p><ul>'
    overwritten_files = '<p>Of these files, these were overwritten</p><ul>'

    for filename in os.listdir(settings.VIDEOS_TO_IMPORT_FOLDER):

        parts = filename.split('.')
        idgloss = '.'.join(parts[:-1])
        extension = parts[-1]

        try:
            gloss = Gloss.objects.get(annotation_idgloss=idgloss)
        except ObjectDoesNotExist:
            return HttpResponse('Failed at '+filename+'. Could not find '+idgloss+'.')

        overwritten, was_allowed = video_to_signbank(settings.VIDEOS_TO_IMPORT_FOLDER,gloss,extension)

        if not was_allowed:
            return HttpResponse('Failed two overwrite '+gloss.annotation_idgloss+'. Maybe this file is not owned by the webserver?')

        out += '<li>'+filename+'</li>'

        if overwritten:
            overwritten_files += '<li>'+filename+'</li>'

    out += '</ul>'
    overwritten_files += '</ul>'

    return HttpResponse(out+overwritten_files)

def import_other_media(request):

    #First do some checks
    if not os.path.isfile(settings.OTHER_MEDIA_TO_IMPORT_FOLDER+'index.csv'):
        return HttpResponse('The required file index.csv is not present')

    for n,row in enumerate(csv.reader(open(settings.OTHER_MEDIA_TO_IMPORT_FOLDER+'index.csv'))):

        #Skip the header
        if n == 0:
            if row == ['Idgloss','filename','type','alternative_gloss']:
                continue
            else:
                return HttpResponse('The header of index.csv is not Idgloss,filename,type,alternative_gloss')

        #Create an other video for this
        try:
            idgloss, file_name, other_media_type, alternative_gloss = row
        except ValueError:
            return HttpResponse('Line '+str(n)+' does not seem to have the correct amount of items')

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

        shutil.copyfile(settings.OTHER_MEDIA_TO_IMPORT_FOLDER+file_name,goal_folder+file_name)

        #Copy at the end, so it only goes through if there was no crash before
        other_media.save()

    return HttpResponse('OK')

def try_code(request):

    """A view for the developer to try out things"""

    result = ''
    # all_id_glosses = []
    #
    # for gloss in Gloss.objects.all():
    #
    #     if gloss.idgloss in all_id_glosses:
    #         result += ' '.join([str(gloss.idgloss),str(gloss.annotation_idgloss),str(gloss.annotation_idgloss_en)]) + '<br>'
    #
    #     all_id_glosses.append(gloss.idgloss)

    for othermedia in OtherMedia.objects.all():

        othermedia.path = othermedia.path.replace('/var/www2/signbank/live/writable/othermedia/','')
        othermedia.save()

        result+= ' '+othermedia.path

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

    return render_to_response('dictionary/add_gloss.html',{'add_gloss_form':GlossCreateForm()},context_instance=RequestContext(request))

def import_csv(request):

    if not(request.user.is_staff) and len(request.user.groups.filter(name="Publisher")) == 0:
        return HttpResponse('You are not allowed to see this page.')

    uploadform = forms.CSVUploadForm
    changes = []
    error = False
    
    
    #Propose changes
    if len(request.FILES) > 0:

        changes = []
        csv_lines = request.FILES['file'].read().split('\n')

        for nl, line in enumerate(csv_lines):

            #The first line contains the keys
            if nl == 0:
                keys = line.strip().split(',')
                continue
            elif len(line) == 0:
                continue

            values = csv.reader([line]).next()
            value_dict = {}

            for nv,value in enumerate(values):

                try:
                    value_dict[keys[nv]] = value
                except IndexError:
                    pass

            try:
                pk = int(value_dict['Signbank ID'])
            except ValueError:
                continue

            gloss = Gloss.objects.get(pk=pk)

            try:
                changes += compare_valuedict_to_gloss(value_dict,gloss)
            except MachineValueNotFoundError as e:
                error = e

        stage = 1

    #Do changes
    elif len(request.POST) > 0:

        for key, new_value in request.POST.items():

            try:
                pk, fieldname = key.split('.')

            #In case there's no dot, this is not a value we set at the previous page
            except ValueError:
                continue

            gloss = Gloss.objects.get(pk=pk)

            #Updating the keywords is a special procedure, because it has relations to other parts of the database
            if fieldname == 'Keywords':

                update_keywords(gloss,None,new_value)
                gloss.save()
                continue

            with override(settings.LANGUAGE_CODE):

                #Replace the value for bools
                if gloss._meta.get_field_by_name(fieldname)[0].__class__.__name__ == 'NullBooleanField':

                    if new_value in ['true','True']:
                        new_value = True
                    else:
                        new_value = False

                #The normal change and save procedure
                setattr(gloss,fieldname,new_value)
                gloss.save()

        stage = 2

    #Show uploadform
    else:

        stage = 0

    return render_to_response('dictionary/import_csv.html',{'form':uploadform,'stage':stage,'changes':changes,'error':error},context_instance=RequestContext(request))

def switch_to_language(request,language):

    user_profile = request.user.get_profile()
    user_profile.last_used_language = language
    user_profile.save()

    return HttpResponse('OK')

def recently_added_glosses(request):

    return render_to_response('dictionary/recently_added_glosses.html', {'glosses':Gloss.objects.filter(isNew=True).order_by('creationDate').reverse()},context_instance=RequestContext(request))

def add_params_to_url(url,params):
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url = urlparse.urlunparse(url_parts)

    url_parts[4] = urlencode(query)
    return urlparse.urlunparse(url_parts)

def add_image(request):

    if request.META.has_key('HTTP_REFERER'):
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
