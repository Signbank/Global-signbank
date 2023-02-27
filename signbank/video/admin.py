from django.contrib import admin
from django import forms
from django.db import models
from signbank.video.models import GlossVideo, Dataset
from signbank.settings.server_specific import WRITABLE_FOLDER
from django.utils.translation import override, ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.core.files import File


class GlossVideoAdminForm(forms.ModelForm):
    # needs additional code to obtain FileField data

    class Meta:
        model = GlossVideo
        fields = ('gloss', )

    def __init__(self, *args, **kwargs):
        super(GlossVideoAdminForm, self).__init__(*args, **kwargs)


class GlossVideoDatasetFilter(admin.SimpleListFilter):

    title = _('Dataset')
    parameter_name = 'videos_per_dataset'

    def lookups(self, request, model_admin):
        datasets = Dataset.objects.all()
        return (tuple(
            (dataset.id, dataset.acronym) for dataset in datasets
        ))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gloss__lemma__dataset_id=self.value())
        return queryset.all()


class GlossVideoAdmin(admin.ModelAdmin):

    list_display = ['id', 'gloss', 'video_file', 'version']
    list_filter = (GlossVideoDatasetFilter,)

    search_fields = ['^gloss__annotationidglosstranslation__text']

    # not used yet
    form = GlossVideoAdminForm

    def video_file(self, obj=None):
        # this will display the full path in the list view
        if obj is None:
            return ""
        import os
        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.videofile))

        return video_file_full_path

    def get_list_display_links(self, request, list_display):
        # do not allow the user to view individual revisions in list
        self.list_display_links = (None, )
        return self.list_display_links


admin.site.register(GlossVideo, GlossVideoAdmin)
