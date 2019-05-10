from django import forms
from django.contrib import admin
from signbank.pages.models import Page, PageVideo
from signbank.video.fields import VideoUploadToFLVField
from django.utils.translation import ugettext_lazy as _

from django_summernote.admin import SummernoteModelAdmin


from signbank.log import debug
from signbank.settings import server_specific

class PageForm(forms.ModelForm):
    url = forms.RegexField(label=_("URL"), max_length=100, regex=r'^[-\w/]+$',
        help_text = _("Example: '/about/contact/'. Make sure to have leading"
                      " and trailing slashes."))

    class Meta:
        model = Page
        fields = '__all__'


class PageVideoForm(forms.ModelForm):
    video = VideoUploadToFLVField(label='Video',
                            required=True,
                            prefix='pages',
                            help_text = _("Uploaded video will be converted to Flash"),
                            widget = admin.widgets.AdminFileWidget)

    class Meta:
        model = PageVideo
        fields = '__all__'

    def save(self, commit=True):
        debug("Saving a video form")
        debug("VideoName: %s" % (self.cleaned_data['video'],))
        debug("Cleaned data: %s" % (self.cleaned_data,))
        instance = super(PageVideoForm, self).save(commit=commit)
        debug("Instance video: %s" % instance.video)
        return instance

class PageVideoInline(admin.TabularInline):
    form = PageVideoForm
    model = PageVideo  
    extra = 1

class PageAdmin(SummernoteModelAdmin):
    form = PageForm
    if hasattr(server_specific, 'SHOW_ENGLISH_ONLY') and server_specific.SHOW_ENGLISH_ONLY:
        fieldsets = (
            (None, {'fields': (
            'url', 'title', 'parent', 'index', 'publish', 'content')}),
            (_('Advanced options'), {'classes': ('collapse',), 'fields': ('group_required', 'template_name')}),
        )
    else:
        fieldsets = (
            (None, {'fields': ('url', 'title', 'title_dutch', 'title_chinese', 'parent', 'index', 'publish', 'content', 'content_dutch', 'content_chinese')}),
            (_('Advanced options'), {'classes': ('collapse',), 'fields': ('group_required', 'template_name')}),
        )
    list_display = ('url', 'title', 'parent', 'index')
    list_filter = ('publish', 'group_required')
    search_fields = ('url', 'title')
    inlines = [PageVideoInline]

admin.site.register(Page, PageAdmin)


