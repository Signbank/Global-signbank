from colorfield.fields import ColorWidget
from django import forms
from django.forms import TextInput, Textarea, CharField
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from signbank.dictionary.models import *
from signbank.dictionary.forms import DefinitionForm, FieldChoiceForm, SemanticFieldForm, HandshapeForm, \
    QueryParameterFieldChoiceForm, SearchHistoryForm, QueryParameterBooleanForm, QueryParameterMultilingualForm, \
    QueryParameterHandshapeForm
from reversion.admin import VersionAdmin
from signbank.settings import server_specific
from signbank.settings.server_specific import FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD, LANGUAGES, LANGUAGE_CODE
from modeltranslation.admin import TranslationAdmin
from guardian.admin import GuardedModelAdmin
from django.contrib.auth import get_permission_codename
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import override, gettext_lazy as _

class DatasetAdmin(GuardedModelAdmin):
    model = Dataset
    list_display = ('name', 'is_public', 'signlanguage',)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class KeywordAdmin(VersionAdmin):
    search_fields = ['^text']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return False

class TranslationInline(admin.TabularInline):
    model = Translation
    readonly_fields = ['id', 'language', 'translation', 'index']
    list_display = ['id', 'language', 'translation', 'index']
    fields = ['id', 'language', 'translation', 'index']
    extra = 0

class RelationToForeignSignInline(admin.TabularInline):
    model = RelationToForeignSign
    readonly_fields = ['id', 'loan', 'other_lang', 'other_lang_gloss']
    list_display = ['id', 'loan', 'other_lang', 'other_lang_gloss']
    fields = ['id', 'loan', 'other_lang', 'other_lang_gloss']
    extra = 0

class DefinitionInline(admin.TabularInline):
    model = Definition
    readonly_fields = ['id', 'text', 'note', 'count', 'published']
    list_display = ['id', 'text', 'note', 'count', 'published', 'sction_checkbox']
    fields = ['id', 'text', 'note', 'count', 'published']
    fk_name = 'gloss'
    extra = 0

    # this is done once at initialization
    choice_list = FieldChoice.objects.filter(field__iexact='NoteType')

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':40}) }
    }

    def note(self, obj):
        try:
            this_role = int(obj.role)
            this_choice = self.choice_list.filter(machine_value=this_role)[0]
            # just choose English for now
            human_value = getattr(this_choice, 'name')
        except (TypeError, ValueError, AttributeError):
            human_value = '-'
        return human_value

    def get_queryset(self, request):
        # this looks sloppy
        this_object = request.environ['PATH_INFO'].split('/')[-3]

        qs = super(DefinitionInline, self).get_queryset(request)
        filtered_queryset = qs.filter(gloss=this_object)
        return filtered_queryset

class RelationInline(admin.TabularInline):
    model = Relation
    readonly_fields = ['id', 'role', 'target']
    fk_name = 'source'
    raw_id_fields = ['target']
    fields = ['id', 'role', 'target']
    verbose_name_plural = "Relations to other Glosses"
    extra = 0

class OtherMediaInline(admin.TabularInline):
    model = OtherMedia
    readonly_fields = ['id', 'path', 'type', 'alternative_gloss']
    list_display = ['id', 'path', 'type', 'alternative_gloss']
    fields = ['id', 'path', 'type', 'alternative_gloss']
    extra = 0

class AnnotationIdglossTranslationInline(admin.TabularInline):
    model = AnnotationIdglossTranslation

    list_display = ['id', 'language', 'text']
    readonly_fields = ['id', 'language', 'text']
    fields = ['id', 'language', 'text']

    extra = 0

class LemmaIdglossTranslationForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(LemmaIdglossTranslationForm, self).__init__(*args, **kwargs)

        if self.instance.id:
            if hasattr(self.fields['language'], '_queryset'):
                qs = self.fields['language']._queryset
                number_of_translations = qs.count()
                try:
                    language_of_translation = self.instance.lemma.dataset.translation_languages.all()
                except (AttributeError, ObjectDoesNotExist, MultipleObjectsReturned, ValueError):
                    language_of_translation = Language.objects.none()
                if number_of_translations > language_of_translation.count():
                    self.fields['language']._queryset = language_of_translation

                self.fields['language'].initial = self.instance.language
                self.fields['language'].disabled = True
                self.fields['language'].widget.can_change_related = False
                self.fields['language'].widget.can_add_related = False
        else:
            self.fields['language'].widget = forms.Select(choices=self.fields['language'].limit_choices_to)

    class Meta:
        model = LemmaIdglossTranslation
        fields = ['id', 'lemma', 'language', 'text']

    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }


