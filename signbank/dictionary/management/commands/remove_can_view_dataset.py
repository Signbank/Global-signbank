from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from guardian.models import UserObjectPermission, GroupObjectPermission


class Command(BaseCommand):
     
    help = 'Remove can_view_dataset permission after copying them to view_dataset permission'
    args = ''

    def handle(self, *args, **options):
        view_dataset_perm = Permission.objects.get(codename='view_dataset')
        can_view_dataset_perm = Permission.objects.get(codename='can_view_dataset')

        # User - Permission
        for user in User.objects.filter(user_permissions=can_view_dataset_perm)\
                .exclude(user_permissions=view_dataset_perm):
            user.user_permissions.add(view_dataset_perm)
            print(f'Added {view_dataset_perm} to {user}')

        # Group - Permission
        for group in Group.objects.filter(permissions=can_view_dataset_perm)\
                .exclude(permissions=view_dataset_perm):
            group.group_permissions.add(view_dataset_perm)
            print(f'Added {view_dataset_perm} to {group}')
            
        # User - Object - Permission (Guardian)
        for user_obj_perm in UserObjectPermission.objects.filter(permission=can_view_dataset_perm)\
                .exclude(permission=view_dataset_perm).values():
            del user_obj_perm['id']
            user_obj_perm['permission_id'] = view_dataset_perm.id
            new_user_obj_perm, created = UserObjectPermission.objects.get_or_create(**user_obj_perm)
            if created:
                print(f'UserObjectPermission created: {new_user_obj_perm}')
            
        # Group - Object - Permission (Guardian)
        for group_obj_perm in GroupObjectPermission.objects.filter(permission=can_view_dataset_perm)\
                .exclude(permission=view_dataset_perm).values():
            del group_obj_perm['id']
            group_obj_perm['permission_id'] = view_dataset_perm.id
            new_group_obj_perm, created = GroupObjectPermission.objects.get_or_create(**group_obj_perm)
            if created:
                print(f'GroupObjectPermission created: {new_group_obj_perm}')

        # Remove the can_view_datset permission
        can_view_dataset_perm.delete()

        # Rename the view_dataset permission
        view_dataset_perm.name = 'Can view dataset'
        view_dataset_perm.save()
