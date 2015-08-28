from django.contrib import admin 
from signbank.feedback.models import *
 
class GeneralFeedbackAdmin(admin.ModelAdmin):
   list_display = ['user', 'date', 'comment']
   list_filter = ['user']
admin.site.register(GeneralFeedback, GeneralFeedbackAdmin)

class SignFeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'translation']
    list_filter = ['user']
admin.site.register(SignFeedback, SignFeedbackAdmin)

class MissingSignFeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'date']
    list_filter = ['user']
admin.site.register(MissingSignFeedback, MissingSignFeedbackAdmin)