class LemmaIdglossTranslationInline(admin.TabularInline):
    model = LemmaIdglossTranslation

    list_display = ['id', 'language', 'text']
    fields = ['id', 'lemma', 'language', 'text']

    form = LemmaIdglossTranslationForm

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            if obj.dataset is None:
                return ['id', 'lemma']
            else:
                return ['id']
        else:
            return []

    def get_extra(self, request, obj=None, **kwargs):
        if obj is not None:
            return 0
        else:
            return 1

    def __init__(self, *args, **kwargs):
        super(LemmaIdglossTranslationInline, self).__init__(*args, **kwargs)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(LemmaIdglossTranslationInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        return field

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(LemmaIdglossTranslationInline, self).get_formset(request, obj, **kwargs)
        if obj:
            translation_languages = []
            for translation in obj.lemmaidglosstranslation_set.all():
                translation_languages.append(translation.language)
            if obj.dataset:
                dataset_languages = obj.dataset.translation_languages.all()
                limited_choices = { f for f in dataset_languages if f not in translation_languages }
                language_choices = [(str(f.id), f.name) for f in limited_choices]
                formset.form.base_fields['language'].limit_choices_to = language_choices
        else:
            # creating new lemma translation
            languages = Language.objects.all()
            language_choices = [(str(f.id), f.name) for f in languages]
            formset.form.base_fields['language'].limit_choices_to = language_choices
        return formset

    def get_max_num(self, request, obj=None, **kwargs):

        maximum = super(LemmaIdglossTranslationInline, self).get_max_num(request, obj, **kwargs)

        if obj:
            if obj.dataset:
                dataset_languages = obj.dataset.translation_languages.all()
                maximum = len(dataset_languages)
            else:
                maximum = 0
        return maximum

class LanguageInline(admin.TabularInline):
    model = Language

    list_display = ['id', 'name', 'description']
    readonly_fields = ['id', 'name', 'description']
    fields = ['id', 'name', 'description']

    extra = 0

from django.contrib.admin import SimpleListFilter

class SenseNumberListFilter(SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('number of senses')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'senses'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (('none', _('No Senses')),
                ('morethanone', _('More than one')),
               )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Decide how to filter the queryset based on the request
        if self.value() == 'none':
            return queryset.filter(sense__isnull=True)
        if self.value() == 'morethanone':
            return queryset.filter(sense__gte=1)



class GlossAdminForm(forms.ModelForm):
    readonly_fields = ['id', 'lemma', 'signlanguage', 'dialect'] + FIELDS['main'] \
                      + FIELDS['phonology'] \
                      + FIELDS['frequency'] \
                      + FIELDS['semantics'] \
                      + ['inWeb', 'isNew', 'creator','creationDate','alternative_id']

    def __init__(self, *args, **kwargs):
        super(GlossAdminForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Gloss
        fields = ['id', 'lemma']

    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }

    def get_form(self, request, obj=None, **kwargs):

        form = super(GlossAdminForm, self).get_form(request, obj, **kwargs)
        return form


class GlossAdmin(VersionAdmin):

    readonly_fields = ['id', 'lemma', 'signlanguage', 'dialect'] + FIELDS['main'] \
                      + FIELDS['phonology'] \
                      + FIELDS['frequency'] \
                      + FIELDS['semantics'] \
                      + ['inWeb', 'isNew', 'creator','creationDate','alternative_id']

    idgloss_fields = ['id', 'lemma']

    actions = []

    raw_id_fields = ['lemma']

    fieldsets = ((None, {'fields': tuple(idgloss_fields)+tuple(FIELDS['main'])+('signlanguage', 'dialect')}, ),
                 ('Publication Status', {'fields': ('inWeb',  'isNew', 'creator','creationDate','alternative_id'),
                                       'classes': ('collapse',)}, ),
                 ('Phonology', {'fields': FIELDS['phonology'], 'classes': ('collapse',)}, ),
                 ('Semantics', {'fields': FIELDS['semantics'], 'classes': ('collapse',)}),
              )
    save_on_top = True
    save_as = True

    list_display = ['id', 'lemma', 'inWeb']

    search_fields = ['^lemma__lemmaidglosstranslation__text', 'id']
    inlines = [ AnnotationIdglossTranslationInline, RelationInline, RelationToForeignSignInline, DefinitionInline, TranslationInline, OtherMediaInline ]

    history_latest_first = True


    model = Gloss
    form = GlossAdminForm

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_form(self, request, obj=None, **kwargs):

        form = super(GlossAdmin, self).get_form(request, obj, **kwargs)
        return form

    def __init__(self, *args, **kwargs):
        super(GlossAdmin, self).__init__(*args, **kwargs)


class MorphologyDefinitionAdmin(VersionAdmin):
    model = MorphologyDefinition

    list_display = ['id', 'morpheme', 'parent_gloss_id', 'parent_gloss_translations', 'role']
    readonly_fields = ['id', 'morpheme', 'role', 'parent_gloss']
    fields = ['id', 'morpheme', 'parent_gloss', 'role']

    ordering = ['morpheme', 'parent_gloss_id', 'role']

    search_fields = ['^morpheme__lemma__lemmaidglosstranslation__text', '^parent_gloss__lemma__lemmaidglosstranslation__text', 'id']

    raw_id_fields = ['morpheme']
    extra = 0

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':40}) }
    }

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def parent_gloss_translations(self, obj=None):
        if obj is None:
            return ""
        translations = []
        count_dataset_languages = obj.parent_gloss.dataset.translation_languages.all().count() if obj.parent_gloss.dataset else 0
        for translation in obj.parent_gloss.lemma.lemmaidglosstranslation_set.all():
            if settings.SHOW_DATASET_INTERFACE_OPTIONS and count_dataset_languages > 1:
                translations.append("{}: {}".format(translation.language, translation.text))
            else:
                translations.append("{}".format(translation.text))
        return ", ".join(translations)

class SimultaneousMorphologyDefinitionAdmin(VersionAdmin):
    model = MorphologyDefinition

    list_display = ['id', 'morpheme', 'parent_gloss_id', 'parent_gloss_translations', 'role']
    readonly_fields = ['id', 'morpheme', 'role', 'parent_gloss']
    fields = ['id', 'morpheme', 'parent_gloss', 'role']

    ordering = ['morpheme', 'parent_gloss_id', 'role']

    search_fields = ['^morpheme__lemma__lemmaidglosstranslation__text', '^parent_gloss__lemma__lemmaidglosstranslation__text', 'id']

    raw_id_fields = ['morpheme']
    extra = 0

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':40}) }
    }

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def parent_gloss_translations(self, obj=None):
        if obj is None:
            return ""
        translations = []
        count_dataset_languages = obj.parent_gloss.dataset.translation_languages.all().count() if obj.parent_gloss.dataset else 0
        for translation in obj.parent_gloss.lemma.lemmaidglosstranslation_set.all():
            if settings.SHOW_DATASET_INTERFACE_OPTIONS and count_dataset_languages > 1:
                translations.append("{}: {}".format(translation.language, translation.text))
            else:
                translations.append("{}".format(translation.text))
        return ", ".join(translations)

