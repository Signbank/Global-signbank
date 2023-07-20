from signbank.dictionary.models import *


def senses_per_language(gloss):
    # Put senses per language in a dictionary that maps dataset languages to list of strings
    sensetranslations_per_language = dict()
    if not gloss:
        return sensetranslations_per_language
    for language in gloss.lemma.dataset.translation_languages.all():
        sensetranslations_per_language[language] = dict()
        sensetranslations_for_language = dict()
        for sensei, sense in enumerate(gloss.ordered_senses().all(), 1):
            if sense.senseTranslations.filter(language=language).exists():
                sensetranslation = sense.senseTranslations.get(language=language)
                translations = sensetranslation.translations.all().order_by('index')
                if translations:
                    keywords_list = [trans.translation.text for trans in translations]
                    sensetranslations_for_language[sensei] = ', '.join(keywords_list)
        senses_for_language_display = []
        for sensei, translations in sensetranslations_for_language.items():
            senses_for_language_display.append(str(sensei) + '. ' + translations)
        sensetranslations_per_language[language] = senses_for_language_display
    return sensetranslations_per_language
