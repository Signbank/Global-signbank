from django.db.models import Q
from django.db import models, OperationalError
from django.conf import settings
from django.http import Http404 
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now
from django.forms.utils import ValidationError
import tagging
import re

import sys, os
import json
from collections import OrderedDict
from datetime import datetime, date

from signbank.settings.base import FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD, LANGUAGE_CODE, DEFAULT_KEYWORDS_LANGUAGE
from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value, choicelist_queryset_to_translated_dict

import signbank.settings

def build_choice_list(field):

    choice_list = []

    # Get choices for a certain field in FieldChoices, append machine_value and english_name
    try:
        for choice in FieldChoice.objects.filter(field__iexact=field):
            choice_list.append((str(choice.machine_value),choice.english_name))

        choice_list = sorted(choice_list,key=lambda x: x[1])

        return [('0','-'),('1','N/A')] + choice_list

    # Enter this exception if for example the db has no data yet (without this it is impossible to migrate)
    except:
        pass


def get_default_language_id():
    language = Language.objects.get(**DEFAULT_KEYWORDS_LANGUAGE)
    if language is not None:
        return language.id
    return None


class Translation(models.Model):
    """A Dutch translation of NGT signs"""

    gloss = models.ForeignKey("Gloss")
    language = models.ForeignKey("Language", default=get_default_language_id)
    translation = models.ForeignKey("Keyword")
    index = models.IntegerField("Index")
    
    def __str__(self):
        return self.gloss.idgloss + '-' + self.translation.text

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
        unique_together = (("gloss", "language", "translation"),)
        ordering = ['gloss', 'index']
        
    class Admin:
        list_display = ['gloss', 'translation']
        search_fields = ['gloss__idgloss']
    
class Keyword(models.Model):
    """A Dutch keyword that is a possible translation equivalent of a sign"""
    
    def __str__(self):
        return self.text
    
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


class Definition(models.Model):
    """An English text associated with a gloss. It's called a note in the web interface"""
    
    def __str__(self):
        return str(self.gloss)+"/"+self.role
        
    gloss = models.ForeignKey("Gloss")
    text = models.TextField()
    role = models.CharField("Type",max_length=20, choices=build_choice_list('NoteType'))
    count = models.IntegerField()
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ['gloss', 'role', 'count']
        
    class Admin:
        list_display = ['gloss', 'role', 'count', 'text']
        list_filter = ['role']
        search_fields = ['gloss__idgloss']


class SignLanguage(models.Model):
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
        ordering = ['signlanguage', 'name']
    
    signlanguage = models.ForeignKey(SignLanguage)
    name = models.CharField(max_length=20)
    description = models.TextField()
    
    def __str__(self):
        return self.signlanguage.name + "/" + self.name

class RelationToForeignSign(models.Model):
    """Defines a relationship to another sign in another language (often a loan)"""
    
    def __str__(self):
        return str(self.gloss)+"/"+self.other_lang+','+self.other_lang_gloss
        
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
    chinese_name = models.CharField(max_length=50, blank=True)
    machine_value = models.IntegerField(help_text="The actual numeric value stored in the database. Created automatically.")

    def __unicode__(self):

        name = self.field + ': ' + self.english_name + ', ' + self.dutch_name + ' (' + str(self.machine_value) + ')'
        return name.encode('ascii',errors='replace')

    class Meta:
        ordering = ['field','machine_value']

class Handshape(models.Model):
    machine_value = models.IntegerField(primary_key=True)
    english_name = models.CharField(max_length=50)
    dutch_name = models.CharField(max_length=50)
    chinese_name = models.CharField(max_length=50, blank=True)
    hsNumSel = models.CharField(_("Quantity"), null=True, blank=True, choices=build_choice_list("Quantity"), max_length=5)
    hsFingSel = models.CharField(_("Finger selection"), blank=True, null=True, choices=build_choice_list("FingerSelection"), max_length=5)
    hsFingSel2 = models.CharField(_("Finger selection 2"), blank=True, null=True, choices=build_choice_list("FingerSelection"), max_length=5)
    hsFingConf = models.CharField(_("Finger configuration"), blank=True, null=True, choices=build_choice_list("JointConfiguration"), max_length=5)
    hsFingConf2 = models.CharField(_("Finger configuration 2"), blank=True, null=True, choices=build_choice_list("JointConfiguration"), max_length=5)
    hsAperture = models.CharField(_("Aperture"), blank=True, null=True, choices=build_choice_list("Aperture"), max_length=5)
    hsThumb = models.CharField(_("Thumb"), blank=True, null=True, choices=build_choice_list("Thumb"), max_length=5)
    hsSpread = models.CharField(_("Spreading"), blank=True,  null=True, choices=build_choice_list("Spreading"), max_length=5)
    hsFingUnsel = models.CharField(_("Unselected fingers"), blank=True, null=True, choices=build_choice_list("FingerSelection"), max_length=5)
    fsT = models.NullBooleanField(_("T"), null=True, default=False)
    fsI = models.NullBooleanField(_("I"), null=True, default=False)
    fsM = models.NullBooleanField(_("M"), null=True, default=False)
    fsR = models.NullBooleanField(_("R"), null=True, default=False)
    fsP = models.NullBooleanField(_("P"), null=True, default=False)
    fs2T = models.NullBooleanField(_("T2"), null=True, default=False)
    fs2I = models.NullBooleanField(_("I2"), null=True, default=False)
    fs2M = models.NullBooleanField(_("M2"), null=True, default=False)
    fs2R = models.NullBooleanField(_("R2"), null=True, default=False)
    fs2P = models.NullBooleanField(_("P2"), null=True, default=False)
    ufT = models.NullBooleanField(_("Tu"), null=True, default=False)
    ufI = models.NullBooleanField(_("Iu"), null=True, default=False)
    ufM = models.NullBooleanField(_("Mu"), null=True, default=False)
    ufR = models.NullBooleanField(_("Ru"), null=True, default=False)
    ufP = models.NullBooleanField(_("Pu"), null=True, default=False)

    def field_labels(self):
        """Return the dictionary of field labels for use in a template"""

        d = dict()
        for f in self._meta.fields:
            try:
                d[f.name] = _(self._meta.get_field(f.name).verbose_name)
            except:
                pass

        return d

    def get_image_path(self,check_existance=True):
        """Returns the path within the writable and static folder"""

        foldername = str(self.machine_value)+'/'
        filename_without_extension = 'handshape_'+str(self.machine_value)

        dir_path = settings.WRITABLE_FOLDER+settings.HANDSHAPE_IMAGE_DIRECTORY+'/'+foldername

        if check_existance:
            try:
                for filename in os.listdir(dir_path):

                    if filename_without_extension in filename:
                        return settings.HANDSHAPE_IMAGE_DIRECTORY+'/'+foldername+'/'+filename
            except OSError:
                return None
        else:
            return settings.HANDSHAPE_IMAGE_DIRECTORY+'/'+foldername+'/'+filename_without_extension

    def get_fingerSelection_display(self):

        selection = ''
        if self.fsT:
            selection += 'T'
        if self.fsI:
            selection += 'I'
        if self.fsM:
            selection += 'M'
        if self.fsR:
            selection += 'R'
        if self.fsP:
            selection += 'P'
        return selection

    def get_fingerSelection2_display(self):

        selection = ''
        if self.fs2T:
            selection += 'T'
        if self.fs2I:
            selection += 'I'
        if self.fs2M:
            selection += 'M'
        if self.fs2R:
            selection += 'R'
        if self.fs2P:
            selection += 'P'
        return selection

    def get_unselectedFingers_display(self):

        selection = ''
        if self.ufT:
            selection += 'T'
        if self.ufI:
            selection += 'I'
        if self.ufM:
            selection += 'M'
        if self.ufR:
            selection += 'R'
        if self.ufP:
            selection += 'P'
        return selection

    def count_selected_fingers(self):

        count_selected_fingers = 0
        if self.fsT:
            count_selected_fingers += 1
        if self.fsI:
            count_selected_fingers += 1
        if self.fsM:
            count_selected_fingers += 1
        if self.fsR:
            count_selected_fingers += 1
        if self.fsP:
            count_selected_fingers += 1
        return count_selected_fingers

