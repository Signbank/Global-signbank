from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from signbank.settings import base
from signbank.tools import get_users_without_dataset
from signbank.dictionary.models import Language

import getpass

class Command(BaseCommand):
	def create_dataset(self,first_question='Name of the dataset: '):
		dataset_name = input(first_question)

		#actually implement: create dataset with name
		
		print('Dataset',dataset_name,'created')
		print()
		
		print('Please specify which translation languages to use for this dataset, in the form of a comma separated list of 3 character language codes (https://en.wikipedia.org/wiki/ISO_639-3). For example: eng,nld,spa')
		
		possible_translation_languages = [(language.language_code_3char,language.name) for language in Language.objects.all()]
		
		if len(possible_translation_languages) > 0:			
			print('* Note: when using one of these codes, we will assume you want to reuse an existing translation language:',', '.join([language_code + ' ('+language_name+')' for language_code,language_name in possible_translation_languages]))

		translation_language_names = []
		for three_char_code in input().split(','):		
			three_char_code = three_char_code.strip()
			existing = Language.objects.filter(language_code_3char = three_char_code)
			
			if existing.first() == None:
				full_name = input('Full name for language '+three_char_code+' (for example "English"): ')
				two_char_code = input('The 2 characters code for language '+full_name+': ')
				
				translation_language = Language()
				translation_language.name = full_name
				translation_language.language_code_3char = three_char_code
				translation_language.language_code_2char = two_char_code
				
				#actually implement: save language
				
				print('Created new language',full_name)
			else:
				translation_language = existing.first()
				
			translation_language_names.append(translation_language.name)

		#actually implement: add translation languages to dataset
			
		if len(translation_language_names) == 1:
			print('Added ',translation_language_names[0],'as translation language to dataset '+dataset_name)
		
		elif len(translation_language_names) > 1:
			print('Added ',' and '.join(translation_language_names),'as translation languages to dataset '+dataset_name)
								
		print()

	def handle(self, *args, **options):

		print('This is a tool to prefill the database of a new Signbank installation. We will go through (1) user management, (2) data management and (3) interface subsequently. Note: none of the choices here are final, you can always change and extend things later; the goal of this tool is just to have a minimal version of Signbank working quickly. Hit enter to continue.')
		input()
		print()
		
		print('Step 1. User management')
		print('=======================')
		root_user_name = input('Name of the superuser: ')
		root_user_password = getpass.getpass('Password of the superuser: ')
		print('Superuser',root_user_name,'created');
		#actually implement: create root user
		print()
		
		if input('Create a user group for users that can edit the content in Signbank? [y/n]: ').lower() in ['y','yes']:
			editor_group_name = input('Name of this group (leave blank for \'Editor\'): ')
			if editor_group_name in ['',' ']:
				editor_group_name = 'Editor'
			#actually implement: create group
			print('Group',editor_group_name,'created')
		
		print()
				
		if input('Create a user group for users with only reading permissions? [y/n]: ').lower() in ['y','yes']:
			guest_group_name = input('Name of this group (leave blank for \'Guest\'): ')
			if guest_group_name in ['',' ']:
				guest_group_name = 'Guest'
			#actually implement: create group
			print('Group',guest_group_name,'created')

		print()
		print('Step 2. Data management')
		print('=======================')
		print('Glosses in Signbank are categorized into datasets. Each dataset can have separate permissions with separate viewing and editing permissions per users, as well as a separate copyright statements, ECVs, etc.')
		self.create_dataset(first_question='Name of first dataset (if only one dataset, this is the main dataset): ')

		while True:
			another = input('Do you want to create another dataset? [y/n]: ').lower() in ['yes','y']

			if not another:
				break
			
			self.create_dataset()
			
		print()
		print('In Signbank, glosses have various fields, like the phonological field "Location" indicating the position of the hands. The options for such a field (like "Face", "Chest", "Hip" etc for "Location") are configurable. This concept is called "Field choices".');
		if input('Do you want to start with a set of basic field choices for all fields? [y/n]: ').lower() in ['yes','y']:
			#Actually implement; import field choices
			print('Basic field choices created')
		print()
		
		print('Step 3. Interface preferences')
		print('=============================')
		if input('Create a menu item for adding new glosses? [y/n]: ').lower() in ['yes','y']:
			#Actually implement: add page
			print('Add new gloss page created')
		print()
		
		if input('Create a menu item for showing all glosses? [y/n]: ').lower() in ['yes','y']:			
			#Actually implement: add page
			print('Show all glosses page created')
		print()	
			
		if input('Create a menu item for showing recently added glosses? [y/n]: ').lower() in ['yes','y']:			
			#Actually implement: add page
			print('Show recent glosses page created')
		print()
			
		if input('Create a menu item to search glosses? [y/n]: ').lower() in ['yes','y']:			
			#Actually implement: add page
			print('Search page created')
		print()

		interface_language = input('Name of the first interface language (leave blank for English): ')
		if interface_language == '':
			interface_language = 'English'
		
		interface_language_code = input('Two character code for the first interface language (leave blank for en): ')
		if interface_language_code == '':
			interface_language_code = 'en'

		#Actually implement, create the interface language, run the sync_translation_fields command so Django-model-translation makes the database aware of them.		
		print('Interface language',interface_language,'created')
		print()
		
		while True:
			another = input('Create another interface language? [y/n]: ').lower() in ['yes','y']
		
			if not another:
				break
				
			interface_language = input('Interface language name (for example "French"): ')			
			interface_language_code = input('Interface language two character code (for example "fr"): ')

			print('Interface language',interface_language,'created')
			print()
			
			#Actually implement, create the interface language, run the sync_translation_fields command so Django-model-translation makes the database aware of them.