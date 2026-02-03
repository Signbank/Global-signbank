from django import forms
from django.contrib import admin
from signbank.pages.models import Page
from django.utils.translation import gettext_lazy as _

from django_summernote.admin import SummernoteModelAdmin
from modeltranslation.admin import TranslationAdmin


from signbank.log import debug
from signbank.settings import server_specific

class PageForm(forms.ModelForm):
    url = forms.RegexField(label=_("URL"), max_length=100, regex=r'^[-\w/]+$',
        help_text = _("Example: '/about/contact/'. Make sure to have leading"
                      " and trailing slashes."))

    class Meta:
        model = Page
        fields = '__all__'

class PageAdmin(TranslationAdmin, SummernoteModelAdmin):
    form = PageForm
    if hasattr(server_specific, 'SHOW_ENGLISH_ONLY') and server_specific.SHOW_ENGLISH_ONLY:
        fieldsets = (
            (None, {'fields': (
            'url', 'title', 'parent', 'index', 'publish', 'content')}),
            (_('Advanced options'), {'classes': ('collapse',), 'fields': ('group_required', 'template_name')}),
        )
    else:
        fieldsets = (
            (None, {'fields': ('url', 'title',
                               'parent', 'index', 'publish',
                               'content', )}),
            (_('Advanced options'), {'classes': ('collapse',), 'fields': ('group_required', 'template_name')}),
        )
    list_display = ('url', 'title', 'parent', 'index')
    list_filter = ('publish', 'group_required')
    search_fields = ('url', 'title')

admin.site.register(Page, PageAdmin)


