from django.template import Library

register = Library()

@register.filter
def underscore_to_space(value):

    return value.replace("_"," ")