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

class FieldChoiceAdmin(VersionAdmin):
    readonly_fields=['machine_value']
    actions=['delete_selected']

    if hasattr(server_specific, 'SHOW_ENGLISH_ONLY') and server_specific.SHOW_ENGLISH_ONLY:
        show_english_only = True
        list_display = ['english_name', 'machine_value','field']
    else:
        list_display = ['english_name', 'dutch_name', 'machine_value', 'field']
        show_english_only = False
    list_filter = ['field']

    def get_form(self, request, obj=None, **kwargs):
        if self.show_english_only:
            self.exclude = ('dutch_name', 'chinese_name')
        form = super(FieldChoiceAdmin, self).get_form(request, obj, **kwargs)
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
