"""
Forms and validation code for user registration.

"""

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.conf import settings
from signbank.settings.server_specific import *
from django.utils.safestring import mark_safe
from django.utils.functional import lazy
from django.utils import six
from django.db.utils import OperationalError, ProgrammingError

mark_safe_lazy = lazy(mark_safe, six.text_type)

from signbank.registration.models import RegistrationProfile, UserProfile

from signbank.dictionary.models import Dataset
from django_select2 import *
from easy_select2.widgets import Select2, Select2Multiple

import re
alnum_re = re.compile(r'^\w+$')


# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary. If/when Django ticket #3515
# lands in trunk, this will no longer be necessary.
attrs_reqd = { 'class': 'required form-control' }
attrs_default = {'class': 'form-control'}

class RegistrationForm(forms.Form):
    """
    Form for registering a new user account.

    Validates that the request username is not already in use, and
    requires the password to be entered twice to catch typos.

    Subclasses should feel free to add any additional validation they
    need, but should either preserve the base ``save()`` or implement
    a ``save()`` which accepts the ``profile_callback`` keyword
    argument and passes it through to
    ``RegistrationProfile.objects.create_inactive_user()``.

    """
    error_css_class = 'error'

    username = forms.CharField(max_length=30, required=True,
                               widget=forms.TextInput(attrs=attrs_reqd),
                               label=_(u'Username'))
    first_name = forms.CharField(max_length=30, required=True,
                               widget=forms.TextInput(attrs=attrs_reqd),
                               label=_(u'First Name'))
    last_name = forms.CharField(max_length=30, required=True,
                                 widget=forms.TextInput(attrs=attrs_reqd),
                                 label=_(u'Last Name'))
    email = forms.EmailField(widget=forms.TextInput(attrs=attrs_reqd), required=True,
                             label=_(u'Your Email Address'))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_reqd), required=True,
                                label=_(u'Password'))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_reqd),
                                label=_(u'Password (again)'))

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:

        try:
            dataset_choices = [ (ds.name, ds.name) for ds in Dataset.objects.filter(is_public='1') ]

            if not dataset_choices:
                dataset_choices = [(ds.name, ds.name) for ds in Dataset.objects.filter(acronym=settings.DEFAULT_DATASET_ACRONYM)]

        #This process can fail during migrations of the Dataset model
        except (OperationalError, ProgrammingError) as e:
            dataset_choices = []

        dataset = forms.TypedMultipleChoiceField(label=_(u'Requested Datasets'),
                                                  choices=dataset_choices,
                                                  required=False, widget=Select2)
        motivation = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 5,
                                                                  'placeholder': 'Motivation'}),
                                     label=_(u'Motivation'), required=False, # this has to be False
                                     # the motivation field is not stored in the database
                                     # it is retrieved from the form to be used in the request access email sent to the dataset manager
                                     # in order to avoid default Django behaviour, it is renamed in the form to motivation_for_use
                                     # required needs to be False
                                     # otherwise Django can't match the new field name with this one
                                     # requested datasets are also passed this way rather than stored in the database
                                     help_text=_("Please explain why you would like to get access to this dataset. What are the purposes for which you wish to use it?"))

    tos_choices = [(True, 'Agree'), (False, 'Disagree')]
    href_hyperlink = settings.URL + settings.PREFIX_URL + '/about/conditions/'
    tos_hyperlink = _(u'I have read and agree to the <a href="' + href_hyperlink + '" target="_blank">Terms of Service</a>')
    tos = forms.BooleanField(label=mark_safe_lazy(tos_hyperlink),
                             widget=forms.RadioSelect(choices=tos_choices),
                             error_messages={'required': 'Error: You must agree to the Terms of Service in order to register'})

    def clean_username(self):
        """
        Validates that the username is alphanumeric and is not already
        in use.

        """
        data = self.cleaned_data['username']
        if '@' in data or '|' in data or ' ' in data or '+' in data:
            raise forms.ValidationError(_(u'Usernames should not have special characters.'))
        try:
            user = User.objects.get(username__exact=self.cleaned_data['username'])
        except User.DoesNotExist:
            return self.cleaned_data['username']
        raise forms.ValidationError(_(u'This username is already taken. Please choose another.'))

    def clean_password2(self):
        """
        Validates that the two password inputs match.

        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] == self.cleaned_data['password2']:
                return self.cleaned_data['password2']
            raise forms.ValidationError(_(u'You must type the same password each time'))

    def clean_motivation(self):

        if 'motivation_for_use' in self.cleaned_data:
            return self.cleaned_data['motivation_for_use']
        elif 'motivation' in self.cleaned_data:
            return self.cleaned_data['motivation']
        else:
            raise forms.ValidationError(_(u'Please provide motivation for your request'))

    def clean_tos(self):
        """
        Validates that the user accepted the Terms of Service.

        """
        if self.cleaned_data.get('tos', True):
            return self.cleaned_data['tos']
        raise forms.ValidationError(_(u'Please consider the Terms of Service.'))

    def __init__(self, request=None, *args, **kwargs):
        """
        If request is passed in, the form will validate that cookies are
        enabled. Note that the request (a HttpRequest object) must have set a
        cookie with the key TEST_COOKIE_NAME and value TEST_COOKIE_VALUE before
        running this validation.
        """
        self.request = request

        super(RegistrationForm, self).__init__(*args, **kwargs)
        if request and request.session:
            if 'requested_datasets' in request.session.keys():
                import json
                self.fields['dataset'].initial = json.dumps(request.session['requested_datasets'])

    def save(self, profile_callback=None):
        """
        Creates the new ``User`` and ``RegistrationProfile``, and
        returns the ``User``.

        This is essentially a light wrapper around
        ``RegistrationProfile.objects.create_inactive_user()``,
        feeding it the form data and a profile callback (see the
        documentation on ``create_inactive_user()`` for details) if
        supplied.

        """
        new_user = RegistrationProfile.objects.create_inactive_user(username=self.cleaned_data['username'],
                                                                    password=self.cleaned_data['password1'],
                                                                    email=self.cleaned_data['email'],
                                                                    firstname=self.cleaned_data['first_name'],
                                                                    lastname=self.cleaned_data['last_name'],
                                                                    agree=self.cleaned_data['tos'],
                                                                    profile_callback=profile_callback)
        return new_user


class RegistrationFormTermsOfService(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which adds a required checkbox
    for agreeing to a site's Terms of Service.

    """
    tos = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_reqd),
                             label=_(u'I have read and agree to the Terms of Service'))

    def clean_tos(self):
        """
        Validates that the user accepted the Terms of Service.

        """
        if self.cleaned_data.get('tos', False):
            return self.cleaned_data['tos']
        raise forms.ValidationError(_(u'You must agree to the terms to register'))


class RegistrationFormUniqueEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which enforces uniqueness of
    email addresses.

    """
    def clean_email(self):
        """
        Validates that the supplied email address is unique for the
        site.

        """
        try:
            user = User.objects.get(email__exact=self.cleaned_data['email'])
        except User.DoesNotExist:
            return self.cleaned_data['email']
        raise forms.ValidationError(_(u'This email address is already in use. Please supply a different email address.'))


yesnoChoices = ((1, 'yes'), (0, 'no'))

import string

def t(message):
    """Replace $country and $language in message with date from settings"""

    tpl = string.Template(message)
    return tpl.substitute(country=settings.COUNTRY_NAME, language=settings.LANGUAGE_NAME)


from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate

class EmailAuthenticationForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """
    email = forms.CharField(label=_("Email"), max_length=100)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        """
        If request is passed in, the form will validate that cookies are
        enabled. Note that the request (a HttpRequest object) must have set a
        cookie with the key TEST_COOKIE_NAME and value TEST_COOKIE_VALUE before
        running this validation.
        """
        self.request = request
        self.user_cache = None
        super(EmailAuthenticationForm, self).__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a correct email and password. Note that password is case-sensitive."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))

        # TODO: determine whether this should move to its own method.
        if self.request:
            if not self.request.session.test_cookie_worked():
                raise forms.ValidationError(_("Your Web browser doesn't appear to have cookies enabled. Cookies are required for logging in."))

        return self.cleaned_data


    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


