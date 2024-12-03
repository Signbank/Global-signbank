from django.core.management.base import BaseCommand
from signbank.dictionary.models import Dataset, Gloss, LemmaIdgloss


class Command(BaseCommand):

    help = 'remove users except for development'
    args = ''

    def handle(self, *args, **options):

        all_datasets = Dataset.objects.all().distinct()

        for dataset in all_datasets:

            if dataset.acronym not in ['tstMH']:
                dataset.delete()

