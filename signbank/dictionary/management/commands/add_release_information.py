"""Add a release information text to glosses"""

from datetime import datetime
from dataclasses import dataclass
from django.core.management.base import BaseCommand, CommandError
from signbank.dictionary.models import Gloss, Dataset


@dataclass
class GlossFilterValues:
    dataset_acronyms: list[str]
    from_creation_date: datetime.date
    until_creation_date: datetime.date
    affiliations: list[str]


class Command(BaseCommand):
    help = 'Add a release information text to glosses'

    def add_arguments(self, parser):
        parser.add_argument('release_information', nargs=1, type=str, help="The text to insert as release information")
        parser.add_argument('date_range', nargs=1, type=str,
                            help="Creation date range; format: YYYY-MM-DD,YYYY-MM-DD (use one date WITH comma for open "
                            "ended range")
        parser.add_argument('affiliations', nargs=1, type=str,
                            help="Comma separated list of affiliation names")
        parser.add_argument('dataset_acronyms', nargs="+", type=str, help="One or more dataset acronyms")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace the current release information with the new one. By default the given text is appended.",
        )

    def handle(self, *args, **options):
        errors = []

        gloss_filter_values = GlossFilterValues(
            self.get_dataset_acronyms(options, errors),
            *self.get_date_range(options, errors),
            options['affiliations'][0].split(',')
        )

        if errors:
            raise CommandError("\n" + "\n".join(errors))

        self.update_glosses(options['release_information'][0], gloss_filter_values, options['replace'])

    def get_date_range(self, options, errors):
        """
        Checks whether `options` has one or two correct dates to construct a range and returns that range
        """
        date_range = options['date_range'][0].split(',')
        try:
            start = datetime.strptime(date_range[0], '%Y-%m-%d').date() if date_range[0] else None
            end = datetime.strptime(date_range[1], '%Y-%m-%d').date() if date_range[1] else None
            if start is None and end is None:
                errors.append("Either a start or an end date should be given")
        except ValueError as e:
            errors.append(str(e))
            return None, None
        return start, end

    def get_dataset_acronyms(self, options, errors):
        """
        Checks for non existent Datasets and returns only existing Datasets
        """
        dataset_acronyms = options['dataset_acronyms']
        existing_dataset_acronyms = list(Dataset.objects.filter(acronym__in=dataset_acronyms)
                                         .values_list('acronym', flat=True))
        non_existing_dataset_acronyms = list(set(dataset_acronyms) - set(existing_dataset_acronyms))
        if non_existing_dataset_acronyms:
            errors.append(f"The following datasets do not exist: {', '.join(non_existing_dataset_acronyms)}")
        return existing_dataset_acronyms

    def update_glosses(self, release_information, gloss_filter_values, replace):
        """
        Updates the release_information field of glosses filtered by a GlossFilterValue instance
        """
        glosses = Gloss.objects.filter(lemma__dataset__acronym__in=gloss_filter_values.dataset_acronyms)
        if date := gloss_filter_values.from_creation_date:
            glosses = glosses.filter(creationDate__gte=date)
        if date := gloss_filter_values.until_creation_date:
            glosses = glosses.filter(creationDate__lte=date)
        if affiliations := gloss_filter_values.affiliations:
            glosses = glosses.filter(affiliation_corpus_contains__affiliation__name__in=affiliations)
        print(f'Updating {glosses.count()} glosses... ', end='')
        for gloss in glosses:
            gloss.release_information = release_information if replace or not gloss.release_information \
                else f'{gloss.release_information} {release_information}'
        Gloss.objects.bulk_update(glosses, ['release_information'])
        print('Done')
