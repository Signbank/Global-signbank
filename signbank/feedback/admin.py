from django.contrib import admin 
from signbank.feedback.models import *
 
class GeneralFeedbackAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'date', 'comment', 'video']
    list_display = ['user', 'date', 'comment']
    list_filter = ['user']
admin.site.register(GeneralFeedback, GeneralFeedbackAdmin)


class SignFeedbackAdmin(admin.ModelAdmin):
    readonly_fields = ['translation', 'comment']
    list_display = ['user', 'date', 'translation']
    list_filter = ['user']

    def get_fields(self, request, obj=None):
        fields = ['translation', 'comment', 'status']
        return fields

admin.site.register(SignFeedback, SignFeedbackAdmin)


class MissingSignFeedbackAdmin(admin.ModelAdmin):

    list_display = ['user', 'date']
    list_filter = ['user']

    def get_fields(self, request, obj=None):
        fields = ['meaning', 'comments', 'video', 'status']
        return fields

admin.site.register(MissingSignFeedback, MissingSignFeedbackAdmin)


class MorphemeFeedbackAdmin(admin.ModelAdmin):
    readonly_fields = ['translation', 'comment']
    list_display = ['user', 'date', 'translation']
    list_filter = ['user']

    def get_fields(self, request, obj=None):
        fields = ['translation', 'comment', 'status']
        return fields

admin.site.register(MorphemeFeedback, MorphemeFeedbackAdmin)
