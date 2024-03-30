"""Add affiliation to glosses appearing in CNGT corpus."""

from django.core.management.base import BaseCommand
from signbank.settings.server_specific import DEFAULT_DATASET_ACRONYM
from signbank.dictionary.models import Dataset, Gloss, GlossFrequency, Affiliation, AffiliatedGloss


class Command(BaseCommand):
    help = 'Add affiliation to corpus NGT glosses.'

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
            if dataset_acronym != DEFAULT_DATASET_ACRONYM:
                print("Command only available for ", DEFAULT_DATASET_ACRONYM)
                return

        dataset_NGT = Dataset.objects.get(acronym=DEFAULT_DATASET_ACRONYM)
        cngt_affiliation, created = Affiliation.objects.get_or_create(acronym='CNGT', name='Corpus CNGT')
        # Radboud Red: #B22E27
        dataset_glosses = Gloss.objects.filter(lemma__dataset=dataset_NGT)
        corpus_gloss_frequencies = GlossFrequency.objects.filter(gloss__lemma__dataset=dataset_NGT)
        for cgf in corpus_gloss_frequencies:
            corpus_gloss = cgf.gloss
            cngt_affiliated_gloss = AffiliatedGloss(affiliation=cngt_affiliation, gloss=corpus_gloss)
            cngt_affiliated_gloss.save()
        affiliation_glosses = AffiliatedGloss.obects.filter(affilation=cngt_affiliation)
        print('Affiliated glosses: '+str(affiliation_glosses.count()) + ' out of ', str(dataset_glosses.count()))

