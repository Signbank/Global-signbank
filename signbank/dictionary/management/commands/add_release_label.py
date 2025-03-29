"""Add a release label text to glosses"""

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from signbank.dictionary.models import Gloss, Dataset


class Command(BaseCommand):
    help = 'Add a release label text to glosses'

    def add_arguments(self, parser):
        parser.add_argument('release_label', nargs=1, type=str, help="The text to insert as release label")
        parser.add_argument('date_range', nargs=1, type=str,
                            help="Creation date range; format: YYYY-MM-DD,YYYY-MM-DD (use one date WITH comma for open "
                            "ended range")
        parser.add_argument('dataset_acronyms', nargs="+", type=str, help="One or more dataset acronyms")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace the current release label with the new one. By default the given text is appended.",
        )

    def handle(self, *args, **options):
        errors = []

        from_creation_date, until_creation_date = self.check_date_range(options, errors)
        dataset_acronyms = self.check_dataset_acronyms(options, errors)

        if errors:
            raise CommandError("\n" + "\n".join(errors))

        self.update_glosses(options['release_label'][0], dataset_acronyms, from_creation_date, until_creation_date,
                            options['replace'])

    def check_date_range(self, options, errors):
        date_range = options['date_range'][0].split(',')
        try:
            start = datetime.strptime(date_range[0], '%Y-%m-%d').date() if date_range[0] else None
            end = datetime.strptime(date_range[1], '%Y-%m-%d').date() if date_range[1] else None
            if start is None and end is None:
                errors.append("Either a start or an end date should be given")
        except ValueError as e:
            errors.append(str(e))
        return start, end

    def check_dataset_acronyms(self, options, errors):
        dataset_acronyms = options['dataset_acronyms']
        non_existing_datasets = [acronym for acronym in dataset_acronyms
                                 if not Dataset.objects.filter(acronym=acronym).exists()]
        if non_existing_datasets:
            errors.append(f"The following datasets do not exist: {', '.join(non_existing_datasets)}")
        return dataset_acronyms

    def update_glosses(self, release_label, dataset_acronyms, from_creation_date, until_creation_date, replace):
        glosses = Gloss.objects.filter(lemma__dataset__acronym__in=dataset_acronyms)
        if from_creation_date:
            glosses = glosses.filter(creationDate__gte=from_creation_date)
        if until_creation_date:
            glosses = glosses.filter(creationDate__lte=until_creation_date)
        print(f'Updating {glosses.count()} glosses... ', end='')
        for gloss in glosses:
            gloss.release_label = release_label if replace or not gloss.release_label \
                else f'{gloss.release_label} {release_label}'
        Gloss.objects.bulk_update(glosses, ['release_label'])
        print('Done')
