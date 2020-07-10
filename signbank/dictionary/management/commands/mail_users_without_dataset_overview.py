from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from signbank.settings import base
from signbank.tools import get_users_without_dataset

class Command(BaseCommand):
    help = 'Sends a list of all users without a dataset to an email addresss'

    def add_arguments(self, parser):
        parser.add_argument('address', type=str)

    def handle(self, *args, **options):

        users_without_dataset = get_users_without_dataset()

        if len(users_without_dataset) == 0:
            return

        text = 'Active Signbank users without dataset access\n\n'
        text += '\n'.join([user.first_name + ' ' + user.last_name + ' (' + user.email + ')' for user in users_without_dataset])

        text += '\n See '+base.URL+'accounts/users_without_dataset/'

        send_mail('Active Signbank users without dataset access',text, 'test',[options['address']])