"""
Forms and validation code for user registration.

"""


from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.conf import settings

from models import RegistrationProfile, UserProfile

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
    username = forms.CharField(max_length=30,
                               widget=forms.TextInput(attrs=attrs_reqd),
                               label=_(u'Username'))
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_reqd,
                                                               maxlength=75)
                                                    
                                                    ),
                             label=_(u'Your Email Address'))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_reqd),
                                label=_(u'Password'))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_reqd),
                                label=_(u'Password (again)'))

    def clean_username(self):
        """
        Validates that the username is alphanumeric and is not already
        in use.

        """
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
                                                                    profile_callback=profile_callback)
        barf
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


class RegistrationFormNoFreeEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which disallows registration with
    email addresses from popular free webmail services; moderately
    useful for preventing automated spam registrations.

    To change the list of banned domains, subclass this form and
    override the attribute ``bad_domains``.

    """
    bad_domains = ['aim.com', 'aol.com', 'email.com', 'gmail.com',
                   'googlemail.com', 'hotmail.com', 'hushmail.com',
                   'msn.com', 'mail.ru', 'mailinator.com', 'live.com']

    def clean_email(self):
        """
        Checks the supplied email address against a list of known free
        webmail domains.

        """
        email_domain = self.cleaned_data['email'].split('@')[1]
        if email_domain in self.bad_domains:
            raise forms.ValidationError(_(u'Registration using free email addresses is prohibited. Please supply a different email address.'))
        return self.cleaned_data['email']

import re
import time

class BirthYearField(forms.Field):
    """A form field for entry of a year of birth,
     must be before this year and not more than 110 years ago"""

    year_re = re.compile("\d\d\d\d")

    def clean(self, value):
        if not value:
            raise forms.ValidationError('Enter a four digit year, eg. 1984.')

        if not self.year_re.match(str(value)):
            raise forms.ValidationError('%s is not a valid year.' % value   )
        year = int(value)
        # check not after this year
        thisyear = time.localtime()[0]
        if year > thisyear:
            raise forms.ValidationError("%s is in the future, please enter your year of birth." % value )
        # or that this person isn't over 110
        if year < thisyear-110:
            raise forms.ValidationError("If you were born in %s you are now %s years old! Please enter your real birth year." % (year, thisyear-year))
        return year


from models import backgroundChoices, learnedChoices, schoolChoices, teachercommChoices

yesnoChoices = ((1, 'yes'), (0, 'no'))

import string

def t(message):
    """Replace $country and $language in message with dat from settings"""
    
    tpl = string.Template(message)
    return tpl.substitute(country=settings.COUNTRY_NAME, language=settings.LANGUAGE_NAME)


class RegistrationFormAuslan(RegistrationFormUniqueEmail):
    """
    Registration form for the site
    """
    username = forms.CharField(widget=forms.HiddenInput, required=False)
    firstname = forms.CharField(label=t("Firstname"), max_length=50)
    
    lastname = forms.CharField(label=t("Lastname"), max_length=50)
    
    yob = BirthYearField(label=t("What year were you born?"))
    
    australian = forms.ChoiceField(yesnoChoices, label=t("Do you live in ${country}?"))
    
    postcode = forms.CharField(label=t("If you live in $country, what is your postcode?"), 
                               max_length=20, required=False)
    
    background = forms.MultipleChoiceField(backgroundChoices, label=_("What is your background?"))
    
    auslan_user = forms.ChoiceField(yesnoChoices, label=t("Do you use $language?"), required=False)
    
    learned = forms.ChoiceField(label=t("If you use $language, when did you learn sign language?"),
                                  choices=learnedChoices, required=False)
    
    deaf = forms.ChoiceField(yesnoChoices, label=t("Are you a deaf person?"))
    
    schooltype = forms.ChoiceField(label=t("What sort of school do you (or did you) attend?"),
                                   choices=schoolChoices, required=False)
    school = forms.CharField(label=t("Which school do you (or did you) attend?"),
                             max_length=50, required=False)
    teachercomm = forms.ChoiceField(label=t("How do (or did) your teachers communicate with you?"),
                                    choices=teachercommChoices,
                                    required=False)



    def save(self, profile_callback=None):
        """
        Creates the new ``User`` and ``RegistrationProfile``, and
        returns the ``User``.

        Also create the userprofile with additional info from the form.

        Differs from the default by using the email address as the username.
        """

        # construct a username based on the email address
        # need to truncate to 30 chars
        username = self.cleaned_data['email'].replace('@','').replace('.','')
        username = username[:30]

        new_user = RegistrationProfile.objects.create_inactive_user(username=username,
                                                                    password=self.cleaned_data['password1'],
                                                                    email=self.cleaned_data['email'],
                                                                    firstname=self.cleaned_data['firstname'],
                                                                    lastname=self.cleaned_data['lastname'],
                                                                    profile_callback=profile_callback)



        # now also create the userprofile for this user with
        # the extra information from the form
        
        profile = UserProfile(user=new_user,
                              yob=self.cleaned_data['yob'],
                              australian=self.cleaned_data['australian'],
                              postcode=self.cleaned_data['postcode'],
                              background=",".join(self.cleaned_data['background']),
                              auslan_user=self.cleaned_data['auslan_user'],
                              learned=self.cleaned_data['learned'],
                              deaf=self.cleaned_data['deaf'],
                              schooltype=self.cleaned_data['schooltype'],
                              school=self.cleaned_data['school'],
                              teachercomm=self.cleaned_data['teachercomm'])

        profile.save()

        return new_user


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

