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

# local imports
from signbank.registration.views import activate, register, mylogin
from signbank.registration.forms import RegistrationForm

#It's weird that I have to set the correct success url by hand, but it doesn't work any other way
password_reset_view = auth_views.PasswordResetView
password_reset_view.success_url = reverse_lazy('registration:password_reset_done')
password_reset_confirm_view = auth_views.PasswordResetConfirmView
password_reset_confirm_view.success_url = reverse_lazy('registration:password_reset_complete')

app_name = 'signbank'

urlpatterns = [
                       # Activation keys get matched by \w+ instead of the more specific
                       # [a-fA-F0-9]+ because a bad activation key should still get to the view;
                       # that way it can return a sensible "invalid key" message instead of a
                       # confusing 404.
                       url(r'^activate/(?P<activation_key>\w+)/$',
                           activate,
                           name='registration_activate'),
                       url(r'^login/$',
                           mylogin,
                           {'template_name': 'registration/login.html'},
                           name='auth_login'),
                       url(r'^logout/$',
                           auth_views.logout,
                           {'template_name': 'registration/logout.html'},
                           name='auth_logout'),
                       url(r'^password/change/$',
                           auth_views.PasswordChangeView.as_view(),
                           name='auth_password_change'),
                       url(r'^password/change/done/$',
                           auth_views.PasswordChangeDoneView.as_view(),
                           name='auth_password_change_done'),
                       url(r'^password/reset/$',
                           password_reset_view.as_view(),
                           name='auth_password_reset'),
                       url(r'^password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           password_reset_confirm_view.as_view(),
                           name='password_reset_confirm'),
                       
                       url(r'^password/reset/complete/$',
                           auth_views.PasswordResetCompleteView.as_view(),
                           name='password_reset_complete'),

                       url(r'^password/reset/done/$',
                           auth_views.PasswordResetDoneView.as_view(),
                           name='password_reset_done'),

                       
                       url(r'^register/$',
                           register,
                           name='registration_register',
                           kwargs = {
                               'form_class': RegistrationForm,
                             },
                           ),

                           
                       url(r'^register/complete/$',
                           TemplateView.as_view(template_name='registration/registration_complete.html'),
                           name='registration_complete'),
                       ]
