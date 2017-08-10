from modeltranslation.translator import translator, TranslationOptions
from .models import Language


# This file lists settings for django-modeltranslation.
# Here you can define which fields from which models to translate.

class LanguageTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = ('en',)


translator.register(Language, LanguageTranslationOptions)