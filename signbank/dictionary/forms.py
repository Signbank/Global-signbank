from django import forms
from django.utils.translation import ugettext_lazy as _
from signbank.video.fields import VideoUploadToFLVField
from signbank.dictionary.models import Dialect, Gloss, Morpheme, Definition, Relation, RelationToForeignSign, MorphologyDefinition, build_choice_list, OtherMedia, Handshape, AnnotationIdglossTranslation
from django.conf import settings
from tagging.models import Tag
import datetime as DT

# category choices are tag values that we'll restrict search to
CATEGORY_CHOICES = (('all', 'All Signs'),
                    ('semantic:health', 'Only Health Related Signs'),
                    ('semantic:education', 'Only Education Related Signs'))

class UserSignSearchForm(forms.Form):

    glossQuery = forms.CharField(label=_(u'Glosses containing'), max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    query = forms.CharField(label=_(u'Translations containing'), max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    category = forms.ChoiceField(label=_(u'Search'), choices=CATEGORY_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
        

class GlossModelForm(forms.ModelForm):
    class Meta:
        model = Gloss
        # fields are defined in settings.py
        fields = settings.QUICK_UPDATE_GLOSS_FIELDS

class GlossCreateForm(forms.ModelForm):
    """Form for creating a new gloss from scratch"""

    gloss_create_field_prefix = "glosscreate_"
    languages = None # Languages to use for annotation idgloss translations
    user = None

    class Meta:
        model = Gloss
        fields = ['idgloss', 'dataset']

    def __init__(self, queryDict, *args, **kwargs):
        self.languages = kwargs.pop('languages')
        self.user = kwargs.pop('user')
        super(GlossCreateForm, self).__init__(queryDict, *args, **kwargs)

        for language in self.languages:
            glosscreate_field_name = self.gloss_create_field_prefix + language.language_code_2char
            self.fields[glosscreate_field_name] = forms.CharField(label=_("Gloss")+(" (%s)" % language.name))
            if glosscreate_field_name in queryDict:
                self.fields[glosscreate_field_name].value = queryDict[glosscreate_field_name]

    def save(self, commit=True):
        gloss = super(GlossCreateForm, self).save(commit)
        for language in self.languages:
            glosscreate_field_name = self.gloss_create_field_prefix + language.language_code_2char
            annotation_idgloss_text = self.fields[glosscreate_field_name].value
            existing_annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
            if existing_annotationidglosstranslations is None or len(existing_annotationidglosstranslations) == 0:
                annotationidglosstranslation = AnnotationIdglossTranslation(gloss=gloss, language=language,
                                                                            text=annotation_idgloss_text)
                annotationidglosstranslation.save()
            elif len(existing_annotationidglosstranslations) == 1:
                annotationidglosstranslation = existing_annotationidglosstranslations[0]
                annotationidglosstranslation.text = annotation_idgloss_text
                annotationidglosstranslation.save()
            else:
                raise Exception(
                    "In class %s: gloss with id %s has more than one annotation idgloss translation for language %s"
                    % (self.__class__.__name__, gloss.pk, language.name)
                )
        gloss.creator.add(self.user)
        gloss.creationDate = DT.datetime.now()
        gloss.save()
        return gloss


class UserMorphemeSearchForm(forms.Form):
    """Facilitate searching for morphemes"""

    morphQuery = forms.CharField(label=_(u'Morphemes containing'), max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'class': 'form-control'}))
    query = forms.CharField(label=_(u'Translations containing'), max_length=100, required=False,
                            widget=forms.TextInput(attrs={'class': 'form-control'}))


class MorphemeModelForm(forms.ModelForm):
    class Meta:
        model = Morpheme
        # fields are defined in settings.py
        fields = settings.QUICK_UPDATE_GLOSS_FIELDS


class MorphemeCreateForm(forms.ModelForm):
    """Form for creating a new morpheme from scratch"""

    morpheme_create_field_prefix = "morphemecreate_"
    languages = None  # Languages to use for annotation idgloss translations
    user = None

    class Meta:
        model = Morpheme
        fields = ['idgloss', 'dataset', 'mrpType']

    def __init__(self, queryDict, *args, **kwargs):
        self.languages = kwargs.pop('languages')
        self.user = kwargs.pop('user')
        super(MorphemeCreateForm, self).__init__(queryDict, *args, **kwargs)

        for language in self.languages:
            morphemecreate_field_name = self.morpheme_create_field_prefix + language.language_code_2char
            self.fields[morphemecreate_field_name] = forms.CharField(label=_("Gloss")+(" (%s)" % language.name))
            if morphemecreate_field_name in queryDict:
                self.fields[morphemecreate_field_name].value = queryDict[morphemecreate_field_name]

    def save(self, commit=True):
        morpheme = super(MorphemeCreateForm, self).save(commit)
        for language in self.languages:
            morphemecreate_field_name = self.morpheme_create_field_prefix + language.language_code_2char
            annotation_idgloss_text = self.fields[morphemecreate_field_name].value
            existing_annotationidglosstranslations = morpheme.annotationidglosstranslation_set.filter(language=language)
            if existing_annotationidglosstranslations is None or len(existing_annotationidglosstranslations) == 0:
                annotationidglosstranslation = AnnotationIdglossTranslation(gloss=morpheme, language=language,
                                                                            text=annotation_idgloss_text)
                annotationidglosstranslation.save()
            elif len(existing_annotationidglosstranslations) == 1:
                annotationidglosstranslation = existing_annotationidglosstranslations[0]
                annotationidglosstranslation.text = annotation_idgloss_text
                annotationidglosstranslation.save()
            else:
                raise Exception(
                    "In class %s: gloss with id %s has more than one annotation idgloss translation for language %s"
                    % (self.__class__.__name__, morpheme.pk, language.name)
                )
        morpheme.creator.add(self.user)
        morpheme.creationDate = DT.datetime.now()
        morpheme.save()
        return morpheme

class VideoUpdateForm(forms.Form):
    """Form to allow update of the video for a sign"""
    videofile = VideoUploadToFLVField()


class TagUpdateForm(forms.Form):
    """Form to add a new tag to a gloss"""

    tag = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control'}), 
                            choices=[(tag.name, tag.name.replace('_',' ')) for tag in Tag.objects.all()])
    delete = forms.BooleanField(required=False, widget=forms.HiddenInput)