class Gloss(models.Model):
    
    class Meta:
        verbose_name_plural = "Glosses"
        # ordering: for Lemma View in the Gloss List View, we need to have glosses in the same Lemma Group sorted
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
        return self.idgloss

    def field_labels(self):
        """Return the dictionary of field labels for use in a template"""
        
        d = dict()
        for f in self._meta.fields:
            try:
                d[f.name] = _(self._meta.get_field(f.name).verbose_name)
            except:
                pass
            
        return d

    dataset = models.ForeignKey("Dataset", verbose_name=_("Dataset"),
                                help_text=_("Dataset a gloss is part of"), null=True)
    
    idgloss = models.CharField(_("Lemma ID Gloss"), max_length=50, help_text="""
    This is the unique identifying name of an entry of a sign form in the
database. No two Sign Entry Names can be exactly the same, but a "Sign
Entry Name" can be (and often is) the same as the Annotation Idgloss.""")    

    # languages that this gloss is part of
    signlanguage = models.ManyToManyField(SignLanguage)

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
    weakdrop = models.NullBooleanField(_("WD"), null=True, blank=True)
    weakprop = models.NullBooleanField(_("WP"), null=True, blank=True)

    domhndsh = models.CharField(_("Strong Hand"), blank=True,  null=True, choices=build_choice_list("Handshape"), max_length=5)
    subhndsh = models.CharField(_("Weak Hand"), null=True, choices=build_choice_list("Handshape"), blank=True, max_length=5)

    # Support for handshape etymology
    domhndsh_number = models.NullBooleanField(_("number"), null=True, blank=True)
    domhndsh_letter = models.NullBooleanField(_("letter"), null=True, blank=True)
    subhndsh_number = models.NullBooleanField(_("number"), null=True, blank=True)
    subhndsh_letter = models.NullBooleanField(_("letter"), null=True, blank=True)

    final_domhndsh = models.CharField(_("Final Dominant Handshape"), blank=True,  null=True, choices=build_choice_list("Handshape"), max_length=5)
    final_subhndsh = models.CharField(_("Final Subordinate Handshape"), null=True, choices=build_choice_list("Handshape"), blank=True, max_length=5)
 
    locprim = models.CharField(_("Location"), choices=build_choice_list("Location"), null=True, blank=True,max_length=20)
    final_loc = models.IntegerField(_("Final Primary Location"), choices=build_choice_list("Location"), null=True, blank=True)
    locVirtObj = models.CharField(_("Virtual Object"), blank=True, null=True, max_length=50)

    locsecond = models.IntegerField(_("Secondary Location"), choices=build_choice_list("Location"), null=True, blank=True)
    
    initial_secondary_loc = models.CharField(_("Initial Subordinate Location"), choices=build_choice_list("Location"), max_length=20, null=True, blank=True)
    final_secondary_loc = models.CharField(_("Final Subordinate Location"), choices=build_choice_list("Location"), max_length=20, null=True, blank=True)
    
    initial_palm_orientation = models.CharField(_("Initial Palm Orientation"), max_length=20, null=True, blank=True)
    final_palm_orientation = models.CharField(_("Final Palm Orientation"), max_length=20, null=True, blank=True)
  
    initial_relative_orientation = models.CharField(_("Initial Interacting Dominant Hand Part"), null=True, max_length=20, blank=True)
    final_relative_orientation = models.CharField(_("Final Interacting Dominant Hand Part"), null=True, max_length=20, blank=True)

    domSF = models.CharField("Dominant hand - Selected Fingers", choices=build_choice_list("DominantHandSelectedFingers"), null=True, blank=True, max_length=5)
    domFlex = models.CharField("Dominant hand - Flexion", choices=build_choice_list("DominantHandFlexion"), null=True, blank=True, max_length=5)
    oriChAbd = models.NullBooleanField(_("Abduction change"), null=True, blank=True)
    oriChFlex = models.NullBooleanField(_("Flexion change"), null=True, blank=True)

    inWeb = models.NullBooleanField(_("In the Web dictionary"), default=False)
    isNew = models.NullBooleanField(_("Is this a proposed new sign?"), null=True, default=False)
    excludeFromEcv = models.NullBooleanField(_("Exclude from ECV"), default=False)
    
    inittext = models.CharField(max_length=50, blank=True)

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

    locPrimLH = models.CharField(_("Placement Active Articulator LH"), choices=build_choice_list("Location"), null=True, blank=True, max_length=5)
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

    wordClass = models.CharField(_("Word class"), null=True, blank=True, max_length=5, choices=build_choice_list('WordClass'))
    wordClass2 = models.CharField(_("Word class 2"), null=True, blank=True, max_length=5, choices=build_choice_list('WordClass'))
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
    lastUpdated = models.DateTimeField(_('Last updated'),auto_now=True)
    creator = models.ManyToManyField(User)
    alternative_id = models.CharField(max_length=50,null=True,blank=True)

    def get_fields(self):
        return [(field.name, field.value_to_string(self)) for field in Gloss._meta.fields]

    def get_fields_dict(self):
        # this function might be obsolete
        fields = {}
        for field in Gloss._meta.fields:
            if field.name in settings.API_FIELDS:
                category = fieldname_to_category(field.name)
                if category != field.name:
                    if not category in fields:
                        fields[category] = {}
                    fields[category][field.verbose_name.title()] = field.value_to_string(self)
                else:
                    fields[field.verbose_name.title()] = field.value_to_string(self)

        # Annotation Idgloss translations
        if self.dataset:
            for language in self.dataset.translation_languages.all():
                annotationidglosstranslation = self.annotationidglosstranslation_set.filter(language=language)
                if annotationidglosstranslation and len(annotationidglosstranslation) > 0:
                    fields[_("Annotation ID Gloss") + ": %s" % language.name] = annotationidglosstranslation[0].text

        # Get all the keywords associated with this sign
        allkwds = ", ".join([x.translation.text for x in self.translation_set.all()])
        fields[Translation.__name__ + "s"] = allkwds

        # Get morphology
        fields[Morpheme.__name__ + "s"] = ", ".join([x.__str__() for x in self.simultaneous_morphology.all()])

        #
        fields["Parent glosses"] = ", ".join([x.__str__() for x in self.parent_glosses.all()])

        fields["Link"] = signbank.settings.base.URL + '/dictionary/gloss/' + str(self.pk)

        return fields

    @property
    def get_phonology_display(self):
        fields = []
        choice_list = []
        for field in ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim','locVirtObj',
          'relOriMov','relOriLoc','oriCh','contType','movSh','movDir','repeat','altern','phonOth', 'mouthG',
          'mouthing', 'phonetVar',]:

            # Get and save the choice list for this field
            fieldchoice_category = fieldname_to_category(field)
            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)
            field_value = getattr(self,field)
            human_value = machine_value_to_translated_human_value(field_value, choice_list, LANGUAGE_CODE)
            if (human_value == '-' or human_value == ' ' or human_value == '' or human_value == None) :
                human_value = '   '
            else:
                human_value = str(human_value)
            fields = fields + [(field,human_value)]

        return fields

    def navigation(self, is_staff):
        """Return a gloss navigation structure that can be used to
        generate next/previous links from within a template page"""
    
        result = dict() 
        result['next'] = self.next_dictionary_gloss(is_staff)
        result['prev'] = self.prev_dictionary_gloss(is_staff)
        return result

    @staticmethod
    def none_morpheme_objects():
        """Get all the GLOSS objects, but excluding the MORPHEME ones"""
        return Gloss.objects.filter(morpheme=None)

    def is_morpheme(self):
        """Test if this instance is a Morpheme or (just) a Gloss"""
        return hasattr(self, 'morpheme')
    
    def admin_next_gloss(self):
        """next gloss in the admin view, shortcut for next_dictionary_gloss with staff=True"""

        return self.next_dictionary_gloss(True)
        
    def admin_prev_gloss(self):
        """previous gloss in the admin view, shortcut for prev_dictionary_gloss with staff=True"""

        return self.prev_dictionary_gloss(True)

        
    def next_dictionary_gloss(self, staff=False):
        """Find the next gloss in dictionary order"""

        if staff:
            # Make sure we only include the none-Morpheme glosses
            all_glosses_ordered = Gloss.none_morpheme_objects().order_by('idgloss')
        else:
            all_glosses_ordered = Gloss.objects.filter(inWeb__exact=True).order_by('idgloss')

        if all_glosses_ordered:

            foundit = False

            for gloss in all_glosses_ordered:
                if gloss == self:
                    foundit = True
                elif foundit:
                    return gloss
                    break

        else:
            return None
 
    def prev_dictionary_gloss(self, staff=False):
        """DEPRICATED!!!! Find the previous gloss in dictionary order"""

        if self.sn == None:
            return None
        elif staff:
            set = Gloss.objects.filter(sn__lt=self.sn).order_by('-idgloss')
        else:
            set = Gloss.objects.filter(sn__lt=self.sn, inWeb__exact=True).order_by('-idgloss')
        if set:
            return set[0]
        else:
            return None

    def get_absolute_url(self):
        return "/dictionary/gloss/%s.html" % self.idgloss

    def lemma_group(self):
        glosses_with_same_lemma_group = Gloss.objects.filter(idgloss__iexact=self.idgloss).exclude(pk=self.pk)

        return glosses_with_same_lemma_group
    
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

    def homonyms_count(self):

        homonyms_count = self.relation_sources.filter(role='homonym').count()

        return homonyms_count

    def synonyms_count(self):

        synonyms_count = self.relation_sources.filter(role='synonym').count()

        return synonyms_count

    def antonyms_count(self):

        antonyms_count = self.relation_sources.filter(role='antonym').count()

        return antonyms_count

    def hyponyms_count(self):

        hyponyms_count = self.relation_sources.filter(role='hyponym').count()

        return hyponyms_count

    def hypernyms_count(self):

        hypernyms_count = self.relation_sources.filter(role='hypernym').count()

        return hypernyms_count

    def seealso_count(self):

        seealso_count = self.relation_sources.filter(role='seealso').count()

        return seealso_count

    def variant_count(self):

        variant_count = self.relation_sources.filter(role='variant').count()

        return variant_count

    def relations_count(self):

        relations_count = self.relation_sources.filter(role__in=['homonym','synonyn','antonym','hyponym','hypernym','seealso','variant']).count()

        return relations_count

    def has_variants(self):

        variant_relations_of_sign = self.variant_relations()

        variant_relation_objects = [ x.target for x in variant_relations_of_sign ]

        return variant_relation_objects

    def pattern_variants(self):

        # Build query
        this_sign_stems = self.get_stems()
        queries = []
        for this_sign_stem in this_sign_stems:
            this_matches = r'^' + re.escape(this_sign_stem[1]) + r'\-[A-Z]$'
            queries.append(Q(annotationidglosstranslation__text__regex=this_matches,
                             dataset=self.dataset, annotationidglosstranslation__language=this_sign_stem[0]))
        query = queries.pop()
        for q in queries:
            query |= q

        other_relations_of_sign = self.other_relations()
        other_relation_objects = [x.target for x in other_relations_of_sign]

        pattern_variants = Gloss.objects.filter(query).exclude(idgloss=self).exclude(
            idgloss__in=other_relation_objects)

        return pattern_variants

    def other_relations(self):

        other_relations = self.relation_sources.filter(role__in=['homonym','synonyn','antonym','hyponym','hypernym','seealso'])

        return other_relations

    def variant_relations(self):

        variant_relations = self.relation_sources.filter(role__in=['variant'])

        return variant_relations

    def homonym_relations(self):

        homonym_relations = self.relation_sources.filter(role__in=['homonym'])

        homonyms = [x.target for x in homonym_relations]

        return homonyms

    def get_stems(self):

        stems = [(x.language, x.text[:-2]) for x in self.annotationidglosstranslation_set.all() if x.text[-2] == '-']

        return stems

    def gloss_relations(self):

        variant_relations = self.relation_sources.filter(role__in=['variant'])

        other_relations = self.relation_sources.filter(role__in=['homonym','synonyn','antonym','hyponym','hypernym','seealso'])

        return (other_relations, variant_relations)

    def empty_non_empty_phonology(self):

        choice_lists = []
        non_empty_phonology = []
        empty_phonology = []

        fieldLabel = {'handedness':'Handedness','domhndsh':'Strong Hand','subhndsh':'Weak Hand',
		  'handCh':'Handshape Change','relatArtic':'Relation between Articulators','locprim':'Location','locVirtObj':'Virual Object',
          'relOriMov':'Relative Orientation: Movement','relOriLoc':'Relative Orientation: Location','oriCh':'Orientation Change',
		  'contType':'Contact Type','movSh':'Movement Shape','movDir':'Movement Direction','repeat':'Repeated Movement',
		  'altern':'Alternating Movement','phonOth':'Phonology Other','mouthG':'Mouth Gesture',
          'mouthing':'Mouthing','phonetVar':'Phonetic Variation'}

        for field in ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim',
          'relOriMov','relOriLoc','oriCh','contType','movSh','movDir',]:

            # Get and save the choice list for this field
            fieldchoice_category = fieldname_to_category(field)
            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)

            # Take the human value in the language we are using
            machine_value = getattr(self,field)
            human_value = machine_value_to_translated_human_value(machine_value, choice_list, LANGUAGE_CODE)
            label = fieldLabel[field]
            if (human_value == '-' or human_value == ' ' or human_value == '' or human_value == None) :
                empty_phonology = empty_phonology + [(field,str(label))]
            else :
                non_empty_phonology = non_empty_phonology + [(field, str(label), str(human_value))]

        for field in ['repeat', 'altern']:
            machine_value = getattr(self,field)
            label = fieldLabel[field]

            if (machine_value):
                fieldchoice_category = fieldname_to_category(field)
                choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)
                human_value = machine_value_to_translated_human_value(machine_value, choice_list, LANGUAGE_CODE)

                non_empty_phonology = non_empty_phonology + [(field, str(label), str(human_value))]
            else:
                empty_phonology = empty_phonology + [(field,str(label))]

        return (empty_phonology, non_empty_phonology)


    def non_empty_phonology(self):

        fieldLabel = {'handedness': 'Handedness', 'domhndsh': 'Strong Hand', 'subhndsh': 'Weak Hand',
                      'handCh': 'Handshape Change', 'relatArtic': 'Relation between Articulators',
                      'locprim': 'Location', 'locVirtObj': 'Virual Object',
                      'relOriMov': 'Relative Orientation: Movement', 'relOriLoc': 'Relative Orientation: Location',
                      'oriCh': 'Orientation Change',
                      'contType': 'Contact Type', 'movSh': 'Movement Shape', 'movDir': 'Movement Direction',
                      'repeat': 'Repeated Movement',
                      'altern': 'Alternating Movement', 'phonOth': 'Phonology Other', 'mouthG': 'Mouth Gesture',
                      'mouthing': 'Mouthing', 'phonetVar': 'Phonetic Variation'}

        non_empty_phonology = []

        for field in ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim',
                      'relOriMov', 'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', ]:

            fieldchoice_category = fieldname_to_category(field)
            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)

            machine_value = getattr(self, field)
            human_value = machine_value_to_translated_human_value(machine_value, choice_list, LANGUAGE_CODE)
            label = fieldLabel[field]

            if not (human_value == '-' or human_value == ' ' or human_value == '' or human_value == None) :
                 non_empty_phonology = non_empty_phonology + [(field,str(label),str(human_value))]

        for field in ['repeat', 'altern']:
            machine_value = getattr(self,field)
            label = fieldLabel[field]

            if (machine_value):
                fieldchoice_category = fieldname_to_category(field)
                choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)
                human_value = machine_value_to_translated_human_value(machine_value, choice_list, LANGUAGE_CODE)

                non_empty_phonology = non_empty_phonology + [(field, str(label), str(human_value))]

        return non_empty_phonology

    def phonology_matrix(self):

        phonology_dict = dict()

        for field in ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim', 'locVirtObj',
                      'relOriMov', 'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', 'repeat', 'altern', 'phonOth',
                      'mouthG',
                      'mouthing', 'phonetVar', ]:

            fieldchoice_category = fieldname_to_category(field)
            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)

            phonology_dict[field] = ''

            machine_value = getattr(self, field)
            human_value = machine_value_to_translated_human_value(machine_value, choice_list, LANGUAGE_CODE)

            if not (human_value == '-' or human_value == ' ' or human_value == '' or human_value == None):
                phonology_dict[field] = machine_value

        return phonology_dict


    # Minimal Pairs
    # 19 total phonology fields
    # omit fields 'locVirtObj': 'Virual Object', 'phonOth': 'Phonology Other', 'mouthG': 'Mouth Gesture', 'mouthing': 'Mouthing', 'phonetVar': 'Phonetic Variation'
    # 14
    def minimal_pairs_objects(self):

        paren = ')'

        phonology_for_gloss = self.phonology_matrix()

        where_minimal_pairs_filled = ''
        where_minimal_pairs_empty = ''
        count_empty = 0
        count_filled = 0

        for field in ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim', 'relOriMov', 'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', 'repeat', 'altern', ]:
            value_of_this_field = str(phonology_for_gloss[field])

            if (value_of_this_field == '-' or value_of_this_field == ' ' or value_of_this_field == '' or value_of_this_field == None):
                if (where_minimal_pairs_empty.endswith(paren)):
                    where_minimal_pairs_empty += " + (" + field + " IS NOT NULL AND " \
                                                 + field + "!=0 AND " + field + "!='-' AND " + field + "!='' AND " + field + "!=' ')"
                else:
                    where_minimal_pairs_empty += "(" + field + " IS NOT NULL AND " \
                                                 + field + "!=0 AND " + field + "!='-' AND " + field + "!='' AND " + field + "!=' ')"
                count_empty = count_empty + 1
            elif (value_of_this_field == 'False'):
                if (where_minimal_pairs_empty.endswith(paren)):
                    where_minimal_pairs_empty += ' + (' + field + '=1)'
                else:
                    where_minimal_pairs_empty += '(' + field + '=1)'
                count_empty = count_empty + 1
            elif (value_of_this_field == 'True'):
                if (where_minimal_pairs_filled.endswith(paren)):
                    where_minimal_pairs_filled += ' + (' + field + '=0)'
                else:
                    where_minimal_pairs_filled += '(' + field + '=0)'
                count_filled = count_filled + 1
            else:
                if (where_minimal_pairs_filled.endswith(paren)):
                    where_minimal_pairs_filled += ' + (' + field + '!=' + value_of_this_field + ')'
                else:
                    where_minimal_pairs_filled += '(' + field + '!=' + value_of_this_field + ')'
                count_filled = count_filled + 1

        where_minimal_pairs = '(' + where_minimal_pairs_filled +  ' + ' + where_minimal_pairs_empty + ')=1'

        qs = Gloss.objects.raw('SELECT * FROM dictionary_gloss WHERE ' + where_minimal_pairs)

        return qs

    def minimal_pairs_dict(self):

        fieldKind = {'handedness': 'list', 'domhndsh': 'list', 'subhndsh': 'list',
                      'handCh': 'list', 'relatArtic': 'list',
                      'locprim': 'list', 'locVirtObj': 'text',
                      'relOriMov': 'list', 'relOriLoc': 'list',
                      'oriCh': 'list',
                      'contType': 'list', 'movSh': 'list', 'movDir': 'list',
                      'repeat': 'check',
                      'altern': 'check', 'phonOth': 'text', 'mouthG': 'text',
                      'mouthing': 'text', 'phonetVar': 'text'}

        minimal_pairs_fields = dict()

        # If handedness is not defined for this gloss, don't bother to look up minimal pairs
        if (self.handedness is None or self.handedness == '0'):
            return minimal_pairs_fields

        # Restrict minimal pairs search if gloss has empty phonology field for Strong Hand
        if (self.domhndsh is None or self.domhndsh == '0'):
            return minimal_pairs_fields

        wmp = self.minimal_pairs_objects()

        (ep, nep) = self.empty_non_empty_phonology()

        for o in wmp:
            different_fields = dict()
            onep = o.non_empty_phonology()
            for f,n,v in onep:
                fc = fieldname_to_category(f)
                self_value_f = getattr(self,f)
                other_value_f = getattr(o,f)
                if self_value_f != other_value_f:
                     different_fields[f] = (n, fc,self_value_f,other_value_f,fieldKind[f])
            if (len(list(different_fields.keys())) == 0):
                for sf,sn,sv in nep:
                    sfc = fieldname_to_category(sf)
                    self_value_sf = getattr(self, sf)
                    other_value_sf = getattr(o,sf)
                    if other_value_sf != self_value_sf:
                        different_fields[sf] = (sn, sfc,self_value_sf,'0',fieldKind[sf])

            minimal_pairs_fields[o] = different_fields

        return minimal_pairs_fields

    # Homonyms
    # 19 total phonology fields
    # omit fields 'locVirtObj': 'Virual Object', 'phonOth': 'Phonology Other', 'mouthG': 'Mouth Gesture', 'mouthing': 'Mouthing', 'phonetVar': 'Phonetic Variation'
    # 14
    def homonym_objects(self):

        paren = ')'

        phonology_for_gloss = self.phonology_matrix()

        homonym_objects_list = []

        where_homonyms_filled = ''
        where_homonyms_empty = ''
        where_homonyms = ''
        count_empty = 0
        count_filled = 0

        for field in ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim', 'relOriMov', 'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', 'repeat', 'altern', ]:
            value_of_this_field = str(phonology_for_gloss[field])

            if (value_of_this_field == '-' or value_of_this_field == ' ' or value_of_this_field == '' or value_of_this_field == None):
                if (where_homonyms_empty.endswith(paren)):
                    where_homonyms_empty += " + (" + field + " IS NOT NULL AND " \
                                                 + field + "!=0 AND " + field + "!='-' AND " + field + "!='' AND " + field + "!=' ')"
                else:
                    where_homonyms_empty += "(" + field + " IS NOT NULL AND " \
                                                 + field + "!=0 AND " + field + "!='-' AND " + field + "!='' AND " + field + "!=' ')"
                count_empty = count_empty + 1
            elif (value_of_this_field == 'False'):
                if (where_homonyms_empty.endswith(paren)):
                    where_homonyms_empty += ' + (' + field + '=1)'
                else:
                    where_homonyms_empty += '(' + field + '=1)'
                count_empty = count_empty + 1
            elif (value_of_this_field == 'True'):
                if (where_homonyms_filled.endswith(paren)):
                    where_homonyms_filled += ' + (' + field + '=0)'
                else:
                    where_homonyms_filled += '(' + field + '=0)'
                count_filled = count_filled + 1
            else:
                if (where_homonyms_filled.endswith(paren)):
                    where_homonyms_filled += ' + (' + field + '!=' + value_of_this_field + ')'
                else:
                    where_homonyms_filled += '(' + field + '!=' + value_of_this_field + ')'
                count_filled = count_filled + 1

        where_homonyms = '(' + where_homonyms_filled +  ' + ' + where_homonyms_empty + ')=0'

        qs = Gloss.objects.raw('SELECT * FROM dictionary_gloss WHERE id != %s AND ' + where_homonyms, [self.id])

        for o in qs:
            homonym_objects_list.append(o)

        return homonym_objects_list


    def homonyms(self):

        phonology_for_gloss = self.phonology_matrix()

        homonyms_of_this_gloss = []

        gloss_homonym_relations = self.relation_sources.filter(role='homonym')

        list_of_homonym_relations = [ r for r in gloss_homonym_relations ]

        targets_of_homonyms_of_this_gloss = [ r.target for r in gloss_homonym_relations ]

        paren = ')'

        phonology_for_gloss = self.phonology_matrix()

        handedness_of_this_gloss = str(phonology_for_gloss['handedness'])
        # Ignore homonyms when the Handedness of this gloss is X
        handedness_X = str(FieldChoice.objects.get(field__iexact='Handedness', english_name__exact='X').machine_value)

        if (handedness_of_this_gloss == '-' or handedness_of_this_gloss == ' ' or handedness_of_this_gloss == '' or
                    handedness_of_this_gloss == None or handedness_of_this_gloss == handedness_X):

            return ([], [], [])

        where_homonyms_filled = ''
        where_homonyms_empty = ''
        where_homonyms = ''
        count_empty = 0
        count_filled = 0

        for field in ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim',
                      'relOriMov', 'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', 'repeat', 'altern', ]:
            value_of_this_field = str(phonology_for_gloss[field])

            if (value_of_this_field == '-' or value_of_this_field == ' ' or value_of_this_field == '' or value_of_this_field == None):
                if (where_homonyms_empty.endswith(paren)):
                    where_homonyms_empty += " + (" + field + " IS NULL OR " + field + "=0 OR " + field + "='-' OR " + field + "='' OR " + field + "=' ')"
                else:
                    where_homonyms_empty += "(" + field + " IS NULL OR " + field + "=0 OR " + field + "='-' OR " + field + "='' OR " + field + "=' ')"
                count_empty = count_empty + 1
            elif (value_of_this_field == 'False'):
                if (where_homonyms_empty.endswith(paren)):
                    where_homonyms_empty += ' + (' + field + " IS NULL OR " + field + '=0)'
                else:
                    where_homonyms_empty += '(' + field + " IS NULL OR " + field + '=0)'
                count_empty = count_empty + 1
            elif (value_of_this_field == 'True'):
                if (where_homonyms_filled.endswith(paren)):
                    where_homonyms_filled += ' + (' + field + '=1)'
                else:
                    where_homonyms_filled += '(' + field + '=1)'
                count_filled = count_filled + 1
            else:
                if (where_homonyms_filled.endswith(paren)):
                    where_homonyms_filled += ' + (' + field + '=' + value_of_this_field + ')'
                else:
                    where_homonyms_filled += '(' + field + '=' + value_of_this_field + ')'
                count_filled = count_filled + 1

        where_homonyms = '(' + where_homonyms_filled + ' + ' + where_homonyms_empty + ')=14'

        qs = Gloss.objects.raw('SELECT * FROM dictionary_gloss WHERE ' + where_homonyms)

        match_glosses = [g for g in qs]

        for other_gloss in match_glosses:
            if other_gloss != self:
                    homonyms_of_this_gloss += [other_gloss]

        homonyms_not_saved = []
        saved_but_not_homonyms = []

        for r in list_of_homonym_relations:
            if (not r.target in homonyms_of_this_gloss):
                saved_but_not_homonyms += [r.target]
        for h in homonyms_of_this_gloss:
            if (not h in targets_of_homonyms_of_this_gloss):
                homonyms_not_saved += [h]

        return (homonyms_of_this_gloss, homonyms_not_saved, saved_but_not_homonyms)

    def get_image_path(self,check_existance=True):
        """Returns the path within the writable and static folder"""

        foldername = self.idgloss[:2]+'/'
        filename_without_extension = self.idgloss+'-'+str(self.pk)

        dir_path = settings.WRITABLE_FOLDER+settings.GLOSS_IMAGE_DIRECTORY+'/'+foldername

        if check_existance:
            try:
                for filename in os.listdir(dir_path):

                    if filename_without_extension in filename:
                        return settings.GLOSS_IMAGE_DIRECTORY+'/'+foldername+'/'+filename
            except OSError:
                return None
        else:
            return settings.GLOSS_IMAGE_DIRECTORY+'/'+foldername+'/'+filename_without_extension


    def get_video_gloss(self):
        """Work out the gloss that might have the video for this sign, usually the sign number but
        if we're a sense>1 then we look at the homophone with sense=1
        Return the gloss instance."""
        
        if self.sense and self.sense > 1:
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

        if os.path.isfile(settings.WRITABLE_FOLDER+'/'+video_path):
            return video_path
        else:
            return None

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

        return '/home/wessel/signbank/signbank/video/testmedia/AANBELLEN-320kbits.mp4'
         
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
            if not d.role in defs:
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
        from signbank.dictionary.forms import DEFN_ROLE_CHOICES
        return self.options_to_json(DEFN_ROLE_CHOICES)

    def relation_role_choices_json(self):
        """Return JSON for the relation role choice list"""
        
        return self.options_to_json(RELATION_ROLE_CHOICES)

    def handedness_weak_choices_json(self):
        """Return JSON for the etymology choice list"""
        from signbank.dictionary.forms import NEUTRALBOOLEANCHOICES

        return self.options_to_json(NEUTRALBOOLEANCHOICES)

    @staticmethod
    def variant_role_choices():

        return '{ "variant" : "Variant" }'

    def wordclass_choices(self):
        """Return JSON for wordclass choices"""

        # Get the list of choices for this field
        li = self._meta.get_field("wordClass").choices

        # Sort the list
        sorted_li = sorted(li, key=lambda x: x[1])

        # Put it in another format
        reformatted_li = [('_' + str(value), text) for value, text in sorted_li]

        return json.dumps(OrderedDict(reformatted_li))

    def signlanguage_choices(self):
        """Return JSON for langauge choices"""
        
        d = dict()
        for l in SignLanguage.objects.all():
            d[l.name] = l.name

        return json.dumps(d)

    def dialect_choices(self):
        """Return JSON for dialect choices"""
        
        d = dict()
        for l in Dialect.objects.all():
            dialect_name = l.signlanguage.name + "/" + l.name
            d[dialect_name] = dialect_name

        dict_list = list(d.items())
        sorted_dict_list = sorted(dict_list)
        first_element_sorted_dict_list = [ x[0] for x in sorted_dict_list ]

        return json.dumps(first_element_sorted_dict_list)

    def dataset_choices(self):

        d = dict()
        for s in Dataset.objects.all():
            d[s.name] = s.name

        return json.dumps(d)

    def get_annotationidglosstranslation_texts(self):
        d = dict()
        annotationidglosstranslations = self.annotationidglosstranslation_set.all()
        for translation in annotationidglosstranslations:
            d[translation.language.language_code_2char] = translation.text

        return d

    def get_choice_lists(self):
        """Return JSON for the location choice list"""
 
        choice_lists = {}

        #Start with your own choice lists
        for fieldname in ['handedness','locprim','domhndsh','subhndsh',
							'relatArtic','absOriPalm','absOriFing','relOriMov',
							'relOriLoc','handCh','repeat','altern','movSh',
							'movDir','movMan','contType','namEnt','oriCh','semField']:

            #Get the list of choices for this field
            li = self._meta.get_field(fieldname).choices

            #Sort the list
            sorted_li = sorted(li,key=lambda x: x[1])

            #Put it in another format
            reformatted_li = [('_'+str(value),text) for value,text in sorted_li]
            choice_lists[fieldname] = OrderedDict(reformatted_li)

        #Choice lists for other models
        choice_lists['morphology_role'] = [human_value for machine_value,human_value in build_choice_list('MorphologyType')]

        return json.dumps(choice_lists)

