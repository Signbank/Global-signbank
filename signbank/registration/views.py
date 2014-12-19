"""
Views which allow users to create and activate accounts.

"""


from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from forms import RegistrationForm, EmailAuthenticationForm
from models import RegistrationProfile


def activate(request, activation_key, template_name='registration/activate.html'):
    """
    Activates a ``User``'s account, if their key is valid and hasn't
    expired.
    
    By default, uses the template ``registration/activate.html``; to
    change this, pass the name of a template as the keyword argument
    ``template_name``.
    
    Context:
    
        account
            The ``User`` object corresponding to the account, if the
            activation was successful. ``False`` if the activation was
            not successful.
    
        expiration_days
            The number of days for which activation keys stay valid
            after registration.
    
    Template:
    
        registration/activate.html or ``template_name`` keyword
        argument.
    
    """
    activation_key = activation_key.lower() # Normalize before trying anything with it.
    account = RegistrationProfile.objects.activate_user(activation_key)
    return render_to_response(template_name,
                              { 'account': account,
                                'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS },
                                context_instance=RequestContext(request))


def register(request, success_url='/accounts/register/complete/',
             form_class=RegistrationForm, profile_callback=None,
             template_name='registration/registration_form.html'):
    """
    Allows a new user to register an account.
    
    Following successful registration, redirects to either
    ``/accounts/register/complete/`` or, if supplied, the URL
    specified in the keyword argument ``success_url``.
    
    By default, ``registration.forms.RegistrationForm`` will be used
    as the registration form; to change this, pass a different form
    class as the ``form_class`` keyword argument. The form class you
    specify must have a method ``save`` which will create and return
    the new ``User``, and that method must accept the keyword argument
    ``profile_callback`` (see below).
    
    To enable creation of a site-specific user profile object for the
    new user, pass a function which will create the profile object as
    the keyword argument ``profile_callback``. See
    ``RegistrationManager.create_inactive_user`` in the file
    ``models.py`` for details on how to write this function.
    
    By default, uses the template
    ``registration/registration_form.html``; to change this, pass the
    name of a template as the keyword argument ``template_name``.
    
    Context:
    
        form
            The registration form.
    
    Template:
    
        registration/registration_form.html or ``template_name``
        keyword argument.
    
    """
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            new_user = form.save(profile_callback=profile_callback)
            return HttpResponseRedirect(success_url)
    else:
        form = form_class()
    return render_to_response(template_name,
                              { 'form': form },
                              context_instance=RequestContext(request))
                              

# a copy of the login view since we need to change the form to allow longer
# userids (> 30 chars) since we're using email addresses
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.views.decorators.cache import never_cache
from django.contrib.sites.models import Site, RequestSite


def mylogin(request, template_name='registration/login.html', redirect_field_name=REDIRECT_FIELD_NAME):
    "Displays the login form and handles the login action."
    
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if request.method == "POST":
        form = EmailAuthenticationForm(data=request.POST)
        if form.is_valid(): 
            # Light security check -- make sure redirect_to isn't garbage.
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            from django.contrib.auth import login
            login(request, form.get_user())
            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        form = EmailAuthenticationForm(request)
    request.session.set_test_cookie()
    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)
    return render_to_response(template_name, {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
        'allow_registration': settings.ALLOW_REGISTRATION,
    }, context_instance=RequestContext(request))
mylogin = never_cache(mylogin)
    
                              
