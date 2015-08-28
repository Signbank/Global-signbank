from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from pages.models import Page
from pages.admin import PageAdmin

publisher_admin = AdminSite('pageadmin')
publisher_admin.register(Page, PageAdmin)
publisher_admin.register(User, UserAdmin)
