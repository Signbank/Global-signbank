from django.contrib import admin 
from signbank.feedback.models import *
from django.utils.translation import override, gettext_lazy as _
from django.contrib.admin import SimpleListFilter
 
class GeneralFeedbackAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'date', 'comment', 'video']
    list_display = ['user', 'date', 'comment']
    list_filter = ['user']


admin.site.register(GeneralFeedback, GeneralFeedbackAdmin)


class SignFeedbackDatasetFilter(SimpleListFilter):

    title = _('Dataset')
    parameter_name = 'signfeedback_per_dataset'

    def lookups(self, request, model_admin):
        datasets = Dataset.objects.all()
        return (tuple(
            (dataset.id, dataset.acronym) for dataset in datasets
        ))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gloss__lemma__dataset_id=self.value())
        return queryset.all()


class SignFeedbackAdmin(admin.ModelAdmin):
    readonly_fields = ['gloss', 'comment']
    list_display = ['date', 'user', 'gloss_annotations']
    list_filter = (SignFeedbackDatasetFilter,)

    def get_fields(self, request, obj=None):
        fields = ['gloss', 'comment', 'status']
        return fields

    def gloss_annotations(self, obj=None):
        if obj is None:
            return ""
        translations = []
        count_dataset_languages = obj.gloss.lemma.dataset.translation_languages.all().count() \
            if obj.gloss.lemma.dataset else 0
        for translation in obj.gloss.annotationidglosstranslation_set.all():
            if settings.SHOW_DATASET_INTERFACE_OPTIONS and count_dataset_languages > 1:
                translations.append("{}: {}".format(translation.language, translation.text))
            else:
                translations.append("{}".format(translation.text))
        return ", ".join(translations)


admin.site.register(SignFeedback, SignFeedbackAdmin)


class MissingSignFeedbackAdmin(admin.ModelAdmin):

    list_display = ['user', 'date']
    list_filter = ['user']

    def get_fields(self, request, obj=None):
        fields = ['meaning', 'comments', 'video', 'status']
        return fields


admin.site.register(MissingSignFeedback, MissingSignFeedbackAdmin)


class MorphemeFeedbackDatasetFilter(SimpleListFilter):

    title = _('Dataset')
    parameter_name = 'morphemefeedback_per_dataset'

    def lookups(self, request, model_admin):
        datasets = Dataset.objects.all()
        return (tuple(
            (dataset.id, dataset.acronym) for dataset in datasets
        ))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(morpheme__lemma__dataset_id=self.value())
        return queryset.all()


class MorphemeFeedbackAdmin(admin.ModelAdmin):
    readonly_fields = ['morpheme', 'comment']
    list_display = ['date', 'user', 'morpheme_annotations']
    list_filter = (MorphemeFeedbackDatasetFilter,)

    def get_fields(self, request, obj=None):
        fields = ['morpheme', 'comment', 'status']
        return fields

    def morpheme_annotations(self, obj=None):
        if obj is None:
            return ""
        translations = []
        count_dataset_languages = obj.morpheme.lemma.dataset.translation_languages.all().count() \
            if obj.morpheme.lemma.dataset else 0
        for translation in obj.morpheme.annotationidglosstranslation_set.all():
            if settings.SHOW_DATASET_INTERFACE_OPTIONS and count_dataset_languages > 1:
                translations.append("{}: {}".format(translation.language, translation.text))
            else:
                translations.append("{}".format(translation.text))
        return ", ".join(translations)


admin.site.register(MorphemeFeedback, MorphemeFeedbackAdmin)
