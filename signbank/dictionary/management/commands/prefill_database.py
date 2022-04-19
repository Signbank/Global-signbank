import getpass
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core import management
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from signbank.dictionary.models import Dataset, Language, SignLanguage
from signbank.settings import base
from signbank.tools import get_users_without_dataset


class Command(BaseCommand):
    @transaction.atomic
    def create_dataset(self, first_question='Name of the dataset: '):
        dataset_name = input(first_question)
        dataset_acronym = input(
            "What acronym should be used to identify this dataset: ")

        print('Dataset', dataset_name, 'created')
        print()

        sign_language_name = input("Name of the sign language: ")

        print('Please specify which translation languages to use for this dataset, in the form of a comma separated list of 3 character language codes (https://en.wikipedia.org/wiki/ISO_639-3). For example: eng,nld,spa')

        possible_translation_languages = [
            (language.language_code_3char, language.name) for language in Language.objects.all()]

        if len(possible_translation_languages) > 0:
            print('* Note: when using one of these codes, we will assume you want to reuse an existing translation language:',
                  ', '.join([language_code + ' ('+language_name+')' for language_code, language_name in possible_translation_languages]))

        translation_languages = []
        for three_char_code in input().split(','):
            three_char_code = three_char_code.strip()
            existing = Language.objects.filter(
                language_code_3char=three_char_code)

            if existing.first() == None:
                full_name = input('Full name for language ' +
                                  three_char_code+' (for example "English"): ')
                two_char_code = input(
                    'The 2 characters code for language '+full_name+': ')

                translation_language = Language()
                translation_language.name = full_name
                translation_language.language_code_3char = three_char_code
                translation_language.language_code_2char = two_char_code
                translation_language.save()

                print('Created new language', full_name)
            else:
                translation_language = existing.first()

            translation_languages.append(translation_language)

        # actually implement: add translation languages to dataset
        sign_language, _created = SignLanguage.objects.get_or_create(
            name=sign_language_name)
        dataset = Dataset()
        dataset.acronym = dataset_acronym
        dataset.name = dataset_name
        dataset.is_public = True
        dataset.default_language = translation_languages[0]
        dataset.signlanguage = sign_language
        dataset.save()

        dataset.translation_languages = translation_languages
        dataset.owners = [User.objects.first()]
        dataset.save()

        if len(translation_languages) == 1:
            print('Added ', translation_languages[0].name,
                  'as translation language to dataset '+dataset_name)

        elif len(translation_languages) > 1:
            print('Added ', ' and '.join([lang.name for lang in translation_languages]),
                  'as translation languages to dataset '+dataset_name)

        print()

    def handle(self, *args, **options):

        print('This is a tool to prefill the database of a new Signbank installation. We will go through (1) user management, (2) data management and (3) interface subsequently. Note: none of the choices here are final, you can always change and extend things later; the goal of this tool is just to have a minimal version of Signbank working quickly. Hit enter to continue.')
        input()
        print()

        print('Step 1. User management')
        print('=======================')
        root_user_name = os.getenv("DJANGO_SUPERUSER_USERNAME") or input(
            'Username of the superuser: ')
        root_user_email = os.getenv("DJANGO_SUPERUSER_EMAIL") or input(
            'Email of the superuser: ')
        root_user_password = os.getenv("DJANGO_SUPERUSER_PASSWORD") or getpass.getpass(
            'Password of the superuser: ')

        User.objects.count() == 0 and User.objects.create_superuser(
            root_user_name, root_user_email, root_user_password)
        print('Superuser', root_user_name, 'created')
        print()

        if input('Create base groups and permissions ? [y/n]: ').lower() in ['y', 'yes']:
            management.call_command('permissions', create_users=False)
            print('Groups and permissions created')

        print()

        if input('The registration functionality requires an extra table in the database. Do want to add this table? [y/n]: ').lower() in ['y', 'yes']:
            print('Registration profile table created')

        print()
        print('Step 2. Data management')
        print('=======================')
        print('A default Signbank writable folder has a folder for videos, images, other media, ecv files, Signbank packages and logs. Create it?')
        if input('Create it? [y/n]: ').lower() in ['y', 'yes']:

            folders = ['glossimage', 'glossvideo',
                       'ecv', 'packages', 'logs', 'othermedia']

            # actually implement: create writable folder
            for folder in folders:
                if not os.path.exists(settings.MEDIA_ROOT+folder):
                    os.makedirs(settings.MEDIA_ROOT + folder)
            print('Writable folder created')

        print()

        print('Glosses in Signbank are categorized into datasets. Each dataset can have separate permissions with separate viewing and editing permissions per users, as well as a separate copyright statements, ECVs, etc.')
        self.create_dataset(
            first_question='Name of first dataset (if only one dataset, this is the main dataset): ')

        while True:
            another = input(
                'Do you want to create another dataset? [y/n]: ').lower() in ['yes', 'y']

            if not another:
                break

            self.create_dataset()

        print()
        print('In Signbank, glosses have various fields, like the phonological field "Location" indicating the position of the hands. The options for such a field (like "Face", "Chest", "Hip" etc for "Location") are configurable. This concept is called "Field choices".')
        if input('Do you want to start with a set of basic field choices for all fields? [y/n]: ').lower() in ['yes', 'y']:
            # Actually implement; import field choices
            print('Basic field choices created')
        print()

        print('Step 3. Interface preferences')
        print('=============================')
        if input('Create a menu item for adding new glosses? [y/n]: ').lower() in ['yes', 'y']:
            # Actually implement: add page
            print('Add new gloss page created')
        print()

        if input('Create a menu item for showing all glosses? [y/n]: ').lower() in ['yes', 'y']:
            # Actually implement: add page
            print('Show all glosses page created')
        print()

        if input('Create a menu item for showing recently added glosses? [y/n]: ').lower() in ['yes', 'y']:
            # Actually implement: add page
            print('Show recent glosses page created')
        print()

        if input('Create a menu item to search glosses? [y/n]: ').lower() in ['yes', 'y']:
            # Actually implement: add page
            print('Search page created')
        print()

        interface_language = input(
            'Name of the first interface language (leave blank for English): ')
        if interface_language == '':
            interface_language = 'English'

        interface_language_code = input(
            'Two character code for the first interface language (leave blank for en): ')
        if interface_language_code == '':
            interface_language_code = 'en'

        # Actually implement, create the interface language, run the sync_translation_fields command so Django-model-translation makes the database aware of them.
        print('Interface language', interface_language, 'created')
        print()

        while True:
            another = input(
                'Create another interface language? [y/n]: ').lower() in ['yes', 'y']

            if not another:
                break

            interface_language = input(
                'Interface language name (for example "French"): ')
            interface_language_code = input(
                'Interface language two character code (for example "fr"): ')

            print('Interface language', interface_language, 'created')
            print()

            # Actually implement, create the interface language, run the sync_translation_fields command so Django-model-translation makes the database aware of them.
