from django.core.management.base import BaseCommand
from signbank.dictionary.models import Keyword


class Command(BaseCommand):
    help = 'Delete duplicate keyword objects that have a space at the end.'

    def handle(self, *args, **options):
        keywords_to_delete = []

        keyword_filter_values = Keyword.objects.filter(text__endswith=' ')

        for kw in keyword_filter_values:
            shorter_keyword = kw.text[:-1]
            shorter_keywords = Keyword.objects.filter(text=shorter_keyword)
            if shorter_keywords.count() < 1:
                continue
            translations = kw.translation_set.all()
            if translations.count() < 1:
                print('No translations use keyword with space: ', kw)
                keywords_to_delete.append(kw)
                continue
            for tr in translations:
                text_without_space = kw.text[:-1]
                # keywords are unique
                shorter_keyword = Keyword.objects.filter(text=text_without_space).first()
                if shorter_keyword:
                    print('Replace with shorter keyword: ', tr.gloss.dataset, tr.gloss, shorter_keyword)
                    tr.translation = shorter_keyword
                    tr.save()
                    keywords_to_delete.append(kw)
        if keywords_to_delete:
            print('Delete unused keywords with a space at the end: ', keywords_to_delete)
        for kw in keywords_to_delete:
            kw.delete()

        double_spaces_to_delete = []
        keyword_filter_two_spaces = Keyword.objects.filter(text__endswith='  ')
        for kw in keyword_filter_two_spaces:
            shorter_keyword = kw.text[:-2]
            shorter_keywords = Keyword.objects.filter(text=shorter_keyword)
            if shorter_keywords.count() < 1:
                continue
            translations = kw.translation_set.all()
            if translations.count() < 1:
                print('No translations use keyword with spaces: ', kw)
                double_spaces_to_delete.append(kw)
                continue
            for tr in translations:
                text_without_spaces = kw.text[:-2]
                # keywords are unique
                shorter_keyword = Keyword.objects.filter(text=text_without_spaces).first()
                if shorter_keyword:
                    print('Replace with shorter keyword: ', tr.gloss.dataset, tr.gloss, shorter_keyword)
                    tr.translation = shorter_keyword
                    tr.save()
                    double_spaces_to_delete.append(kw)
        if double_spaces_to_delete:
            print('Delete unused keywords with two spaces at the end: ', double_spaces_to_delete)
        for kw in double_spaces_to_delete:
            kw.delete()
