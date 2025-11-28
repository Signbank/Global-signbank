from django.contrib import admin 
from signbank.attachments.models import Attachment, Communication


class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['file', 'date', 'uploader']


class CommunicationAdmin(admin.ModelAdmin):
    list_display = ['label', 'subject', 'text']


admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(Communication, CommunicationAdmin)
