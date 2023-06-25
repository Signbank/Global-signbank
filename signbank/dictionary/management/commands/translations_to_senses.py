from signbank.dictionary.models import *
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = 'make senses from gloss translations.'

    def add_arguments(self, parser):
        parser.add_argument('dataset_acronym', type=str)

    def handle(self, *args, **options):
        dataset = Dataset.objects.get(acronym=options['dataset_acronym'])
        
        for gloss in Gloss.objects.filter(lemma__dataset=dataset):
            non_empty_translations = gloss.translation_set.all().exclude(translation__text='')
            if not non_empty_translations:
                continue
            gloss_translations = gloss.translation_set.all().order_by('orderIndex', 'index')
            # determine the sense numbers
            orderIndices = list(set([gti.orderIndex for gti in gloss_translations]))
            for oi in orderIndices:
                sense_for_gloss = Sense(dataset=dataset)
                sense_for_gloss.save()
                glosssense = GlossSense(gloss=gloss, sense=sense_for_gloss, order=oi)
                glosssense.save()
                translation_lookup = dict()
                for dataset_language in dataset.translation_languages.all():
                    glosssenselanguage = SenseTranslation(language=dataset_language)
                    glosssenselanguage.save()
                    translation_lookup[dataset_language] = glosssenselanguage
                gloss_translations_order = gloss_translations.filter(orderIndex=oi).order_by('index')
                for gto in gloss_translations_order:
                    translation_lookup[gto.language].translations.add(gto)
                for dataset_language in dataset.translation_languages.all():
                    sense_for_gloss.senseTranslations.add(translation_lookup[dataset_language])