YESNOCHOICES = (("unspecified", "Unspecified" ), ('yes', 'Yes'), ('no', 'No'))
NULLBOOLEANCHOICES = [(0,'---------'),(1,'Unknown'),(2,'True'),(3,'False')]
NONEBOOLEANCHOICES = [(0,'---------'),(1,'None'),(2,'True'),(3,'False')]
UNKNOWNBOOLEANCHOICES = [(0,'---------'),(1,'Unknown'),(2,'True'),(3,'False')]
NEUTRALBOOLEANCHOICES = [(1,'Neutral'),(2,'Yes'),(3,'No')]
NEUTRALQUERYCHOICES = [(0,'---------'),(1,'Neutral'),(2,'True'),(3,'False')]

RELATION_ROLE_CHOICES = (('','---------'),
                         ('all', 'All'),
                         ('homonym', 'Homonym'),
                         ('synonym', 'Synonym'),
                         ('variant', 'Variant'),
                         ('antonym', 'Antonym'),
                         ('hyponym', 'Hyponym'),
                         ('hypernym', 'Hypernym'),
                         ('seealso', 'See Also'),
                         )

DEFN_ROLE_CHOICES = [('','---------'),('all','All')] + build_choice_list('NoteType')
COMPONENT_ROLE_CHOICES = [('','---------')] + build_choice_list('MorphologyType')
MORPHEME_ROLE_CHOICES = [('','---------')] + build_choice_list('MorphemeType')
ATTRS_FOR_FORMS = {'class':'form-control'}

