from django.core.management.base import BaseCommand
from signbank.dictionary.models import User, UserProfile

class Command(BaseCommand):

    help = 'remove users except for development'
    args = ''

    def handle(self, *args, **options):

        all_users = User.objects.all().distinct()
        if not all_users.count():
            return

        for user in all_users:

            if user.username not in ['susanodd', 'wessel', 'AnonymousUser',
                                     'DivyaKanekal', 'jetske',
                                     'micha']:

                userprofile = UserProfile.objects.filter(user=user)
                if userprofile:
                    userprofile.delete()
                user.delete()
