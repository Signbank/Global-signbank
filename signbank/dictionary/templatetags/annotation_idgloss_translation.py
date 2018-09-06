from django.template import Library
from signbank.dictionary.forms import GlossSearchForm, MorphemeSearchForm
import json

register = Library()


@register.filter
def get_annotation_idgloss_translation(gloss, language):
    annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
    if annotationidglosstranslations is not None and len(annotationidglosstranslations) > 0:
        return annotationidglosstranslations[0].text
    return gloss.annotationidglosstranslation_set.filter(language__language_code_3char='eng')[0].text


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


@register.filter
def getattr (obj, args):
    """ Try to get an attribute from an object.

    Example: {% if block|getattr:"editable,True" %}

    Beware that the default is always a string, if you want this
    to return False, pass an empty second argument:
    {% if block|getattr:"editable," %}
    """
    args = args.split(',')
    if len(args) == 1:
        (attribute, default) = [args[0], '']
    else:
        (attribute, default) = args
    try:
        return obj.__getattribute__(attribute)
    except AttributeError:
         return  obj.__dict__.get(attribute, default)
    except:
        return default