# register Gloss for tags
try:
    tagging.register(Gloss)
except:
    pass

@receiver(pre_delete, sender=Gloss, dispatch_uid='gloss_delete_signal')
def save_info_about_deleted_gloss(sender,instance,using,**kwarsg):
    from signbank.tools import get_default_annotationidglosstranslation
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(instance)

    deleted_gloss = DeletedGlossOrMedia()
    deleted_gloss.item_type = 'gloss'
    deleted_gloss.idgloss = instance.idgloss
    deleted_gloss.annotation_idgloss = default_annotationidglosstranslation
    deleted_gloss.old_pk = instance.pk
    deleted_gloss.save()

#We want to remember some stuff about deleted glosses
class DeletedGlossOrMedia(models.Model):

    item_type = models.CharField(max_length=5,choices=(('gloss','gloss'),('image','image'),('video','video')))
    idgloss = models.CharField("ID Gloss", max_length=50)
    annotation_idgloss = models.CharField("Annotation ID Gloss", max_length=30)
    old_pk = models.IntegerField()

    filename = models.CharField(max_length=100,blank=True) #For media only

    deletion_date = models.DateField(default=date.today)


RELATION_ROLE_CHOICES = (('homonym', 'Homonym'),
                         ('synonym', 'Synonym'),
                         ('variant', 'Variant'),
                         ('antonym', 'Antonym'),
                         ('hyponym', 'Hyponym'),
                         ('hypernym', 'Hypernym'),
                         ('seealso', 'See Also'),
                         )

