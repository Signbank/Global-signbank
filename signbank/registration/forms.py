"""
Forms and validation code for user registration.
"""
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _, gettext as __
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.safestring import mark_safe
from django.db.utils import OperationalError, ProgrammingError
from django.contrib.auth import authenticate
from easy_select2.widgets import Select2

from signbank.registration.models import RegistrationProfile
from signbank.dictionary.models import Dataset

from signbank.pages.models import Page


class RegistrationForm(forms.Form):
    """
    Form for registering a new user account.

    Validates that the request username is not already in use, and
    requires the password to be entered twice to catch typos.
    """
    username = forms.CharField(max_length=30, required=True, widget=forms.TextInput(), label=_('Username'))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(), label=_('First Name'))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(), label=_('Last Name'))
    email = forms.EmailField(widget=forms.TextInput(), required=True, label=_('Your Email Address'))
    password1 = forms.CharField(widget=forms.PasswordInput(), required=True, label=_('Password'))
    password2 = forms.CharField(widget=forms.PasswordInput(), label=_('Password (again)'))

    if getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', None):
        try:
            dataset_choices = [(ds.name, ds.name) for ds in Dataset.objects.filter(is_public='1')]
            if not dataset_choices:
                dataset_choices = [(ds.name, ds.name) for ds in
                                   Dataset.objects.filter(acronym=settings.DEFAULT_DATASET_ACRONYM)]
        # This process can fail during migrations of the Dataset model
        except (OperationalError, ProgrammingError):
            dataset_choices = []

        dataset = forms.TypedMultipleChoiceField(label=_('Requested Datasets'), choices=dataset_choices,
                                                 required=False, widget=Select2)

        # The motivation field is not stored in the database. It is retrieved from the form to be used in the request
        # access email sent to the dataset manager. In order to avoid default Django behaviour, it is renamed in the
        # form to 'motivation_for_use'. 'required' needs to be False otherwise Django can't match the new field name
        # with this one. Requested datasets are also passed this way rather than stored in the database.
        motivation = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 5, 'placeholder': 'Motivation'}),
                                     label=_('Motivation'), required=False,
                                     help_text=_("Please explain why you would like to get access to this dataset. "
                                                 "What are the purposes for which you wish to use it?"))

    try:
        terms_of_service_page = Page.objects.get(url='/about/conditions/')
    except ObjectDoesNotExist:
        terms_of_service_page = '#'
    terms_of_service_hyperlink = __('I have read and agree to the <a href="{link}" target="_blank">Terms of Service</a>'
                                    .format(link=terms_of_service_page.get_absolute_url()))
    error_message_required = 'Error: You must agree to the Terms of Service in order to register'
    terms_of_service = forms.BooleanField(label=mark_safe(terms_of_service_hyperlink),
                                          widget=forms.RadioSelect(choices=[(True, 'Agree'), (False, 'Disagree')]),
                                          error_messages={'required': error_message_required})

    def clean_username(self):
        """Validates that the username does not contain special characters and is not already in use."""
        username = self.cleaned_data.get('username', '')
        if any(char in username for char in '@| +'):
            raise forms.ValidationError(_('Usernames should not have special characters.'))
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_("This username is already taken. Please choose another."))
        return username

    def clean_password2(self):
        """Validates that the two password inputs match."""
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if not password1 or not password2:
            return None
        if password1 != password2:
            raise forms.ValidationError(_("You must type the same password each time"))
        return password2

    def clean_motivation(self):
        if 'motivation_for_use' in self.cleaned_data:
            return self.cleaned_data['motivation_for_use']
        if 'motivation' in self.cleaned_data:
            return self.cleaned_data['motivation']
        raise forms.ValidationError(_('Please provide motivation for your request'))

    def clean_terms_of_service(self):
        """Validates that the user accepted the Terms of Service."""
        if not self.cleaned_data.get('terms_of_service', True):
            raise forms.ValidationError(_("Please consider the Terms of Service."))
        return self.cleaned_data['terms_of_service']

    def save(self):
        """Creates the new ``User`` and ``RegistrationProfile``, and returns the ``User``."""
        new_user = RegistrationProfile.objects.create_user(username=self.cleaned_data['username'],
                                                           password=self.cleaned_data['password1'],
                                                           email=self.cleaned_data['email'],
                                                           firstname=self.cleaned_data['first_name'],
                                                           lastname=self.cleaned_data['last_name'],)
        return new_user


class SignbankAuthenticationForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """
    username = forms.CharField(label=_("User name"), max_length=100)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        """
        If request is passed in, the form will validate that cookies are
        enabled. Note that the request (a HttpRequest object) must have set a
        cookie with the key TEST_COOKIE_NAME and value TEST_COOKIE_VALUE before
        running this validation.
        """
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        print(username, password)

        if not (username and password):
            self.check_cookies_are_enabled()
            return self.cleaned_data

        self.user_cache = authenticate(username=username, password=password)
        if self.user_cache is None:
            raise forms.ValidationError(_("Please enter a correct user name and password. "
                                          "Note that password is case-sensitive."))
        if not self.user_cache.is_active:
            raise forms.ValidationError(_("This account is inactive."))

        self.check_cookies_are_enabled()
        return self.cleaned_data

    def check_cookies_are_enabled(self):
        if self.request and not self.request.session.test_cookie_worked():
            raise forms.ValidationError(_("Your Web browser doesn't appear to have cookies enabled. "
                                          "Cookies are required for logging in."))

    def get_user(self):
        return self.user_cache
