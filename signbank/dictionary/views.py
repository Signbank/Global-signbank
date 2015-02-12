from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from tagging.models import Tag, TaggedItem
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ObjectDoesNotExist

from django.utils.encoding import smart_unicode

import os
import csv

from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from signbank.feedback.models import *
import forms

from signbank.video.forms import VideoUploadForGlossForm
from signbank.tools import video_to_signbank, compare_valuedict_to_gloss

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
                              {'translation': trans,
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
                               'lastmatch': unicode(trans.translation)+"-"+str(n),
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
        # need to transcode the query to our encoding
        term = form.cleaned_data['query']
        category = form.cleaned_data['category']
        
        # safe search for authenticated users if the setting says so
        safe = (not request.user.is_authenticated()) and settings.ANON_SAFE_SEARCH

        try:
            term = smart_unicode(term)
        except:
            # if the encoding didn't work this is
            # a strange unicode or other string
            # and it won't match anything in the dictionary
            words = []

        if request.user.has_perm('dictionary.search_gloss'):
            # staff get to see all the words that have at least one translation
            words = Keyword.objects.filter(text__istartswith=term, translation__isnull=False).distinct()
        else:
            # regular users see either everything that's published
            words = Keyword.objects.filter(text__istartswith=term,
                                            translation__gloss__inWeb__exact=True).distinct()

        try:
            crudetag = Tag.objects.get(name='lexis:crude')
        except:
            crudetag = None
        
        if safe and crudetag != None:
            
            crude = TaggedItem.objects.get_by_model(Gloss, crudetag)
            # remove crude words from result

            result = []
            for w in words:
                # remove word if all glosses for any translation are tagged crude
                trans = w.translation_set.all()
                glosses = [t.gloss for t in trans]
                
                if not all([g in crude for g in glosses]):
                    result.append(w)
            
            words = result
            
            
        if not category in ['all', '']:
            
            tag = Tag.objects.get(name=category)
            
            result = []
            for w in words:
                trans = w.translation_set.all()
                glosses = [t.gloss for t in trans]
                for g in glosses:
                    if tag in g.tags:
                        result.append(w)
            words = result


    else:
        term = ''
        words = []


    # display the keyword page if there's only one hit and it is an exact match
    if len(words) == 1 and words[0].text == term:
        return HttpResponseRedirect('/dictionary/words/'+words[0].text+'-1.html' )

    paginator = Paginator(words, 50)
    if request.GET.has_key('page'):
        
        page = request.GET['page']
        try:
            result_page = paginator.page(page)
        except PageNotAnInteger:
            result_page = paginator.page(1)
        except EmptyPage:
            result_page = paginator.page(paginator.num_pages)

    else:
        result_page = paginator.page(1)



    return render_to_response("dictionary/search_result.html",
                              {'query' : term,
                               'form': form,
                               'paginator' : paginator,
                               'wordcount' : len(words),
                               'page' : result_page,
                               'ANON_SAFE_SEARCH': settings.ANON_SAFE_SEARCH,                                         
                               'ANON_TAG_SEARCH': settings.ANON_TAG_SEARCH,
                               'language': settings.LANGUAGE_NAME,
                               },
                              context_instance=RequestContext(request))



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

    video_folder = '/var/www2/signbank/live/writable/import_videos/';

    out = '<p>Imported</p><ul>';

    for filename in os.listdir(video_folder):

        parts = filename.split('.');
        idgloss = '.'.join(parts[:-1]);
        extension = parts[-1];

        try:
            gloss = Gloss.objects.get(annotation_idgloss=idgloss);
        except ObjectDoesNotExist:
            return HttpResponse('Failed at '+filename+'. Could not find '+idgloss+'.');

        video_to_signbank(video_folder,gloss,extension);
        out += '<li>'+filename+'</li>';

    return HttpResponse(out+'</ul>');

def try_code(request):

    """A view for the developer to try out things""";

    choicedict = {};

    choicedict['AbsOriPalm'] = (
                        ('0', 'No Value Set'),
                        ('1', 'N/A'),
                        ('2', 'Downwards'),
                        ('3', 'Towards each other'),
                        ('4', 'Backwards'),
                        ('5', 'Upwards'),
                        ('6', 'Inwards'),
                        ('7', 'Forwards'),
                        ('8', 'Backwards > forwards'),
                        ('9', 'Inwards, forwards'),
                        ('10', 'Forwards, sidewards'),
                        ('11', 'Downwards, sidewards'),
                        ('12', 'Variable'),
                        ('13', 'Outwards'),
                        ('14', 'Backs towards each other'),
                        ('15', 'Inwards > backwards'),
                        ('16', 'Sidewards'),
                        ('17', 'Forwards, downwards'),
    )

    choicedict['AbsOriFing'] = (
                        ('0', 'No Value Set'),
                        ('1', 'N/A'),
                        ('2', 'Inwards'),
                        ('3', 'Downwards'),
                        ('4', 'Upwards'),
                        ('5', 'Upwards, forwards'),
                        ('6', 'Forwards'),
                        ('7', 'Backwards'),
                        ('8', 'Towards location'),
                        ('9', 'Inwards, upwards'),
                        ('10', 'Back/palm'),
                        ('11', 'Towards each other'),
                        ('12', 'Neutral'),
                        ('13', 'Forwards > inwards'),
                        ('14', 'Towards weak hand'),
    )

    choicedict['RelOriMov'] = (
                        ('0', 'No Value Set'),
                        ('1', 'N/A'),
                        ('2', 'Pinkie'),
                        ('3', 'Palm'),
                        ('4', 'Tips'),
                        ('5', 'Thumb'),
                        ('6', 'Basis'),
                        ('7', 'Back'),
                        ('8', 'Thumb/pinkie'),
                        ('9', 'Variable'),
                        ('10', 'Basis + palm'),
                        ('11', 'Basis + basis'),
                        ('12', 'Pinkie + back'),
                        ('13', 'Palm > basis'),
                        ('14', 'Palm > back'),
                        ('15', 'Back > palm'),
                        ('16', 'Basis, pinkie'),
                        ('17', 'Pinkie > palm'),
                        ('18', 'Basis > pinkie'),
                        ('19', 'Pinkie > palm > thumb'),
                        ('20', 'Back > basis'),
                        ('21', 'Thumb > pinkie'),
    )

    choicedict['RelOriLoc'] = (
                        ('0', 'No Value Set'),
                        ('1', 'N/A'),
                        ('2', 'Pinkie/thumb'),
    )

    choicedict['HandshapeChange'] = (
                        ("0", 'No Value Set'),
                        ("1", 'N/A'),
                        ("2", '+ closing'),
                        ("3", 'Closing, opening'),
                        ("4", 'Closing a little'),
                        ("5", 'Opening'),
                        ("6", 'Closing'),
                        ("7", 'Bending'),
                        ("8", 'Curving'),
                        ("9", 'Wiggle'),
                        ("10", 'Unspreading'),
                        ("11", 'Extension'),
                        ("12", '>5'),
                        ("13", 'Partly closing'),
                        ("14", 'Closing one by one'),
                        ("15", '>s'),
                        ("16", '>b'),
                        ("17", '>a'),
                        ("18", '>1'),
                        ("19", 'Wiggle, closing'),
                        ("20", 'Thumb rubs finger'),
                        ("21", 'Spreading'),
                        ("22", '>i'),
                        ("23", '>l'),
                        ("24", '>5m'),
                        ("25", 'Thumb rubs fingers'),
                        ("26", 'Thumb curving'),
                        ("27", 'Thumbfold'),
                        ("28", 'Finger rubs thumb'),
                        ("29", '>o'),
                        ("30", '>t'),
                        ("31", 'Extension one by one'),
                    )

    choicedict['MovementShape'] = (
                        ("0", 'No Value Set'),
                        ("1", 'N/A'),
                        ("2", 'Circle sagittal > straight'),
                        ("3", 'Rotation > straight'),
                        ("4", 'Arc'),
                        ("5", 'Rotation'),
                        ("6", 'Straight'),
                        ("7", 'Flexion'),
                        ("8", 'Circle sagittal'),
                        ("9", 'Arc horizontal'),
                        ("10", 'Arc up'),
                        ("11", 'Question mark'),
                        ("12", 'Zigzag'),
                        ("13", 'Arc outside'),
                        ("14", 'Circle horizontal'),
                        ("15", 'Extension'),
                        ("16", 'Abduction'),
                        ("17", 'Straight > abduction'),
                        ("18", 'Z-shape'),
                        ("19", 'Straight + straight'),
                        ("20", 'Arc > straight'),
                        ("21", 'Parallel arc > straight'),
                        ("22", 'Zigzag > straight'),
                        ("23", 'Arc down'),
                        ("24", 'Arc + rotation'),
                        ("25", 'Arc + flexion'),
                        ("26", 'Circle parallel'),
                        ("27", 'Arc front'),
                        ("28", 'Circle horizontal small'),
                        ("29", 'Arc back'),
                        ("30", 'Waving'),
                        ("31", 'Straight, rotation'),
                        ("32", 'Circle parallel + straight'),
                        ("33", 'Down'),
                        ("34", 'Thumb rotation'),
                        ("35", 'Circle sagittal small'),
                        ("36", 'Heart-shape'),
                        ("37", 'Circle'),
                        ("38", 'Cross'),
                        ("39", 'Supination'),
                        ("40", 'Pronation'),
                        ("41", 'M-shape'),
                        ("42", 'Circle sagittal big'),
                        ("43", 'Circle parallel small'),
                     )

    choicedict['MovementDir'] = (
                        ("0", 'No Value Set'),
                        ("1", 'N/A'),
                        ("2", '+ forward'),
                        ("3", '> downwards'),
                        ("4", '> forwards'),
                        ("5", 'Backwards'),
                        ("6", 'Backwards > downwards'),
                        ("7", 'Directional'),
                        ("8", 'Downwards'),
                        ("9", 'Downwards + inwards'),
                        ("10", 'Downwards + outwards'),
                        ("11", 'Downwards > inwards'),
                        ("12", 'Downwards > outwards'),
                        ("13", 'Downwards > outwards, downwards'),
                        ("14", 'Downwards, inwards'),
                        ("15", 'Forward'),
                        ("16", 'Forwards'),
                        ("17", 'Forwards > downwards'),
                        ("18", 'Forwards > inwards'),
                        ("19", 'Forwards > sidewards > forwards'),
                        ("20", 'Forwards-backwards'),
                        ("21", 'Forwards, downwards'),
                        ("22", 'Forwards, inwards'),
                        ("23", 'Forwards, outwards'),
                        ("24", 'Forwards, upwards'),
                        ("25", 'Hands approach vertically'),
                        ("26", 'Inwards'),
                        ("27", 'Inwards > forwards'),
                        ("28", 'Inwards, downwards'),
                        ("29", 'Inwards, forwards'),
                        ("30", 'Inwards, upwards'),
                        ("31", 'No movement'),
                        ("32", 'Upwards'),
                        ("33", 'Upwards > downwards'),
                        ("34", 'Up and down'),
                        ("35", 'Upwards, inwards'),
                        ("36", 'Upwards, outwards'),
                        ("37", 'Upwards, forwards'),
                        ("38", 'Outwards'),
                        ("39", 'Outwards > downwards'),
                        ("40", 'Outwards > downwards > inwards'),
                        ("41", 'Outwards > upwards'),
                        ("42", 'Outwards, downwards > downwards'),
                        ("43", 'Outwards, forwards'),
                        ("44", 'Outwards, upwards'),
                        ("45", 'Rotation'),
                        ("46", 'To and fro'),
                        ("47", 'To and fro, forwards-backwards'),
                        ("48", 'Upwards/downwards'),
                        ("49", 'Variable'),
    )

    choicedict['MovementMan'] = (
                        ("0", 'No Value Set'),
                        ("1", 'N/A'),
                        ("2", 'Short'),
                        ("3", 'Strong'),
                        ("4", 'Slow'),
                        ("5", 'Large, powerful'),
                        ("6", 'Long'),
                        ("7", 'Relaxed'),
                        ("8", 'Trill'),
                        ("9", 'Small'),
                        ("10", 'Tense'),
    )

    choicedict['ContactType'] = (
                        ("0", 'No Value Set'),
                        ("1", 'N/A'),
                        ("2", 'Brush'),
                        ("3", 'Initial > final'),
                        ("4", 'Final'),
                        ("5", 'Initial'),
                        ("6", 'Continuous'),
                        ("7", 'Contacting hands'),
                        ("8", 'Continuous + final'),
                        ("9", 'None + initial'),
                        ("10", '> final'),
                        ("11", 'None + final'),
    )

    choicedict['NamedEntity'] = (
                        ("0", 'No Value Set'),
                        ("1", 'N/A'),
                        ("2", 'Person'),
                        ("3", 'Public figure'),
                        ("4", 'Place'),
                        ("5", 'Region'),
                        ("6", 'Brand'),
                        ("7", 'Country'),
                        ("8", 'Device'),
                        ("9", 'Product'),
                        ("10", 'Project'),
                        ("11", 'Place nickname'),
                        ("12", 'Event'),
                        ("13", 'Newspaper'),
                        ("14", 'Story character'),
                        ("15", 'Continent'),
                        ("16", 'Organisation'),
                        ("17", 'Company'),
                        ("18", 'Team'),
                        ("19", 'Drink'),
                        ("20", 'Magazine'),
    )

    for key,choices in choicedict.items():

        for machine_value,english_name in choices:
            FieldChoice(english_name=english_name,field=key,machine_value=machine_value).save();

    return HttpResponse('OK');

def import_csv(request):

    uploadform = forms.CSVUploadForm;
    changes = [];

    #Propose changes
    if len(request.FILES) > 0:

        changes = [];
        csv_lines = request.FILES['file'].read().split('\n');

        for nl, line in enumerate(csv_lines):

            #The first line contains the keys
            if nl == 0:
                keys = line.split(',');
                continue;
            elif len(line) == 0:
                continue;

            values = csv.reader([line]).next();
            value_dict = {};

            for nv,value in enumerate(values):

                try:
                    value_dict[keys[nv]] = value;
                except IndexError:
                    pass;

            try:
                pk = int(value_dict['Signbank ID']);
            except ValueError:
                continue;

            gloss = Gloss.objects.get(pk=pk);

            changes += compare_valuedict_to_gloss(value_dict,gloss);

        stage = 1;

    #Do changes
    elif len(request.POST) > 0:

        for key, new_value in request.POST.items():

            try:
                pk, fieldname = key.split('.');

            #In case there's no dot, this is not a value we set at the previous page
            except ValueError:
                continue;

            gloss = Gloss.objects.get(pk=pk);

            if gloss._meta.get_field_by_name(fieldname)[0].__class__.__name__ == 'NullBooleanField':

                if new_value in ['true','True']:
                    new_value = True;
                else:
                    new_value = False;

            setattr(gloss,fieldname,new_value);
            gloss.save();

        stage = 2;

    #Show uploadform
    else:

        stage = 0;

    return render_to_response('dictionary/import_csv.html',{'form':uploadform,'stage':stage,'changes':changes},context_instance=RequestContext(request));