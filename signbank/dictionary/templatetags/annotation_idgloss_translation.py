from django.template import Library
from signbank.dictionary.forms import GlossSearchForm, MorphemeSearchForm

register = Library()


@register.filter
def get_annotation_idgloss_translation(gloss, language):
    return gloss.annotationidglosstranslation_set.filter(language=language)[0].text


@register.filter
def get_search_field_for_language(form, language):
    return getattr(form, GlossSearchForm.gloss_search_field_prefix + language.language_code_2char)


@register.filter
def get_morpheme_search_field_for_language(form, language):
    return getattr(form, MorphemeSearchForm.morpheme_search_field_prefix + language.language_code_2char)


@register.filter
def get_type(obj):
    return type(obj)