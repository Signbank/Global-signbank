from django.contrib import admin 
from signbank.feedback.models import *
 
class GeneralFeedbackAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'date', 'comment', 'video']
    list_display = ['user', 'date', 'comment']
    list_filter = ['user']
admin.site.register(GeneralFeedback, GeneralFeedbackAdmin)

class SignFeedbackAdmin(admin.ModelAdmin):
    readonly_fields = ['translation', 'isAuslan', 'whereused', 'like', 'use', 'suggested', 'correct', 'kwnotbelong', 'comment']
    list_display = ['user', 'date', 'translation']
    list_filter = ['user']

    def get_fields(self, request, obj=None):
        fields = ['translation', 'comment', 'status']
        return fields

admin.site.register(SignFeedback, SignFeedbackAdmin)

class MissingSignFeedbackAdmin(admin.ModelAdmin):
    readonly_fields = ['handform', 'handform_fk_id', 'handshape', 'handshape_fk_id', 'althandshape', 'althandshape_fk_id',
               'location', 'location_fk_id', 'relativelocation', 'relativelocation_fk_id', 'handbodycontact',
               'handbodycontact_fk_id', 'handinteraction', 'handinteraction_fk_id', 'direction', 'direction_fk_id',
               'movementtype', 'movementtype_fk_id', 'smallmovement', 'smallmovement_fk_id', 'repetition',
               'meaning', 'video', 'comments']
    list_display = ['user', 'date']
    list_filter = ['user']

    def get_fields(self, request, obj=None):
        fields = ['meaning', 'comments', 'video', 'status']
        return fields

admin.site.register(MissingSignFeedback, MissingSignFeedbackAdmin)


