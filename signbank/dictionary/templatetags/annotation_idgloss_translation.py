from django.template import Library
from signbank.dictionary.forms import GlossSearchForm, MorphemeSearchForm

register = Library()


@register.filter
def get_annotation_idgloss_translation(gloss, language):
    annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
    if annotationidglosstranslations is not None and len(annotationidglosstranslations) > 0:
        return annotationidglosstranslations[0].text
    return ""


@register.filter
def get_lemma_idgloss_translation(lemma, language):
    lemmaidglosstranslations = lemma.lemmaidglosstranslation_set.filter(language=language)
    if lemmaidglosstranslations is not None and len(lemmaidglosstranslations) > 0:
        return lemmaidglosstranslations[0].text
    return ""


@register.filter
def get_search_field_for_language(form, language):
    return getattr(form, GlossSearchForm.gloss_search_field_prefix + language.language_code_2char)


@register.filter
def get_morpheme_search_field_for_language(form, language):
    return getattr(form, MorphemeSearchForm.morpheme_search_field_prefix + language.language_code_2char)


@register.filter
def get_keyword_field_for_language(form, language):
    return getattr(form, GlossSearchForm.keyword_search_field_prefix + language.language_code_2char)


@register.filter
def get_type(obj):
    return type(obj)


@register.filter
def keyvalue(dict, key):
    if key in dict:
        return dict[key]
    return ''
