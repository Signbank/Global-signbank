from django.template import Library

register = Library()

@register.filter
def underscore_to_space(value):

    return value.replace("_"," ")

@register.filter
def hyphen_to_underscore(value):

    return value.replace("-","_")
