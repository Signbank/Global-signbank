from django.contrib import admin 
from signbank.video.models import Video, GlossVideo

#admin.site.register(Video)

class GlossVideoAdmin(admin.ModelAdmin):
    search_fields = ['^gloss__idgloss']
    
admin.site.register(GlossVideo, GlossVideoAdmin)