VARIANT_ROLE_CHOICES = (('variant', 'Variant'))

def fieldname_to_category(fieldname):

    if fieldname in ['domhndsh','subhndsh','final_domdndsh','final_subhndsh']:
        field_category = 'Handshape'
    elif fieldname in ['locprim','locPrimLH','final_loc','loc_second','initial_secondary_loc','final_secondary_loc']:
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
    elif fieldname == 'mrpType':
        field_category = 'MorphemeType'
    elif fieldname == 'domFlex':
        field_category = 'DominantHandFlexion'
    elif fieldname == 'domSF':
        field_category = 'DominantHandSelectedFingers'
    elif fieldname in ['wordClass', 'wordClass2']:
        field_category = 'WordClass'
    elif fieldname == 'hasComponentOfType':
        field_category = 'MorphologyType'
    elif fieldname == 'hasMorphemeOfType':
        field_category = 'MorphemeType'
    elif fieldname in ['hsFingSel', 'hsFingSel2', 'hsFingUnsel']:
        field_category = 'FingerSelection'
    elif fieldname in ['hsFingConf', 'hsFingConf2']:
        field_category = 'JointConfiguration'
    elif fieldname == 'hsNumSel':
        field_category = 'Quantity'
    elif fieldname == 'hsAperture':
        field_category = 'Aperture'
    elif fieldname == 'hsThumb':
        field_category = 'Thumb'
    elif fieldname == 'hsSpread':
        field_category = 'Spreading'
    else:
        field_category = fieldname

    return field_category

