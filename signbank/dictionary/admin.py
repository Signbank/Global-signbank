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

    fieldsets = ((None, {'fields': tuple(idgloss_fields)+tuple(FIELDS['main'])+('dataset', 'signlanguage', 'dialect')}, ),
                 ('Publication Status', {'fields': ('inWeb',  'isNew', 'creator','creationDate','alternative_id'),
                                       'classes': ('collapse',)}, ),
                 ('Phonology', {'fields': FIELDS['phonology'], 'classes': ('collapse',)}, ),
                 ('Semantics', {'fields': FIELDS['semantics'], 'classes': ('collapse',)}),
                 ('Frequency', {'fields': FIELDS['frequency'], 'classes': ('collapse',)}),
                ('Obsolete Fields', {'fields': ('inittext', ), 'classes': ('collapse',)}),
              )
    save_on_top = True
    save_as = True

    list_display = ['lemma','dataset']

    list_display += ['morph', 'sense', 'sn']
    search_fields = ['^lemma__lemmaidglosstranslation__text', '=sn']
    list_filter = ['lemma__dataset', 'signlanguage', 'dialect', SenseNumberListFilter, 'inWeb', 'domhndsh']
    inlines = [ RelationInline, RelationToForeignSignInline, DefinitionInline, TranslationInline, OtherMediaInline ]

    history_latest_first = True


class HandshapeAdmin(VersionAdmin):

    list_display = ['machine_value', 'english_name', 'dutch_name']

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

    def has_delete_permission(self, request, obj=None):
        objects_with_domhndsh = 0
        objects_with_subhndsh = 0
        if obj is not None and obj.field == 'Handshape':
            objects_with_domhndsh = Gloss.objects.filter(domhndsh=obj.machine_value).count()
            objects_with_subhndsh = Gloss.objects.filter(subhndsh=obj.machine_value).count()
            if objects_with_domhndsh > 0 or objects_with_subhndsh > 0:
                return False
        elif obj is not None and obj.field == 'FingerSelection':
            # This is a reserved field, used for displaying the Finger Selection
            # Do not allow deletion
            return False

        # if it's not a Handshape, then do the BaseAdmin code
        opts = self.opts
        codename = get_permission_codename('delete', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_change_permission(self, request, obj=None):

        if obj is not None and obj.field == 'FingerSelection':
            # This is a reserved field, used for displaying the Finger Selection
            # Do not allow deletion
            return False

        opts = self.opts
        codename = get_permission_codename('change', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def delete_selected(self, request, queryset):

        for obj in queryset:
            if obj.field == 'FingerSelection':
                # FingerSelection is used for display in the code, do not allow deletion
                messages.add_message(request, messages.ERROR, ("Deletion of FingerSelection fields is not allowed."))
                pass
            if obj.field == 'Handshape':
                objects_with_domhndsh = Gloss.objects.filter(domhndsh=obj.machine_value).count()
                objects_with_subhndsh = Gloss.objects.filter(subhndsh=obj.machine_value).count()
                if objects_with_domhndsh > 0 or objects_with_subhndsh > 0:
                    inuse_message = "Handshape " + obj.english_name + " is currently in use."
                    messages.add_message(request, messages.ERROR, inuse_message)
                    pass
            obj.delete()

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

admin.site.register(UserProfile)
admin.site.register(Language, LanguageAdmin)
admin.site.register(Dataset, DatasetAdmin)

admin.site.register(LemmaIdgloss, LemmaIdglossAdmin)
admin.site.register(LemmaIdglossTranslation, LemmaIdglossTranslationAdmin)
