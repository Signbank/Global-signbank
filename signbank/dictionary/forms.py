from colorfield.fields import ColorWidget
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _, get_language
from django.db import OperationalError, ProgrammingError
from django.db.transaction import atomic
from signbank.video.fields import VideoUploadToFLVField
from signbank.dictionary.models import Dialect, Gloss, Morpheme, Definition, Relation, RelationToForeignSign, \
                                        MorphologyDefinition, OtherMedia, Handshape, SemanticField, DerivationHistory, \
                                        AnnotationIdglossTranslation, Dataset, FieldChoice, LemmaIdgloss, \
                                        LemmaIdglossTranslation, Translation, Keyword, Language, SignLanguage
from django.conf import settings
from tagging.models import Tag
import datetime as DT
from signbank.settings.server_specific import DEFAULT_KEYWORDS_LANGUAGE, LANGUAGES
from signbank.settings.base import FIELDS

from signbank.dictionary.translate_choice_list import choicelist_queryset_to_translated_dict
from django.utils.translation import gettext

from django_select2 import *
from easy_select2.widgets import Select2, Select2Multiple

# category choices are tag values that we'll restrict search to
CATEGORY_CHOICES = (('all', 'All Signs'),
                    ('semantic:health', 'Only Health Related Signs'),
                    ('semantic:education', 'Only Education Related Signs'))


# See if there are any tags there, but don't crash if there isn't even a table
def tag_choices():
    try:
        tag_choices_list = [(tag.name, tag.name.replace('_', ' ')) for tag in Tag.objects.all()]
    except (OperationalError, ProgrammingError) as e:
        tag_choices_list = []
    return tag_choices_list


def not_tag_choices():
    try:
        not_tag_choices_list = [(tag.name, tag.name) for tag in Tag.objects.all()]
    except:
        not_tag_choices_list = []
    return not_tag_choices_list


