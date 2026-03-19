from modeltranslation.translator import translator, TranslationOptions
from signbank.settings.server_specific import MODELTRANSLATION_LANGUAGES
from .models import Page


class PageTranslationOptions(TranslationOptions):
    fields = ('title', 'content')
    required_languages = tuple(MODELTRANSLATION_LANGUAGES)


translator.register(Page, PageTranslationOptions)
