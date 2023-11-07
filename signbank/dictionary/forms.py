from colorfield.fields import ColorWidget
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import override, gettext_lazy as _, get_language
from django.db import OperationalError, ProgrammingError
from django.db.transaction import atomic
from signbank.video.fields import VideoUploadToFLVField
from signbank.dictionary.models import Dialect, Gloss, Morpheme, Definition, Relation, RelationToForeignSign, \
                                        MorphologyDefinition, OtherMedia, Handshape, SemanticField, DerivationHistory, \
                                        AnnotationIdglossTranslation, Dataset, FieldChoice, LemmaIdgloss, \
                                        LemmaIdglossTranslation, Translation, Keyword, Language, SignLanguage, \
                                        QueryParameterFieldChoice, SearchHistory, QueryParameter, \
                                        QueryParameterMultilingual, QueryParameterHandshape, SemanticFieldTranslation, \
                                        ExampleSentence
from signbank.dictionary.field_choices import fields_to_fieldcategory_dict
from django.conf import settings
from tagging.models import Tag
import datetime as DT
from django.utils.timezone import get_current_timezone
from signbank.settings.server_specific import DEFAULT_KEYWORDS_LANGUAGE, LANGUAGES, MODELTRANSLATION_LANGUAGES
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

        return gloss


class MorphemeCreateForm(forms.ModelForm):
    """Form for creating a new morpheme from scratch"""

    morpheme_create_field_prefix = "morphemecreate_"
    languages = None  # Languages to use for annotation idgloss translations
    user = None
    last_used_dataset = None

    class Meta:
        model = Morpheme
        fields = []

    def __init__(self, queryDict, *args, **kwargs):
        self.languages = kwargs.pop('languages')
        self.user = kwargs.pop('user')
        self.last_used_dataset = kwargs.pop('last_used_dataset')
        super(MorphemeCreateForm, self).__init__(queryDict, *args, **kwargs)

        if 'dataset' in queryDict:
            self.fields['dataset'] = forms.ModelChoiceField(queryset=Dataset.objects.all())
            self.fields['dataset'].initial = queryDict['dataset']
        if self.last_used_dataset:
            self.fields['dataset'] = forms.ModelChoiceField(queryset=Dataset.objects.filter(acronym=self.last_used_dataset))

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

        return morpheme


class TagUpdateForm(forms.Form):
    """Form to add a new tag to a gloss"""

    tag = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control'}), 
                            choices=tag_choices)
    delete = forms.BooleanField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super(TagUpdateForm, self).__init__(*args, **kwargs)

        self.fields['tag'] = forms.ChoiceField(label=_('Tags'),
                                               choices=[(tag.name, tag.name.replace('_', ' '))
                                                        for tag in Tag.objects.all()],
                                               widget=forms.Select(attrs=ATTRS_FOR_FORMS))


ATTRS_FOR_FORMS = {'class': 'form-control'}
ATTRS_FOR_BOOLEAN_FORMS = {'class': 'form-control', 'style': 'width:80px'}


