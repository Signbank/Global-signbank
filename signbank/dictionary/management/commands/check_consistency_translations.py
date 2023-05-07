"""Create other media files."""

import os
import shutil
from django.core.management.base import BaseCommand
from django.core.exceptions import *
from signbank.dictionary.models import Dataset, Gloss, Translation, Keyword, Language


class Command(BaseCommand):
    help = 'Check for duplicate keywords in translations.'

    def handle(self, *args, **kwargs):
        all_languages = [lang.id for lang in Language.objects.all()]
        duplicates = []
        for gloss in Gloss.objects.all():
            translations_this_gloss = gloss.translation_set.all()
            if not translations_this_gloss:
                continue
            for lang in all_languages:
                translations_this_gloss_this_language = gloss.translation_set.filter(language__id=lang)
                if not translations_this_gloss_this_language:
                    continue
                for trans in translations_this_gloss_this_language:
                    matches = [t.id for t in translations_this_gloss
                               if t.gloss.id == gloss.id
                               and t.language.id == trans.language.id
                               and t.translation.id == trans.translation.id
                               ]
                    if len(matches) > 1:
                        if gloss.id not in duplicates:
                            duplicates.append(gloss.id)
                        print('Duplicate: Gloss ID, language, keywords, index: ',
                              gloss.id, trans.language, trans.translation.text, trans.index)

