"""Add affiliation to glosses based on creator."""

from django.core.management.base import BaseCommand
from signbank.dictionary.models import *


class Command(BaseCommand):
    help = 'Add affiliation to glosses based on that of creator.'

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

            radboud, created = Affiliation.objects.get_or_create(acronym='Radboud')
            dataset_glosses = Gloss.objects.filter(lemma__dataset=dataset).distinct()

            for gloss in dataset_glosses:
                if not gloss.creator.all():
                    # original glosses have no creator
                    # at that time all glosses were Radboud glosses
                    new_affiliation, created = AffiliatedGloss.objects.get_or_create(affiliation=radboud,
                                                                                     gloss=gloss)
                else:
                    creator = gloss.creator.first()
                    user_affiliations = AffiliatedUser.objects.filter(user=creator)
                    if user_affiliations.count() > 0:
                        for ua in user_affiliations:
                            new_affiliation, created = AffiliatedGloss.objects.get_or_create(affiliation=ua.affiliation,
                                                                                             gloss=gloss)
