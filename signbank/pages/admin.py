from django import forms
from django.contrib import admin
from signbank.pages.models import Page, PageVideo
from signbank.video.fields import VideoUploadToFLVField
from django.utils.translation import ugettext_lazy as _

from django_summernote.admin import SummernoteModelAdmin


from signbank.log import debug

class PageForm(forms.ModelForm):
    url = forms.RegexField(label=_("URL"), max_length=100, regex=r'^[-\w/]+$',
        help_text = _("Example: '/about/contact/'. Make sure to have leading"
                      " and trailing slashes."),
        error_message = _("This value must contain only letters, numbers,"
                          " underscores, dashes or slashes."))

    class Meta:
        model = Page

   
class PageVideoForm(forms.ModelForm):
    video = VideoUploadToFLVField(label='Video',
                            required=True,
                            prefix='pages',
                            help_text = _("Uploaded video will be converted to Flash"),
                            widget = admin.widgets.AdminFileWidget)
    class Meta:
        model = PageVideo

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
    fieldsets = (
        (None, {'fields': ('url', 'title', 'parent', 'index', 'publish', 'content' )}),
        (_('Advanced options'), {'classes': ('collapse',), 'fields': ('group_required', 'template_name')}),
    )
    list_display = ('url', 'title', 'parent', 'index')
    list_filter = ('publish', 'group_required')
    search_fields = ('url', 'title')
    inlines = [PageVideoInline]

admin.site.register(Page, PageAdmin)