class HandshapeAdmin(VersionAdmin, TranslationAdmin):

    readonly_fields = ['machine_value']
    actions = ['delete_selected']

    model = Handshape
    fields = ['name', 'field_color', 'machine_value']
    form = HandshapeForm

    if hasattr(server_specific, 'SHOW_FIELD_CHOICE_COLORS') and server_specific.SHOW_FIELD_CHOICE_COLORS:
        show_handshape_colors = True
    else:
        show_handshape_colors = False

    list_display = ['machine_value', 'name', 'gloss_count']
    ordering = ['machine_value']

    def gloss_count(self, obj):

        gloss_count = 0
        if not obj:
            return gloss_count
        else:
            machine_value = int(obj.machine_value)
            from signbank.tools import gloss_handshape_fields

            gloss_handshape_fields = gloss_handshape_fields()
            for field_name in gloss_handshape_fields:
                queries = [Q(**{field_name + '__machine_value': machine_value})]
                query = queries.pop()
                for item in queries:
                    query |= item
                count_in_use = Gloss.objects.filter(query).count()
                gloss_count += count_in_use

            return gloss_count

    def get_form(self, request, obj=None, **kwargs):
        form = super(HandshapeAdmin, self).get_form(request, obj, **kwargs)

        if obj:
            # for display in the HTML color picker, the field color needs to be prefixed with #
            # in the database,only the hex number is stored
            # check whether there is already an initial # before adding one
            obj_color = obj.field_color
            if obj_color[0] != '#':
                obj.field_color = '#'+obj.field_color
        return form

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        if not obj:
            # print('ADMIN has_delete_permission obj is None')
            # just return False if there is no object, prevent arbitrary deletion of field choices
            return False

        machine_value = obj.__dict__.get('machine_value', 0)
        if not machine_value:
            print('ADMIN has_delete_permission: handshape ', obj.name, ' has an empty machine value')

        # check if this is a duplicate, if so allow deletion
        handshapes_with_same_machine_value = Handshape.objects.filter(machine_value=machine_value).count()
        if handshapes_with_same_machine_value > 1:
            return True

        from signbank.tools import gloss_handshape_fields

        gloss_handshape_fields = gloss_handshape_fields()
        for field_name in gloss_handshape_fields:
            queries = [Q(**{ field_name + '__machine_value' : machine_value })]
            query = queries.pop()
            for item in queries:
                query |= item
            count_in_use = Gloss.objects.filter(query).count()
            if count_in_use > 0:
                return False
        return True

