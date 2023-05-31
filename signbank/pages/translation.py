from modeltranslation.translator import translator, TranslationOptions
from .models import Page
from signbank.settings.server_specific import MODELTRANSLATION_LANGUAGES


class PageTranslationOptions(TranslationOptions):
    fields = ('title', 'content')
    required_languages = tuple([t for t in MODELTRANSLATION_LANGUAGES])


translator.register(Page, PageTranslationOptions)