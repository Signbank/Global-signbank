from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from pages.models import Page
from pages.admin import PageAdmin

publisher_admin = AdminSite('pageadmin')
publisher_admin.register(Page, PageAdmin)
publisher_admin.register(User, UserAdmin)

def groups_part_of(self,obj):
    return ', '.join([group.name for group in obj.groups.all()])

def number_of_logins(self,obj):
    return obj.get_profile().number_of_logins

def expiry_date(self,obj):
    return obj.get_profile().expiry_date

UserAdmin.groups_part_of = groups_part_of
UserAdmin.number_of_logins = number_of_logins
UserAdmin.expiry_date = expiry_date

UserAdmin.list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'last_login', 'groups_part_of', 'number_of_logins','expiry_date')