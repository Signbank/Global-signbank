"""Models for the NGT database.

These are refactored from the original database to 
normalise the data and hopefully make it more
manageable.  

"""

from django.db.models import Q
from django.db import models
from django.conf import settings
from django.http import Http404 
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
import tagging

import sys, os
import json
from collections import OrderedDict
from datetime import datetime

class Translation(models.Model):
    """A Dutch translation of NGT signs"""
     
    gloss = models.ForeignKey("Gloss")
    translation = models.ForeignKey("Keyword")
    index = models.IntegerField("Index")
    
    def __str__(self):
        #return unicode(self.gloss).encode('ascii','ignore')+"-"+unicode(self.translation).encode('ascii','ignore')
        return self.gloss.idgloss.encode('utf-8') + '-' + self.translation.text.encode('utf-8')

    def get_absolute_url(self):
        """Return a URL for a view of this translation."""
        
        alltrans = self.translation.translation_set.all()
        idx = 0
        for tr in alltrans: 
            if tr == self:
                return "/dictionary/words/"+str(self.translation)+"-"+str(idx+1)+".html"
            idx += 1
        return "/dictionary/"
        
    
    class Meta:
        ordering = ['gloss', 'index']
        
    class Admin:
        list_display = ['gloss', 'translation']
        search_fields = ['gloss__idgloss']
    
    
    
class Keyword(models.Model):
    """A Dutch keyword that is a possible translation equivalent of a sign"""
    
    def __str__(self):
        return self.text.encode('utf-8')
    
    text = models.CharField(max_length=100, unique=True)
    
    def inWeb(self):
        """Return True if some gloss associated with this
        keyword is in the web version of the dictionary"""
        
        return len(self.translation_set.filter(gloss__inWeb__exact=True)) != 0
            
    class Meta:
        ordering = ['text']
        
    class Admin:
        search_fields = ['text']
        
        
        
    def match_request(self, request, n):
        """Find the translation matching a keyword request given an index 'n'
        response depends on login status
        Returns a tuple (translation, count) where count is the total number
        of matches."""
        
        if request.user.has_perm('dictionary.search_gloss'):
            alltrans = self.translation_set.all()
        else:
            alltrans = self.translation_set.filter(gloss__inWeb__exact=True)
        
        # remove crude signs for non-authenticated users if ANON_SAFE_SEARCH is on
        try:
            crudetag = tagging.models.Tag.objects.get(name='lexis:crude')
        except:
            crudetag = None
            
        safe = (not request.user.is_authenticated()) and settings.ANON_SAFE_SEARCH
        if safe and crudetag:
            alltrans = [tr for tr in alltrans if not crudetag in tagging.models.Tag.objects.get_for_object(tr.gloss)]
        
        # if there are no translations, generate a 404
        if len(alltrans) == 0:
            raise Http404
        
        # take the nth translation if n is in range
        # otherwise take the last
        if n-1 < len(alltrans):
            trans = alltrans[n-1]
        else:
            trans = alltrans[len(alltrans)-1]
        
        return (trans, len(alltrans))
    
    
DEFN_ROLE_CHOICES = (('note', 'Note'),
                     ('privatenote', 'Private Note'),
                     ('phon', 'Phonology'),
                     ('todo', 'To Do'),
                     ('sugg', 'Suggestion for other gloss'),
                     )


class Definition(models.Model):
    """An English text associated with a gloss. It's called a note in the web interface"""
    
    def __str__(self):
        return str(self.gloss)+"/"+self.role
        
    gloss = models.ForeignKey("Gloss")
    text = models.TextField()
    role = models.CharField("Type",max_length=20, choices=DEFN_ROLE_CHOICES)
    count = models.IntegerField()
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ['gloss', 'role', 'count']
        
    class Admin:
        list_display = ['gloss', 'role', 'count', 'text']
        list_filter = ['role']
        search_fields = ['gloss__idgloss']
        
