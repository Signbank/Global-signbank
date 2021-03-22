from colorfield.fields import ColorWidget
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from signbank.dictionary.models import *
from reversion.admin import VersionAdmin
from signbank.settings import server_specific
from signbank.settings.server_specific import FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD
from modeltranslation.admin import TranslationAdmin
from guardian.admin import GuardedModelAdmin
from django.contrib.auth import get_permission_codename
from django.contrib import messages


class DatasetAdmin(GuardedModelAdmin):
    model = Dataset
    list_display = ('name', 'is_public', 'signlanguage',)


class KeywordAdmin(VersionAdmin):
    search_fields = ['^text']
    
    
class TranslationInline(admin.TabularInline):
    model = Translation
    extra = 1
    raw_id_fields = ['translation']

class RelationToOtherSignInline(admin.TabularInline):
    model = Relation
    extra = 1
    
class RelationToForeignSignInline(admin.TabularInline):
    model = RelationToForeignSign
    extra = 1
#    raw_id_fields = ['other_lang_gloss']
    
class DefinitionInline(admin.TabularInline):
    model = Definition  
    extra = 1
    
class RelationInline(admin.TabularInline):
    model = Relation
    fk_name = 'source' 
    raw_id_fields = ['source', 'target']
    verbose_name_plural = "Relations to other Glosses"
    extra = 1

class OtherMediaInline(admin.TabularInline):
    model = OtherMedia
    extra = 1

from django.utils.translation import ugettext_lazy as _
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
        
        

class GlossAdmin(VersionAdmin):

    idgloss_fields = ['lemma']

    fieldsets = ((None, {'fields': tuple(idgloss_fields)+tuple(FIELDS['main'])+('signlanguage', 'dialect')}, ),
                 ('Publication Status', {'fields': ('inWeb',  'isNew', 'creator','creationDate','alternative_id'),
                                       'classes': ('collapse',)}, ),
                 ('Phonology', {'fields': FIELDS['phonology'], 'classes': ('collapse',)}, ),
                 ('Semantics', {'fields': FIELDS['semantics'], 'classes': ('collapse',)}),
                 ('Frequency', {'fields': FIELDS['frequency'], 'classes': ('collapse',)}),
                ('Obsolete Fields', {'fields': ('inittext', ), 'classes': ('collapse',)}),
              )
    save_on_top = True
    save_as = True

    list_display = ['lemma']

    list_display += ['morph', 'sense', 'sn']
    search_fields = ['^lemma__lemmaidglosstranslation__text', '=sn']
    list_filter = ['signlanguage', 'dialect', SenseNumberListFilter, 'inWeb', 'domhndsh']
    inlines = [ RelationInline, RelationToForeignSignInline, DefinitionInline, TranslationInline, OtherMediaInline ]

    history_latest_first = True


class HandshapeAdmin(VersionAdmin):

    list_display = ['machine_value', 'english_name', 'dutch_name']

class GlossRevisionAdmin(VersionAdmin):

    model = GlossRevision

class RegistrationProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'activation_key_expired', )
    search_fields = ('user__username', 'user__first_name', )
 
class DialectInline(admin.TabularInline):
    
    model = Dialect

class DialectAdmin(VersionAdmin):
    model = Dialect
 
class SignLanguageAdmin(VersionAdmin):
    model = SignLanguage
    inlines = [DialectInline]

# Define an inline admin descriptor for UserProfile model
# which acts a bit like a singleton
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'

# Define a new User admin
class UserAdmin(UserAdmin):
    inlines = (UserProfileInline, )


