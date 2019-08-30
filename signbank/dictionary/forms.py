from django import forms
from django.utils.translation import ugettext_lazy as _
from django.db import OperationalError
from django.db.transaction import atomic
from signbank.video.fields import VideoUploadToFLVField
from signbank.dictionary.models import Dialect, Gloss, Morpheme, Definition, Relation, RelationToForeignSign, \
                                        MorphologyDefinition, build_choice_list, OtherMedia, Handshape, \
                                        AnnotationIdglossTranslation, Dataset, FieldChoice, LemmaIdgloss, \
                                        LemmaIdglossTranslation, Translation, Keyword, Language, SignLanguage
from django.conf import settings
from tagging.models import Tag
import datetime as DT
from signbank.settings.server_specific import DEFAULT_KEYWORDS_LANGUAGE
from signbank.settings.base import FIELDS

from signbank.dictionary.translate_choice_list import choicelist_queryset_to_translated_dict
from django.utils.translation import gettext

from django_select2 import *
from easy_select2.widgets import Select2, Select2Multiple

# category choices are tag values that we'll restrict search to
CATEGORY_CHOICES = (('all', 'All Signs'),
                    ('semantic:health', 'Only Health Related Signs'),
                    ('semantic:education', 'Only Education Related Signs'))

#See if there are any tags there, but don't crash if there isn't even a table
try:
    tag_choices = [(tag.name, tag.name.replace('_',' ')) for tag in Tag.objects.all()]
    not_tag_choices = [(tag.name, tag.name) for tag in Tag.objects.all()]
except OperationalError:
    tag_choices = []
    not_tag_choices = []

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
    last_used_dataset = None

    class Meta:
        model = Gloss
        fields = []

    def __init__(self, queryDict, *args, **kwargs):
        self.languages = kwargs.pop('languages')
        self.user = kwargs.pop('user')
        self.last_used_dataset = kwargs.pop('last_used_dataset')

        super(GlossCreateForm, self).__init__(queryDict, *args, **kwargs)

        if 'dataset' in queryDict:
            self.fields['dataset'] = forms.ModelChoiceField(queryset=Dataset.objects.all())
            self.fields['dataset'].initial = queryDict['dataset']

        for language in self.languages:
            glosscreate_field_name = self.gloss_create_field_prefix + language.language_code_2char
            self.fields[glosscreate_field_name] = forms.CharField(label=_("Gloss")+(" (%s)" % language.name))
            if glosscreate_field_name in queryDict:
                self.fields[glosscreate_field_name].value = queryDict[glosscreate_field_name]

    @atomic  # This rolls back the gloss creation if creating annotationidglosstranslations fails
    def save(self, commit=True):
        gloss = super(GlossCreateForm, self).save(commit)
        dataset = Dataset.objects.get(id=self['dataset'].value())
        for language in self.languages:
            glosscreate_field_name = self.gloss_create_field_prefix + language.language_code_2char
            annotation_idgloss_text = self[glosscreate_field_name].value()
            existing_annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
            if existing_annotationidglosstranslations is None or len(existing_annotationidglosstranslations) == 0:
                annotationidglosstranslation = AnnotationIdglossTranslation(gloss=gloss, language=language,
                                                                            text=annotation_idgloss_text,
                                                                            dataset=dataset)
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

        default_language = Language.objects.get(language_code_2char=DEFAULT_KEYWORDS_LANGUAGE['language_code_2char'])
        # create empty keywords (Keyword '' has default language)
        # when the newly created gloss is later edited in GlossDetailView, when the user enters new keywords,
        # the old keywords are removed on (via clear), so setting the initial keywords to '' here is a placeholder
        (kobj, created) = Keyword.objects.get_or_create(text='')
        trans = Translation(gloss=gloss, translation=kobj, index=0, language=default_language)
        trans.save()

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
    last_used_dataset = None

    class Meta:
        model = Morpheme
        fields = ['mrpType']

    def __init__(self, queryDict, *args, **kwargs):
        self.languages = kwargs.pop('languages')
        self.user = kwargs.pop('user')
        self.last_used_dataset = kwargs.pop('last_used_dataset')

        super(MorphemeCreateForm, self).__init__(queryDict, *args, **kwargs)

        for language in self.languages:
            morphemecreate_field_name = self.morpheme_create_field_prefix + language.language_code_2char
            self.fields[morphemecreate_field_name] = forms.CharField(label=_("Gloss")+(" (%s)" % language.name))
            if morphemecreate_field_name in queryDict:
                self.fields[morphemecreate_field_name].value = queryDict[morphemecreate_field_name]

    @atomic  # This rolls back the gloss creation if creating annotationidglosstranslations fails
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

        default_language = Language.objects.get(language_code_2char=DEFAULT_KEYWORDS_LANGUAGE['language_code_2char'])
        # create empty keywords (Keyword '' has default language)
        # when the newly created morpheme is later edited in MorphemeDetailView, when the user enters new keywords,
        # the old keywords are removed (via clear), so setting the initial keywords to '' here is a placeholder
        (kobj, created) = Keyword.objects.get_or_create(text='')
        trans = Translation(gloss=morpheme, translation=kobj, index=0, language=default_language)
        trans.save()

        return morpheme


