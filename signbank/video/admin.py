from django.contrib import admin
from django import forms
from django.db import models
from signbank.video.models import GlossVideo, GlossVideoHistory
from signbank.dictionary.models import Dataset
from django.contrib.auth.models import User
from signbank.settings.base import *
from signbank.settings.server_specific import WRITABLE_FOLDER, FILESYSTEM_SIGNBANK_GROUPS
from django.utils.translation import override, gettext_lazy as _
from django.db.models import Q, Count, CharField, TextField, Value as V


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


class GlossVideoFileSystemGroupFilter(admin.SimpleListFilter):

    title = _('File System Group')
    parameter_name = 'filesystem_group'

    def lookups(self, request, model_admin):
        filesystem_groups = tuple((g, g) for g in FILESYSTEM_SIGNBANK_GROUPS)
        return filesystem_groups

    def queryset(self, request, queryset):

        def matching_file_group(videofile, key):
            if not key:
                return False
            from pathlib import Path
            video_file_full_path = Path(WRITABLE_FOLDER, videofile)
            if video_file_full_path.exists():
                return video_file_full_path.group() == key
            else:
                return False

        queryset_res = queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file_group(qv['videofile'], self.value())]

        if self.value():
            return queryset.filter(id__in=results)
        else:
            return queryset.all()


class GlossVideoExistenceFilter(admin.SimpleListFilter):

    title = _('File Exists')
    parameter_name = 'file_exists'

    def lookups(self, request, model_admin):
        file_exists = tuple((b, b) for b in ('True', 'False'))
        return file_exists

    def queryset(self, request, queryset):

        def matching_file_exists(videofile, key):
            if not key:
                return False
            from pathlib import Path
            video_file_full_path = Path(WRITABLE_FOLDER, videofile)
            if video_file_full_path.exists():
                return key == 'True'
            else:
                return key == 'False'

        queryset_res = queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file_exists(qv['videofile'], self.value())]

        if self.value():
            return queryset.filter(id__in=results)
        else:
            return queryset.all()


class GlossVideoAdmin(admin.ModelAdmin):

    list_display = ['id', 'gloss', 'video_file', 'file_timestamp', 'file_group', 'permissions', 'file_size', 'version']
    list_filter = (GlossVideoDatasetFilter, GlossVideoFileSystemGroupFilter, GlossVideoExistenceFilter)

    search_fields = ['^gloss__annotationidglosstranslation__text']

    def video_file(self, obj=None):
        # this will display the full path in the list view
        if obj is None:
            return ""
        import os
        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.videofile))

        return video_file_full_path

    def file_timestamp(self, obj=None):
        # if the file exists, this will display its timestamp in the list view
        if obj is None:
            return ""
        import os
        import datetime
        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.videofile))
        if os.path.exists(video_file_full_path):
            return datetime.datetime.fromtimestamp(os.path.getctime(video_file_full_path))
        else:
            return ""

    def file_group(self, obj=None):
        # this will display a group in the list view
        if obj is None:
            return ""
        else:
            from pathlib import Path
            video_file_full_path = Path(WRITABLE_FOLDER, str(obj.videofile))
            if video_file_full_path.exists():
                group = video_file_full_path.group()
                return group
            else:
                return ""

    def file_size(self, obj=None):
        # this will display a group in the list view
        if obj is None:
            return ""
        else:
            from pathlib import Path
            video_file_full_path = Path(WRITABLE_FOLDER, str(obj.videofile))
            if video_file_full_path.exists():
                size = str(video_file_full_path.stat().st_size)
                return size
            else:
                return ""

    def permissions(self, obj=None):
        # this will display a group in the list view
        if obj is None:
            return ""
        else:
            from pathlib import Path
            import stat
            video_file_full_path = Path(WRITABLE_FOLDER, str(obj.videofile))
            if video_file_full_path.exists():
                stats = stat.filemode(video_file_full_path.stat().st_mode)
                return stats
            else:
                return ""

    def get_list_display_links(self, request, list_display):
        # do not allow the user to view individual revisions in list
        self.list_display_links = (None, )
        return self.list_display_links

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if not self.file_timestamp(obj):
            return True
        return False


class GlossVideoHistoryDatasetFilter(admin.SimpleListFilter):

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


class GlossVideoHistoryActorFilter(admin.SimpleListFilter):

    title = _('Actor')
    parameter_name = 'videos_per_actor'

    def lookups(self, request, model_admin):
        users = User.objects.all().distinct().order_by('first_name')
        return (tuple(
            (user.id, user.username) for user in users
        ))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(actor__id=self.value())
        return queryset.all()


class GlossVideoHistoryAdmin(admin.ModelAdmin):

    list_display = ['action', 'datestamp', 'uploadfile', 'goal_location', 'actor', 'gloss']
    list_filter = (GlossVideoHistoryDatasetFilter, GlossVideoHistoryActorFilter)

    search_fields = ['^gloss__annotationidglosstranslation__text']


admin.site.register(GlossVideo, GlossVideoAdmin)
admin.site.register(GlossVideoHistory, GlossVideoHistoryAdmin)