class SemanticFieldTranslationInline(admin.TabularInline):

    model = SemanticFieldTranslation

    list_display = ['language', 'name']

    extra = 0

    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }


class SemanticFieldAdmin(VersionAdmin, TranslationAdmin):

    model = SemanticField
    fields = ['machine_value', 'name', 'field_color', 'description']
    form = SemanticFieldForm

    readonly_fields = ['machine_value']

    list_display = ['machine_value', 'name', 'description']

    inlines = [SemanticFieldTranslationInline,]

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 40}) }
    }

    def get_form(self, request, obj=None, **kwargs):
        form = super(SemanticFieldAdmin, self).get_form(request, obj, **kwargs)

        if obj:
            # for display in the HTML color picker, the field color needs to be prefixed with #
            # in the database,only the hex number is stored
            # check whether there is already an initial # before adding one
            obj_color = obj.field_color
            if obj_color[0] != '#':
                obj.field_color = '#'+obj.field_color
        return form

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False


class SemanticFieldTranslationAdmin(VersionAdmin):

    model = SemanticFieldTranslation

    readonly_fields = ['semField', 'language', 'name']

    list_display = ['semField', 'name', 'language']

    list_filter = ['semField']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


class DerivationHistoryAdminForm(forms.ModelForm):

    class Meta:
        model = DerivationHistory
        fields = ['name', 'description']

    def __init__(self, *args, **kwargs):
        super(DerivationHistoryAdminForm, self).__init__(*args, **kwargs)

    def clean(self):
        # check that the name is not empty
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError(_('The derivation history name is required'))

    def get_form(self, request, obj=None, **kwargs):

        form = super(DerivationHistoryAdminForm, self).get_form(request, obj, **kwargs)
        return form


class DerivationHistoryTranslationInline(admin.TabularInline):

    model = DerivationHistoryTranslation

    list_display = ['language', 'name']

    extra = 0

    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }


class DerivationHistoryAdmin(VersionAdmin, TranslationAdmin):

    model = DerivationHistory
    form = DerivationHistoryAdminForm

    readonly_fields=['machine_value']

    list_display = ['machine_value', 'name', 'description']

    inlines = [DerivationHistoryTranslationInline,]

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':40}) }
    }

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False


class DerivationHistoryTranslationAdmin(VersionAdmin):

    model = DerivationHistoryTranslation

    readonly_fields=['derivHist', 'language', 'name']

    list_display = ['derivHist', 'name', 'language']

    list_filter = ['derivHist']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

class GlossRevisionUserFilter(admin.SimpleListFilter):

    title = _('User')
    parameter_name = 'revisions_per_user'

    def lookups(self, request, model_admin):
        # filter on users who have actually changed things
        users_present = GlossRevision.objects.all().values('user').distinct()
        user_tuples = [ (u.id, u.username) for u in User.objects.filter(id__in=users_present) ]
        return (tuple(
            (user_id, user_username) for (user_id, user_username) in user_tuples
        ))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_id=self.value())
        return queryset.all()

class GlossRevisionDatasetFilter(admin.SimpleListFilter):

    title = _('Dataset')
    parameter_name = 'revisions_per_dataset'

    def lookups(self, request, model_admin):
        datasets = Dataset.objects.all()
        return (tuple(
            (dataset.id, dataset.acronym) for dataset in datasets
        ))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gloss__lemma__dataset_id=self.value())
        return queryset.all()

class GlossRevisionAdmin(VersionAdmin):

    model = GlossRevision

    list_display = ['time', 'user', 'dataset', 'gloss', 'field_name', 'old_value', 'new_value']
    readonly_fields = ['user', 'gloss', 'field_name', 'old_value', 'new_value', 'time', 'old_value']
    list_filter = (GlossRevisionDatasetFilter, GlossRevisionUserFilter,)

    def has_add_permission(self, request):
        return False

    def get_list_display_links(self, request, list_display):
        # do not allow the user to view individual revisions in list
        self.list_display_links = (None, )
        return self.list_display_links


class RegistrationProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'activation_key_expired', )
    search_fields = ('user__username', 'user__first_name', )