class Relation(models.Model):
    """A relation between two glosses"""
     
    source = models.ForeignKey(Gloss, related_name="relation_sources")
    target = models.ForeignKey(Gloss, related_name="relation_targets")
    role = models.CharField(max_length=20, choices=RELATION_ROLE_CHOICES)  

    class Admin:
        list_display = [ 'source', 'role','target']
        search_fields = ['source__idgloss', 'target__idgloss']        
        
    class Meta:
        ordering = ['source']

    def get_reverse_role(role):
        if role == 'hyponym':
            return 'hypernym'
        elif role == 'hypernym':
            return 'hyponym'
        else:
            return role

class MorphologyDefinition(models.Model):
    """Tells something about morphology of a gloss"""

    parent_gloss = models.ForeignKey(Gloss, related_name="parent_glosses")
    role = models.CharField(max_length=5,choices=build_choice_list('MorphologyType'))
    morpheme = models.ForeignKey(Gloss,related_name="morphemes")

    def __str__(self):
        return self.morpheme.idgloss

class Morpheme(Gloss):
    """A morpheme definition uses all the fields of a gloss, but adds its own characteristics (#174)"""

    # Fields that are specific for morphemes, and not so much for 'sign-words' (=Gloss) as a whole
    # (1) optional morpheme-type field (not to be confused with MorphologyType from MorphologyDefinition)
    mrpType = models.CharField(max_length=5,blank=True,  null=True, choices=build_choice_list('MorphemeType'))

    def __str__(self):
        """Morpheme string is like a gloss but with a marker identifying it as a morpheme"""
        # return "%s (%s)" % (self.idgloss, self.get_mrpType_display())
        # The display needs to be overrided to accomodate translations, the mrpType is done in adminviews
        # The idgloss field is no longer correct
        # We won't use this method in the interface but leave it for debugging purposes

        return "%s" % (self.idgloss)

    def admin_next_morpheme(self):
        """next morpheme in the admin view, shortcut for next_dictionary_morpheme with staff=True"""

        return self.next_dictionary_morpheme(True)


    def next_dictionary_morpheme(self, staff=False):
        """Find the next morpheme in dictionary order"""

        if staff:
            all_morphemes_ordered = Morpheme.objects.all().order_by('idgloss')
        else:
            all_morphemes_ordered = Morpheme.objects.filter(inWeb__exact=True).order_by('idgloss')

        if all_morphemes_ordered:

            foundit = False

            for morpheme in all_morphemes_ordered:
                if morpheme == self:
                    foundit = True
                elif foundit:
                    return morpheme
                    break

        else:
            return None


    def mrptype_choices(self):
        """Return JSON for mrptype choices"""

        # Get the list of choices for this field
        li = self._meta.get_field("mrpType").choices

        # Sort the list
        sorted_li = sorted(li, key=lambda x: x[1])

        # Put it in another format
        reformatted_li = [('_' + str(value), text) for value, text in sorted_li]

        return json.dumps(OrderedDict(reformatted_li))

