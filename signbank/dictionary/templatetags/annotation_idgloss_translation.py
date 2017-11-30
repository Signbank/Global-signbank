from django.template import Library

register = Library()


@register.filter
def get_annotation_idgloss_translation(gloss, language):
    return gloss.annotationidglosstranslation_set.filter(language=language)[0].text


@register.filter
def get_type(obj):
    return type(obj)