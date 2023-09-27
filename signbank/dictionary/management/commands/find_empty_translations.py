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
            empty_translations_for_dataset = GlossSense.objects.filter(
                gloss__lemma__dataset=dataset,
                gloss__translation__translation__text='').order_by(
                'gloss__id', 'order').distinct()
            if empty_translations_for_dataset.count():
                print('Empty translations found for dataset ', dataset_acronym)
                for glosssense_with_empty in empty_translations_for_dataset:
                    print(glosssense_with_empty.gloss, glosssense_with_empty.order, glosssense_with_empty.sense)
                    gloss_translations = glosssense_with_empty.gloss.translation_set.all()
                    for trans in gloss_translations:
                        if not trans.translation.text:
                            trans.delete()
                continue

