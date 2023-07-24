from modeltranslation.translator import translator, TranslationOptions
from .models import Language, FieldChoice, Handshape, SemanticField, DerivationHistory
from signbank.settings.server_specific import LANGUAGES, MODELTRANSLATION_LANGUAGES, MODELTRANSLATION_FIELDCHOICE_LANGUAGES

# This file lists settings for django-modeltranslation.
# Here you can define which fields from which models to translate.


class LanguageTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = tuple([t for t in MODELTRANSLATION_LANGUAGES])


translator.register(Language, LanguageTranslationOptions)


class FieldChoiceTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = tuple([t for t in MODELTRANSLATION_FIELDCHOICE_LANGUAGES])


translator.register(FieldChoice, FieldChoiceTranslationOptions)


class HandshapeTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = tuple([t for t in MODELTRANSLATION_LANGUAGES])


translator.register(Handshape, HandshapeTranslationOptions)


class SemanticFieldTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = tuple([t for t in MODELTRANSLATION_LANGUAGES])


translator.register(SemanticField, SemanticFieldTranslationOptions)


class DerivationHistoryTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = tuple([t for t in MODELTRANSLATION_LANGUAGES])


translator.register(DerivationHistory, DerivationHistoryTranslationOptions)
