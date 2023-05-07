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
        # if duplicates:
        #     print('To delete: ', duplicates)
        #     for glossid in duplicates:
        #         gloss_object = Gloss.objects.get(id=glossid)
        #         for lang in all_languages:
        #             translations_this_gloss_this_language = gloss_object.translation_set.filter(language__id=lang)
        #             if not translations_this_gloss_this_language:
        #                 continue
        #             print(translations_this_gloss_this_language)
        #             seen_text = []
        #             already_seen = []
        #             for trans in translations_this_gloss_this_language:
        #                 print(trans.id, trans.translation.text, trans.index)
        #                 if trans.translation.text in seen_text:
        #                     print('seen already: ', trans.translation.text)
        #                     already_seen.append(trans.id)
        #                 else:
        #                     print('not seen yet: ', trans.translation.text)
        #                     seen_text.append(trans.translation.text)
        #             if already_seen:
        #                 print('duplicates: ', already_seen)
        #                 for transid in already_seen:
        #                     translation_object = Translation.objects.get(pk=transid)
        #                     translation_object.delete()

                #         matches = [t.id for t in translations_this_gloss
                #                    if t.gloss.id == gloss.id
                #                    and t.language.id == trans.language.id
                #                    and t.translation.id == trans.translation.id
                #                    ]
                # translations_this_gloss_2 = gloss.translation_set.all()
                # print(glossid, language, translationtext)
                # multiple_translations = Translation.objects.filter(gloss__id=glossid,
                #                                                    language=language,
                #                                                    translation__text=translationtext).order_by('index')
                # print(multiple_translations)
                # if multiple_translations.count() > 1:
                #     # This is a duplicate that violates the constraint
                #     duplicate_translation = multiple_translations.last()
                #     print('Deleting Duplicate Translation: ', duplicate_translation)
                #     duplicate_translation.delete()
