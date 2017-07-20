from django import forms
from django.utils.translation import ugettext_lazy as _
from signbank.video.fields import VideoUploadToFLVField
from signbank.dictionary.models import Dialect, Gloss, Morpheme, Definition, Relation, RelationToForeignSign, MorphologyDefinition, build_choice_list, OtherMedia
from django.conf import settings
from tagging.models import Tag

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
    class Meta:
        model = Gloss
        fields = ['idgloss', 'annotation_idgloss', 'annotation_idgloss_en']


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
    class Meta:
        model = Morpheme
        fields = ['idgloss', 'annotation_idgloss', 'annotation_idgloss_en', 'mrpType']



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

DEFN_ROLE_CHOICES = [('','---------'),('all','All')] + build_choice_list('NoteType');
COMPONENT_ROLE_CHOICES = [('','---------')] + build_choice_list('MorphologyType');
MORPHEME_ROLE_CHOICES = [('','---------')] + build_choice_list('MorphemeType');
ATTRS_FOR_FORMS = {'class':'form-control'};


class GlossSearchForm(forms.ModelForm):

    use_required_attribute = False #otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Dutch Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"), initial="idgloss")       # Used in glosslistview to store user-selection
    englishGloss = forms.CharField(label=_("English Gloss"))
    tags = forms.MultipleChoiceField(choices=[(tag.name, tag.name.replace('_',' ')) for tag in Tag.objects.all()])
    nottags = forms.MultipleChoiceField(choices=[(tag.name, tag.name) for tag in Tag.objects.all()])
    keyword = forms.CharField(label=_(u'Translations'))
    hasvideo = forms.ChoiceField(label=_(u'Has Video'), choices=YESNOCHOICES)
    defspublished = forms.ChoiceField(label=_("All Definitions Published"), choices=YESNOCHOICES)
    
    defsearch = forms.CharField(label=_(u'Search Definition/Notes'))
    #defrole = forms.ChoiceField(label=_(u'Search Definition/Note Type'), choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))

    relation = forms.CharField(label=_(u'Search for gloss of related signs'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    relationToForeignSign = forms.CharField(label=_(u'Search for gloss of foreign signs'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    morpheme = forms.CharField(label=_(u'Search for gloss with this as morpheme'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    oriChAbd = forms.ChoiceField(label=_(u'Abduction change'),choices=NULLBOOLEANCHOICES)
    oriChFlex = forms.ChoiceField(label=_(u'Flexion change'),choices=NULLBOOLEANCHOICES)

    phonOth = forms.CharField(label=_(u'Phonology other'),widget=forms.TextInput())

    hasRelationToForeignSign = forms.ChoiceField(label=_(u'Related to foreign sign or not'),choices=[(0,'---------'),(1,'Yes'),(2,'No')],widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasRelation = forms.ChoiceField(label=_(u'Type of relation'),choices=RELATION_ROLE_CHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    # A "component" is one part of a compound
    hasComponentOfType = forms.TypedChoiceField(label=_(u'Has compound component type'),choices=COMPONENT_ROLE_CHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    # A "morpheme" is an item from the "Morpheme" list
    hasMorphemeOfType = forms.TypedChoiceField(label=_(u'Has morpheme type'),choices=MORPHEME_ROLE_CHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    repeat = forms.ChoiceField(label=_(u'Repeating Movement'),choices=NULLBOOLEANCHOICES)#,widget=forms.Select(attrs=ATTRS_FOR_FORMS));
    altern = forms.ChoiceField(label=_(u'Alternating Movement'),choices=NULLBOOLEANCHOICES)#,widget=forms.Select(attrs=ATTRS_FOR_FORMS));

    isNew = forms.ChoiceField(label=_(u'Is a proposed new sign'),choices=NULLBOOLEANCHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    inWeb = forms.ChoiceField(label=_(u'Is in Web dictionary'),choices=NULLBOOLEANCHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionRole = forms.ChoiceField(label=_(u'Note type'),choices=DEFN_ROLE_CHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionContains = forms.CharField(label=_(u'Note contains'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    createdBefore = forms.DateField(label=_(u'Created before'), widget=forms.DateInput(attrs={'placeholder': _('mm/dd/yyyy')}))
    createdAfter = forms.DateField(label=_(u'Created after'), widget=forms.DateInput(attrs={'placeholder': _('mm/dd/yyyy')}))

    createdBy = forms.CharField(label=_(u'Created by'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    class Meta:

        ATTRS_FOR_FORMS = {'class':'form-control'};

        model = Gloss
        fields = ('idgloss', 'annotation_idgloss', 'annotation_idgloss_en', 'morph', 'sense', 
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


class MorphemeSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Dutch Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"),
                                initial="idgloss")  # Used in morphemelistview to store user-selection
    englishGloss = forms.CharField(label=_("English Gloss"))
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
                               choices=NULLBOOLEANCHOICES)  # ,widget=forms.Select(attrs=ATTRS_FOR_FORMS));
    altern = forms.ChoiceField(label=_(u'Alternating Movement'),
                               choices=NULLBOOLEANCHOICES)  # ,widget=forms.Select(attrs=ATTRS_FOR_FORMS));

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

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Morpheme
        fields = ('idgloss', 'annotation_idgloss', 'annotation_idgloss_en', 'morph', 'sense',
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
    #loan = forms.CharField(label=_(u'Loan'))
    other_lang = forms.CharField(label=_(u'Related Language'))
    other_lang_gloss = forms.CharField(label=_(u'Gloss in Related Language'), required=False)
    
    class Meta:
        model = RelationToForeignSign
        fields = ['loan','other_lang','other_lang_gloss']
        widgets = {}


class GlossMorphologyForm(forms.ModelForm):
    """Morphology specification of a Gloss"""

    parent_gloss_id = forms.CharField(label=_(u'Parent Gloss'))
    role = forms.ChoiceField(label=_(u'Type'),choices=build_choice_list('MorphologyType'),widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    morpheme_id = forms.CharField(label=_(u'Morpheme'));

    class Meta:
        model = MorphologyDefinition;
        fields = ['role'];


class GlossMorphemeForm(forms.Form):
    """Specify simultaneous morphology components belonging to a Gloss"""

    host_gloss_id = forms.CharField(label=_(u'Host Gloss'))
    description = forms.CharField()
    morph_id = forms.CharField(label=_(u'Morpheme'))

class MorphemeMorphologyForm(forms.ModelForm):
    """Morphology specification for a Morpheme"""

    parent_gloss_id = forms.CharField(label=_(u'Parent Gloss'))
    role = forms.ChoiceField(label=_(u'Type'),choices=build_choice_list('MorphologyType'),widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    morpheme_id = forms.CharField(label=_(u'Morpheme'));

    class Meta:
        model = MorphologyDefinition;
        fields = ['role'];

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