class FieldChoiceAdminForm(forms.ModelForm):

    # this form is needed in order to validate against duplicates
    # hide some fields

    show_field_choice_colors = server_specific.SHOW_FIELD_CHOICE_COLORS
    show_english_only = server_specific.SHOW_ENGLISH_ONLY

    def __init__(self, *args, **kwargs):
        super(FieldChoiceAdminForm, self).__init__(*args, **kwargs)
        if self.instance.field:
            self.fields['field'].disabled = True
        if not self.show_field_choice_colors:
            self.fields['field_color'].widget = forms.HiddenInput()
        if self.show_english_only:
            self.fields['dutch_name'].widget = forms.HiddenInput()
            self.fields['chinese_name'].widget = forms.HiddenInput()

    class Meta:
        model = FieldChoice
        fields = ['field', 'english_name', 'dutch_name', 'chinese_name', 'field_color', 'machine_value']

    def clean(self):
        # check that the field category and (english) name does not already occur
        en_name = self.cleaned_data['english_name']
        field = self.cleaned_data['field']

        if not field:
            raise forms.ValidationError(_('The field name category is required'))

        qs_f = FieldChoice.objects.filter(field=field)

        if len(qs_f) == 0:
            raise forms.ValidationError(_('This field category does not exist'))

        qs_en = FieldChoice.objects.filter(field=field, english_name=en_name)

        if len(qs_en) == 0:
            # new field choice
            return self.cleaned_data
        elif len(qs_en) == 1:
            # found exactly one match
            fc_obj = qs_en[0]
            if fc_obj.id == self.instance.id:
                return self.cleaned_data
            else:
                raise forms.ValidationError(_('This field choice already exists'))
        else:
            # multiple duplicates found
            raise forms.ValidationError(_('This field choice already exists'))

    def get_form(self, request, obj=None, **kwargs):

        form = super(FieldChoiceAdminForm, self).get_form(request, obj, **kwargs)
        return form