class GlossSearchForm(forms.ModelForm):

    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_('Search Gloss'))
    sortOrder = forms.CharField(label=_('Sort Order'))
    tags = forms.ChoiceField(label=_('Tags'), choices=[(0, '-')])
    translation = forms.CharField(label=_('Search Senses'))
    hasvideo = forms.ChoiceField(label=_('Has Video'), choices=[(0, '-')])
    hasothermedia = forms.ChoiceField(label=_('Has Other Media'), choices=[(0, '-')])
    defspublished = forms.ChoiceField(label=_("All Definitions Published"), choices=[(0, '-')],
                                      widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasmultiplesenses = forms.ChoiceField(label=_("Has Multiple Senses"), choices=[(0, '-')],
                                          widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    relation = forms.CharField(label=_('Gloss of Related Sign'),
                               widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    relationToForeignSign = forms.CharField(label=_('Gloss of Foreign Sign'),
                                            widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    morpheme = forms.CharField(label=_('Search for gloss with this as morpheme'))

    phonOth = forms.CharField(label=_('Phonology Other'), widget=forms.TextInput())

    hasRelationToForeignSign = forms.ChoiceField(label=_('Related to Foreign Sign'),
                                                 choices=[(0, '-')],
                                                 widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    hasRelation = forms.ChoiceField(label=_('Type of Relation'),
                                    choices=[(0, '-')],
                                    widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    hasComponentOfType = forms.ChoiceField(label=_('Has Compound Component Type'),
                                           choices=[(0, '-')],
                                           widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    repeat = forms.ChoiceField(label=_('Repeating Movement'), choices=[(0, '-')],
                               widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    altern = forms.ChoiceField(label=_('Alternating Movement'), choices=[(0, '-')],
                               widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))

    weakprop = forms.ChoiceField(label=_('Weak Prop'), choices=[(0, '-')],
                                 widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    weakdrop = forms.ChoiceField(label=_('Weak Drop'), choices=[(0, '-')],
                                 widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))

    domhndsh_letter = forms.ChoiceField(label=_('letter'), choices=[(0, '-')],
                                        widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    domhndsh_number = forms.ChoiceField(label=_('number'), choices=[(0, '-')],
                                        widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))

    subhndsh_letter = forms.ChoiceField(label=_('letter'), choices=[(0, '-')],
                                        widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    subhndsh_number = forms.ChoiceField(label=_('number'), choices=[(0, '-')],
                                        widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))

    isNew = forms.ChoiceField(label=_('Is a proposed new sign'), choices=[(0, '-')],
                              widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    inWeb = forms.ChoiceField(label=_('Is in Web Dictionary'), choices=[(0, '-')],
                              widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    excludeFromEcv = forms.ChoiceField(label=_('Exclude from ECV'), choices=[(0, '-')],
                                       widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))

    definitionRole = forms.ChoiceField(label=_('Note Type'),
                                       choices=[(0, '-')],
                                       widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    definitionContains = forms.CharField(label=_('Note Contains'),
                                         widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    mrpType = forms.ChoiceField(label=_('Has Morpheme Type'),
                                choices=[(0, '-')],
                                widget=forms.Select(attrs=ATTRS_FOR_FORMS))

    createdBy = forms.CharField(label=_('Created By'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    createdAfter = forms.DateField(label=_('Created After'),
                                   input_formats=[settings.DATE_FORMAT], required=False,
                                   widget=forms.TextInput(attrs={'type': 'date'}))
    createdBefore = forms.DateField(label=_('Created Before'),
                                    input_formats=[settings.DATE_FORMAT], required=False,
                                    widget=forms.TextInput(attrs={'type': 'date'}))

    gloss_search_field_prefix = "glosssearch_"
    keyword_search_field_prefix = "keyword_"
    lemma_search_field_prefix = "lemma_"
    menu_bar_search = "Menu Bar Search Gloss"
    menu_bar_translation = "Menu Bar Search Senses"

    class Meta:

        model = Gloss
        fields = settings.FIELDS['phonology'] + settings.FIELDS['semantics'] + settings.FIELDS['main'] + \
                 ['inWeb', 'isNew', 'excludeFromEcv']

    def __init__(self, *args, **kwargs):

        super(GlossSearchForm, self).__init__(*args, **kwargs)

        # language fields will be set up elsewhere
        # field choice choices will be set up elsewhere
        # these are the multiselect field choice fields for morphemes
        for fieldname in settings.GLOSS_CHOICE_FIELDS:
            if fieldname in ['definitionRole', 'hasComponentOfType', 'mrpType', 'hasRelation']:
                # this is a search form field name
                continue
            else:
                field_label = Gloss.get_field(fieldname).verbose_name
            self.fields[fieldname] = forms.ChoiceField(label=field_label,
                                                       choices=[(0, '-')],
                                                       required=False, widget=Select2)
        self.fields['tags'] = forms.ChoiceField(label=_('Tags'),
                                                choices=[(tag.name, tag.name.replace('_', ' '))
                                                         for tag in Tag.objects.all()],
                                                widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        for boolean_field in ['hasvideo', 'repeat', 'altern', 'isNew', 'inWeb', 'defspublished',
                              'excludeFromEcv', 'hasRelationToForeignSign', 'hasmultiplesenses',
                              'hasothermedia']:
            self.fields[boolean_field].choices = [('0', '-'), ('2', _('Yes')), ('3', _('No'))]
        for boolean_field in ['weakdrop', 'weakprop']:
            self.fields[boolean_field].choices = [(0, '-'), (1, _('Neutral')), (2, _('True')), (3, _('False'))]
        for boolean_field in ['domhndsh_letter', 'domhndsh_number', 'subhndsh_letter', 'subhndsh_number']:
            self.fields[boolean_field].choices = [(0, '-'), (2, _('True')), (3, _('False'))]


def check_language_fields(SearchForm, queryDict, languages):
    # this function inspects the search parameters from GlossSearchForm looking for occurrences of + at the start
    language_fields_okay = True
    search_fields = []
    if not queryDict:
        return language_fields_okay, search_fields
    menu_bar_fields = ['search', 'translation']

    language_field_labels = dict()
    language_field_values = dict()
    for language in languages:
        if hasattr(SearchForm, 'gloss_search_field_prefix'):
            glosssearch_field_name = SearchForm.gloss_search_field_prefix + language.language_code_2char
            if glosssearch_field_name in queryDict.keys():
                language_field_values[glosssearch_field_name] = queryDict[glosssearch_field_name]
                language_field_labels[glosssearch_field_name] = _("Gloss")+(" (%s)" % language.name)

        # do the same for Translations
        if hasattr(SearchForm, 'keyword_search_field_prefix'):
            keyword_field_name = SearchForm.keyword_search_field_prefix + language.language_code_2char
            if keyword_field_name in queryDict.keys():
                language_field_values[keyword_field_name] = queryDict[keyword_field_name]
                language_field_labels[keyword_field_name] = _("Senses")+(" (%s)" % language.name)

        # and for LemmaIdgloss
        if hasattr(SearchForm, 'lemma_search_field_prefix'):
            lemma_field_name = SearchForm.lemma_search_field_prefix + language.language_code_2char
            if lemma_field_name in queryDict.keys():
                language_field_values[lemma_field_name] = queryDict[lemma_field_name]
                language_field_labels[lemma_field_name] = _("Lemma")+(" (%s)" % language.name)

    for menu_bar_field in menu_bar_fields:
        if menu_bar_field in queryDict.keys():
            if not hasattr(SearchForm, menu_bar_field):
                continue
            language_field_values[menu_bar_field] = queryDict[menu_bar_field]
            menu_bar_field_label = getattr(SearchForm, menu_bar_field)
            language_field_labels[menu_bar_field] = gettext(menu_bar_field_label)

    import re
    # check for matches starting with: + * [ ( ) ?
    # or ending with a +
    regexp = re.compile('^[+*\[()?]|([^+]+\+$)')
    for language_field in language_field_values.keys():
        if regexp.search(language_field_values[language_field]):
            language_fields_okay = False
            search_fields.append(language_field_labels[language_field])
    return language_fields_okay, search_fields


class MorphemeSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Search Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"))
    tags = forms.ChoiceField(label=_('Tags'), choices=[(0, '-')],
                             widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    translation = forms.CharField(label=_('Search Senses'))
    hasvideo = forms.ChoiceField(label=_('Has Video'), choices=[(0, '-')],
                                 widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    useInstr = forms.CharField(label=_("Annotation instructions"))

    phonOth = forms.CharField(label=_('Phonology Other'), widget=forms.TextInput())

    repeat = forms.ChoiceField(label=_('Repeating Movement'),
                               choices=[(0, '-')],
                               widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    altern = forms.ChoiceField(label=_('Alternating Movement'),
                               choices=[(0, '-')],
                               widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))

    isNew = forms.ChoiceField(label=_('Is a proposed new sign'), choices=[(0, '-')],
                              widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    inWeb = forms.ChoiceField(label=_('Is in Web Dictionary'), choices=[(0, '-')],
                              widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))

    definitionRole = forms.ChoiceField(label=_('Note Type'), choices=[(0, '-')],
                                       required=False, widget=Select2)
    definitionContains = forms.CharField(label=_('Note Contains'),
                                         widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
    defspublished = forms.ChoiceField(label=_("All Definitions Published"), choices=[(0, '-')],
                                      widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))

    createdBefore = forms.DateField(label=_('Created Before'),
                                    input_formats=[settings.DATE_FORMAT],
                                    widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))
    createdAfter = forms.DateField(label=_('Created After'),
                                   input_formats=[settings.DATE_FORMAT],
                                   widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}))

    createdBy = forms.CharField(label=_('Created By'), widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))

    gloss_search_field_prefix = "morphemesearch_"
    keyword_search_field_prefix = "keyword_"
    lemma_search_field_prefix = "lemma_"
    menu_bar_search = "Menu Bar Search Gloss"
    menu_bar_translation = "Menu Bar Search Senses"

    class Meta:

        model = Morpheme

        fields = settings.MORPHEME_DISPLAY_FIELDS + settings.FIELDS['semantics'] + settings.FIELDS['main'] + ['inWeb', 'isNew', 'mrpType']

    def __init__(self, *args, **kwargs):
        super(MorphemeSearchForm, self).__init__(*args, **kwargs)

        # language fields will be set up elsewhere
        # field choice choices will be set up elsewhere
        # these are the multiselect field choice fields for morphemes
        for fieldname in settings.MORPHEME_CHOICE_FIELDS:
            if fieldname in ['definitionRole']:
                # this is a search form field name
                continue
            elif fieldname.startswith('mrpType'):
                field_label = Morpheme.get_field(fieldname).verbose_name
            else:
                field_label = Gloss.get_field(fieldname).verbose_name
            self.fields[fieldname] = forms.ChoiceField(label=field_label,
                                                       choices=[(0, '-')],
                                                       required=False, widget=Select2)
        self.fields['tags'] = forms.ChoiceField(label=_('Tags'),
                                                choices=[(tag.name, tag.name.replace('_', ' '))
                                                         for tag in Tag.objects.all()],
                                                widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        for boolean_field in ['hasvideo', 'repeat', 'altern', 'isNew', 'inWeb', 'defspublished']:
            self.fields[boolean_field].choices = [('0', '-'), ('2', _('Yes')), ('3', _('No'))]


class DefinitionForm(forms.ModelForm):
    class Meta:
        model = Definition
        fields = ('published','count', 'text')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['note'] = forms.ChoiceField(label=_('Type'),
                                                choices=choicelist_queryset_to_translated_dict(
                                                     list(FieldChoice.objects.filter(field='NoteType').order_by(
                                                         'machine_value')),
                                                     ordered=False, id_prefix='', shortlist=False
                                                ),
                                                widget=forms.Select(attrs=ATTRS_FOR_FORMS))


class RelationForm(forms.ModelForm):
    
    sourceid = forms.CharField(label=_('Source Gloss'))
    targetid = forms.CharField(label=_('Target Gloss'))
    
    class Meta:
        model = Relation
        fields = ['role']
        widgets = {
                   'role': forms.Select(attrs={'class': 'form-control'}),
                   }


class VariantsForm(forms.Form):
    sourceid = forms.CharField(label=_('Source Gloss'))
    targetid = forms.CharField(label=_('Target Gloss'))

    class Meta:
        model = Relation
        

class RelationToForeignSignForm(forms.ModelForm):

    sourceid = forms.CharField(label=_('Source Gloss'))
    other_lang = forms.CharField(label=_('Related Language'))
    other_lang_gloss = forms.CharField(label=_('Gloss in Related Language'), required=False)
    
    class Meta:
        model = RelationToForeignSign
        fields = ['loan','other_lang','other_lang_gloss']
        widgets = {}


class GlossMorphologyForm(forms.Form):
    """Morphology specification of a Gloss"""

    parent_gloss_id = forms.CharField(label=_('Parent Gloss'))
    role = forms.ChoiceField(label=_('Type'),choices=[],
                             widget=forms.Select(attrs=ATTRS_FOR_FORMS), required=True)
    morpheme_id = forms.CharField(label=_('Morpheme'))

    def __init__(self, *args, **kwargs):
        super(GlossMorphologyForm, self).__init__(*args, **kwargs)
        self.fields['role'].choices = list(FieldChoice.objects.filter(field='MorphologyType').order_by('machine_value')
                                           .values_list('pk', 'name'))


class GlossMorphemeForm(forms.Form):
    """Specify simultaneous morphology components belonging to a Gloss"""

    host_gloss_id = forms.CharField(label=_('Host Gloss'))
    description = forms.CharField(label=_('Meaning'), required=False)
    morph_id = forms.CharField(label=_('Morpheme'))


class GlossBlendForm(forms.Form):
    """Specify simultaneous morphology components belonging to a Gloss"""

    host_gloss_id = forms.CharField(label=_('Host Gloss'))
    role = forms.CharField(label=_('Role'))
    blend_id = forms.CharField(label=_('Blend'))


class OtherMediaForm(forms.ModelForm):

    gloss = forms.CharField()
    file = forms.FileField(widget=forms.FileInput(attrs={'accept':'video/*, image/*, application/pdf'}),
                           required=True)
    alternative_gloss = forms.TextInput()

    class Meta:
        model = OtherMedia
        fields = ['file']

    def __init__(self, *args, **kwargs):
        super(OtherMediaForm, self).__init__(*args, **kwargs)
        self.fields['type'] = forms.ChoiceField(label=_('Type'),
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


attrs_default = {'class': 'form-control'}
FINGER_SELECTION = ((True, 'True'), (False, 'False'))


class HandshapeSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    sortOrder = forms.CharField(label=_("Sort Order"),
                                initial="machine_value")  # Used in Handshapelistview to store user-selection

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
                'fsT': forms.RadioSelect(choices=FINGER_SELECTION),
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

        self.fields['unselectedFingers'] = forms.ChoiceField(label=_('Unselected Fingers Extended'),
                                                    choices=choicelist_queryset_to_translated_dict(
                                                        list(
                                                            FieldChoice.objects.filter(field='FingerSelection').order_by(
                                                                'machine_value')),
                                                        ordered=False, id_prefix='', shortlist=False
                                                    ),
                                                    widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsNumSel'] = forms.ChoiceField(label=_('Quantity'),
                                                    choices=choicelist_queryset_to_translated_dict(
                                                          list(
                                                              FieldChoice.objects.filter(field='Quantity').order_by(
                                                                  'machine_value')),
                                                          ordered=False, id_prefix='', shortlist=False
                                                    ),
                                                    widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsFingConf'] = forms.ChoiceField(label=_('Finger configuration'),
                                                      choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='JointConfiguration').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                      ),
                                                      widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsFingConf2'] = forms.ChoiceField(label=_('Finger configuration 2'),
                                                       choices=choicelist_queryset_to_translated_dict(
                                                          list(
                                                              FieldChoice.objects.filter(field='JointConfiguration').order_by(
                                                                  'machine_value')),
                                                          ordered=False, id_prefix='', shortlist=False
                                                       ),
                                                       widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsSpread'] = forms.ChoiceField(label=_('Spreading'),
                                                    choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='Spreading').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                    ),
                                                    widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        self.fields['hsAperture'] = forms.ChoiceField(label=_('Aperture'),
                                                      choices=choicelist_queryset_to_translated_dict(
                                                              list(
                                                                  FieldChoice.objects.filter(field='Aperture').order_by(
                                                                      'machine_value')),
                                                              ordered=False, id_prefix='', shortlist=False
                                                      ),
                                                      widget=forms.Select(attrs=ATTRS_FOR_FORMS))
        for finger in ['fsT', 'fsI', 'fsM', 'fsR', 'fsP',
                       'fs2T', 'fs2I', 'fs2M', 'fs2R', 'fs2P',
                       'ufT', 'ufI', 'ufM', 'ufR', 'ufP']:
            self.fields[finger].inital = False
            self.fields[finger].widget.choices = [(True, _('Yes')), (False, _('No'))]


def check_multilingual_fields(ClassModel, queryDict, languages):
    # this function inspects the name field of HandshapeSearchForm looking for occurrences of special characters
    language_fields_okay = True
    search_fields = []
    if not queryDict:
        return language_fields_okay, search_fields

    language_field_labels = dict()
    language_field_values = dict()
    if 'name' in queryDict.keys():
        language_field_values['name'] = queryDict['name']
        class_name_plus_name = ClassModel.__name__ + ' Name'
        language_field_labels['name'] = gettext(class_name_plus_name)
    else:
        # this is only needed if the user can search on multiple (model translation) languages in the same form
        for language in languages:
            search_field_name = 'name_' + language.language_code_2char
            if search_field_name in queryDict.keys():
                language_field_values[search_field_name] = queryDict[search_field_name]
                language_field_labels[search_field_name] = ClassModel.get_field(search_field_name).verbose_name+(
                        " (%s)" % language.name)

    import re
    # check for matches starting with: + * [ ( ) ?
    # or ending with a +
    regexp = re.compile('^[+*\[()?]|([^+]+\+$)')
    for language_field in language_field_values.keys():
        if regexp.search(language_field_values[language_field]):
            language_fields_okay = False
            search_fields.append(language_field_labels[language_field])

    return language_fields_okay, search_fields


class ImageUploadForHandshapeForm(forms.Form):
    """Form for image upload for a particular gloss"""

    imagefile = forms.FileField(label="Upload Image")
    handshape_id = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)


class LemmaSearchForm(forms.ModelForm):
    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Lemma"))
    sortOrder = forms.CharField(label=_("Sort Order"))
    lemma_search_field_prefix = "lemma_"
    no_glosses = forms.ChoiceField(label=_('Only show results without glosses'), choices=[],
                                   widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    has_glosses = forms.ChoiceField(label=_('Only show results with glosses'), choices=[],
                                    widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    menu_bar_search = "Menu Bar Search Gloss"
    menu_bar_translation = "Menu Bar Search Translation"

    class Meta:

        ATTRS_FOR_FORMS = {'class': 'form-control'}

        model = LemmaIdgloss
        fields = ['dataset']

    def __init__(self, queryDict, *args, **kwargs):
        languages = kwargs.pop('languages')
        super(LemmaSearchForm, self).__init__(queryDict, *args, **kwargs)

        count_languages = len(languages)
        for language in languages:
            # and for LemmaIdgloss
            lemma_field_name = self.lemma_search_field_prefix + language.language_code_2char
            if count_languages > 1:
                lemma_label = _("Lemma")+(" (%s)" % language.name)
            else:
                lemma_label = _("Lemma")
            setattr(self, lemma_field_name, forms.CharField(label=lemma_label))
            if lemma_field_name in queryDict:
                getattr(self, lemma_field_name).value = queryDict[lemma_field_name]
        for boolean_field in ['no_glosses', 'has_glosses']:
            self.fields[boolean_field].choices = [(0, _('No')), (1, _('Yes'))]


class LemmaCreateForm(forms.ModelForm):
    """Form for creating a new lemma from scratch"""

    lemma_create_field_prefix = "lemmacreate_"
    languages = None # Languages to use for lemma idgloss translations
    user = None
    last_used_dataset = None

    class Meta:
        model = LemmaIdgloss
        fields = ['dataset']

    def __init__(self, queryDict, *args, **kwargs):
        if 'languages' in kwargs:
            self.languages = kwargs.pop('languages')
        self.user = kwargs.pop('user')
        self.last_used_dataset = kwargs.pop('last_used_dataset')

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

        if self.last_used_dataset:
            self.fields['dataset'] = forms.ModelChoiceField(queryset=Dataset.objects.filter(acronym=self.last_used_dataset))

    @atomic  # This rolls back the lemma creation if creating lemmaidglosstranslations fails
    def save(self, commit=True):
        lemma = super(LemmaCreateForm, self).save(commit)
        # get initial translations before saving new ones
        existing_lemma_translations = lemma.lemmaidglosstranslation_set.all()
        for language in self.languages:
            lemmacreate_field_name = self.lemma_create_field_prefix + language.language_code_2char
            lemma_idgloss_text = self[lemmacreate_field_name].value()
            existing_lemmaidglosstranslations = existing_lemma_translations.filter(language=language)
            if existing_lemmaidglosstranslations.count() == 0:
                lemmaidglosstranslation = LemmaIdglossTranslation(lemma=lemma, language=language,
                                                                            text=lemma_idgloss_text)
                lemmaidglosstranslation.save()
            elif existing_lemmaidglosstranslations.count() == 1:
                lemmaidglosstranslation = existing_lemmaidglosstranslations.first()
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


class KeyMappingSearchForm(forms.ModelForm):

    tags = forms.ChoiceField(label=_('Tags'), choices=tag_choices)

    class Meta:

        ATTRS_FOR_FORMS = {'class': 'form-control'}

        model = Gloss
        fields = settings.MINIMAL_PAIRS_SEARCH_FIELDS

    def __init__(self, queryDict, *args, **kwargs):
        languages = kwargs.pop('languages')
        super(KeyMappingSearchForm, self).__init__(queryDict, *args, **kwargs)

        self.fields['tags'] = forms.ChoiceField(label=_('Tags'),
                                                choices=[(tag.name, tag.name.replace('_', ' '))
                                                         for tag in Tag.objects.all()],
                                                widget=forms.Select(attrs=ATTRS_FOR_FORMS))


class FocusGlossSearchForm(forms.ModelForm):

    use_required_attribute = False  # otherwise the html required attribute will show up on every form

    search = forms.CharField(label=_("Search Gloss"))
    sortOrder = forms.CharField(label=_("Sort Order"))       # Used in glosslistview to store user-selection
    translation = forms.CharField(label=_('Search Senses'))

    repeat = forms.ChoiceField(label=_('Repeating Movement'), choices=[('0', '-')])
    altern = forms.ChoiceField(label=_('Alternating Movement'), choices=[('0', '-')])

    gloss_search_field_prefix = "glosssearch_"
    keyword_search_field_prefix = "keyword_"
    lemma_search_field_prefix = "lemma_"
    menu_bar_search = "Menu Bar Search Gloss"
    menu_bar_translation = "Menu Bar Search Senses"

    class Meta:

        ATTRS_FOR_FORMS = {'class': 'form-control'}

        model = Gloss
        fields = settings.MINIMAL_PAIRS_SEARCH_FIELDS

    def __init__(self, queryDict, *args, **kwargs):
        languages = kwargs.pop('languages')
        super(FocusGlossSearchForm, self).__init__(queryDict, *args, **kwargs)

        for language in languages:
            glosssearch_field_name = self.gloss_search_field_prefix + language.language_code_2char
            setattr(self, glosssearch_field_name, forms.CharField(label=_("Gloss")+(" (%s)" % language.name)))
            if glosssearch_field_name in queryDict:
                getattr(self, glosssearch_field_name).value = queryDict[glosssearch_field_name]

            # do the same for Translations
            keyword_field_name = self.keyword_search_field_prefix + language.language_code_2char
            setattr(self, keyword_field_name, forms.CharField(label=_("Senses")+(" (%s)" % language.name)))
            if keyword_field_name in queryDict:
                getattr(self, keyword_field_name).value = queryDict[keyword_field_name]

            # and for LemmaIdgloss
            lemma_field_name = self.lemma_search_field_prefix + language.language_code_2char
            setattr(self, lemma_field_name, forms.CharField(label=_("Lemma")+(" (%s)" % language.name)))
            if lemma_field_name in queryDict:
                getattr(self, lemma_field_name).value = queryDict[lemma_field_name]

        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew']
        fields_with_choices = fields_to_fieldcategory_dict(fieldnames)

        for (fieldname, field_category) in fields_with_choices.items():
            field_label = Gloss.get_field(fieldname).verbose_name
            if fieldname.startswith('semField'):
                field_choices = SemanticField.objects.all()
            elif fieldname.startswith('derivHist'):
                field_choices = DerivationHistory.objects.all()
            elif fieldname in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
                field_choices = Handshape.objects.all()
            else:
                field_choices = FieldChoice.objects.filter(field__iexact=field_category)
            translated_choices = choicelist_queryset_to_translated_dict(field_choices, ordered=False, id_prefix='', shortlist=True)
            self.fields[fieldname] = forms.TypedMultipleChoiceField(label=field_label,
                                                                    choices=translated_choices,
                                                                    required=False, widget=Select2)
        for boolean_field in ['repeat', 'altern']:
            self.fields[boolean_field].choices = [('0', '-'), ('2', _('Yes')), ('3', _('No'))]


class FieldChoiceColorForm(forms.Form):
    field_color = forms.CharField(widget=ColorWidget)
    readonly_fields = ['machine_value']

    class Meta:
        model = FieldChoice
        fields = ['field', 'name'] \
                 + ['field_color', 'machine_value', ]


class FieldChoiceForm(forms.ModelForm):
    # this ModelForm is needed in order to validate against duplicates

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    field_category = ''
    prepopulated_fields = {}

    class Meta:
        model = FieldChoice
        fields = ['field'] \
                 + ['name_' + language.replace('-', '_') for language in MODELTRANSLATION_LANGUAGES] \
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

    def already_exists(self, field, language_field, language_field_value):
        matches = FieldChoice.objects.filter(field=field).filter(**{language_field: language_field_value}).count()
        return matches

    def clean(self):
        # check that the field category and (english) name does not already occur
        super(FieldChoiceForm, self).clean()

        data_fields = self.data

        if 'field' not in data_fields.keys() or not data_fields['field']:
            raise forms.ValidationError(_('The Field Choice Category is required'))
        field = data_fields['field']

        qs_f = FieldChoice.objects.filter(field=field)
        # if qs_f.count() == 0:
        #     raise forms.ValidationError(_('This Field Choice Category does not exist'))

        for language in MODELTRANSLATION_LANGUAGES:
            name_languagecode = 'name_'+ language.replace('-', '_')
            if name_languagecode not in data_fields.keys():
                raise forms.ValidationError(_('The Name fields for all languages are required'))

        if not self.instance:
            for language, langauge_name in [(l[0], l[1]) for l in LANGUAGES if l[0] in MODELTRANSLATION_LANGUAGES]:
                name_languagecode = 'name_'+ language.replace('-', '_')
                name_languagecode_value = data_fields[name_languagecode]
                if self.already_exists(field, name_languagecode, name_languagecode_value):
                    raise forms.ValidationError(_('The combination ' + field + ' -- ' + name_languagecode_value
                                                  + ' already exists for ' + langauge_name))
        else:
            for language, langauge_name in [(l[0], l[1]) for l in LANGUAGES if l[0] in MODELTRANSLATION_LANGUAGES]:
                name_languagecode = 'name_'+ language.replace('-', '_')
                name_languagecode_value = data_fields[name_languagecode]
                if getattr(self.instance, name_languagecode) == name_languagecode_value:
                    continue
                if self.already_exists(field, name_languagecode, name_languagecode_value):

                    raise forms.ValidationError(_('The combination ' + field + ' -- ' + name_languagecode_value
                                                  + ' already exists for ' + langauge_name))


class SemanticFieldColorForm(forms.Form):

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    field_color = forms.CharField(widget=ColorWidget)
    readonly_fields = ['machine_value']

    class Meta:
        model = SemanticField
        fields = ['name'] \
                 + ['field_color', 'machine_value', ]


class SemanticFieldForm(forms.ModelForm):
    # this ModelForm is needed in order to validate against duplicates

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    prepopulated_fields = {}

    class Meta:
        model = SemanticField
        fields = ['name'] \
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


class SemanticFieldTranslationForm(forms.ModelForm):
    # this ModelForm is needed in order to validate against duplicates

    use_required_attribute = False
    prepopulated_fields = {}

    class Meta:
        model = SemanticFieldTranslation
        fields = ['semField', 'language', 'name', ]

    def __init__(self, *args, **kwargs):
        languages = kwargs.pop('languages')
        semfield = kwargs.pop('semField')
        with override(settings.LANGUAGE_CODE):
            default_initial = semfield.name

        super(SemanticFieldTranslationForm, self).__init__(*args, **kwargs)

        if self.instance:
            for lang in languages:
                namefield = 'name_' + lang.language_code_2char
                self.fields[namefield] = forms.TextInput(attrs=ATTRS_FOR_FORMS)

            semfield_translations = semfield.semanticfieldtranslation_set.filter(language__in=languages)
            self.fields['semField'].value = semfield
            for lang in languages:
                namefield = 'name_' + lang.language_code_2char
                translation_exists = semfield_translations.filter(language=lang)
                if translation_exists.count() > 0:
                    semfield_translation = translation_exists.first()
                    self.fields[namefield].value = semfield_translation.name
                else:
                    self.fields[namefield].value = default_initial


class DerivationHistoryColorForm(forms.Form):

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    field_color = forms.CharField(widget=ColorWidget)
    readonly_fields = ['machine_value']

    class Meta:
        model = DerivationHistory
        fields = ['name'] \
                 + ['field_color', 'machine_value', ]

class HandshapeColorForm(forms.Form):

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    field_color = forms.CharField(widget=ColorWidget)
    readonly_fields = ['machine_value']

    class Meta:
        model = Handshape
        fields = ['name'] \
                 + ['field_color', 'machine_value', ]

class HandshapeForm(forms.ModelForm):
    # this ModelForm is needed in order to validate against duplicates

    show_field_choice_colors = settings.SHOW_FIELD_CHOICE_COLORS
    prepopulated_fields = {}

    class Meta:
        model = Handshape
        fields = ['name'] \
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


class QueryParameterBooleanForm(forms.ModelForm):

    class Meta:
        model = QueryParameterFieldChoice

        fields = ['search_history', 'multiselect', 'fieldName', 'fieldValue']

    def __init__(self, *args, **kwargs):
        super(QueryParameterBooleanForm, self).__init__(*args, **kwargs)
        if self.instance:
            field_name = self.instance.fieldName
            # the following variables are used to restrict selection to only the saved Boolean field
            restricted_field_names = [(field_name, self.instance.display_verbose_fieldname())]
            self.fields['fieldName'] = forms.ChoiceField(choices=restricted_field_names, label=_("Field Name"))
            self.fields['search_history'].disabled = True
            field_value = self.instance.display_fieldvalue()
            restricted_choices = [(field_value, field_value)]
            self.fields['fieldValue'] = forms.ChoiceField(label=_('Field Value'), choices=restricted_choices)


class QueryParameterHandshapeForm(forms.ModelForm):

    class Meta:
        model = QueryParameterHandshape

        fields = ['search_history', 'multiselect', 'fieldName', 'fieldValue']

    def __init__(self, *args, **kwargs):
        super(QueryParameterHandshapeForm, self).__init__(*args, **kwargs)
        if self.instance:
            field_name = self.instance.fieldName
            # the following variables are used to restrict selection to only the saved handshape
            restricted_field_names = [(field_name, self.instance.display_verbose_fieldname())]
            self.fields['fieldName'] = forms.ChoiceField(choices=restricted_field_names, label=_("Field Name"))
            self.fields['search_history'].disabled = True
            field_value = self.instance.fieldValue.machine_value
            restricted_choices = Handshape.objects.filter(machine_value=field_value)
            self.fields['fieldValue'] = forms.ModelChoiceField(label=_('Field Value'),
                                                               queryset=restricted_choices, empty_label=None)


class QueryParameterMultilingualForm(forms.ModelForm):

    class Meta:
        model = QueryParameterMultilingual

        fields = ['search_history', 'multiselect', 'fieldName', 'fieldLanguage', 'fieldValue']

    def __init__(self, *args, **kwargs):
        super(QueryParameterMultilingualForm, self).__init__(*args, **kwargs)
        if self.instance:
            field_name = self.instance.fieldName
            # the following variables are used to restrict selection to only the saved multilingual field
            restricted_field_names = [(field_name, self.instance.display_verbose_fieldname())]
            self.fields['fieldName'] = forms.ChoiceField(choices=restricted_field_names, label=_("Field Name"))
            self.fields['search_history'].disabled = True
            language = self.instance.fieldLanguage
            restricted_choices = [(language, language)]
            self.fields['fieldLanguage'] = forms.ChoiceField(label=_('Language'), choices=restricted_choices)


class QueryParameterFieldChoiceForm(forms.ModelForm):

    class Meta:
        model = QueryParameterFieldChoice

        fields = ['search_history', 'multiselect', 'fieldName', 'fieldValue']

    def __init__(self, *args, **kwargs):
        super(QueryParameterFieldChoiceForm, self).__init__(*args, **kwargs)
        if not self.instance or not self.instance.fieldName or self.instance.fieldName == '-':
            categories = dict(QueryParameterFieldChoice.QUERY_FIELD_CATEGORY).values()
            self.fields['fieldValue'] = forms.ModelChoiceField(queryset=FieldChoice.objects.filter(
                field__in=categories).order_by('field'))
        else:
            field_name = self.instance.fieldName
            categories = dict(QueryParameterFieldChoice.QUERY_FIELD_CATEGORY)
            field_choice = categories[field_name]
            # the following variables are used to restrict selection to only the saved field choice
            restricted_field_names = [(field_name, field_name)]
            choices_field_value = FieldChoice.objects.filter(
                field=field_choice, machine_value=self.instance.fieldValue.machine_value)
            self.fields['fieldName'] = forms.ChoiceField(choices=restricted_field_names)
            self.fields['fieldValue'] = forms.ModelChoiceField(queryset=choices_field_value, empty_label=None)
            self.fields['search_history'].disabled = True


class SearchHistoryForm(forms.ModelForm):

    class Meta:
        model = SearchHistory

        fields = ['user', 'queryName', 'parameters']

    def __init__(self, *args, **kwargs):
        super(SearchHistoryForm, self).__init__(*args, **kwargs)

        if not self.instance:
            self.fields['queryDate'].initial = DT.datetime.now(tz=get_current_timezone())
            self.fields['parameters'] = forms.MultipleChoiceField(label=_('Parameters'),
                                                                  widget=forms.CheckboxSelectMultiple,
                                                                  choices=QueryParameter.objects.all())
        else:
            query_parameters_of_instance = QueryParameter.objects.filter(search_history=self.instance)
            self.fields['parameters'] = forms.ModelMultipleChoiceField(label=_('Parameters'),
                                                                       widget=forms.CheckboxSelectMultiple,
                                                                       queryset=query_parameters_of_instance)


class SentenceForm(forms.ModelForm):

    sentenceType = forms.ChoiceField(label=_("Type"), choices=[('0', '-')])
    negative = forms.ChoiceField(label=_('Negative'), choices=[('0', '-')],
                                 widget=forms.Select(attrs=ATTRS_FOR_BOOLEAN_FORMS))
    sentenceContains = forms.CharField(label=_('Sentence Contains'),
                                       widget=forms.TextInput(attrs=ATTRS_FOR_FORMS), required=False)

    class Meta:

        ATTRS_FOR_FORMS = {'class': 'form-control'}

        model = ExampleSentence

        fields = ['sentenceType', 'negative']

    def __init__(self, *args, **kwargs):
        super(SentenceForm, self).__init__(*args, **kwargs)

        field_choices = FieldChoice.objects.filter(field__iexact='sentenceType')

        translated_choices = choicelist_queryset_to_translated_dict(field_choices,
                                                                    ordered=False, id_prefix='',
                                                                    shortlist=True)
        self.fields['sentenceType'] = forms.TypedMultipleChoiceField(label=_('Type'),
                                                                     choices=translated_choices,
                                                                     required=False, widget=Select2)
        self.fields['negative'].choices = [('0', '-'), ('yes', _('Yes')), ('no', _('No'))]
