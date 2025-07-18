from django.template import Library
from django.utils.translation import gettext

from urllib import request
from xml.dom import minidom

from signbank.settings.base import ECV_SETTINGS

from signbank.dictionary.models import Language
from signbank.dictionary.forms import GlossSearchForm, MorphemeSearchForm, AnnotatedSentenceSearchForm
from signbank.tools import get_ecv_description_for_gloss, get_default_annotationidglosstranslation, duplicate_lemmas
from signbank.dataset_operations import dataset_lemma_constraints_check
from signbank.dictionary.batch_edit import get_sense_numbers

register = Library()


@register.filter
def get_annotation_idgloss_translation(gloss, language):
    annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)

    if annotationidglosstranslations.count():
        return annotationidglosstranslations.first().text

    # This is a fallback to the English translation, but we rather want nothing, see #583
    # Use the other function _no_default below if no default is wanted
    translations = gloss.annotationidglosstranslation_set.filter(language__language_code_3char='eng')
    if translations:
        return translations.first().text

    return str(gloss.id)


@register.filter
def get_annotation_idgloss_translation_no_default(gloss, language):
    annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language).first()
    if annotationidglosstranslations:
        return annotationidglosstranslations.text
    return ""


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
    if lemmaidglosstranslations:
        return lemmaidglosstranslations.first().text
    return ""

@register.filter
def get_annotatedsentence_translation(sentence, language):
    sentencetranslations = sentence.annotated_sentence_translations.filter(language=language)
    if sentencetranslations:
        return sentencetranslations.first().text
    return ""

@register.filter
def get_annotatedgloss_translation(annotated_gloss, language):
    gloss_translation = annotated_gloss.gloss.annotationidglosstranslation_set.filter(language=language)
    if gloss_translation:
        return gloss_translation.first().text
    return ""

@register.filter
def get_lemma_idgloss_translation_no_default(lemma, language):
    lemmaidglosstranslations = lemma.lemmaidglosstranslation_set.filter(language=language)
    if lemmaidglosstranslations is not None and len(lemmaidglosstranslations) > 0:
        return lemmaidglosstranslations.first().text
    if not lemma.dataset:
        return ""
    lemma_translation_languages = lemma.dataset.translation_languages.all()
    if language not in lemma_translation_languages:
        return ""
    # one of the dataset translation languages has no annotation for this lemma
    return str(lemma.id)

@register.filter
def check_lemma_constraints(lemma):
    # for use in the LemmaListView and LemmaUpdateView to summarise constraint violations
    duplicatelemmas = duplicate_lemmas(lemma)
    constraints_dict = dataset_lemma_constraints_check(lemma)
    result = []
    for duplicate_lemma in duplicatelemmas:
        result.append(gettext("Lemma {thislemma} overlaps with Lemma {lemmaid}").format(thislemma=str(lemma.pk), lemmaid=str(duplicate_lemma)))
    for key  in constraints_dict.keys():
        (no_translations, multiple_translations, empty_text) = constraints_dict[key]
        if no_translations:
            result.append(key.name + gettext(" translation is missing"))
        elif multiple_translations:
            result.append(key.name + gettext(" has multiple translations"))
        elif empty_text:
            result.append(key.name + gettext(" has an empty text translation"))
    string_result = "; ".join(result)
    return "" if string_result == "" else string_result

@register.filter
def get_search_field_for_language(form, language):
    return getattr(form, GlossSearchForm.gloss_search_field_prefix + language.language_code_2char)

@register.filter
def get_annotation_search_field_for_language(form, language):
    field = GlossSearchForm.gloss_search_field_prefix + language.language_code_2char
    return form.fields[field]

@register.filter
def get_morpheme_search_field_for_language(form, language):
    field = MorphemeSearchForm.gloss_search_field_prefix + language.language_code_2char
    return form.fields[field]

@register.filter
def get_keyword_field_for_language(form, language):
    return getattr(form, GlossSearchForm.keyword_search_field_prefix + language.language_code_2char)

@register.filter
def get_senses_form_field_for_language(form, language):
    field = GlossSearchForm.keyword_search_field_prefix + language.language_code_2char
    return form.fields[field]

@register.filter
def get_keyword_form_field_for_language(form, language):
    field = MorphemeSearchForm.keyword_search_field_prefix + language.language_code_2char
    return form.fields[field]

@register.filter
def get_lemma_field_for_language(form, language):
    return getattr(form, GlossSearchForm.lemma_search_field_prefix + language.language_code_2char)

@register.filter
def get_lemma_form_field_for_language(form, language):
    field = MorphemeSearchForm.lemma_search_field_prefix + language.language_code_2char
    return form.fields[field]

@register.filter
def get_annotatedsentence_form_field_for_language(form, language):
    field = AnnotatedSentenceSearchForm.annotatedsentence_search_field_prefix + language.language_code_2char
    return form.fields[field]

@register.filter
def get_type(obj):
    return type(obj)


@register.filter
def keyvalue(dict, key):
    if key in dict:
        return dict[key]
    return ''

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return ""
    return dictionary.get(key)

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
    url = 'http://catalog.clarin.eu/ds/ComponentRegistry/rest/registry/components/clarin.eu:cr1:c_1271859438110'
    dom = minidom.parse(request.urlopen(url))
    items = dom.getElementsByTagName('item')
    if isinstance(languages, str):
        # Assume is it a language_code_3char
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
    return get_ecv_description_for_gloss(gloss, language_code_2char, ECV_SETTINGS['include_phonology_and_frequencies'])

@register.filter
def translated_annotationidgloss(gloss, language_code):
    annotationidgloss = gloss.annotation_idgloss(language_code)
    return annotationidgloss

@register.filter
def get_senses_mapping(gloss):

    senses_mapping = get_sense_numbers(gloss)
    return senses_mapping


@register.filter
def get_senses_for_language(sensetranslations, language):
    if language not in sensetranslations.keys():
        return ""
    return sensetranslations[language]

@register.filter
def sense_translations_dict_with(sense, join_char):
    sense_translations = sense.get_sense_translations_dict_with(join_char, True)
    return sense_translations

@register.filter
# this replaces the newline character with the HTML variant for display in the textarea
def splitlines(value):
    split_value = value.split('\\n')
    values = "&#10;".join(split_value)
    return values

@register.filter
def to_all_keys(dictionary):
    new_dictionary = {}
    if not dictionary:
        return new_dictionary
    keys = list(dictionary.keys())
    if not keys:
        return new_dictionary
    last_key = keys[-1]
    for key in range(1, last_key + 1):
        if key in dictionary:
            new_dictionary[key] = dictionary[key]
        else:
            new_dictionary[key] = ""
    return new_dictionary
