from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from signbank.settings import base
from signbank.tools import get_users_without_dataset
from signbank.dictionary.models import User

class Command(BaseCommand):
    help = 'Sends a list of all users without a dataset to an email addresss'

    def add_arguments(self, parser):
        parser.add_argument('address', type=str)

    def handle(self, *args, **options):

        users_without_dataset = User.objects.all()

        if len(users_without_dataset) == 0:
            return

        for user in users_without_dataset:
            if user.username not in ['susanodd', 'wessel', 'wesseltest',
                                     'AnonymousUser', 'DivyaKanekal', 'jetske', 'jetsketest',
                                     'micha', 'michatest']:
                user.delete()
