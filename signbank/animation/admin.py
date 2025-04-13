from django.contrib import admin
from django import forms
from django.db import models
from signbank.animation.models import GlossAnimation, GlossAnimationHistory
from signbank.dictionary.models import Dataset, AnnotatedGloss
from django.contrib.auth.models import User
from signbank.settings.base import *
from signbank.settings.server_specific import WRITABLE_FOLDER, FILESYSTEM_SIGNBANK_GROUPS
from django.utils.translation import override, gettext_lazy as _
from django.db.models import Q, Count, CharField, TextField, Value as V


class GlossAnimationAdmin(admin.ModelAdmin):

    list_display = ['id', 'gloss', 'file', 'file_timestamp', 'file_size']

    search_fields = ['^gloss__annotationidglosstranslation__text']

    def file(self, obj=None):
        # this will display the full path in the list view
        if obj is None:
            return ""
        import os
        file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.file))

        return file_full_path

    def file_timestamp(self, obj=None):
        # if the file exists, this will display its timestamp in the list view
        if obj is None:
            return ""
        import os
        import datetime
        file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.file))
        if os.path.exists(file_full_path):
            return datetime.datetime.fromtimestamp(os.path.getctime(file_full_path))
        else:
            return ""

    def file_size(self, obj=None):
        # this will display a group in the list view
        if obj is None:
            return ""
        else:
            from pathlib import Path
            file_full_path = Path(WRITABLE_FOLDER, str(obj.file))
            if file_full_path.exists():
                size = str(file_full_path.stat().st_size)
                return size
            else:
                return ""


class GlossAnnotationHistoryAdmin(admin.ModelAdmin):

    list_display = ['action', 'datestamp', 'uploadfile', 'goal_location', 'actor', 'gloss']

    search_fields = ['^gloss__annotationidglosstranslation__text']

admin.site.register(GlossAnimation, GlossAnimationAdmin)
admin.site.register(GlossAnimationHistory, GlossAnnotationHistoryAdmin)
