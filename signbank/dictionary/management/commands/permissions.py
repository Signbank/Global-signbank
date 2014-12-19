"""Set up default groups and permissions"""

from django.core.management.base import BaseCommand, CommandError  
from signbank.dictionary.models import Gloss
from django.contrib.auth.models import User, Group, Permission

change_gloss = Permission.objects.get(codename='change_gloss', content_type__model__exact='gloss')
advanced_search = Permission.objects.get(codename='search_gloss', content_type__model__exact='gloss')
view_adv_properties = Permission.objects.get(codename='view_advanced_properties', content_type__model__exact='gloss')
export_csv = Permission.objects.get(codename='export_csv', content_type__model__exact='gloss')
add_video = Permission.objects.get(codename='update_video', content_type__model__exact='gloss')
create_signs = Permission.objects.get(codename='add_gloss', content_type__model__exact='gloss')
publish = Permission.objects.get(codename='can_publish', content_type__model__exact='gloss')
delete_unpublished = Permission.objects.get(codename='can_delete_unpublished', content_type__model__exact='gloss')
delete_published = Permission.objects.get(codename='can_delete_published', content_type__model__exact='gloss')
view_interp_note = Permission.objects.get(codename='view_interpreterfeedback', content_type__model__exact='interpreterfeedback')
create_interp_note = Permission.objects.get(codename='add_interpreterfeedback', content_type__model__exact='interpreterfeedback')
delete_interp_note = Permission.objects.get(codename='delete_interpreterfeedback', content_type__model__exact='interpreterfeedback')
delete_gen_feedback = Permission.objects.get(codename='delete_generalfeedback', content_type__model__exact='generalfeedback')
change_page = Permission.objects.get(codename='change_page', content_type__model__exact='page')
add_page = Permission.objects.get(codename='add_page', content_type__model__exact='page')
add_attachment = Permission.objects.get(codename='add_attachment', content_type__app_label__exact='attachments')



class Command(BaseCommand):
     
    help = 'set up default groups and permissions'
    args = ''

    def handle(self, *args, **options):

        
            # Publisher
            publisher, created = Group.objects.get_or_create(name='Publisher')
            publisher.permissions.add(advanced_search)
            publisher.permissions.add(view_adv_properties)
            publisher.permissions.add(export_csv)
            publisher.permissions.add(change_gloss)
            publisher.permissions.add(add_video)
            publisher.permissions.add(create_signs)
            publisher.permissions.add(publish)
            publisher.permissions.add(delete_unpublished)
            publisher.permissions.add(delete_published)
            publisher.permissions.add(view_interp_note)
            publisher.permissions.add(create_interp_note)
            publisher.permissions.add(delete_interp_note)
            publisher.permissions.add(delete_gen_feedback)
            publisher.permissions.add(change_page)
            publisher.permissions.add(add_page)
            publisher.permissions.add(add_attachment)
            

            
            # Editor
            editor, created = Group.objects.get_or_create(name='Editor')
            editor.permissions.add(advanced_search)
            editor.permissions.add(change_gloss)
            editor.permissions.add(view_adv_properties)
            editor.permissions.add(export_csv)
            editor.permissions.add(add_video)
            editor.permissions.add(create_signs)
            editor.permissions.add(delete_unpublished)
            editor.permissions.add(view_interp_note)
            editor.permissions.add(create_interp_note)
            editor.permissions.add(delete_interp_note)
            editor.permissions.add(delete_gen_feedback)

            
            # Interpreter
            interpreter, created = Group.objects.get_or_create(name='Interpreter')
            interpreter.permissions.add(advanced_search)
            interpreter.permissions.add(view_adv_properties)
            interpreter.permissions.add(export_csv)
            interpreter.permissions.add(view_interp_note)
            interpreter.permissions.add(create_interp_note)
            
            
            # Interpreter Supervisor
            supervisor, created = Group.objects.get_or_create(name='Interpreter Supervisor')
            supervisor.permissions.add(advanced_search)
            supervisor.permissions.add(view_adv_properties)
            supervisor.permissions.add(export_csv)
            supervisor.permissions.add(view_interp_note)
            supervisor.permissions.add(create_interp_note)
            supervisor.permissions.add(delete_interp_note)
            
            
            # Researcher
            researcher, created = Group.objects.get_or_create(name='Researcher')
            researcher.permissions.add(advanced_search)
            researcher.permissions.add(view_adv_properties)
            researcher.permissions.add(export_csv)
            
            # Observer
            observer, created = Group.objects.get_or_create(name='Observer')
            observer.permissions.add(advanced_search)
            observer.permissions.add(view_adv_properties)
            
            
            # Public
            public, created = Group.objects.get_or_create(name='Public')
            
            
            
            # create sample users if we don't have them already
            if len(User.objects.filter(username='publisher')) == 0:
            
                # create some sample users            
                peter = User.objects.create_user('publisher', 'example@example.com', 'publisher', first_name='Peter', last_name='Publisher')
                eric = User.objects.create_user('editor', 'example@example.com', 'editor', first_name='Eric', last_name='Editor')
                ian = User.objects.create_user('interpreter', 'example@example.com', 'interpreter', first_name='Ian', last_name='Interpreter')
                boss = User.objects.create_user('boss', 'example@example.com', 'boss', first_name='Interpreter', last_name='Boss')
                roger = User.objects.create_user('researcher', 'example@example.com', 'researcher', first_name='Roger', last_name='Researcher')
                olive = User.objects.create_user('observer', 'example@example.com', 'observer', first_name='Olive', last_name='Observer')
                public = User.objects.create_user('public', 'example@example.com', 'public', first_name='Pamela', last_name='Public')
            
        
                peter.groups.add(publisher)
                eric.groups.add(editor)
                ian.groups.add(interpreter)
                boss.groups.add(supervisor)
                roger.groups.add(researcher)
                olive.groups.add(observer)
            
            