class SimultaneousMorphologyDefinition(models.Model):

    parent_gloss = models.ForeignKey(Gloss,related_name='simultaneous_morphology')
    role = models.CharField(max_length=100)
    morpheme = models.ForeignKey(Morpheme,related_name='glosses_containing')

    def __str__(self):
        return self.parent_gloss.idgloss

class BlendMorphology(models.Model):
    parent_gloss = models.ForeignKey(Gloss,related_name='blend_morphology')
    role = models.CharField(max_length=100)
    glosses = models.ForeignKey(Gloss,related_name='glosses_comprising')

    def __str__(self):
        return self.parent_gloss.idgloss

class OtherMedia(models.Model):
    """Videos of or related to a gloss, often created by another project"""

    parent_gloss = models.ForeignKey(Gloss)
    type = models.CharField(max_length=5,choices=build_choice_list('OtherMediaType'))
    alternative_gloss = models.CharField(max_length=50)
    path = models.CharField(max_length=100)


class Dataset(models.Model):
    """A dataset, can be public/private and can be of only one SignLanguage"""
    name = models.CharField(unique=True, blank=False, null=False, max_length=60)
    is_public = models.BooleanField(default=False, help_text="Is this dataset public or private?")
    signlanguage = models.ForeignKey("SignLanguage")
    translation_languages = models.ManyToManyField("Language", help_text="These languages are shown as options"
                                                                          "for translation equivalents.")
    description = models.TextField()

    class Meta:
        permissions = (
            ('view_dataset', _('View dataset')),
        )

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User,related_name="user_profile_user")

    # Other fields here
    last_used_language = models.CharField(max_length=20, default=settings.LANGUAGE_CODE)
    expiry_date = models.DateField(null=True, blank=True)
    number_of_logins = models.IntegerField(null=True,default=0)
    comments = models.CharField(max_length=500,null=True, blank=True)
    selected_datasets = models.ManyToManyField(Dataset)

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

