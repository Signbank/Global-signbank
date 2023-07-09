from signbank.dictionary.models import *
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = 'make senses from gloss translations.'

    def add_arguments(self, parser):
        parser.add_argument('dataset_acronym', type=str)

    def handle(self, *args, **options):

        dataset_acronym = options['dataset_acronym']
        try:
            dataset = Dataset.objects.get(acronym=dataset_acronym)
        except ObjectDoesNotExist as e:
            print("Dataset '{}' not found.".format(dataset_acronym), e)
            return

        # see if there are already senses
        senses_for_dataset = GlossSense.objects.filter(gloss__lemma__dataset=dataset).count()
        if senses_for_dataset:
            print('Translations already mapped to senses for dataset ', dataset_acronym)
            return

        for gloss in Gloss.objects.filter(lemma__dataset=dataset):
            empty_translations = gloss.translation_set.filter(translation__text='')
            for trans in empty_translations:
                trans.delete()
