from django import template
from signbank.tags.models import Tag

register = template.Library()


@register.simple_tag
def tags_for_object(obj):
    """Get all tags for an object (replaces django-tagging template tag)"""
    return Tag.objects.get_for_object(obj)