class UserSignSearchForm(forms.Form):

    glossQuery = forms.CharField(label=_(u'Glosses Containing'), max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    query = forms.CharField(label=_(u'Translations Containing'), max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
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

    morphQuery = forms.CharField(label=_(u'Morphemes Containing'), max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'class': 'form-control'}))
    query = forms.CharField(label=_(u'Translations Containing'), max_length=100, required=False,
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

        if 'dataset' in queryDict:
            self.fields['dataset'] = forms.ModelChoiceField(queryset=Dataset.objects.all())
            self.fields['dataset'].initial = queryDict['dataset']

        for language in self.languages:
            morphemecreate_field_name = self.morpheme_create_field_prefix + language.language_code_2char
            self.fields[morphemecreate_field_name] = forms.CharField(label=_("Morpheme")+(" (%s)" % language.name))
            if morphemecreate_field_name in queryDict:
                self.fields[morphemecreate_field_name].value = queryDict[morphemecreate_field_name]

    @atomic  # This rolls back the gloss creation if creating annotationidglosstranslations fails
    def save(self, commit=True):
        morpheme = super(MorphemeCreateForm, self).save(commit)
        dataset = Dataset.objects.get(id=self['dataset'].value())
        for language in self.languages:
            morphemecreate_field_name = self.morpheme_create_field_prefix + language.language_code_2char
            annotation_idgloss_text = self.fields[morphemecreate_field_name].value
            existing_annotationidglosstranslations = morpheme.annotationidglosstranslation_set.filter(language=language)
            if existing_annotationidglosstranslations is None or len(existing_annotationidglosstranslations) == 0:
                annotationidglosstranslation = AnnotationIdglossTranslation(gloss=morpheme, language=language,
                                                                            text=annotation_idgloss_text,
                                                                            dataset=dataset)
                annotationidglosstranslation.save()
            elif len(existing_annotationidglosstranslations) == 1:
                annotationidglosstranslation = existing_annotationidglosstranslations[0]
                annotationidglosstranslation.text = annotation_idgloss_text
                annotationidglosstranslation.save()
            else:
                raise Exception(
                    "In class %s: morpheme with id %s has more than one annotation idgloss translation for language %s"
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

YESNOCHOICES = (('unspecified', "---------" ), ('yes', 'Yes'), ('no', 'No'))
NULLBOOLEANCHOICES = [(0,'---------'),(2,'True'),(3,'False')]
NONEBOOLEANCHOICES = [(0,'---------'),(1,'None'),(2,'True'),(3,'False')]
UNKNOWNBOOLEANCHOICES = [(0,'---------'),(2,'True'),(3,'False')]
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
                         ('paradigm', 'Handshape Paradigm')
                         )


def get_definition_role_choices():
    choices = [('','---------'),('all','All')]
    return choices


def get_component_role_choice():
    choices = [('','---------')]
    return choices


def get_morpheme_role_choices():
    choices = [('','---------')]
    return choices


ATTRS_FOR_FORMS = {'class':'form-control'}

class GlossSearchForm(forms.ModelForm):

    use_required_attribute = False #otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Search Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"))       # Used in glosslistview to store user-selection
    # englishGloss = forms.CharField(label=_("English Gloss"))
    tags = forms.MultipleChoiceField(label=_('Tags'), choices=tag_choices)
    nottags = forms.MultipleChoiceField(label=_('Not Tags'), choices=not_tag_choices)  # this field is not used in the template
    keyword = forms.CharField(label=_('Search Translations'))
    hasvideo = forms.ChoiceField(label=_('Has Video'), choices=NULLBOOLEANCHOICES)
    hasothermedia = forms.ChoiceField(label=_('Has Other Media'), choices=NULLBOOLEANCHOICES)
    defspublished = forms.ChoiceField(label=_("All Definitions Published"), choices=YESNOCHOICES)

    # defsearch = forms.CharField(label=_(u'Search Definition/Notes')) # this field is a duplicate of definitionContains

    relation = forms.CharField(label=_(u'Gloss of Related Sign'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    relationToForeignSign = forms.CharField(label=_(u'Gloss of Foreign Sign'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    morpheme = forms.CharField(label=_(u'Search for gloss with this as morpheme'))

    oriChAbd = forms.ChoiceField(label=_(u'Abduction Change'),choices=NULLBOOLEANCHOICES)
    oriChFlex = forms.ChoiceField(label=_(u'Flexion Change'),choices=NULLBOOLEANCHOICES)

    phonOth = forms.CharField(label=_(u'Phonology Other'),widget=forms.TextInput())

    hasRelationToForeignSign = forms.ChoiceField(label=_(u'Related to Foreign Sign'),choices=[(0,'---------'),(1,'Yes'),(2,'No')],widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasRelation = forms.ChoiceField(label=_(u'Type of Relation'),choices=RELATION_ROLE_CHOICES,widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    # these field's choices are set dynamically in the __init__ method below
    # that they appear here is used statically by the query parameters method which looks at the gloss search form fields
    hasComponentOfType = forms.ChoiceField(label=_(u'Has Compound Component Type'),
                                           choices=get_component_role_choice,
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasComponentOfType.field_choice_category = 'MorphologyType'
    hasMorphemeOfType = forms.ChoiceField(label=_(u'Has Morpheme Type'),
                                          choices=get_morpheme_role_choices,
                                          widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasMorphemeOfType.field_choice_category = 'MorphemeType'

    repeat = forms.ChoiceField(label=_(u'Repeating Movement'),choices=NULLBOOLEANCHOICES)
    altern = forms.ChoiceField(label=_(u'Alternating Movement'),choices=NULLBOOLEANCHOICES)

    weakprop = forms.ChoiceField(label=_(u'Weak Prop'),choices=NEUTRALQUERYCHOICES)
    weakdrop = forms.ChoiceField(label=_(u'Weak Drop'),choices=NEUTRALQUERYCHOICES)

    domhndsh_letter = forms.ChoiceField(label=_(u'letter'),choices=UNKNOWNBOOLEANCHOICES)
    domhndsh_number = forms.ChoiceField(label=_(u'number'),choices=UNKNOWNBOOLEANCHOICES)

    subhndsh_letter = forms.ChoiceField(label=_(u'letter'),choices=UNKNOWNBOOLEANCHOICES)
    subhndsh_number = forms.ChoiceField(label=_(u'number'),choices=UNKNOWNBOOLEANCHOICES)

    isNew = forms.ChoiceField(label=_(u'Is a proposed new sign'),choices=NULLBOOLEANCHOICES)
    inWeb = forms.ChoiceField(label=_(u'Is in Web Dictionary'),choices=NULLBOOLEANCHOICES)
    excludeFromEcv = forms.ChoiceField(label=_(u'Exclude from ECV'),choices=NULLBOOLEANCHOICES)

    # this field's choices are set dynamically in the __init__ method below
    # It's presence here is used statically by the query parameters method which looks at the gloss search form fields
    definitionRole = forms.ChoiceField(label=_(u'Note Type'),
                                       choices=get_definition_role_choices,
                                       widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionRole.field_choice_category = 'NoteType'
    definitionContains = forms.CharField(label=_(u'Note Contains'),widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    createdBy = forms.CharField(label=_(u'Created By'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    createdAfter = forms.DateField(label=_(u'Created After'), widget=forms.DateInput(attrs={'placeholder': _('mm/dd/yyyy')}))

    createdBefore = forms.DateField(label=_(u'Created Before'), widget=forms.DateInput(attrs={'placeholder': _('mm/dd/yyyy')}))


    gloss_search_field_prefix = "glosssearch_"
    keyword_search_field_prefix = "keyword_"
    lemma_search_field_prefix = "lemma_"

    class Meta:

        ATTRS_FOR_FORMS = {'class':'form-control'}

        model = Gloss
        fields = settings.FIELDS['phonology'] + settings.FIELDS['semantics'] + settings.FIELDS['main'] + ['inWeb', 'isNew', 'excludeFromEcv']

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

        field_label_signlanguage = gettext("Sign Language")
        field_label_dialects = gettext("Dialect")
        self.fields['signLanguage'] = forms.ModelMultipleChoiceField(label=field_label_signlanguage, widget=Select2,
                    queryset=SignLanguage.objects.filter(id__in=[signlanguage[0] for signlanguage in sign_languages]))

        self.fields['dialects'] = forms.ModelMultipleChoiceField(label=field_label_dialects, widget=Select2,
                    queryset=Dialect.objects.filter(id__in=[dia[0] for dia in dialects]))

        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew', 'excludeFromEcv']
        multiple_select_gloss_fields = [(field.name, field.field_choice_category) for field in Gloss._meta.fields if field.name in fieldnames and hasattr(field, 'field_choice_category') ]

        for (fieldname, field_category) in multiple_select_gloss_fields:
            field_label = self.Meta.model._meta.get_field(fieldname).verbose_name
            if fieldname.startswith('semField'):
                field_choices = SemanticField.objects.all()
            elif fieldname.startswith('derivHist'):
                field_choices = DerivationHistory.objects.all()
            elif fieldname in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
                field_choices = Handshape.objects.all()
            else:
                field_choices = FieldChoice.objects.filter(field__iexact=field_category)
            translated_choices = choicelist_queryset_to_translated_dict(field_choices,ordered=False,id_prefix='',shortlist=True)
            self.fields[fieldname] = forms.TypedMultipleChoiceField(label=field_label,
                                                        choices=translated_choices,
                                                        required=False, widget=Select2)
        self.fields['definitionRole'] = forms.ChoiceField(label=_(u'Note Type'),
                                                          choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='NoteType').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                          ),
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hasComponentOfType'] = forms.ChoiceField(label=_(u'Has Compound Component Type'),
                                                          choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='MorphologyType').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                          ),
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hasMorphemeOfType'] = forms.ChoiceField(label=_(u'Has Morpheme Type'),
                                                          choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='MorphemeType').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                          ),
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))

class MorphemeSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Dutch Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"))  # Used in morphemelistview to store user-selection
    # englishGloss = forms.CharField(label=_("English Gloss"))
    lemmaGloss = forms.CharField(label=_("Lemma Gloss")) # used in Morpheme Search
    tags = forms.MultipleChoiceField(choices=tag_choices)
    nottags = forms.MultipleChoiceField(choices=not_tag_choices)
    keyword = forms.CharField(label=_(u'Translations'))
    hasvideo = forms.ChoiceField(label=_(u'Has Video'), choices=NULLBOOLEANCHOICES)
    hasothermedia = forms.ChoiceField(label=_(u'Has Other Media'), choices=NULLBOOLEANCHOICES)
    useInstr = forms.CharField(label=_("Annotation instructions"))
    # defspublished = forms.ChoiceField(label=_("All Definitions Published"), choices=YESNOCHOICES)

    # defsearch = forms.CharField(label=_(u'Search Definition/Notes'))

    relation = forms.CharField(label=_(u'Search for Gloss of Related Signs'),
                               widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    relationToForeignSign = forms.CharField(label=_(u'Search for Gloss of Foreign Signs'),
                                            widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    morpheme = forms.CharField(label=_(u'Search for Gloss with This as Morpheme'),
                               widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    phonOth = forms.CharField(label=_(u'Phonology Other'), widget=forms.TextInput())

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
    inWeb = forms.ChoiceField(label=_(u'Is in Web Dictionary'), choices=NULLBOOLEANCHOICES,
                              widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionRole = forms.ChoiceField(label=_(u'Note Type'), choices=get_definition_role_choices,
                                       widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionRole.field_choice_category = 'NoteType'
    definitionContains = forms.CharField(label=_(u'Note Contains'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    createdBefore = forms.DateField(label=_(u'Created Before'))
    createdAfter = forms.DateField(label=_(u'Created After'))

    createdBy = forms.CharField(label=_(u'Created By'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    morpheme_search_field_prefix = "morphemesearch_"
    keyword_search_field_prefix = "keyword_"

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'}

        model = Morpheme

        fields = settings.MORPHEME_DISPLAY_FIELDS + settings.FIELDS['semantics'] + settings.FIELDS['main'] + ['inWeb', 'isNew']

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

        field_label_signlanguage = gettext("Sign Language")
        field_label_dialects = gettext("Dialect")
        self.fields['SIGNLANG'] = forms.ModelMultipleChoiceField(label=field_label_signlanguage, widget=Select2,
                    queryset=SignLanguage.objects.filter(id__in=[signlanguage[0] for signlanguage in sign_languages]))

        self.fields['dialects'] = forms.ModelMultipleChoiceField(label=field_label_dialects, widget=Select2,
                    queryset=Dialect.objects.filter(id__in=[dia[0] for dia in dialects]))

        field_language = language_code
        fieldnames = FIELDS['main']+settings.MORPHEME_DISPLAY_FIELDS+FIELDS['semantics']+['inWeb', 'isNew', 'mrpType']
        multiple_select_morpheme_fields = [(field.name, field.field_choice_category) for field in Morpheme._meta.fields if field.name in fieldnames and hasattr(field, 'field_choice_category') ]

        for (fieldname, field_category) in multiple_select_morpheme_fields:
            field_label = self.Meta.model._meta.get_field(fieldname).verbose_name
            field_choices = FieldChoice.objects.filter(field__iexact=field_category)
            translated_choices = choicelist_queryset_to_translated_dict(field_choices,ordered=False,id_prefix='',shortlist=True)
            self.fields[fieldname] = forms.TypedMultipleChoiceField(label=field_label,
                                                        choices=translated_choices,
                                                        required=False, widget=Select2)

class DefinitionForm(forms.ModelForm):
    class Meta:
        model = Definition
        fields = ('published','count', 'text')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['note'] = forms.ChoiceField(label=_(u'Type'),
                             choices=choicelist_queryset_to_translated_dict(
                                 list(FieldChoice.objects.filter(field='NoteType').order_by(
                                     'machine_value') ),
                                 ordered=False, id_prefix='', shortlist=False
                             ),
                             widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        
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


def get_morphology_type_choices():
    choices = [('','---------')]
    return choices


class GlossMorphologyForm(forms.ModelForm):
    """Morphology specification of a Gloss"""

    parent_gloss_id = forms.CharField(label=_(u'Parent Gloss'))
    # role = forms.ChoiceField(label=_(u'Type'),choices=get_morphology_type_choices,
    #                          widget=forms.Select(attrs=ATTRS_FOR_FORMS), required=True)
    morpheme_id = forms.CharField(label=_(u'Morpheme'))

    class Meta:
        model = MorphologyDefinition
        fields = []

    def __init__(self, *args, **kwargs):
        super(GlossMorphologyForm, self).__init__(*args, **kwargs)
        self.fields['role'] = forms.ChoiceField(label=_(u'Type'),
                                                choices= choicelist_queryset_to_translated_dict(
                                                    list(FieldChoice.objects.filter(field='MorphologyType').order_by(
                                                        'machine_value')),
                                                    ordered=False, id_prefix='', shortlist=False
                                                ),
                                                widget=forms.Select(attrs=ATTRS_FOR_FORMS), required=True)

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


def get_other_media_type_choices():
    choices = [('','---------')]
    return choices

class OtherMediaForm(forms.ModelForm):

    gloss = forms.CharField()
    file = forms.FileField(widget=forms.FileInput(attrs={'accept':'video/*, image/*, application/pdf'}), required=True)
    # type = forms.ChoiceField(choices=get_other_media_type_choices,widget=forms.Select(attrs=ATTRS_FOR_FORMS), required=True)
    alternative_gloss = forms.TextInput()

    class Meta:
        model = OtherMedia
        fields = ['file']

    def __init__(self, *args, **kwargs):
        super(OtherMediaForm, self).__init__(*args, **kwargs)
        self.fields['type'] = forms.ChoiceField(label=_(u'Type'),
                                                choices= choicelist_queryset_to_translated_dict(
                                                    list(FieldChoice.objects.filter(field='OtherMediaType').order_by(
                                                        'machine_value')),
                                                    ordered=False, id_prefix='', shortlist=False
                                                ),
                                                widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    def get_form(self, request, obj=None, **kwargs):
        form = super(OtherMediaForm, self).get_form(request, obj, **kwargs)
        return form

    def clean_type(self):
        data = self.cleaned_data['type']
        if data in ['0', '1']:
            # choice is '-' or 'N/A'
            raise forms.ValidationError(_("Please choose a type description when uploading other media."))
        else:
            return data

    def clean_file(self):
        data = self.cleaned_data['file']
        if not data:
            raise forms.ValidationError(_("Please choose a video or image file to upload."))
        else:
            return data

class CSVMetadataForm(forms.Form):

    file = forms.FileField()

class EAFFilesForm(forms.Form):

    file = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))

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

def get_finger_selection_choices():
    choices = [('','---------')]
    return choices

def get_quantity_choices():
    choices = [('','---------')]
    return choices

def get_joint_configuration_choices():
    choices = [('','---------')]
    return choices

def get_spreading_choices():
    choices = [('','---------')]
    return choices

def get_aperture_choices():
    choices = [('','---------')]
    return choices

attrs_default = {'class': 'form-control'}
FINGER_SELECTION = ((True, 'True'), (False, 'False'), (None, 'Either'))

class HandshapeSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Handshape"))
    sortOrder = forms.CharField(label=_("Sort Order"),
                                initial="machine_value")  # Used in Handshapelistview to store user-selection

    # this is used to pass the label to the handshapes list view, the choices aren't displayed, there are radio buttons
    unselectedFingers = forms.ChoiceField(label=_(u'Unselected Fingers Extended'), choices=get_finger_selection_choices,
                                        widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    hsFingConf = forms.ChoiceField(label=_(u'Finger configuration'), choices=get_joint_configuration_choices,
                                  widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hsFingConf2 = forms.ChoiceField(label=_(u'Finger configuration 2'), choices=get_joint_configuration_choices,
                                  widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hsNumSel = forms.ChoiceField(label=_(u'Quantity'), choices=get_quantity_choices,
                                  widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hsSpread = forms.ChoiceField(label=_(u'Spreading'), choices=get_spreading_choices,
                                  widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hsAperture = forms.ChoiceField(label=_(u'Aperture'), choices=get_aperture_choices,
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
        fields = ('machine_value', 'name',
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

    def __init__(self, queryDict=None, *args, **kwargs):
        super(HandshapeSearchForm, self).__init__(queryDict, *args, **kwargs)

        self.fields['unselectedFingers'] = forms.ChoiceField(label=_(u'Unselected Fingers Extended'),
                                                    choices=choicelist_queryset_to_translated_dict(
                                                        list(
                                                            FieldChoice.objects.filter(field='FingerSelection').order_by(
                                                                'machine_value')),
                                                        ordered=False, id_prefix='', shortlist=False
                                                    ),
                                                    widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsNumSel'] = forms.ChoiceField(label=_(u'Quantity'),
                                                          choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='Quantity').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                          ),
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsFingConf'] = forms.ChoiceField(label=_(u'Finger configuration'),
                                                          choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='JointConfiguration').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                          ),
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsFingConf2'] = forms.ChoiceField(label=_(u'Finger configuration 2'),
                                                          choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='JointConfiguration').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                          ),
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsSpread'] = forms.ChoiceField(label=_(u'Spreading'),
                                                          choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='Spreading').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                          ),
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsAperture'] = forms.ChoiceField(label=_(u'Aperture'),
                                                          choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='Aperture').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                          ),
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))

class ImageUploadForHandshapeForm(forms.Form):
    """Form for image upload for a particular gloss"""

    imagefile = forms.FileField(label="Upload Image")
    handshape_id = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)


NO_GLOSS_SELECTION = [(0,'False'),(1,'True')]

class LemmaSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Lemma"))
    sortOrder = forms.CharField(label=_("Sort Order"))
    lemma_search_field_prefix = "lemma_"
    no_glosses = forms.ChoiceField(label=_(u'Only show results without glosses'),choices=NO_GLOSS_SELECTION)
    has_glosses = forms.ChoiceField(label=_(u'Only show results with glosses'),choices=NO_GLOSS_SELECTION)

    class Meta:

        ATTRS_FOR_FORMS = {'class':'form-control'}

        model = LemmaIdgloss
        fields = ['dataset']

    def __init__(self, queryDict, *args, **kwargs):
        languages = kwargs.pop('languages')
        language_code = kwargs.pop('language_code')
        super(LemmaSearchForm, self).__init__(queryDict, *args, **kwargs)

        for language in languages:
            # and for LemmaIdgloss
            lemma_field_name = self.lemma_search_field_prefix + language.language_code_2char
            setattr(self, lemma_field_name, forms.CharField(label=_("Lemma")+(" (%s)" % language.name)))
            if lemma_field_name in queryDict:
                getattr(self, lemma_field_name).value = queryDict[lemma_field_name]


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
        self.languages = self.instance.dataset.translation_languages.all()

        for language in self.languages:
            lemmaupdate_field_name = self.lemma_update_field_prefix + language.language_code_2char
            self.fields[lemmaupdate_field_name] = forms.CharField(label=_("Lemma") + (" (%s)" % language.name), required=True)
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
        # the number of translations should be at least 1
        instance_has_translations = self.instance.lemmaidglosstranslation_set.count()
        for language in self.languages:
            lemmaupdate_field_name = self.lemma_update_field_prefix + language.language_code_2char
            lemma_idgloss_text = self.fields[lemmaupdate_field_name].initial
            existing_lemmaidglosstranslations = self.instance.lemmaidglosstranslation_set.filter(language=language)
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
                        translation_to_delete = LemmaIdglossTranslation.objects.get(pk = lemmaidglosstranslation.pk, language = language)
                        translation_to_delete.delete()
                        # one of the translations has been deleted, update the total
                        instance_has_translations -= 1
                    else:
                        # this exception refuses to be put into messages after being caught in LemmaUpdateView
                        # gives a runtime error
                        # therefore the exception is caught byt a different message is displayed
                        raise Exception("Lemma with id %s must have at least one translation."% (self.instance.pk))
                else:
                    lemmaidglosstranslation.text = lemma_idgloss_text
                    lemmaidglosstranslation.save()
            else:
                raise Exception("Lemma with id %s has more than one lemma idgloss translation for language %s"% (self.instance.pk, language.name))
        return

class FocusGlossSearchForm(forms.ModelForm):

    use_required_attribute = False #otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Dutch Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"))       # Used in glosslistview to store user-selection
    englishGloss = forms.CharField(label=_("English Gloss"))
    keyword = forms.CharField(label=_(u'Translations'))

    oriChAbd = forms.ChoiceField(label=_(u'Abduction Change'),choices=NULLBOOLEANCHOICES)
    oriChFlex = forms.ChoiceField(label=_(u'Flexion Change'),choices=NULLBOOLEANCHOICES)

    repeat = forms.ChoiceField(label=_(u'Repeating Movement'),choices=NULLBOOLEANCHOICES)
    altern = forms.ChoiceField(label=_(u'Alternating Movement'),choices=NULLBOOLEANCHOICES)

    createdBefore = forms.DateField(label=_(u'Created Before'), widget=forms.DateInput(attrs={'placeholder': _('mm/dd/yyyy')}))
    createdAfter = forms.DateField(label=_(u'Created After'), widget=forms.DateInput(attrs={'placeholder': _('mm/dd/yyyy')}))

    createdBy = forms.CharField(label=_(u'Created By'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    gloss_search_field_prefix = "glosssearch_"
    keyword_search_field_prefix = "keyword_"
    lemma_search_field_prefix = "lemma_"

    class Meta:

        ATTRS_FOR_FORMS = {'class':'form-control'}

        model = Gloss
        fields = settings.MINIMAL_PAIRS_SEARCH_FIELDS

    def __init__(self, queryDict, *args, **kwargs):
        languages = kwargs.pop('languages')
        sign_languages = kwargs.pop('sign_languages')
        dialects = kwargs.pop('dialects')
        language_code = kwargs.pop('language_code')
        super(FocusGlossSearchForm, self).__init__(queryDict, *args, **kwargs)

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

        field_label_signlanguage = gettext("Sign Language")
        field_label_dialects = gettext("Dialect")
        self.fields['signLanguage'] = forms.ModelMultipleChoiceField(label=field_label_signlanguage, widget=Select2,
                    queryset=SignLanguage.objects.filter(id__in=[signlanguage[0] for signlanguage in sign_languages]))

        self.fields['dialects'] = forms.ModelMultipleChoiceField(label=field_label_dialects, widget=Select2,
                    queryset=Dialect.objects.filter(id__in=[dia[0] for dia in dialects]))

        field_language = language_code
        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew']
        multiple_select_gloss_fields = [(field.name, field.field_choice_category) for field in Gloss._meta.fields if field.name in fieldnames and hasattr(field, 'field_choice_category') ]

        for (fieldname, field_category) in multiple_select_gloss_fields:
            field_label = self.Meta.model._meta.get_field(fieldname).verbose_name
            if fieldname.startswith('semField'):
                field_choices = SemanticField.objects.all()
            elif fieldname.startswith('derivHist'):
                field_choices = DerivationHistory.objects.all()
            elif fieldname in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
                field_choices = Handshape.objects.all()
            else:
                field_choices = FieldChoice.objects.filter(field__iexact=field_category)
            translated_choices = choicelist_queryset_to_translated_dict(field_choices,ordered=False,id_prefix='',shortlist=True)
            self.fields[fieldname] = forms.TypedMultipleChoiceField(label=field_label,
                                                        choices=translated_choices,
                                                        required=False, widget=Select2)

class FieldChoiceColorForm(forms.Form):
    field_color = forms.CharField(widget=ColorWidget)
    readonly_fields = ['machine_value']

    class Meta:
        model = FieldChoice
        fields = ['field', 'name_en'] \
                 + ['field_color', 'machine_value', ]


class FieldChoiceForm(forms.ModelForm):
    # this ModelForm is needed in order to validate against duplicates

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    show_english_only = settings.SHOW_ENGLISH_ONLY
    field_category = ''
    prepopulated_fields = {}

    class Meta:
        model = FieldChoice
        fields = ['field'] \
                 + ['name_' + language.replace('-', '_') for language in [l[0] for l in settings.LANGUAGES]] \
                 + ['field_color', 'machine_value', ]

    def __init__(self, *args, **kwargs):
        super(FieldChoiceForm, self).__init__(*args, **kwargs)

        # a new field choice is being created or edited
        # see if the user is inside a category
        try:
            changelist_filters = self.initial['_changelist_filters']
        except:
            changelist_filters = ''

        from urllib.parse import parse_qsl
        if changelist_filters:
            query_params = dict(parse_qsl(changelist_filters))
        else:
            query_params = ''
        if query_params:
            new_field_category = query_params.get('field__exact')
            self.fields['field'].initial = new_field_category
            # construct a singleton choice list in order to appear in the data fields
            self.fields['field'].widget = forms.Select(choices=[(new_field_category, new_field_category)])
        else:
            # restrict categories to those already existing
            # categories are determined by the fields in the Models, the user does not create categories
            field_choice_categories = FieldChoice.objects.all().values('field').distinct()
            field_choice_categories = [ f['field'] for f in field_choice_categories]
            field_choice_categories = sorted(list(set(field_choice_categories)))
            field_choices = [(f, f) for f in field_choice_categories]
            self.fields['field'].widget = forms.Select(choices=field_choices)

        if self.show_english_only:
            if 'name_en' in self.fields.keys():
                self.fields['name_en'].label = 'Name'
            else:
                # there was some weird stuff going on with the behind the scenes Django creation of a form
                # before getting to __init__
                # sometimes neither name_en nor name were present in the form
                print('other case init english only has no name_en field')
                self.fields['name'] = forms.CharField(max_length=50)
                self.fields['name'].label = 'Name'
                self.fields['name'].widget = forms.CharField(max_length=50)
                if self.instance.id:
                    self.fields['name'].initial = self.instance.name
                else:
                    self.fields['name'].initial = '-'
            for field_name in self.fields.keys():
                # there were some problems with the iteration that constructed the field names dynamically
                # at the moment this is hard coded because of that
                if field_name in ['name_nl', 'name_zh_hans']:
                    self.fields[field_name].widget = forms.HiddenInput()
                    self.fields[field_name].initial = '-'
        if not self.instance.id:
            self.fields['field_color'].initial = '#ffffff'
        else:
            self.fields['field_color'].initial = '#' + self.instance.field_color

        if not self.show_field_choice_colors:
            self.fields['field_color'].widget = forms.HiddenInput()
        else:
            # SHOW_FIELD_COLORS
            # set up the HTML color picker widget
            # for display in the HTML color picker, the field color needs to be prefixed with #
            # in the database,only the hex number is stored
            # adding a # has already been taken care for an instance object by the get_form of FieldChoiceAdmin
            self.fields['field_color'].widget = forms.TextInput(attrs={'type': 'color' })

        # in the model, the default value is ffffff
        # in the admin, the default value is a display value, so needs the #

        if self.instance.id:
            # we are updating a field choice
            instance_field = self.instance.field
            self.fields['field'].initial = instance_field
            # construct a singleton choice list to prevent user from changing it
            self.fields['field'].widget = forms.Select(choices=[(instance_field, instance_field)])

    def clean(self):
        # check that the field category and (english) name does not already occur
        super(FieldChoiceForm, self).clean()

        data_fields = self.data

        if self.show_english_only:
            if 'name_en' not in data_fields.keys():
                raise forms.ValidationError(_('The Name field is required'))
            else:
                en_name = data_fields['name_en']
        else:
            for language in [l[0] for l in LANGUAGES]:
                name_languagecode = 'name_'+ language.replace('-', '_')
                if name_languagecode not in data_fields.keys():
                    raise forms.ValidationError(_('The Name fields for all languages are required'))
            en_name = data_fields['name_en']

        if 'field_color' not in data_fields.keys():
            print('field color not in data fields')
        else:
            new_color = data_fields['field_color']
            # strip any initial #'s
            while new_color[0] == '#':
                new_color = new_color[1:]
            field_color = new_color

        if 'field' not in data_fields.keys() or not data_fields['field']:
            raise forms.ValidationError(_('The Field Choice Category is required'))
        field = data_fields['field']

        qs_f = FieldChoice.objects.filter(field=field)
        if qs_f.count() == 0:
            raise forms.ValidationError(_('This Field Choice Category does not exist'))

        qs_en = FieldChoice.objects.filter(field=field, name=en_name)
        if qs_en.count() == 0:
            # new field choice
            if not self._errors.keys():
                return
            else:
                raise forms.ValidationError(_('New Field Choice. Please fix the following errors.'))
        elif qs_en.count() == 1:
            # found exactly one match
            fc_obj = qs_en.first()
            if self.instance and fc_obj.id == self.instance.id:
                # this is an update
                # new field choice
                if not self._errors.keys():
                    return
                else:
                    raise forms.ValidationError(_('Update Field Choice. Please fix the following errors.'))
            else:
                raise forms.ValidationError(_('The combination '+field+' -- '+en_name+' already exists'))
        else:
            # multiple duplicates found
            raise forms.ValidationError(_('The combination '+field+' -- '+en_name+' already exists'))

class SemanticFieldColorForm(forms.Form):

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    field_color = forms.CharField(widget=ColorWidget)
    readonly_fields = ['machine_value']

    class Meta:
        model = SemanticField
        fields = ['name_en'] \
                 + ['field_color', 'machine_value', ]


class SemanticFieldForm(forms.ModelForm):
    # this ModelForm is needed in order to validate against duplicates

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    prepopulated_fields = {}

    class Meta:
        model = SemanticField
        fields = ['name_' + language.replace('-', '_') for language in [l[0] for l in settings.LANGUAGES]] \
                 + ['field_color', 'machine_value', ]

    def __init__(self, *args, **kwargs):
        super(SemanticFieldForm, self).__init__(*args, **kwargs)

        if not self.instance:
            self.fields['field_color'].initial = '#ffffff'
        else:
            self.fields['field_color'].initial = '#' + self.instance.field_color

        if not self.show_field_choice_colors:
            self.fields['field_color'].widget = forms.HiddenInput()
        else:
            # SHOW_FIELD_COLORS
            # set up the HTML color picker widget
            # for display in the HTML color picker, the field color needs to be prefixed with #
            # in the database,only the hex number is stored
            # adding a # has already been taken care for an instance object by the get_form of FieldChoiceAdmin
            self.fields['field_color'].widget = forms.TextInput(attrs={'type': 'color'})

class HandshapeForm(forms.ModelForm):
    # this ModelForm is needed in order to validate against duplicates

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    prepopulated_fields = {}

    class Meta:
        model = Handshape
        fields = ['name_' + language.replace('-', '_') for language in [l[0] for l in settings.LANGUAGES]] \
                 + ['field_color', 'machine_value', ]

    def __init__(self, *args, **kwargs):
        super(HandshapeForm, self).__init__(*args, **kwargs)

        if not self.instance:
            self.fields['field_color'].initial = '#ffffff'
        else:
            self.fields['field_color'].initial = '#' + self.instance.field_color

        if not self.show_field_choice_colors:
            self.fields['field_color'].widget = forms.HiddenInput()
        else:
            # SHOW_FIELD_COLORS
            # set up the HTML color picker widget
            # for display in the HTML color picker, the field color needs to be prefixed with #
            # in the database,only the hex number is stored
            # adding a # has already been taken care for an instance object by the get_form of FieldChoiceAdmin
            self.fields['field_color'].widget = forms.TextInput(attrs={'type': 'color'})