class Language(models.Model):
    """A written language, used for translations in written languages."""
    name = models.CharField(max_length=50)
    language_code_2char = models.CharField(max_length=7, unique=False, null=False, blank=False, help_text=_(
        """Language code (2 characters long) of a written language. This also includes codes of the form zh-Hans, cf. IETF BCP 47"""))
    language_code_3char = models.CharField(max_length=3, unique=False, null=False, blank=False, help_text=_(
        """ISO 639-3 language code (3 characters long) of a written language."""))
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class AnnotationIdglossTranslation(models.Model):
    """An annotation ID Gloss"""
    text = models.CharField(_("Annotation ID Gloss"), max_length=30, help_text="""
        This is the name of a sign used by annotators when glossing the corpus in
        an ELAN annotation file.""")
    gloss = models.ForeignKey("Gloss")
    language = models.ForeignKey("Language")

    class Meta:
        unique_together = (("gloss", "language"),)

    def save(self, *args, **kwargs):
        """
        1. Before an item is saved the language is checked against the languages of the dataset the gloss is in.
        2. The annotation idgloss translation text for a language must be unique within a dataset. 
        Note that bulk updates will not use this method. Therefore, always iterate over a queryset when updating."""
        dataset = self.gloss.dataset
        if dataset:
            # Before an item is saved the language is checked against the languages of the dataset the gloss is in.
            dataset_languages = self.gloss.dataset.translation_languages.all()
            if not self.language in dataset_languages:
                msg = "Language %s is not in the set of language of the dataset gloss %s belongs to" \
                      % (self.language.name, self.gloss.id)
                raise ValidationError(msg)

            # The annotation idgloss translation text for a language must be unique within a dataset.
            glosses_with_same_text = dataset.gloss_set.filter(annotationidglosstranslation__text__exact=self.text,
                                                              annotationidglosstranslation__language=self.language)
            if not(
                (len(glosses_with_same_text) == 1 and glosses_with_same_text[0] == self)
                   or glosses_with_same_text is None or len(glosses_with_same_text) == 0):
                msg = "The annotation idgloss translation text '%s' is not unique within dataset '%s' for gloss '%s'." \
                      % (self.text, dataset.name, self.gloss.id)
                raise ValidationError(msg)

        super(AnnotationIdglossTranslation, self).save(*args, **kwargs)