class Language(models.Model):
    """A sign language name"""
        
    class Meta:
        ordering = ['name']
        
    name = models.CharField(max_length=20)
    description = models.TextField()
    
    def __str__(self):
        return self.name

class Dialect(models.Model):
    """A dialect name - a regional dialect of a given Language"""
    
    class Meta:
        ordering = ['language', 'name']
    
    language = models.ForeignKey(Language)
    name = models.CharField(max_length=20)
    description = models.TextField()
    
    def __str__(self):
        return self.language.name+"/"+self.name  

class RelationToForeignSign(models.Model):
    """Defines a relationship to another sign in another language (often a loan)"""
    
    def __str__(self):
        return str(self.gloss)+"/"+self.other_lang+','+self.other_lang_gloss;
        
    gloss = models.ForeignKey("Gloss")
    loan = models.BooleanField("Loan Sign",default=False)
    other_lang = models.CharField("Related Language",max_length=20)  
    other_lang_gloss = models.CharField("Gloss in related language",max_length=50)

    class Meta:
        ordering = ['gloss', 'loan', 'other_lang','other_lang_gloss']
        
    class Admin:
        list_display = ['gloss', 'loan', 'other_lang','other_lang_gloss']
        list_filter = ['other_lang']
        search_fields = ['gloss__idgloss']

class FieldChoice(models.Model):

    field = models.CharField(max_length=50)
    english_name = models.CharField(max_length=50)
    dutch_name = models.CharField(max_length=50)
    chinese_name = models.CharField(max_length=50)
    machine_value = models.IntegerField(help_text="The actual numeric value stored in the database. Created automatically.")

    def __unicode__(self):

        name = self.field + ': ' + self.english_name + ', ' + self.dutch_name + ' (' + str(self.machine_value) + ')'
        return name.encode('ascii',errors='replace');

    class Meta:
        ordering = ['field','machine_value']

def build_choice_list(field):

    choice_list = [];

    for choice in FieldChoice.objects.filter(field__iexact=field):
        choice_list.append((str(choice.machine_value),choice.english_name));

    choice_list = sorted(choice_list,key=lambda x: x[1]);

    return [('0','-'),('1','N/A')] + choice_list;