class TagUpdateForm(forms.Form):
    """Form to add a new tag to a gloss"""

    tag = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control'}), 
                            choices=tag_choices)
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
    sortOrder = forms.CharField(label=_("Sort Order"))       # Used in glosslistview to store user-selection
    englishGloss = forms.CharField(label=_("English Gloss"))
    tags = forms.MultipleChoiceField(choices=tag_choices)
    nottags = forms.MultipleChoiceField(choices=not_tag_choices)
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
    keyword_search_field_prefix = "keywords_"
    lemma_search_field_prefix = "lemma_"

    class Meta:

        ATTRS_FOR_FORMS = {'class':'form-control'}

        model = Gloss
        fields = settings.FIELDS['phonology'] + settings.FIELDS['semantics'] + settings.FIELDS['main'] + ['inWeb', 'isNew']

    def __init__(self, queryDict, *args, **kwargs):
        languages = kwargs.pop('languages')
        sign_languages = kwargs.pop('sign_languages')
        dialects = kwargs.pop('dialects')
        language_code = kwargs.pop('language_code')
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

            # and for LemmaIdgloss
            lemma_field_name = self.lemma_search_field_prefix + language.language_code_2char
            setattr(self, lemma_field_name, forms.CharField(label=_("Lemma")+(" (%s)" % language.name)))
            if lemma_field_name in queryDict:
                getattr(self, lemma_field_name).value = queryDict[lemma_field_name]

        field_label_signlanguage = gettext("Sign language")
        field_label_dialects = gettext("Dialect")
        self.fields['signLanguage'] = forms.ModelMultipleChoiceField(label=field_label_signlanguage, widget=Select2,
                    queryset=SignLanguage.objects.filter(id__in=[signlanguage[0] for signlanguage in sign_languages]))

        self.fields['dialects'] = forms.ModelMultipleChoiceField(label=field_label_dialects, widget=Select2,
                    queryset=Dialect.objects.filter(id__in=[dia[0] for dia in dialects]))

        field_language = language_code
        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew']
        try:
            multiple_select_gloss_fields = [(field.name, field.field_choice_category) for field in Gloss._meta.fields if field.name in fieldnames and len(field.choices) > 0]
        except:
            print('GlossSearchForm error getting multiple_select_gloss_fields, set to empty list. Check models.py for choice list declarations.')
            multiple_select_gloss_fields = []
        for (fieldname, field_category) in multiple_select_gloss_fields:
            field_label = self.Meta.model._meta.get_field(fieldname).verbose_name
            field_choices = FieldChoice.objects.filter(field__iexact=field_category)
            translated_choices = [('0','---------')] + choicelist_queryset_to_translated_dict(field_choices,field_language,ordered=False,id_prefix='',shortlist=True)
            self.fields[fieldname] = forms.TypedMultipleChoiceField(label=field_label,
                                                        choices=translated_choices,
                                                        required=False, widget=Select2)


class MorphemeSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Dutch Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"))  # Used in morphemelistview to store user-selection
    englishGloss = forms.CharField(label=_("English Gloss"))
    lemmaGloss = forms.CharField(label=_("Lemma Gloss"))
    tags = forms.MultipleChoiceField(choices=tag_choices)
    nottags = forms.MultipleChoiceField(choices=not_tag_choices)
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
    keyword_search_field_prefix = "keyword_"

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'}

        model = Morpheme

        fields = settings.FIELDS['phonology'] + settings.FIELDS['semantics'] + settings.FIELDS['main'] + ['inWeb', 'isNew']

    def __init__(self, queryDict, *args, **kwargs):
        languages = kwargs.pop('languages')
        sign_languages = kwargs.pop('sign_languages')
        dialects = kwargs.pop('dialects')
        language_code = kwargs.pop('language_code')
        super(MorphemeSearchForm, self).__init__(queryDict, *args, **kwargs)

        for language in languages:
            morphemesearch_field_name = self.morpheme_search_field_prefix + language.language_code_2char
            setattr(self, morphemesearch_field_name, forms.CharField(label=_("Gloss") + (" (%s)" % language.name)))
            if morphemesearch_field_name in queryDict:
                getattr(self, morphemesearch_field_name).value = queryDict[morphemesearch_field_name]

            # do the same for Translations
            keyword_field_name = self.keyword_search_field_prefix + language.language_code_2char
            setattr(self, keyword_field_name, forms.CharField(label=_("Translations")+(" (%s)" % language.name)))
            if keyword_field_name in queryDict:
                getattr(self, keyword_field_name).value = queryDict[keyword_field_name]

        field_label_signlanguage = gettext("Sign language")
        field_label_dialects = gettext("Dialect")
        self.fields['SIGNLANG'] = forms.ModelMultipleChoiceField(label=field_label_signlanguage, widget=Select2,
                    queryset=SignLanguage.objects.filter(id__in=[signlanguage[0] for signlanguage in sign_languages]))

        self.fields['dialects'] = forms.ModelMultipleChoiceField(label=field_label_dialects, widget=Select2,
                    queryset=Dialect.objects.filter(id__in=[dia[0] for dia in dialects]))

        field_language = language_code
        fieldnames = FIELDS['main']+FIELDS['phonology']+FIELDS['semantics']+['inWeb', 'isNew', 'mrpType']
        try:
            multiple_select_morpheme_fields = [(field.name, field.field_choice_category) for field in Morpheme._meta.fields if field.name in fieldnames and len(field.choices) > 0]
        except:
            print('MorphemeSearchForm error getting multiple_select_morpheme_fields, set to empty list. Check models.py for choice list declarations.')
            multiple_select_morpheme_fields = []
        for (fieldname, field_category) in multiple_select_morpheme_fields:
            field_label = self.Meta.model._meta.get_field(fieldname).verbose_name
            field_choices = FieldChoice.objects.filter(field__iexact=field_category)
            translated_choices = [('0','---------')] + choicelist_queryset_to_translated_dict(field_choices,field_language,ordered=False,id_prefix='',shortlist=True)
            self.fields[fieldname] = forms.TypedMultipleChoiceField(label=field_label,
                                                        choices=translated_choices,
                                                        required=False, widget=Select2)

class DefinitionForm(forms.ModelForm):
    note = forms.ChoiceField(label=_(u'Type'), choices=build_choice_list('NoteType'),
                             widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    class Meta:
        model = Definition
        fields = ('published','count', 'text')
        
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
    description = forms.CharField(label=_(u'Meaning'), required=False)
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
    """Form for image upload for a particular gloss"""

    imagefile = forms.FileField(label="Upload Image")
    gloss_id = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)

class DatasetUpdateForm(forms.ModelForm):

    description = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 5, 'placeholder': 'Description'}))
    copyright = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 5, 'placeholder': 'Copyright'}))
    conditions_of_use = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 5, 'placeholder': 'Conditions of use'}))
    reference = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 5, 'placeholder': 'Reference'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'}

        model = Dataset
        fields = ['description', 'conditions_of_use', 'acronym', 'copyright', 'reference', 'owners', 'is_public', 'default_language']

    def __init__(self, *args, **kwargs):
        languages = kwargs.pop('languages')
        super(DatasetUpdateForm, self).__init__(*args, **kwargs)
        self.fields['default_language'] = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control'}), choices=languages)

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
    """Form for image upload for a particular gloss"""

    imagefile = forms.FileField(label="Upload Image")
    handshape_id = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)


class LemmaCreateForm(forms.ModelForm):
    """Form for creating a new lemma from scratch"""

    lemma_create_field_prefix = "lemmacreate_"
    languages = None # Languages to use for lemma idgloss translations
    user = None

    class Meta:
        model = LemmaIdgloss
        fields = ['dataset']

    def __init__(self, queryDict, *args, **kwargs):
        if 'languages' in kwargs:
            self.languages = kwargs.pop('languages')
        self.user = kwargs.pop('user')
        super(LemmaCreateForm, self).__init__(queryDict, *args, **kwargs)

        from signbank.tools import get_selected_datasets_for_user
        if not self.languages:
            selected_datasets = get_selected_datasets_for_user(self.user)
            self.languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

        for language in self.languages:
            lemmacreate_field_name = self.lemma_create_field_prefix + language.language_code_2char
            self.fields[lemmacreate_field_name] = forms.CharField(label=_("Lemma")+(" (%s)" % language.name))
            if lemmacreate_field_name in queryDict:
                self.fields[lemmacreate_field_name].initial = queryDict[lemmacreate_field_name]

    @atomic  # This rolls back the lemma creation if creating lemmaidglosstranslations fails
    def save(self, commit=True):
        lemma = super(LemmaCreateForm, self).save(commit)
        for language in self.languages:
            lemmacreate_field_name = self.lemma_create_field_prefix + language.language_code_2char
            lemma_idgloss_text = self[lemmacreate_field_name].value()
            existing_lemmaidglosstranslations = lemma.lemmaidglosstranslation_set.filter(language=language)
            if existing_lemmaidglosstranslations is None or len(existing_lemmaidglosstranslations) == 0:
                lemmaidglosstranslation = LemmaIdglossTranslation(lemma=lemma, language=language,
                                                                            text=lemma_idgloss_text)
                lemmaidglosstranslation.save()
            elif len(existing_lemmaidglosstranslations) == 1:
                lemmaidglosstranslation = existing_lemmaidglosstranslations[0]
                lemmaidglosstranslation.text = lemma_idgloss_text
                lemmaidglosstranslation.save()
            else:
                raise Exception(
                    "In class %s: gloss with id %s has more than one lemma idgloss translation for language %s"
                    % (self.__class__.__name__, lemma.pk, language.name)
                )
        return lemma