class FieldChoiceAdmin(VersionAdmin):
    readonly_fields=['machine_value']
    actions=['delete_selected']

    model = FieldChoice
    form = FieldChoiceAdminForm

    if hasattr(server_specific, 'SHOW_FIELD_CHOICE_COLORS') and server_specific.SHOW_FIELD_CHOICE_COLORS:
        show_field_choice_colors = True
    else:
        show_field_choice_colors = False

    if hasattr(server_specific, 'SHOW_ENGLISH_ONLY') and server_specific.SHOW_ENGLISH_ONLY:
        show_english_only = True
        list_display = ['english_name', 'machine_value','field']
    else:
        list_display = ['english_name', 'dutch_name', 'machine_value', 'field']
        show_english_only = False
    list_filter = ['field']

    def get_form(self, request, obj=None, **kwargs):
        # for display in the HTML color picker, the field color needs to be prefixed with #
        # in the database,only the hex number is stored
        # because Django loads the form multiple times (why?), check whether there is already an initial # before adding one
        if obj:
            obj_color = obj.field_color
            if obj_color[0] != '#':
                obj.field_color = '#'+obj.field_color

        if self.show_english_only:
            self.exclude = ('dutch_name', 'chinese_name')
        if self.show_field_choice_colors:
            self.exclude = ('field_color')

        form = super(FieldChoiceAdmin, self).get_form(request, obj, **kwargs)
        form_base_fields = form.__dict__['base_fields']
        if not obj:
            # a new field choice is being created
            # see if the user is inside a category
            try:
                changelist_filters = request.GET['_changelist_filters']
            except:
                changelist_filters = ''
            from urllib.parse import parse_qsl
            query_params = dict(parse_qsl(changelist_filters))
            if query_params:
                new_field_category = query_params.get('field')
                form_base_fields['field'].initial = new_field_category
                form_base_fields['field'].disabled = True
            else:
                # restrict categories to those already existing
                # categories are determined by the fields in the Models, the user does not create categories
                field_choice_categories = FieldChoice.objects.all().values('field').distinct()
                field_choice_categories = [ f['field'] for f in field_choice_categories]
                field_choice_categories = sorted(list(set(field_choice_categories)))
                field_choices = [(f, f) for f in field_choice_categories]
                form_base_fields['field'].widget = forms.Select(choices=field_choices)

        if self.show_field_choice_colors:
            # SHOW_FIELD_COLORS
            # set up the HTML color picker widget
            form_base_fields['field_color'].widget = forms.TextInput(attrs={'type': 'color' })

            # in the model, the default value is ffffff
            # in the admin, the default value is a display value, so needs the #
            form_base_fields['field_color'].initial = '#ffffff'

        return form

    def get_actions(self, request):
        actions = super(FieldChoiceAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            # for field choices, do not offer delete selected to user
            # in order to protect accidently field choice deletion
            del actions['delete_selected']
        return actions

    def get_action_choices(self, request):
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

        from signbank.tools import fields_with_choices_glosses, fields_with_choices_handshapes, \
            fields_with_choices_definition, fields_with_choices_morphology_definition, \
            fields_with_choices_other_media_type, fields_with_choices_morpheme_type

        fields_with_choices_glosses = fields_with_choices_glosses()
        if field_value in fields_with_choices_glosses.keys():
            queries = [Q(**{ field_name : field_machine_value }) for field_name in fields_with_choices_glosses[field_value]]
            query = queries.pop()
            for item in queries:
                query |= item
            count_in_use = Gloss.objects.filter(query).count()
            return not count_in_use

        fields_with_choices_handshapes = fields_with_choices_handshapes()
        if field_value in fields_with_choices_handshapes.keys():
            queries_h = [Q(**{ field_name : field_machine_value }) for field_name in fields_with_choices_handshapes[field_value]]
            query_h = queries_h.pop()
            for item in queries_h:
                query_h |= item
            count_in_use = Handshape.objects.filter(query_h).count()
            return not count_in_use

        fields_with_choices_definition = fields_with_choices_definition()
        if field_value in fields_with_choices_definition.keys():
            queries_d = [Q(**{ field_name : field_machine_value }) for field_name in fields_with_choices_definition[field_value]]
            query_d = queries_d.pop()
            for item in queries_d:
                query_d |= item
            count_in_use = Definition.objects.filter(query_d).count()
            return not count_in_use

        fields_with_choices_morphology_definition = fields_with_choices_morphology_definition()
        if field_value in fields_with_choices_morphology_definition.keys():
            queries_d = [Q(**{ field_name : field_machine_value }) for field_name in fields_with_choices_morphology_definition[field_value]]
            query_d = queries_d.pop()
            for item in queries_d:
                query_d |= item
            count_in_use = MorphologyDefinition.objects.filter(query_d).count()
            return not count_in_use

        fields_with_choices_other_media_type = fields_with_choices_other_media_type()
        if field_value in fields_with_choices_other_media_type.keys():
            queries_d = [Q(**{ field_name : field_machine_value }) for field_name in fields_with_choices_other_media_type[field_value]]
            query_d = queries_d.pop()
            for item in queries_d:
                query_d |= item
            count_in_use = OtherMedia.objects.filter(query_d).count()
            return not count_in_use

        fields_with_choices_morpheme_type = fields_with_choices_morpheme_type()
        if field_value in fields_with_choices_morpheme_type.keys():
            queries_d = [Q(**{ field_name : field_machine_value }) for field_name in fields_with_choices_morpheme_type[field_value]]
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
            if len(qs) == 0:
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
        if self.show_field_choice_colors:
            # the color in the database needs to be without the #, which is for display
            if form and form.cleaned_data.get('field_color'):
                new_color = form.cleaned_data['field_color']
                # strip any initial #'s
                while new_color[0] == '#':
                    new_color = new_color[1:]
                # store only the hex part
                obj.field_color = new_color
        obj.save()

class LanguageAdmin(TranslationAdmin):
    pass


class LemmaIdglossAdmin(VersionAdmin):
    pass

class LemmaIdglossTranslationAdmin(VersionAdmin):
    pass


admin.site.register(Dialect, DialectAdmin)
admin.site.register(SignLanguage, SignLanguageAdmin)
admin.site.register(Gloss, GlossAdmin) 
admin.site.register(Morpheme, GlossAdmin)
admin.site.register(Keyword, KeywordAdmin)
admin.site.register(FieldChoice,FieldChoiceAdmin)
admin.site.register(MorphologyDefinition)
admin.site.register(SimultaneousMorphologyDefinition)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Handshape, HandshapeAdmin)
admin.site.register(GlossRevision,GlossRevisionAdmin)

admin.site.register(UserProfile)
admin.site.register(Language, LanguageAdmin)
admin.site.register(Dataset, DatasetAdmin)

admin.site.register(LemmaIdgloss, LemmaIdglossAdmin)
admin.site.register(LemmaIdglossTranslation, LemmaIdglossTranslationAdmin)
