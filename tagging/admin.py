from django.contrib import admin
from .models import Tag, TaggedItem


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(TaggedItem)
class TaggedItemAdmin(admin.ModelAdmin):
    list_display = ('tag', 'content_type', 'object_id')
    list_filter = ('tag', 'content_type')
    search_fields = ('tag__name',)