class GlossSearchForm(forms.ModelForm):

    use_required_attribute = False #otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Dutch Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"), initial="idgloss")       # Used in glosslistview to store user-selection
    englishGloss = forms.CharField(label=_("English Gloss"))
    lemmaGloss = forms.CharField(label=_("Lemma Gloss"))
    tags = forms.MultipleChoiceField(choices=[(tag.name, tag.name.replace('_',' ')) for tag in Tag.objects.all()])
    nottags = forms.MultipleChoiceField(choices=[(tag.name, tag.name) for tag in Tag.objects.all()])
    keyword = forms.CharField(label=_(u'Translations'))
    hasvideo = forms.ChoiceField(label=_(u'Has Video'), choices=YESNOCHOICES)
    defspublished = forms.ChoiceField(label=_("All Definitions Published"), choices=YESNOCHOICES)
    
    defsearch = forms.CharField(label=_(u'Search Definition/Notes'))

    relation = forms.CharField(label=_(u'Search for gloss of related signs'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    relationToForeignSign = forms.CharField(label=_(u'Search for gloss of foreign signs'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    morpheme = forms.CharField(label=_(u'Search for gloss with this as morpheme'))

    oriChAbd = forms.ChoiceField(label=_(u'Abduction change'),choices=NULLBOOLEANCHOICES)
    oriChFlex = forms.ChoiceField(label=_(u'Flexion change'),choices=NULLBOOLEANCHOICES)

    phonOth = forms.CharField(label=_(u'Phonology other'),widget=forms.TextInput())

    hasRelationToForeignSign = forms.ChoiceField(label=_(u'Related to foreign sign or not'),choices=[(0,'---------'),(1,'Yes'),(2,'No')],widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasRelation = forms.ChoiceField(label=_(u'Type of relation'),choices=RELATION_ROLE_CHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    hasComponentOfType = forms.TypedChoiceField(label=_(u'Has compound component type'),choices=COMPONENT_ROLE_CHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasMorphemeOfType = forms.TypedChoiceField(label=_(u'Has morpheme type'),choices=MORPHEME_ROLE_CHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    repeat = forms.ChoiceField(label=_(u'Repeating Movement'),choices=NULLBOOLEANCHOICES)
    altern = forms.ChoiceField(label=_(u'Alternating Movement'),choices=NULLBOOLEANCHOICES)
    weakprop = forms.ChoiceField(label=_(u'Weak prop'),choices=NEUTRALQUERYCHOICES)
    weakdrop = forms.ChoiceField(label=_(u'Weak drop'),choices=NEUTRALQUERYCHOICES)

    domhndsh_letter = forms.ChoiceField(label=_(u'letter'),choices=UNKNOWNBOOLEANCHOICES)
    domhndsh_number = forms.ChoiceField(label=_(u'number'),choices=UNKNOWNBOOLEANCHOICES)
    subhndsh_letter = forms.ChoiceField(label=_(u'letter'),choices=UNKNOWNBOOLEANCHOICES)
    subhndsh_number = forms.ChoiceField(label=_(u'number'),choices=UNKNOWNBOOLEANCHOICES)

    isNew = forms.ChoiceField(label=_(u'Is a proposed new sign'),choices=NULLBOOLEANCHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    inWeb = forms.ChoiceField(label=_(u'Is in Web dictionary'),choices=NULLBOOLEANCHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionRole = forms.ChoiceField(label=_(u'Note type'),choices=DEFN_ROLE_CHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionContains = forms.CharField(label=_(u'Note contains'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    createdBefore = forms.DateField(label=_(u'Created before'), widget=forms.DateInput(attrs={'placeholder': _('mm/dd/yyyy')}))
    createdAfter = forms.DateField(label=_(u'Created after'), widget=forms.DateInput(attrs={'placeholder': _('mm/dd/yyyy')}))

    createdBy = forms.CharField(label=_(u'Created by'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    gloss_search_field_prefix = "glosssearch_"
    keyword_search_field_prefix = "keyword_"

    class Meta:

        ATTRS_FOR_FORMS = {'class':'form-control'}

        model = Gloss
        fields = ('idgloss', 'morph', 'sense',
                   'sn', 'StemSN', 'comptf', 'compound', 'signlanguage', 'dialect',
                   'inWeb', 'isNew',
                   'initial_relative_orientation', 'final_relative_orientation',
                   'initial_palm_orientation', 'final_palm_orientation', 
                   'initial_secondary_loc', 'final_secondary_loc',
                   'domhndsh', 'subhndsh', 'locprim', 'locVirtObj', 'locsecond',
                   'final_domhndsh', 'final_subhndsh', 'final_loc',

                    'locPrimLH','locFocSite','locFocSiteLH','initArtOri','finArtOri','initArtOriLH','finArtOriLH',

                   'handedness', 'useInstr','rmrks', 'relatArtic','absOriPalm','absOriFing',
                   'relOriMov','relOriLoc','oriCh','handCh','repeat', 'altern', 'movSh','movDir','movMan','contType', 'mouthG',
                   'mouthing', 'phonetVar', 'domSF', 'domFlex', 'oriChAbd', 'oriChFlex',

                   'iconImg','iconType','namEnt', 'semField', 'wordClass', 'wordClass2', 'derivHist', 'lexCatNotes', 'valence',

                   'tokNoA','tokNoSgnrA','tokNoV','tokNoSgnrV','tokNoR','tokNoSgnrR','tokNoGe','tokNoSgnrGe',
                   'tokNoGr','tokNoSgnrGr','tokNoO','tokNoSgnrO')

    def __init__(self, queryDict, *args, **kwargs):
        languages = kwargs.pop('languages')
        super(GlossSearchForm, self).__init__(queryDict, *args, **kwargs)

        for language in languages:
            glosssearch_field_name = self.gloss_search_field_prefix + language.language_code_2char
            setattr(self, glosssearch_field_name, forms.CharField(label=_("Gloss")+(" (%s)" % language.name)))
            if glosssearch_field_name in queryDict:
                getattr(self, glosssearch_field_name).value = queryDict[glosssearch_field_name]

            # do the same for Translations
            keyword_field_name = self.keyword_search_field_prefix + language.language_code_2char
            setattr(self, keyword_field_name, forms.CharField(label=_("Translations")+(" (%s)" % language.name)))
            if keyword_field_name in queryDict:
                getattr(self, keyword_field_name).value = queryDict[keyword_field_name]


class MorphemeSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Dutch Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"),
                                initial="idgloss")  # Used in morphemelistview to store user-selection
    englishGloss = forms.CharField(label=_("English Gloss"))
    lemmaGloss = forms.CharField(label=_("Lemma Gloss"))
    tags = forms.MultipleChoiceField(choices=[(tag.name, tag.name.replace('_', ' ')) for tag in Tag.objects.all()])
    nottags = forms.MultipleChoiceField(choices=[(tag.name, tag.name) for tag in Tag.objects.all()])
    keyword = forms.CharField(label=_(u'Translations'))
    hasvideo = forms.ChoiceField(label=_(u'Has Video'), choices=YESNOCHOICES)
    defspublished = forms.ChoiceField(label=_("All Definitions Published"), choices=YESNOCHOICES)

    defsearch = forms.CharField(label=_(u'Search Definition/Notes'))

    relation = forms.CharField(label=_(u'Search for gloss of related signs'),
                               widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    relationToForeignSign = forms.CharField(label=_(u'Search for gloss of foreign signs'),
                                            widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    morpheme = forms.CharField(label=_(u'Search for gloss with this as morpheme'),
                               widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    phonOth = forms.CharField(label=_(u'Phonology other'), widget=forms.TextInput())

    hasRelationToForeignSign = forms.ChoiceField(label=_(u'Related to foreign sign or not'),
                                                 choices=[(0, '---------'), (1, 'Yes'), (2, 'No')],
                                                 widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasRelation = forms.ChoiceField(label=_(u'Type of relation'), choices=RELATION_ROLE_CHOICES,
                                    widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasMorphemeOfType = forms.ChoiceField(label=_(u'Has morpheme type'), choices=MORPHEME_ROLE_CHOICES,
                                          widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    repeat = forms.ChoiceField(label=_(u'Repeating Movement'),
                               choices=NULLBOOLEANCHOICES)
    altern = forms.ChoiceField(label=_(u'Alternating Movement'),
                               choices=NULLBOOLEANCHOICES)

    isNew = forms.ChoiceField(label=_(u'Is a proposed new sign'), choices=NULLBOOLEANCHOICES,
                              widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    inWeb = forms.ChoiceField(label=_(u'Is in Web dictionary'), choices=NULLBOOLEANCHOICES,
                              widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionRole = forms.ChoiceField(label=_(u'Note type'), choices=DEFN_ROLE_CHOICES,
                                       widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionContains = forms.CharField(label=_(u'Note contains'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    createdBefore = forms.DateField(label=_(u'Created before'))
    createdAfter = forms.DateField(label=_(u'Created after'))

    createdBy = forms.CharField(label=_(u'Created by'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    morpheme_search_field_prefix = "morphemesearch_"

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'}

        model = Morpheme
        fields = ('idgloss', 'morph', 'sense',
                  'sn', 'StemSN', 'comptf', 'compound', 'signlanguage', 'dialect',
                  'inWeb', 'isNew',
                  'initial_relative_orientation', 'final_relative_orientation',
                  'initial_palm_orientation', 'final_palm_orientation',
                  'initial_secondary_loc', 'final_secondary_loc',
                  'domhndsh', 'subhndsh', 'locprim', 'locVirtObj', 'locsecond',
                  'final_domhndsh', 'final_subhndsh', 'final_loc',

                  'locPrimLH', 'locFocSite', 'locFocSiteLH', 'initArtOri', 'finArtOri', 'initArtOriLH', 'finArtOriLH',

                  'handedness', 'useInstr', 'rmrks', 'relatArtic', 'absOriPalm', 'absOriFing',
                  'relOriMov', 'relOriLoc', 'oriCh', 'handCh', 'repeat', 'altern', 'movSh', 'movDir', 'movMan',
                  'contType', 'mouthG',
                  'mouthing', 'phonetVar',

                  'iconImg', 'iconType', 'namEnt', 'semField', 'wordClass', 'wordClass2', 'derivHist', 'lexCatNotes',
                  'valence',

                  'tokNoA', 'tokNoSgnrA', 'tokNoV', 'tokNoSgnrV', 'tokNoR', 'tokNoSgnrR', 'tokNoGe', 'tokNoSgnrGe',
                  'tokNoGr', 'tokNoSgnrGr', 'tokNoO', 'tokNoSgnrO')

    def __init__(self, queryDict, *args, **kwargs):
        languages = kwargs.pop('languages')
        super(MorphemeSearchForm, self).__init__(queryDict, *args, **kwargs)

        for language in languages:
            morphemesearch_field_name = self.morpheme_search_field_prefix + language.language_code_2char
            setattr(self, morphemesearch_field_name, forms.CharField(label=_("Gloss") + (" (%s)" % language.name)))
            if morphemesearch_field_name in queryDict:
                getattr(self, morphemesearch_field_name).value = queryDict[morphemesearch_field_name]


class DefinitionForm(forms.ModelForm):
    role = forms.ChoiceField(label=_(u'Type'), choices=build_choice_list('NoteType'),
                             widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    class Meta:
        model = Definition
        fields = ('published','count', 'role', 'text')
        
class RelationForm(forms.ModelForm):
    
    sourceid = forms.CharField(label=_(u'Source Gloss'))
    targetid = forms.CharField(label=_(u'Target Gloss'))
    
    class Meta:
        model = Relation
        fields = ['role']
        widgets = {
                   'role': forms.Select(attrs={'class': 'form-control'}),
                   }

class VariantsForm(forms.Form):
    sourceid = forms.CharField(label=_(u'Source Gloss'))
    targetid = forms.CharField(label=_(u'Target Gloss'))

    class Meta:
        model = Relation
        
class RelationToForeignSignForm(forms.ModelForm):

    sourceid = forms.CharField(label=_(u'Source Gloss'))
    other_lang = forms.CharField(label=_(u'Related Language'))
    other_lang_gloss = forms.CharField(label=_(u'Gloss in Related Language'), required=False)
    
    class Meta:
        model = RelationToForeignSign
        fields = ['loan','other_lang','other_lang_gloss']
        widgets = {}


class GlossMorphologyForm(forms.ModelForm):
    """Morphology specification of a Gloss"""

    parent_gloss_id = forms.CharField(label=_(u'Parent Gloss'))
    role = forms.ChoiceField(label=_(u'Type'),choices=build_choice_list('MorphologyType'),widget=forms.Select(attrs=ATTRS_FOR_FORMS), required=True)
    morpheme_id = forms.CharField(label=_(u'Morpheme'))

    class Meta:
        model = MorphologyDefinition
        fields = ['role']


class GlossMorphemeForm(forms.Form):
    """Specify simultaneous morphology components belonging to a Gloss"""

    host_gloss_id = forms.CharField(label=_(u'Host Gloss'))
    description = forms.CharField(label=_(u'Meaning'), )
    morph_id = forms.CharField(label=_(u'Morpheme'))

class GlossBlendForm(forms.Form):
    """Specify simultaneous morphology components belonging to a Gloss"""

    host_gloss_id = forms.CharField(label=_(u'Host Gloss'))
    role = forms.CharField(label=_(u'Role'))
    blend_id = forms.CharField(label=_(u'Blend'))

class MorphemeMorphologyForm(forms.ModelForm):
    """Morphology specification for a Morpheme"""

    parent_gloss_id = forms.CharField(label=_(u'Parent Gloss'))
    role = forms.ChoiceField(label=_(u'Type'),choices=build_choice_list('MorphologyType'),widget=forms.Select(attrs=ATTRS_FOR_FORMS), required=True)
    morpheme_id = forms.CharField(label=_(u'Morpheme'))

    class Meta:
        model = MorphologyDefinition
        fields = ['role']

class OtherMediaForm(forms.ModelForm):

    gloss = forms.CharField()
    file = forms.FileField()
    type = forms.ChoiceField(choices=build_choice_list('OtherMediaType'),widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    alternative_gloss = forms.TextInput()

    class Meta:
        model = OtherMedia
        fields = ['type']

class CSVUploadForm(forms.Form):

    file = forms.FileField()

class ImageUploadForGlossForm(forms.Form):
    """Form for video upload for a particular gloss"""

    imagefile = forms.FileField(label="Upload Image")
    gloss_id = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)


FINGER_SELECTION_CHOICES = [('','---------')] + build_choice_list('FingerSelection')
FINGER_CONFIGURATION_CHOICES = [('','---------')] + build_choice_list('JointConfiguration')
QUANTITY_CHOICES = [('','---------')] + build_choice_list('Quantity')
THUMB_CHOICES = [('','---------')] + build_choice_list('Thumb')
SPREADING_CHOICES = [('','---------')] + build_choice_list('Spreading')
APERTURE_CHOICES = [('','---------')] + build_choice_list('Aperture')
attrs_default = {'class': 'form-control'}
FINGER_SELECTION = ((True, 'True'), (False, 'False'), (None, 'Either'))

class HandshapeSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Handshape"))
    sortOrder = forms.CharField(label=_("Sort Order"),
                                initial="machine_value")  # Used in Handshapelistview to store user-selection

    fingerSelection = forms.ChoiceField(label=_(u'Finger Selection'), choices=FINGER_SELECTION_CHOICES,
                                    widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    fingerConfiguration = forms.ChoiceField(label=_(u'Finger Configuration'), choices=FINGER_CONFIGURATION_CHOICES,
                                          widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    numSelected = forms.ChoiceField(label=_(u'Quantity'),
                               choices=QUANTITY_CHOICES ,widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    # this is used to pass the label to the handshapes list view
    unselectedFingers = forms.ChoiceField(label=_(u'Unselected fingers extended'), choices=FINGER_SELECTION_CHOICES,
                                        widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    spreading = forms.ChoiceField(label=_(u'Spreading'), choices=SPREADING_CHOICES,
                              widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    aperture = forms.ChoiceField(label=_(u'Aperture'), choices=APERTURE_CHOICES,
                              widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    fsT = forms.NullBooleanSelect()
    fsI = forms.NullBooleanSelect()
    fsM = forms.NullBooleanSelect()
    fsR = forms.NullBooleanSelect()
    fsP = forms.NullBooleanSelect()
    fs2T = forms.NullBooleanSelect()
    fs2I = forms.NullBooleanSelect()
    fs2M = forms.NullBooleanSelect()
    fs2R = forms.NullBooleanSelect()
    fs2P = forms.NullBooleanSelect()
    ufT = forms.NullBooleanSelect()
    ufI = forms.NullBooleanSelect()
    ufM = forms.NullBooleanSelect()
    ufR = forms.NullBooleanSelect()
    ufP = forms.NullBooleanSelect()

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'}

        model = Handshape
        fields = ('machine_value', 'english_name', 'dutch_name', 'chinese_name',
				  'hsNumSel', 'hsFingSel', 'hsFingSel2', 'hsFingConf', 'hsFingConf2',
				  'hsAperture', 'hsThumb', 'hsSpread', 'hsFingUnsel',
                  'fsT', 'fsI', 'fsM', 'fsR', 'fsP',
                  'fs2T', 'fs2I', 'fs2M', 'fs2R', 'fs2P',
                  'ufT', 'ufI', 'ufM', 'ufR', 'ufP')
        widgets = {
                'fsT' : forms.RadioSelect(choices = FINGER_SELECTION),
                'fsI': forms.RadioSelect(choices=FINGER_SELECTION),
                'fsM': forms.RadioSelect(choices=FINGER_SELECTION),
                'fsR': forms.RadioSelect(choices=FINGER_SELECTION),
                'fsP': forms.RadioSelect(choices=FINGER_SELECTION),
                'fs2T': forms.RadioSelect(choices=FINGER_SELECTION),
                'fs2I': forms.RadioSelect(choices=FINGER_SELECTION),
                'fs2M': forms.RadioSelect(choices=FINGER_SELECTION),
                'fs2R': forms.RadioSelect(choices=FINGER_SELECTION),
                'fs2P': forms.RadioSelect(choices=FINGER_SELECTION),
                'ufT': forms.RadioSelect(choices=FINGER_SELECTION),
                'ufI': forms.RadioSelect(choices=FINGER_SELECTION),
                'ufM': forms.RadioSelect(choices=FINGER_SELECTION),
                'ufR': forms.RadioSelect(choices=FINGER_SELECTION),
                'ufP': forms.RadioSelect(choices=FINGER_SELECTION),
        }


class ImageUploadForHandshapeForm(forms.Form):
    """Form for video upload for a particular gloss"""

    imagefile = forms.FileField(label="Upload Image")
    handshape_id = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)