class Gloss(models.Model):
    
    class Meta:
        verbose_name_plural = "Glosses"
        ordering = ['idgloss']
        permissions = (('update_video', "Can Update Video"),
                       ('search_gloss', 'Can Search/View Full Gloss Details'),
                       ('export_csv', 'Can export sign details as CSV'),
                       ('export_ecv', 'Can create an ECV export file of Signbank'),
                       ('can_publish', 'Can publish signs and definitions'),
                       ('can_delete_unpublished', 'Can delete unpub signs or defs'),
                       ('can_delete_published', 'Can delete pub signs and defs'),
                       ('view_advanced_properties', 'Include all properties in sign detail view'),
                        )

    def __str__(self):
        return "%s" % (self.idgloss)
    
    def field_labels(self):
        """Return the dictionary of field labels for use in a template"""
        
        d = dict()
        for f in self._meta.fields:
            try:
                d[f.name] = _(self._meta.get_field(f.name).verbose_name)
            except:
                pass
            
        return d
    
    def admin_fields(self):
        """Return a list of field values in settings.ADMIN_RESULT_FIELDS 
        for use in the admin list view"""
        
        result = []
        for field in settings.ADMIN_RESULT_FIELDS:
            fname = self._meta.get_field(field).verbose_name

            #First, try to give the human readable choice value back
            try:
                result.append((fname, getattr(self, 'get_'+field+'_display')()))

            #If that doesn't work, give the raw value back
            except AttributeError:
                result.append((fname, getattr(self, field)))


        return result
        
    
    idgloss = models.CharField(_("ID Gloss"), unique=True, max_length=50, help_text="""
    This is the unique identifying name of an entry of a sign form in the
database. No two Sign Entry Names can be exactly the same, but a "Sign
Entry Name" can be (and often is) the same as the Annotation Idgloss.""")    
  
    annotation_idgloss = models.CharField(_("Annotation ID Gloss: Dutch"), unique=True,max_length=30, help_text="""
    This is the Dutch name of a sign used by annotators when glossing the corpus in
an ELAN annotation file. The Annotation Idgloss may be the same for two or
more entries (each with their own 'Sign Entry Name'). If two sign entries
have the same 'Annotation Idgloss' that means they differ in form in only
minor or insignificant ways that can be ignored.""") 
    # the idgloss used in transcription, may be shared between many signs

    annotation_idgloss_en = models.CharField(_("Annotation ID Gloss: English"), unique=True,blank=True, max_length=30, help_text="""
    This is the English name of a sign used by annotators when glossing the corpus in
an ELAN annotation file. The Annotation Idgloss may be the same for two or
more entries (each with their own 'Sign Entry Name'). If two sign entries
have the same 'Annotation Idgloss' that means they differ in form in only
minor or insignificant ways that can be ignored.""") 

    # languages that this gloss is part of
    language = models.ManyToManyField(Language)

    # these language fields are subsumed by the language field above
    bsltf = models.NullBooleanField(_("BSL sign"), null=True, blank=True)
    asltf = models.NullBooleanField(_("ASL sign"), null=True, blank=True)

    # these fields should be reviewed - do we put them in another class too?
    aslgloss = models.CharField(_("ASL gloss"), blank=True, max_length=50) # American Sign Language gloss
    asloantf = models.NullBooleanField(_("ASL loan sign"), null=True, blank=True)
 
    # loans from british sign language
    bslgloss = models.CharField(_("BSL gloss"), max_length=50, blank=True)
    bslloantf = models.NullBooleanField(_("BSL loan sign"), null=True, blank=True)
 
    useInstr = models.CharField(_("Annotation instructions"), max_length=50, blank=True)
    rmrks = models.CharField(_("Remarks"), max_length=50, blank=True)

    ########
    
    # one or more regional dialects that this gloss is used in
    dialect = models.ManyToManyField(Dialect)
    
    blend = models.CharField(_("Blend of"), max_length=100, null=True, blank=True) # This field type is a guess.
    blendtf = models.NullBooleanField(_("Blend"), null=True, blank=True)
    
    compound = models.CharField(_("Compound of"), max_length=100, blank=True) # This field type is a guess.
    comptf = models.NullBooleanField(_("Compound"), null=True, blank=True)
    

    # Phonology fields
    handedness = models.CharField(_("Handedness"), blank=True,  null=True, choices=build_choice_list("Handedness"), max_length=5)
    
    domhndsh = models.CharField(_("Strong Hand"), blank=True,  null=True, choices=build_choice_list("Handshape"), max_length=5)
    subhndsh = models.CharField(_("Weak Hand"), null=True, choices=build_choice_list("Handshape"), blank=True, max_length=5)
   
    final_domhndsh = models.CharField(_("Final Dominant Handshape"), blank=True,  null=True, choices=build_choice_list("Handshape"), max_length=5)
    final_subhndsh = models.CharField(_("Final Subordinate Handshape"), null=True, choices=build_choice_list("Handshape"), blank=True, max_length=5)
 
    locprim = models.CharField(_("Location"), choices=build_choice_list("Location"), null=True, blank=True,max_length=20)
    final_loc = models.IntegerField(_("Final Primary Location"), choices=build_choice_list("Location"), null=True, blank=True)
    locVirtObj = models.CharField(_("Virtual Object"), blank=True, null=True, max_length=50)

    locsecond = models.IntegerField(_("Secondary Location"), choices=build_choice_list("Location"), null=True, blank=True)
    
    initial_secondary_loc = models.CharField(_("Initial Subordinate Location"), max_length=20, null=True, blank=True)
    final_secondary_loc = models.CharField(_("Final Subordinate Location"), max_length=20, null=True, blank=True)
    
    initial_palm_orientation = models.CharField(_("Initial Palm Orientation"), max_length=20, null=True, blank=True)
    final_palm_orientation = models.CharField(_("Final Palm Orientation"), max_length=20, null=True, blank=True)
  
    initial_relative_orientation = models.CharField(_("Initial Interacting Dominant Hand Part"), null=True, max_length=20, blank=True)
    final_relative_orientation = models.CharField(_("Final Interacting Dominant Hand Part"), null=True, max_length=20, blank=True)
 
    
    inWeb = models.NullBooleanField(_("In the Web dictionary"), default=False)
    isNew = models.NullBooleanField(_("Is this a proposed new sign?"), null=True, default=False)
    
    inittext = models.CharField(max_length="50", blank=True) 

    morph = models.CharField(_("Morphemic Analysis"), max_length=50, blank=True)

    # zero or more morphemes that are used in this sign-word (=gloss) #175
    morphemePart = models.ManyToManyField('Morpheme', blank=True)

    sedefinetf = models.TextField(_("Signed English definition available"), null=True, blank=True)  # TODO: should be boolean
    segloss = models.CharField(_("Signed English gloss"), max_length=50, blank=True,  null=True)

    sense = models.IntegerField(_("Sense Number"), null=True, blank=True, help_text="If there is more than one sense of a sign enter a number here, all signs with sense>1 will use the same video as sense=1")
    sense.list_filter_sense = True

    sn = models.IntegerField(_("Sign Number"), help_text="Sign Number must be a unique integer and defines the ordering of signs in the dictionary", null=True, blank=True, unique=True)
            # this is a sign number - was trying
            # to be a primary key, also defines a sequence - need to keep the sequence
            # and allow gaps between numbers for inserting later signs
            
    StemSN = models.IntegerField(null=True, blank=True) 

    relatArtic = models.CharField(_("Relation between Articulators"), choices=build_choice_list("RelatArtic"), null=True, blank=True, max_length=5)

    absOriPalm = models.CharField(_("Absolute Orientation: Palm"), choices=build_choice_list("AbsOriPalm"), null=True, blank=True, max_length=5)
    absOriFing = models.CharField(_("Absolute Orientation: Fingers"), choices=build_choice_list("AbsOriFing"), null=True, blank=True, max_length=5)

    relOriMov = models.CharField(_("Relative Orientation: Movement"), choices=build_choice_list("RelOriMov"), null=True, blank=True, max_length=5)
    relOriLoc = models.CharField(_("Relative Orientation: Location"), choices=build_choice_list("RelOriLoc"), null=True, blank=True, max_length=5)

    oriCh = models.CharField(_("Orientation Change"),choices=build_choice_list("OriChange"), null=True, blank=True, max_length=5)

    handCh = models.CharField(_("Handshape Change"), choices=build_choice_list("HandshapeChange"), null=True, blank=True, max_length=5)

    repeat = models.NullBooleanField(_("Repeated Movement"), null=True, default=False)
    altern = models.NullBooleanField(_("Alternating Movement"), null=True, default=False)

    movSh = models.CharField(_("Movement Shape"), choices=build_choice_list("MovementShape"), null=True, blank=True, max_length=5)
    movDir = models.CharField(_("Movement Direction"), choices=build_choice_list("MovementDir"), null=True, blank=True, max_length=5)
    movMan = models.CharField(_("Movement Manner"), choices=build_choice_list("MovementMan"), null=True, blank=True, max_length=5)
    contType = models.CharField(_("Contact Type"), choices=build_choice_list("ContactType"), null=True, blank=True, max_length=5)

    phonOth = models.TextField(_("Phonology Other"), null=True, blank=True)

    mouthG = models.CharField(_("Mouth Gesture"), max_length=50, blank=True)
    mouthing = models.CharField(_("Mouthing"), max_length=50, blank=True)
    phonetVar = models.CharField(_("Phonetic Variation"), max_length=50, blank=True,)

    locPrimLH = models.CharField(_("Placement Active Articulator LH"), null=True, blank=True, max_length=5)
    locFocSite = models.CharField(_("Placement Focal Site RH"), null=True, blank=True, max_length=5)
    locFocSiteLH = models.CharField(_("Placement Focal site LH"), null=True, blank=True, max_length=5)
    initArtOri = models.CharField(_("Orientation RH (initial)"), null=True, blank=True, max_length=5)
    finArtOri = models.CharField(_("Orientation RH (final)"), null=True, blank=True, max_length=5)
    initArtOriLH = models.CharField(_("Orientation LH (initial)"), null=True, blank=True, max_length=5)
    finArtOriLH = models.CharField(_("Orientation LH (final)"), null=True, blank=True, max_length=5)

    #Semantic fields

    iconImg = models.CharField(_("Iconic Image"), max_length=50, blank=True)
    iconType = models.CharField(_("Type of iconicity"), choices=build_choice_list("iconicity"), null=True, blank=True, max_length=5)

    namEnt = models.CharField(_("Named Entity"), choices=build_choice_list("NamedEntity"), null=True, blank=True, max_length=5)
    semField = models.CharField(_("Semantic Field"), choices=build_choice_list("SemField"), null=True, blank=True, max_length=5)

    wordClass = models.CharField(_("Word class 1"), null=True, blank=True, max_length=5)
    wordClass2 = models.CharField(_("Word class 2"), null=True, blank=True, max_length=5)
    derivHist = models.CharField(_("Derivation history"), choices=build_choice_list("MovementShape"), max_length=50, blank=True)
    lexCatNotes = models.CharField(_("Lexical category notes"),null=True, blank=True, max_length=300)
    valence = models.CharField(_("Valence"), choices=build_choice_list("Valence"), null=True, blank=True, max_length=50)

    #Frequency fields

    tokNo = models.IntegerField(_("Number of Occurrences"),null=True, blank=True)
    tokNoSgnr = models.IntegerField(_("Number of Signers"),null=True, blank=True)
    tokNoA = models.IntegerField(_("Number of Occurrences in Amsterdam"),null=True, blank=True)
    tokNoV = models.IntegerField(_("Number of Occurrences in Voorburg"),null=True, blank=True)
    tokNoR = models.IntegerField(_("Number of Occurrences in Rotterdam"),null=True, blank=True)
    tokNoGe = models.IntegerField(_("Number of Occurrences in Gestel"),null=True, blank=True)
    tokNoGr = models.IntegerField(_("Number of Occurrences in Groningen"),null=True, blank=True)
    tokNoO = models.IntegerField(_("Number of Occurrences in Other Regions"),null=True, blank=True)

    tokNoSgnrA = models.IntegerField(_("Number of Amsterdam Signers"),null=True, blank=True)
    tokNoSgnrV = models.IntegerField(_("Number of Voorburg Signers"),null=True, blank=True)
    tokNoSgnrR = models.IntegerField(_("Number of Rotterdam Signers"),null=True, blank=True)
    tokNoSgnrGe = models.IntegerField(_("Number of Gestel Signers"),null=True, blank=True)
    tokNoSgnrGr = models.IntegerField(_("Number of Groningen Signers"),null=True, blank=True)
    tokNoSgnrO = models.IntegerField(_("Number of Other Region Signers"),null=True, blank=True)

    creationDate = models.DateField(_('Creation date'),default=datetime(2015,1,1))
    creator = models.ManyToManyField(User,null=True)
    alternative_id = models.CharField(max_length=50,null=True,blank=True)

    def get_fields(self):
        return [(field.name, field.value_to_string(self)) for field in Gloss._meta.fields]

    def navigation(self, is_staff):
        """Return a gloss navigation structure that can be used to
        generate next/previous links from within a template page"""
    
        result = dict() 
        result['next'] = self.next_dictionary_gloss(is_staff)
        result['prev'] = self.prev_dictionary_gloss(is_staff)
        return result
    
    def admin_next_gloss(self):
        """next gloss in the admin view, shortcut for next_dictionary_gloss with staff=True"""

        return self.next_dictionary_gloss(True)
        
    def admin_prev_gloss(self):
        """previous gloss in the admin view, shortcut for prev_dictionary_gloss with staff=True"""

        return self.prev_dictionary_gloss(True)

        
    def next_dictionary_gloss(self, staff=False):
        """Find the next gloss in dictionary order"""

        if staff:
            all_glosses_ordered =  Gloss.objects.all().order_by('annotation_idgloss')
        else:
            all_glosses_ordered = Gloss.objects.filter(inWeb__exact=True).order_by('annotation_idgloss')

        if all_glosses_ordered:

            foundit = False;

            for gloss in all_glosses_ordered:
                if gloss == self:
                    foundit = True
                elif foundit:
                    return gloss;
                    break;

        else:
            return None
 
    def prev_dictionary_gloss(self, staff=False):
        """DEPRICATED!!!! Find the previous gloss in dictionary order"""

        if self.sn == None:
            return None
        elif staff:
            set = Gloss.objects.filter(sn__lt=self.sn).order_by('-annotation_idgloss')
        else:
            set = Gloss.objects.filter(sn__lt=self.sn, inWeb__exact=True).order_by('-annotation_idgloss')
        if set:
            return set[0]
        else:
            return None     
             
    def get_absolute_url(self):
        return "/dictionary/gloss/%s.html" % self.idgloss
    
    
    def homophones(self):
        """Return the set of homophones for this gloss ordered by sense number"""
        
        if self.sense == 1:
            relations = Relation.objects.filter(role="homophone", target__exact=self).order_by('source__sense')
            homophones = [rel.source for rel in relations]
            homophones.insert(0,self)
            return homophones
        elif self.sense > 1:
            # need to find the root and see how many senses it has
            homophones = self.relation_sources.filter(role='homophone', target__sense__exact=1)
            if len(homophones) > 0:   
                root = homophones[0].target
                return root.homophones()
        return []

    def get_image_path(self):
        """Returns the path within the writable and static folder"""

        foldername = self.idgloss[:2]+'/'
        filename_without_extension = self.idgloss+'-'+str(self.pk)

        try:
            for filename in os.listdir(settings.WRITABLE_FOLDER+settings.GLOSS_IMAGE_DIRECTORY+'/'+foldername):

                if filename_without_extension in filename:
                    return settings.GLOSS_IMAGE_DIRECTORY+'/'+foldername+'/'+filename
        except OSError:
            return None

    def get_video_gloss(self):
        """Work out the gloss that might have the video for this sign, usually the sign number but
        if we're a sense>1 then we look at the homophone with sense=1
        Return the gloss instance."""
        
        if self.sense > 1:
            homophones = self.relation_sources.filter(role='homophone', target__sense__exact=1)
            # should be only zero or one of these
            if len(homophones) > 0:   
                return homophones[0].target
        return self

    def get_video_path(self):

        return 'glossvideo/'+self.idgloss[:2]+'/'+self.idgloss+'-'+str(self.pk)+'.mp4'

    def get_video(self):
        """Return the video object for this gloss or None if no video available"""

        video_path = self.get_video_path()

        if os.path.isfile(settings.MEDIA_ROOT+'/'+video_path):
            return video_path;
        else:
            return None;

        video_with_gloss = self.get_video_gloss()
        
        try:
            video = video_with_gloss.glossvideo_set.get(version__exact=0)
            return video
        except:
            return None
        
    def count_videos(self):
        """Return a count of the number of videos we have 
        for this video - ie. the number of versions stored"""
        
        
        video_with_gloss = self.get_video_gloss()
        
        return video_with_gloss.glossvideo_set.count()
    
    
    def get_video_url(self):
        """return  the url of the video for this gloss which may be that of a homophone"""

        return '/home/wessel/signbank/signbank/video/testmedia/AANBELLEN-320kbits.mp4';
         
        video = self.get_video()
        if video != None:
            return video.get_absolute_url()
        else:
            return ""
        
    def has_video(self):
        """Test to see if the video for this sign is present"""
        
        return self.get_video() != None

    def published_definitions(self):
        """Return a query set of just the published definitions for this gloss
        also filter out those fields not in DEFINITION_FIELDS"""
        

        defs = self.definition_set.filter(published__exact=True)
    
        return [d for d in defs if d.role in settings.DEFINITION_FIELDS]
    
    
    def definitions(self):
        """gather together the definitions for this gloss"""
    
        defs = dict()
        for d in self.definition_set.all().order_by('count'):
            if not defs.has_key(d.role):
                defs[d.role] = []
            
            defs[d.role].append(d.text)
        return defs
   
    def options_to_json(self, options):
        """Convert an options list to a json dict"""
        
        result = []
        for k, v in options:
            result.append('"%s":"%s"' % (k, v))
        return "{" + ",".join(result) + "}"

    def definition_role_choices_json(self):
        """Return JSON for the definition role choice list"""

        return self.options_to_json(DEFN_ROLE_CHOICES)

    def relation_role_choices_json(self):
        """Return JSON for the relation role choice list"""
        
        return self.options_to_json(RELATION_ROLE_CHOICES)    
    
    def language_choices(self):
        """Return JSON for langauge choices"""
        
        d = dict()
        for l in Language.objects.all():
            d[l.name] = l.name

        return json.dumps(d)

    def dialect_choices(self):
        """Return JSON for dialect choices"""
        
        d = dict()
        for l in Dialect.objects.all():
            d[l.name] = l.name

        return json.dumps(d)
    
    def get_choice_lists(self):
        """Return JSON for the location choice list"""
 
        choice_lists = {}; 

        #Start with your own choice lists
        for fieldname in ['handedness','locprim','domhndsh','subhndsh',
							'relatArtic','absOriPalm','absOriFing','relOriMov',
							'relOriLoc','handCh','repeat','altern','movSh',
							'movDir','movMan','contType','namEnt','oriCh','semField']:

            #Get the list of choices for this field
            li = self._meta.get_field(fieldname).choices;

            #Sort the list
            sorted_li = sorted(li,key=lambda x: x[1]);

            #Put it in another format
            reformatted_li = [('_'+str(value),text) for value,text in sorted_li]
            choice_lists[fieldname] = OrderedDict(reformatted_li);

        #Choice lists for other models
        choice_lists['morphology_role'] = [human_value for machine_value,human_value in build_choice_list('MorphologyType')];

        return json.dumps(choice_lists)