class DialectInline(admin.TabularInline):

    model = Dialect
    fields = ['id', 'signlanguage', 'name', 'description']
    extra = 0

    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':40}) }
    }

class DialectAdmin(VersionAdmin):
    model = Dialect

    list_display = ['id', 'signlanguage', 'name', 'description']
    readonly_fields = ['id', 'signlanguage', 'name']
    fields = ['id', 'signlanguage', 'name', 'description']
    list_filter = ['signlanguage']

    extra = 0

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':40}) }
    }

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class SignLanguageAdmin(VersionAdmin):
    model = SignLanguage
    inlines = [DialectInline]
    list_display = ['id', 'name', 'description']
    readonly_fields = ['id']
    fields = ['id', 'name', 'description']

    extra = 0

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':40}) }
    }

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

# Define an inline admin descriptor for UserProfile model
# which acts a bit like a singleton
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'

# Define a new User admin
class UserAdmin(UserAdmin):
    inlines = (UserProfileInline, )


class FieldChoiceAdmin(VersionAdmin, TranslationAdmin):
    readonly_fields=['machine_value']
    actions=['delete_selected']

    model = FieldChoice
    fields = ['field', 'name'] \
             + ['field_color', 'machine_value' ]
    form = FieldChoiceForm

    if hasattr(server_specific, 'SHOW_FIELD_CHOICE_COLORS') and server_specific.SHOW_FIELD_CHOICE_COLORS:
        show_field_choice_colors = True
    else:
        show_field_choice_colors = False

    list_display = ['name'] \
                   + ['machine_value', 'field']
    list_filter = ['field']

    def get_form(self, request, obj=None, **kwargs):
        form = super(FieldChoiceAdmin, self).get_form(request, obj, **kwargs)

        if obj:
            # for display in the HTML color picker, the field color needs to be prefixed with #
            # in the database,only the hex number is stored
            # check whether there is already an initial # before adding one
            obj_color = obj.field_color
            if obj_color[0] != '#':
                obj.field_color = '#'+obj.field_color
        return form

    def get_actions(self, request):
        actions = super(FieldChoiceAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            # for field choices, do not offer delete selected to user
            # in order to protect accidently field choice deletion
            del actions['delete_selected']
        return actions

    def get_action_choices(self, request, **kwargs):
        # remove the empty choice '---------' from actions
        choices = super(FieldChoiceAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices

    def has_delete_permission(self, request, obj=None):
        if not obj:
            # print('ADMIN has_delete_permission obj is None')
            # just return False if there is no object, prevent arbitrary deletion of field choices
            return False

        field_value = obj.__dict__.get('field', '')
        field_machine_value = obj.__dict__.get('machine_value', 0)
        if not field_machine_value:
            print('ADMIN has_delete_permission: field ', field_value, ' has an empty machine value')

        # do not allow deletion of choices in to be removed field choice categories
        if field_value in ['Handshape', 'SemField', 'derivHist']:
            return False

        # check if this is a duplicate, if so allow deletion
        fieldchoices_with_same_machine_value = FieldChoice.objects.filter(field=field_value,machine_value=field_machine_value).count()
        if fieldchoices_with_same_machine_value > 1:
            return True

        from signbank.tools import fields_with_choices_glosses, fields_with_choices_handshapes, \
            fields_with_choices_definition, fields_with_choices_morphology_definition, \
            fields_with_choices_other_media_type, fields_with_choices_morpheme_type

        fields_with_choices_glosses = fields_with_choices_glosses()
        if field_value in fields_with_choices_glosses.keys():
            queries = [Q(**{ field_name + '__machine_value' : field_machine_value })
                       for field_name in fields_with_choices_glosses[field_value]]
            query = queries.pop()
            for item in queries:
                query |= item
            count_in_use = Gloss.objects.filter(query).count()
            return not count_in_use

        fields_with_choices_handshapes = fields_with_choices_handshapes()
        if field_value in fields_with_choices_handshapes.keys():
            queries_h = [Q(**{ field_name + '__machine_value' : field_machine_value })
                         for field_name in fields_with_choices_handshapes[field_value]]
            query_h = queries_h.pop()
            for item in queries_h:
                query_h |= item
            count_in_use = Handshape.objects.filter(query_h).count()
            return not count_in_use

        fields_with_choices_definition = fields_with_choices_definition()
        if field_value in fields_with_choices_definition.keys():
            queries_d = [Q(**{ field_name + '__machine_value' : field_machine_value })
                                for field_name in fields_with_choices_definition[field_value]]
            query_d = queries_d.pop()
            for item in queries_d:
                query_d |= item
            count_in_use = Definition.objects.filter(query_d).count()
            return not count_in_use

        fields_with_choices_morphology_definition = fields_with_choices_morphology_definition()
        if field_value in fields_with_choices_morphology_definition.keys():
            queries_d = [Q(**{ field_name + '__machine_value' : field_machine_value })
                         for field_name in fields_with_choices_morphology_definition[field_value]]
            query_d = queries_d.pop()
            for item in queries_d:
                query_d |= item
            count_in_use = MorphologyDefinition.objects.filter(query_d).count()
            return not count_in_use

        fields_with_choices_other_media_type = fields_with_choices_other_media_type()
        if field_value in fields_with_choices_other_media_type.keys():
            queries_d = [Q(**{ field_name + '__machine_value' : field_machine_value })
                         for field_name in fields_with_choices_other_media_type[field_value]]
            query_d = queries_d.pop()
            for item in queries_d:
                query_d |= item
            count_in_use = OtherMedia.objects.filter(query_d).count()
            return not count_in_use

        fields_with_choices_morpheme_type = fields_with_choices_morpheme_type()
        if field_value in fields_with_choices_morpheme_type.keys():
            queries_d = [Q(**{ field_name + '__machine_value' : field_machine_value })
                         for field_name in fields_with_choices_morpheme_type[field_value]]
            query_d = queries_d.pop()
            for item in queries_d:
                query_d |= item
            count_in_use = Morpheme.objects.filter(query_d).count()
            return not count_in_use

        # fall through: the fieldname is not used in Gloss, Handshape, Definition, MorphologyDefinition, OtherMedia, Morpheme
        print('ADMIN, field choices, has_delete_permission: fall through on: ', field_value)
        opts = self.opts
        codename = get_permission_codename('delete', opts)
        # note that this delete option only checks whether the user is allowed, not if there are other uses of the field
        # this would be the case for fields that are in the model and used by other signbanks
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_change_permission(self, request, obj=None):

        if obj is not None and obj.field == 'FingerSelection':
            # This is a reserved field, used for displaying the Finger Selection
            # Do not allow deletion
            # print('ADMIN has_change_permission is False for FingerSelection')
            return False

        if obj is not None and obj.machine_value in [0,1]:
            return False

        opts = self.opts
        codename = get_permission_codename('change', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def delete_selected(self, request, queryset):
        # this code is not called anymore for field choices
        for obj in queryset:
            print('delete_selected not available for field choices, admin command ignored: ', obj)
            pass

    delete_selected.short_description = "Delete selected field choices"

    def save_model(self, request, obj, form, change):

        if obj.machine_value == None:
            # Check out the query-set and make sure that it exists
            qs = FieldChoice.objects.filter(field=obj.field)
            if qs.count() == 0:
                # The field does not yet occur within FieldChoice
                # Future: ask user if that is what he wants (don't know how...)
                # For now: assume user wants to add a new field (e.g: wordClass)
                # NOTE: start with '2', because 0,1 are already taken by default values
                obj.machine_value = 2
            else:
                # Calculate highest currently occurring value
                highest_machine_value = max([field_choice.machine_value for field_choice in qs])
                # The automatic machine value we calculate is 1 higher
                obj.machine_value= highest_machine_value+1
        elif obj.machine_value < 2:
            # this case is prevented in the interface via Permission Denied
            # it may be possible during testing
            print('Not allowed to update field choices with machine value 0 or 1.')
            return

        if 'field_color' in form.data.keys():
            new_color = form.data['field_color']
            # strip any initial #'s
            while new_color[0] == '#':
                new_color = new_color[1:]
            # store only the hex part
            original_color = getattr(obj, 'field_color')
            if new_color != original_color:
                setattr(obj, 'field_color', new_color)

        with override(LANGUAGE_CODE):
            for name_field in form.data.keys():
                if name_field not in form.fields:
                    continue
                if name_field == 'field_color' or name_field == 'csrfmiddlewaretoken':
                    continue
                new_name_value = form.data[name_field]
                original_value = getattr(obj, name_field)
                if new_name_value != original_value:
                    setattr(obj, name_field, new_name_value)

            try:
                obj.save()
            except Exception as e:
                print('Constraint violated, FieldChoice not saved: ', obj.field, obj.machine_value, obj.id, e)



class LanguageAdmin(TranslationAdmin):

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class LemmaIdglossAdminForm(forms.ModelForm):

    fields = ['dataset', 'id']
    readonly_fields = ['id']

    base_fields = []

    lemma_create_field_prefix = 'lemmacreate_'

    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }

    def __init__(self, *args, **kwargs):

        super(LemmaIdglossAdminForm, self).__init__(*args, **kwargs)

        if self.instance:
            if self.instance.dataset:
                dataset_acronym = self.instance.dataset.acronym
                self.fields['dataset'].initial = dataset_acronym
                self.fields['dataset'].disabled = True
                self.fields['dataset'].widget.can_change_related = False
                self.fields['dataset'].widget.can_add_related = False
            else:
                # dataset is not set
                if self.instance.id:
                    # if we are editing a lemma without a dataset, do not allow setting the dataset
                    self.fields['dataset'].disabled = True
                    self.fields['dataset'].widget.can_change_related = False
                    self.fields['dataset'].widget.can_add_related = False
                else:
                    datasets = Dataset.objects.all()
                    dataset_choices = [(str(f.id), f.acronym) for f in datasets]
                    self.fields['dataset'].widget = forms.Select(choices=dataset_choices)
                    self.fields['dataset'].limit_choices_to = dataset_choices
                    self.fields['dataset'].widget.can_change_related = False
                    self.fields['dataset'].widget.can_add_related = False

class LemmaIdglossAdmin(VersionAdmin):

    list_display = ['id', 'dataset', 'lemmaidgloss']
    fields = ['dataset']
    list_filter = ['dataset']

    search_fields = ['lemmaidglosstranslation__text']

    history_latest_first = True

    actions = []

    inlines = [LemmaIdglossTranslationInline, ]

    model = LemmaIdgloss
    form = LemmaIdglossAdminForm

    lemma_create_field_prefix = 'lemmacreate_'

    def lemmaidgloss(self, obj=None):
        if obj is None:
            return ""
        translations = []
        count_dataset_languages = obj.dataset.translation_languages.all().count() if obj.dataset else 0
        for translation in obj.lemmaidglosstranslation_set.all():
            if settings.SHOW_DATASET_INTERFACE_OPTIONS and count_dataset_languages > 1:
                translations.append("{}: {}".format(translation.language, translation.text))
            else:
                translations.append("{}".format(translation.text))
        return ", ".join(translations)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def change_view(self, request, object_id, form_url='', extra_content=None):
        if extra_content is None:
            extra_content = {}
        extra_content['title'] = _('Make changes') + ' lemma idgloss ' + str(object_id)
        view = super(LemmaIdglossAdmin, self).change_view(request, object_id, form_url, extra_content)
        return view

    def __init__(self, *args, **kwargs):
        super(LemmaIdglossAdmin, self).__init__(*args, **kwargs)

    def has_add_permission(self, request):
        return False

class LemmaIdglossTranslationAdmin(VersionAdmin):
    readonly_fields = ['lemma', 'language', 'text']
    fields = ['lemma', 'language', 'text']

    list_display = ['id', 'lemma', 'language', 'text']
    list_filter = ['language']

    search_fields = ['text']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def change_view(self, request, object_id, form_url='', extra_content=None):
        if extra_content is None:
            extra_content = {}
        extra_content['title'] = _('Make changes') + ' lemma idgloss translation ' + str(object_id)
        view = super(LemmaIdglossTranslationAdmin, self).change_view(request, object_id, form_url, extra_content)
        return view

    def get_queryset(self, request):
        qs = super(LemmaIdglossTranslationAdmin, self).get_queryset(request)
        return qs

    def get_search_results(self, request, queryset, search_term):
        use_distinct = False
        if queryset:
            pass
        else:
            queryset = super(LemmaIdglossTranslationAdmin, self).get_queryset(request)
        new_queryset = queryset.filter(Q(text__iregex=search_term))
        return (new_queryset, use_distinct)

    def has_add_permission(self, request):
        return False


class QueryParameterFieldChoiceAdmin(VersionAdmin):

    model = QueryParameterFieldChoice

    form = QueryParameterFieldChoiceForm

    list_display = ['search_history', '__str__']
    list_filter = ['search_history']

    def has_add_permission(self, request):
        # don't allow adding new search histories in the admin, since the user field is problematic
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and not obj.search_history:
            return True
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class QueryParameterHandshapeAdmin(VersionAdmin):

    model = QueryParameterHandshape
    form = QueryParameterHandshapeForm

    list_display = ['search_history', '__str__']
    list_filter = ['search_history']

    def has_add_permission(self, request):
        # don't allow adding new search histories in the admin, since the user field is problematic
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and not obj.search_history:
            return True
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class QueryParameterSemanticFieldAdmin(VersionAdmin):

    model = QueryParameterSemanticField

    list_display = ['search_history', '__str__']
    list_filter = ['search_history']

    def has_add_permission(self, request):
        # don't allow adding new search histories in the admin, since the user field is problematic
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and not obj.search_history:
            return True
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class QueryParameterDerivationHistoryAdmin(VersionAdmin):

    model = QueryParameterDerivationHistory

    list_display = ['search_history', '__str__']
    list_filter = ['search_history']

    def has_add_permission(self, request):
        # don't allow adding new search histories in the admin, since the user field is problematic
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and not obj.search_history:
            return True
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class QueryParameterBooleanAdmin(VersionAdmin):

    model = QueryParameterBoolean

    form = QueryParameterBooleanForm

    list_display = ['search_history', '__str__']
    list_filter = ['search_history']

    def has_add_permission(self, request):
        # don't allow adding new search histories in the admin, since the user field is problematic
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and not obj.search_history:
            return True
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class QueryParameterMultilingualAdmin(VersionAdmin):

    model = QueryParameterMultilingual
    form = QueryParameterMultilingualForm

    list_display = ['search_history', '__str__']
    list_filter = ['search_history']

    def has_add_permission(self, request):
        # don't allow adding new search histories in the admin, since the user field is problematic
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and not obj.search_history:
            return True
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class SearchHistoryAdmin(VersionAdmin):

    model = SearchHistory

    form = SearchHistoryForm

    list_display = ['queryName', 'query_parameters', 'user', 'queryDate']
    readonly_fields = ['user']

    def query_parameters(self, obj=None):
        if obj is None:
            return ""
        parameter_list = []
        for translation in obj.parameters.all():
            if translation.is_fieldchoice():
                field_choice = translation.queryparameterfieldchoice
                parameter_list.append(str(field_choice))
            elif translation.is_handshape():
                handshape = translation.queryparameterhandshape
                parameter_list.append(str(handshape))
            elif translation.is_semanticfield():
                semanticfield = translation.queryparametersemanticfield
                parameter_list.append(str(semanticfield))
            elif translation.is_derivationhistory():
                derivationhistory = translation.queryparameterderivationhistory
                parameter_list.append(str(derivationhistory))
            elif translation.is_boolean():
                nullbooleanfield = translation.queryparameterboolean
                parameter_list.append(str(nullbooleanfield))
            elif translation.is_multilingual():
                multilingual = translation.queryparametermultilingual
                parameter_list.append(str(multilingual))
            else:
                parameter_list.append(str(translation))
        return ", ".join(parameter_list)

    def has_add_permission(self, request):
        # don't allow adding new search histories in the admin, since the user field is problematic
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if extra_context is None:
            extra_context = {}

        extra_context['title'] = _("Change Title of Saved Query")
        view = super(SearchHistoryAdmin, self).change_view(request, object_id, form_url, extra_context)
        return view


admin.site.register(Dialect, DialectAdmin)
admin.site.register(SignLanguage, SignLanguageAdmin)
admin.site.register(Gloss, GlossAdmin)
admin.site.register(Morpheme, GlossAdmin)
admin.site.register(Keyword, KeywordAdmin)
admin.site.register(FieldChoice,FieldChoiceAdmin)
admin.site.register(MorphologyDefinition,MorphologyDefinitionAdmin)
admin.site.register(SimultaneousMorphologyDefinition, SimultaneousMorphologyDefinitionAdmin)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Handshape, HandshapeAdmin)
admin.site.register(SemanticField, SemanticFieldAdmin)
admin.site.register(SemanticFieldTranslation, SemanticFieldTranslationAdmin)
admin.site.register(DerivationHistory, DerivationHistoryAdmin)
admin.site.register(DerivationHistoryTranslation, DerivationHistoryTranslationAdmin)
admin.site.register(GlossRevision,GlossRevisionAdmin)

admin.site.register(UserProfile)
admin.site.register(Language, LanguageAdmin)
admin.site.register(Dataset, DatasetAdmin)

admin.site.register(LemmaIdgloss, LemmaIdglossAdmin)
admin.site.register(LemmaIdglossTranslation, LemmaIdglossTranslationAdmin)

admin.site.register(QueryParameterFieldChoice, QueryParameterFieldChoiceAdmin)
admin.site.register(QueryParameterHandshape, QueryParameterHandshapeAdmin)
admin.site.register(QueryParameterSemanticField, QueryParameterSemanticFieldAdmin)
admin.site.register(QueryParameterDerivationHistory, QueryParameterDerivationHistoryAdmin)
admin.site.register(QueryParameterBoolean, QueryParameterBooleanAdmin)
admin.site.register(QueryParameterMultilingual, QueryParameterMultilingualAdmin)
admin.site.register(SearchHistory, SearchHistoryAdmin)

