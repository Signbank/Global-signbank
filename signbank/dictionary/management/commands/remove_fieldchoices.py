from django.core.management import BaseCommand
from signbank.dictionary.models import FieldChoice


class Command(BaseCommand):
    help = "Remove obsolete FieldChoice objects for a given field category."

    def add_arguments(self, parser):
        parser.add_argument(
            'fieldchoice_name',
            nargs='+',
            type=str,
            help="One or more FieldChoice field category names to remove (e.g. Handshape derivHist SemField).",
        )

    def handle(self, *args, **options):
        for fieldchoice_name in options['fieldchoice_name']:
            field_choices = FieldChoice.objects.filter(field__exact=fieldchoice_name)

            if field_choices.count() == 0:
                self.stdout.write(f"No objects found for field='{fieldchoice_name}'")
                continue

            self.stdout.write(f"The following FieldChoice objects with field='{fieldchoice_name}' will be deleted:")
            for fc in field_choices:
                self.stdout.write(f"  machine_value={fc.machine_value}, name={fc.name}")

            self.stdout.write("Confirm deletion? [yes/no]: ", ending='')
            self.stdout.flush()
            confirmation = self.stdin.readline().strip()
            if confirmation.lower() != 'yes':
                self.stdout.write("Deletion cancelled.")
                continue

            field_choices.delete()
            self.stdout.write(f"Deleted all FieldChoice objects for field='{fieldchoice_name}'.")