# register Gloss for tags
try:
    tagging.register(Gloss)
except tagging.AlreadyRegistered:
    pass

RELATION_ROLE_CHOICES = (('homonym', 'Homonym'),
                         ('synonym', 'Synonym'),
                         ('variant', 'Variant'),
                         ('antonym', 'Antonym'),
                         ('hyponym', 'Hyponym'),
                         ('hypernym', 'Hypernym'),
                         ('seealso', 'See Also'),
                         )

def fieldname_to_category(fieldname):

    if fieldname in ['domhndsh','subhndsh','final_domdndsh','final_subhndsh']:
        field_category = 'Handshape'
    elif fieldname in ['locprim','final_loc','loc_second']:
        field_category = 'Location'
    elif fieldname == 'handCh':
        field_category = 'handshapeChange'
    elif fieldname == 'oriCh':
        field_category = 'oriChange'
    elif fieldname == 'movSh':
        field_category = 'MovementShape'
    elif fieldname == 'movDir':
        field_category = 'MovementDir'
    elif fieldname == 'movMan':
        field_category = 'MovementMan'
    elif fieldname == 'contType':
        field_category = 'ContactType'
    elif fieldname == 'namEnt':
        field_category = 'NamedEntity'
    elif fieldname == 'iconType':
        field_category = 'iconicity'
    else:
        field_category = fieldname

    return field_category