class LemmaUpdateForm(forms.ModelForm):
    """Form for updating a lemma"""
    lemma_update_field_prefix = "lemmaupdate_"

    class Meta:
        model = LemmaIdgloss
        fields = []

    def __init__(self, queryDict=None, *args, **kwargs):
        if 'page_in_lemma_list' in kwargs:
            self.page_in_lemma_list = kwargs.pop('page_in_lemma_list')

        super(LemmaUpdateForm, self).__init__(queryDict, *args, **kwargs)
        # print("Object: " + str(self.instance))
        self.languages = self.instance.dataset.translation_languages.all()

        for language in self.languages:
            lemmaupdate_field_name = self.lemma_update_field_prefix + language.language_code_2char
            self.fields[lemmaupdate_field_name] = forms.CharField(label=_("Lemma") + (" (%s)" % language.name), required=False)
            if queryDict:
                if lemmaupdate_field_name in queryDict:
                    self.fields[lemmaupdate_field_name].initial = queryDict[lemmaupdate_field_name]
            else:
                try:
                    self.fields[lemmaupdate_field_name].initial = \
                        self.instance.lemmaidglosstranslation_set.get(language=language).text
                except:
                    pass

    @atomic
    def save(self, commit=True):
        # print("PRE SAVE for Translations")
        # print('languages: ', self.languages)
        # the number of translations should be at least 1
        instance_has_translations = self.instance.lemmaidglosstranslation_set.count()
        # print('instance has translations: ', instance_has_translations)
        for language in self.languages:
            lemmaupdate_field_name = self.lemma_update_field_prefix + language.language_code_2char
            lemma_idgloss_text = self.fields[lemmaupdate_field_name].initial
            existing_lemmaidglosstranslations = self.instance.lemmaidglosstranslation_set.filter(language=language)
            # print('existing lemma trans for lang ', language, ': ', existing_lemmaidglosstranslations)
            if existing_lemmaidglosstranslations is None or len(existing_lemmaidglosstranslations) == 0:
                if lemma_idgloss_text == '':
                    # lemma translation is already empty for this language
                    # don't create an empty translation
                    pass
                else:
                    # save a new translation
                    lemmaidglosstranslation = LemmaIdglossTranslation(lemma=self.instance, language=language,
                                                                    text=lemma_idgloss_text)
                    lemmaidglosstranslation.save()
            elif len(existing_lemmaidglosstranslations) == 1:
                lemmaidglosstranslation = existing_lemmaidglosstranslations[0]
                if lemma_idgloss_text == '':
                    # delete existing translation if there is already a translation for a different language
                    if instance_has_translations > 1:
                        # print('try to delete text', str(lemmaidglosstranslation.pk))
                        translation_to_delete = LemmaIdglossTranslation.objects.get(pk = lemmaidglosstranslation.pk, language = language)
                        translation_to_delete.delete()
                        # one of the translations has been deleted, update the total
                        instance_has_translations -= 1
                    else:
                        # print('raise exception 1')
                        # this exception refuses to be put into messages after being caught in LemmaUpdateView
                        # gives a runtime error
                        # therefore the exception is caught byt a different message is displayed
                        raise Exception("Lemma with id %s must have at least one translation."% (self.instance.pk))
                else:
                    # print('save new translation')
                    lemmaidglosstranslation.text = lemma_idgloss_text
                    lemmaidglosstranslation.save()
            else:
                # print('exception 2: existing translations length > 1: ', existing_lemmaidglosstranslations)
                raise Exception("Lemma with id %s has more than one lemma idgloss translation for language %s"% (self.instance.pk, language.name))
        # print("POST SAVE for Translations")
        return


