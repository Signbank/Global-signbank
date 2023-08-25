
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from signbank.dictionary.models import *
from signbank.dictionary.consistency_senses import consistent_senses


class Command(BaseCommand):
    help = 'Check for inconsistent senses: sense order appears twice; ' \
           'more than one sense translation object for language, ' \
           'translation object language does not match, ' \
           'translation order index does not match, ' \
           'gloss does not match'

    def add_arguments(self, parser):
        parser.add_argument('dataset_acronym', nargs="*", type=str)
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all datasets",
        )

    def handle(self, *args, **options):
        if options["all"]:
            dataset_acronyms = list(Dataset.objects.values_list('acronym', flat=True))
        elif options['dataset_acronym']:
            dataset_acronyms = options['dataset_acronym']
        else:
            print("No datasets given (or --all)")
            return

        for dataset_acronym in dataset_acronyms:
            print("Processing", dataset_acronym)
            try:
                dataset = Dataset.objects.get(acronym=dataset_acronym)
            except ObjectDoesNotExist as e:
                print("Dataset '{}' not found.".format(dataset_acronym), e)
                continue

            for gloss in Gloss.objects.filter(lemma__dataset=dataset):

                if not consistent_senses(gloss, include_translations=True, allow_empty_language=True):
                    print('Inconsistent Senses for Gloss ID: ', gloss.id)


