from django.template import Library
from signbank.dictionary.forms import GlossSearchForm, MorphemeSearchForm
from signbank.tools import get_default_annotationidglosstranslation
import json

register = Library()


@register.filter
def get_annotation_idgloss_translation(gloss, language):
    annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
    if annotationidglosstranslations is not None and len(annotationidglosstranslations) > 0:
        return annotationidglosstranslations[0].text

    #This is a fallback to the English translation, but we rather want nothing, see #583

    #translations = gloss.annotationidglosstranslation_set.filter(language__language_code_3char='eng')
    #if translations:
    #    return translations[0].text

    return ''

@register.filter
def get_default_annotation_idgloss_translation(gloss):
    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)
    return default_annotationidglosstranslation

@register.filter
def display_language(gloss,interface_language):
    if interface_language == "nl":
        filter = "nl"
    elif interface_language == "zh-hans":
        filter = "zh"
    else:
        filter = "en"
    translations = gloss.annotationidglosstranslation_set.filter(language__language_code_2char=filter)
    if translations:
        return translations[0].text
    else:
        translations = gloss.annotationidglosstranslation_set.filter(language__language_code_3char='eng')
    if translations:
        return translations[0].text
    return ''

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
def get_lemma_field_for_language(form, language):
    return getattr(form, GlossSearchForm.lemma_search_field_prefix + language.language_code_2char)


@register.filter
def get_type(obj):
    return type(obj)


@register.filter
def keyvalue(dict, key):
    if key in dict:
        return dict[key]
    return ''

@register.filter
def get_item(dictionary,key):
    return dictionary.get(key)

@register.filter
def to_int(value):
    if value:
        return int(value)
    else:
        return 0

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


@register.filter
def get_iso_639_3_info(languages):
    """
    Adds ISO 639-3 info to a list of languages
    :param languages: a list of Language objects or a language_code_3char string 
    :return: 
    """
    from urllib import request
    from xml.dom import minidom
    url = 'http://catalog.clarin.eu/ds/ComponentRegistry/rest/registry/components/clarin.eu:cr1:c_1271859438110'
    dom = minidom.parse(request.urlopen(url))
    items = dom.getElementsByTagName('item')
    if isinstance(languages, str):
        # Assume is it a language_code_3char
        from signbank.dictionary.models import Language
        languages = [Language.objects.get(language_code_3char=languages)]

    # Return a dict with format
    # {"eng": ("http://cdb.iso.org/lg/CDB-00138502-001", "English (eng)"), "nld": (..., ...), ... }
    return dict([(language.language_code_3char,
                [(item.attributes['ConceptLink'].value, item.attributes['AppInfo'].value)
                    for item in items if item.firstChild.nodeValue == language.language_code_3char][0])
                 for language in languages])


@register.filter
def get_gloss_description(gloss, language_code_2char):
    """
    
    :param gloss: 
    :param language_code_2char: 
    :return: 
    """
    from signbank.tools import get_ecv_descripion_for_gloss
    from signbank.settings.base import ECV_SETTINGS
    return get_ecv_descripion_for_gloss(gloss, language_code_2char, ECV_SETTINGS['include_phonology_and_frequencies'])
