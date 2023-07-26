from signbank.dictionary.models import *
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = 'make senses from gloss translations.'

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

            # see if there are already senses
            senses_for_dataset = GlossSense.objects.filter(gloss__lemma__dataset=dataset).count()
            if senses_for_dataset:
                print('Translations already mapped to senses for dataset ', dataset_acronym)
                continue

            for gloss in Gloss.objects.filter(lemma__dataset=dataset):
                empty_translations = gloss.translation_set.filter(translation__text='')
                for trans in empty_translations:
                    trans.delete()
