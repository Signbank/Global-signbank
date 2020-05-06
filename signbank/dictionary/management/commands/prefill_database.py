from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from signbank.settings import base
from signbank.tools import get_users_without_dataset
from signbank.dictionary.models import Language

class Command(BaseCommand):
	def create_dataset(self,first_question='Name of the dataset: '):
		dataset_name = input(first_question)
		print('Dataset',dataset_name,'created')
		print()
		
		print('Please specify which translation languages to use for this dataset, in the form of a comma separated list of 3 character language codes (https://en.wikipedia.org/wiki/ISO_639-3). For example: eng,nld,spa')
		
		possible_translation_languages = [(language.language_code_3char,language.name) for language in Language.objects.all()]
		
		if len(possible_translation_languages) > 0:			
			print('When using one of these codes, we will assume you want to reuse an existing translation language:',', '.join([language_code + ' ('+language_name+')' for language_code,language_name in possible_translation_languages]))

		translation_language_names = []
		for lang in input().split(','):		
			lang = lang.strip()
			existing = Language.objects.get(language_code_3char = lang)
			
			if existing == None: #TODO: this does not work
				full_name = input('Full name for language',new_language,' (for example "English"): ')
				two_char_code = input('The 2 char code for language',new_language,': ')

			translation_language_names.append(existing.name)
				
		print('Added ',' and '.join(translation_language_names),'as translation languages to dataset '+dataset_name)
								
		print()

	def handle(self, *args, **options):

		print('This is a tool to prefill the database of a new Signbank installation. We will go through (1) user management, (2) data management and (3) interface subsequently. Hit enter to continue.')
		input()
		print()
		
		print('Step 1. User management')
		print('=======================')
		root_user_name = input('Name of the superuser: ')
		root_user_password = input('Password of the superuser: ')
		print('Superuser',root_user_name,'created');
		print()
		
		if input('Create a user group for users that can edit the content in Signbank? [y/n]: ').lower() in ['y','yes']:
			editor_group_name = input('Name of this group (leave blank for \'Editor\'): ')
			if editor_group_name in ['',' ']:
				editor_group_name = 'Editor'
			print('Group',editor_group_name,'created')
		print()
				
		if input('Create a user group for users with only reading permissions? [y/n]: ').lower() in ['y','yes']:
			guest_group_name = input('Name of this group (leave blank for \'Guest\'): ')
			if guest_group_name in ['',' ']:
				guest_group_name = 'Guest'
			print('Group',guest_group_name,'created')

		print()
		print('Step 2. Data management')
		print('=======================')
		print('Glosses in Signbank are categorized into datasets. Each dataset can have separate permissions with separate viewing and editing permissions per users, as well as a separate copyright statements, ECVs, etc.')
		self.create_dataset(first_question='Name of first dataset (if only one dataset, this is the main dataset): ')

		another = input('Do you want to create another dataset? [y/n]: ').lower() in ['yes','y']
		while another:
				
			self.create_dataset()
			another = input('Do you want to create another dataset? [y/n]: ').lower() in ['yes','y']
			
		print()
		print('Step 3. Interface preferences')
		print('=============================')
		if input('Create a menu item for adding new glosses? [y/n]: ').lower() in ['yes','y']:
			print('Add new gloss page created')
		print()
		
		if input('Create a menu item for showing all glosses? [y/n]: ').lower() in ['yes','y']:			
			print('Show all glosses page created')
		print()	
			
		if input('Create a menu item for showing recently added glosses? [y/n]: ').lower() in ['yes','y']:			
			print('Show recent glosses page created')
		print()
			
		if input('Create a menu item to search glosses? [y/n]: ').lower() in ['yes','y']:			
			print('Search page created')
		print()

		interface_language = input('Name of the first interface language (leave blank for English): ')
		if interface_language == '':
			interface_language = 'English'
		
		interface_language_code = input('Two character code for the first interface language (leave blank for en): ')
		if interface_language_code == '':
			interface_language_code = 'en'
		
		print('Interface language',interface_language,'created')
		print()
		
		another = input('Create another interface language? [y/n]: ').lower() in ['yes','y']
		
		#Hier gebleven
		#while another:
		#	another = input('Create a menu item for showing all glosses? [y/n]: ').lower() in ['yes','y']:			
				#print()
