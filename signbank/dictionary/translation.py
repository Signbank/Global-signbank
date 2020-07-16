from modeltranslation.translator import translator, TranslationOptions
from .models import Language
from signbank.settings.base import LANGUAGES

# This file lists settings for django-modeltranslation.
# Here you can define which fields from which models to translate.

class LanguageTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = (LANGUAGES[0][0],)


translator.register(Language, LanguageTranslationOptions)