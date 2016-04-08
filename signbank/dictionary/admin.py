from django.contrib import admin 
from django.contrib.auth.admin import UserAdmin
from signbank.dictionary.models import *
from reversion.admin import VersionAdmin
from signbank.settings.server_specific import FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD

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

class OtherVideoInline(admin.TabularInline):
    model = OtherVideo
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
    fieldsets = ((None, {'fields': ('idgloss', 'annotation_idgloss', 'annotation_idgloss_en','useInstr','morph', 'sense', 
                                    'sn', 'StemSN', 'comptf', 'compound', 'language', 'dialect','rmrks')}, ),
                 ('Publication Status', {'fields': ('inWeb',  'isNew', 'creator','creationDate'),
                                       'classes': ('collapse',)}, ),
                 ('Phonology', {'fields': FIELDS['phonology'], 'classes': ('collapse',)}, ),
                 ('Semantics', {'fields': FIELDS['semantics'], 'classes': ('collapse',)}),
                 ('Frequency', {'fields': FIELDS['frequency'], 'classes': ('collapse',)}),
                ('Obsolete Fields', {'fields': ('inittext', ), 'classes': ('collapse',)}),
              )
    save_on_top = True
    save_as = True

    list_display = ['idgloss','annotation_idgloss']

    if SEPARATE_ENGLISH_IDGLOSS_FIELD:
        list_display += ['annotation_idgloss_en']

    list_display += ['morph', 'sense', 'sn']
    search_fields = ['^idgloss', '=sn', '^annotation_idgloss']
    list_filter = ['language', 'dialect', SenseNumberListFilter, 'inWeb', 'domhndsh']
    inlines = [ RelationInline, RelationToForeignSignInline, DefinitionInline, TranslationInline, OtherVideoInline ]


class RegistrationProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'activation_key_expired', )
    search_fields = ('user__username', 'user__first_name', )
 
class DialectInline(admin.TabularInline):
    
    model = Dialect

class DialectAdmin(VersionAdmin):
    model = Dialect
 
class LanguageAdmin(VersionAdmin):
    model = Language
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
    list_display = ['english_name','dutch_name','machine_value','field']
    list_filter = ['field']

    def save_model(self, request, obj, form, change):

        if obj.machine_value == None:
            highest_machine_value = max([field_choice.machine_value for field_choice in FieldChoice.objects.filter(field=obj.field)])
            obj.machine_value= highest_machine_value+1

        obj.save()

admin.site.register(Dialect, DialectAdmin)
admin.site.register(Language, LanguageAdmin) 
admin.site.register(Gloss, GlossAdmin) 
admin.site.register(Keyword, KeywordAdmin) 
admin.site.register(FieldChoice,FieldChoiceAdmin)
admin.site.register(MorphologyDefinition)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(UserProfile)