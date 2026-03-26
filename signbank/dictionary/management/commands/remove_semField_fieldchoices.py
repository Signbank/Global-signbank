from django.core.management import BaseCommand
from signbank.dictionary.models import FieldChoice


class Command(BaseCommand):
    help = "Remove obsolete field='SemField' objects from FieldChoice."

    def handle(self, *args, **options):

        field_choices_for_handshape = FieldChoice.objects.filter(field__exact='SemField')

        if field_choices_for_handshape.count() == 0:
            print('No objects found matching query')
            return

        for fc in field_choices_for_handshape:
            print("Remove FieldChoice object with field='SemField', machine_value=", fc.machine_value, ", name=", fc.name)
            fc.delete()