class Relation(models.Model):
    """A relation between two glosses"""
     
    source = models.ForeignKey(Gloss, related_name="relation_sources")
    target = models.ForeignKey(Gloss, related_name="relation_targets")
    role = models.CharField(max_length=20, choices=RELATION_ROLE_CHOICES)  
                # antonym, synonym, cf (what's this? - see also), var[b-f]
                               # (what's this - variant (XXXa is the stem, XXXb is a variant)
                       
    class Admin:
        list_display = [ 'source', 'role','target']
        search_fields = ['source__idgloss', 'target__idgloss']        
        
    class Meta:
        ordering = ['source']

class MorphologyDefinition(models.Model):
    """Tells something about morphology of a gloss"""

    parent_gloss = models.ForeignKey(Gloss, related_name="parent_glosses")
    role = models.CharField(max_length=5,choices=build_choice_list('MorphologyType'))
    morpheme = models.ForeignKey(Gloss,related_name="morphemes")

    def __str__(self):

        return self.morpheme.idgloss + ' is ' + self.get_role_display() + ' of ' + self.parent_gloss.idgloss

class Morpheme(Gloss):
    """A morpheme definition uses all the fields of a gloss, but adds its own characteristics (#174)"""

    # Fields that are specific for morphemes, and not so much for 'sign-words' (=Gloss) as a whole
    # (1) optional morpheme-type field (not to be confused with MorphologyType from MorphologyDefinition)
    mrpType = models.CharField(max_length=5,blank=True,  null=True, choices=build_choice_list('MorphemeType'))

    def __str__(self):
        """Morpheme string is like a gloss but with a marker identifying it as a morpheme"""
        return "%s+M" % (self.idgloss)


    def admin_next_morpheme(self):
        """next morpheme in the admin view, shortcut for next_dictionary_morpheme with staff=True"""

        return self.next_dictionary_morpheme(True)


    def next_dictionary_morpheme(self, staff=False):
        """Find the next morpheme in dictionary order"""

        if staff:
            all_morphemes_ordered = Morpheme.objects.all().order_by('annotation_idgloss')
        else:
            all_morphemes_ordered = Morpheme.objects.filter(inWeb__exact=True).order_by('annotation_idgloss')

        if all_morphemes_ordered:

            foundit = False;

            for morpheme in all_morphemes_ordered:
                if morpheme == self:
                    foundit = True
                elif foundit:
                    return morpheme;
                    break;

        else:
            return None




class OtherMedia(models.Model):
    """Videos of or related to a gloss, often created by another project"""

    parent_gloss = models.ForeignKey(Gloss)
    type = models.CharField(max_length=5,choices=build_choice_list('OtherMediaType'))
    alternative_gloss = models.CharField(max_length=50)
    path = models.CharField(max_length=100)

# This is the wrong location, but I can't think of a better one:

class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User,related_name="user_profile_user")

    # Other fields here
    last_used_language = models.CharField(max_length=5, default=settings.LANGUAGE_CODE)
    expiry_date = models.DateField(null=True, blank=True)
    number_of_logins = models.IntegerField(null=True,default=0)

    def save(self, *args, **kwargs):
        if not self.pk:
            try:
                p = UserProfile.objects.get(user=self.user)
                self.pk = p.pk
            except UserProfile.DoesNotExist:
                pass

        super(UserProfile, self).save(*args, **kwargs)

    def __str__(self):

        return 'Profile for '+str(self.user)

def create_user_profile(sender, instance, created, **kwargs):

    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
