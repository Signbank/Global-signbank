from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from signbank.settings import base
from signbank.tools import get_users_without_dataset

class Command(BaseCommand):
	def handle(self, *args, **options):

		print('This is a tool to prefill the database of a new Signbank installation. We will go through (1) user management, (2) data management and (3) interface subsequently. Hit enter to continue.')
		input()
		print()
		
		print('Step 1. User management')
		print('=======================')
		print('Name of the superuser')
		root_user_name = input()
		print('Password of the superuser')
		root_user_password = input()
		print('Root user created');

		print('Create a user group for users that can edit the content in Signbank? y/n')
		if input().lower() in ['y','yes']:
			print('Name of this group (leave blank for \'Editor\')')
			editor_group_name = input()
			if editor_group_name in ['',' ']:
				editor_group_name = 'Editor'
		print('Group',editor_group_name,'created')
				
		print('Create a user group for users with only reading permissions? y/n')
		if input().lower() in ['y','yes']:
			print('Name of this group (leave blank for \'Guest\')')
			guest_group_name = input()
			if guest_group_name in ['',' ']:
				guest_group_name = 'Guest'
		print('Group',guest_group_name,'created')

		print()
		print('Step 2. Data management')
		print('=======================')
		print('Glosses in Signbank are categorized into datasets. Each dataset can have separate permissions with separate viewing and editing permissions per users, as well as a separate copyright statements, ECVs, etc.')
		print('Name of first dataset (if only one dataset: the main dataset)')
		first_dataset_name = input()
		print('Dataset created')

		print('Do you want to create another dataset? y/n')
		another = input().lower() in ['yes','y']
		while another:
			print('Name of dataset:')
			dataset_name = input()
			print('Dataset created')
			print('Do you want to create another dataset? y/n')
			another = input().lower() in ['yes','y']
		
		#Still missing: translation languages
		
		print()
		print('Step 3. Interface preferences')
		print('=============================')
		print('Create a menu item for adding new glosses? y/n')
		if input().lower() in ['yes','y']:
			print('Add new gloss page created')
		
		print('Create a menu item for showing all glosses? y/n')
		if input().lower() in ['yes','y']:			
			print('Show all glosses page created')

		print('Create a menu item for showing recently added glosses? y/n')
		if input().lower() in ['yes','y']:			
			print('Show recent glosses page created')

		print('Create a menu item to search glosses? y/n')
		if input().lower() in ['yes','y']:			
			print('Search page created')
			
		#Still missing: interface languages
