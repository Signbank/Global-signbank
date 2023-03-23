"""
URLConf for Django user registration.

Recommended usage is to use a call to ``include()`` in your project's
root URLConf to include this URLConf for any URL beginning with
'/accounts/'.

"""

from django.conf.urls import *
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from django.urls import re_path, path, include

# local imports
from signbank.registration.views import activate, register, mylogin, users_without_dataset, user_profile
from signbank.registration.forms import RegistrationForm

#It's weird that I have to set the correct success url by hand, but it doesn't work any other way
password_reset_view = auth_views.PasswordResetView
password_reset_view.success_url = reverse_lazy('registration:password_reset_done')
password_reset_confirm_view = auth_views.PasswordResetConfirmView
password_reset_confirm_view.success_url = reverse_lazy('registration:password_reset_complete')

# app_name = 'signbank'
app_name = 'registration'
urlpatterns = [
                       # Activation keys get matched by \w+ instead of the more specific
                       # [a-fA-F0-9]+ because a bad activation key should still get to the view;
                       # that way it can return a sensible "invalid key" message instead of a
                       # confusing 404.
                       re_path(r'^activate/(?P<activation_key>\w+)/$',
                           activate,
                           name='registration_activate'),
                       re_path(r'^login/$',
                           mylogin,
                           {'template_name': 'registration/login.html'},
                           name='login'),
                       re_path(r'^password/change/$',
                           auth_views.PasswordChangeView.as_view(),
                           name='auth_password_change'),
                       re_path(r'^password/change/done/$',
                           auth_views.PasswordChangeDoneView.as_view(),
                           name='auth_password_change_done'),
                       re_path(r'^password/reset/$',
                           password_reset_view.as_view(),
                           name='auth_password_reset'),
                       re_path(r'^password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           password_reset_confirm_view.as_view(),
                           name='password_reset_confirm'),
                       
                       re_path(r'^password/reset/complete/$',
                           auth_views.PasswordResetCompleteView.as_view(),
                           name='password_reset_complete'),

                       re_path(r'^password/reset/done/$',
                           auth_views.PasswordResetDoneView.as_view(),
                           name='password_reset_done'),

                       re_path(r'^register/$',
                           register,
                           name='register',
                           kwargs = {
                               'form_class': RegistrationForm,
                             },
                           ),

                       re_path(r'^register/complete/$',
                           TemplateView.as_view(template_name='registration/registration_complete.html'),
                           name='registration_complete'),

                        re_path(r'^users_without_dataset/$',users_without_dataset, name='users_without_dataset'),

                        re_path(r'^user_profile/$',user_profile, name='user_profile')
                       ]
