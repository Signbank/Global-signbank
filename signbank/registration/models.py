"""
A model (``RegistrationProfile``) for storing user-registration data,
and an associated custom manager (``RegistrationManager``).

"""


import datetime, random, re, hashlib

from django.conf import settings
from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.utils import timezone

SHA1_RE = re.compile('^[a-f0-9]{40}$')


class RegistrationManager(models.Manager):
    """
    Custom manager for the ``RegistrationProfile`` model.
    
    The methods defined here provide shortcuts for account creation
    and activation (including generation and emailing of activation
    keys), and for cleaning out expired inactive accounts.
    
    """
    def activate_user(self, activation_key):
        """
        Validates an activation key and activates the corresponding
        ``User`` if valid.accounts/activate/{{ activation_key }}
        
        If the key is valid and has not expired, returns the ``User``
        after activating.
        
        If the key is not valid or has expired, returns ``False``.
        
        If the key is valid but the ``User`` is already active,
        returns the ``User``.
        
        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(activation_key):
            try:
                profile = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not profile.activation_key_expired():
                user = profile.user
                # user will be set to active after dataset access has been granted
                # check if this makes sense for ASL
                # user.is_active = True
                user.save()

                # send emails for the requested datasets
                # we might not have the list of datasets anymore if this is a new session

                return user
        return False
    
    def create_inactive_user(self, username, password, email,
                             firstname="", lastname="", agree=True,
                             send_email=True):
        """
        Creates a new, inactive ``User``, generates a
        ``RegistrationProfile`` and emails its activation key to the
        ``User``. Returns the new ``User``.
        
        To disable the email, call with ``send_email=False``.
        
        To enable creation of a custom user profile along with the
        ``User`` (e.g., the model specified in the
        ``AUTH_PROFILE_MODULE`` setting), define a function which
        knows how to create and save an instance of that model with
        appropriate default values, and pass it as the keyword
        argument ``profile_callback``. This function should accept one
        keyword argument:

        ``user``
            The ``User`` to relate the profile to.
        
        """
        new_user = User.objects.create_user(username, email, password)
        new_user.is_active = False
        new_user.first_name = firstname
        new_user.last_name = lastname
        group_guest = Group.objects.get(name='Guest')
        new_user.groups.add(group_guest)
        new_user.save()


        registration_profile = self.create_profile(new_user)

        # print('activation key: ', registration_profile.activation_key)

        if send_email:
            from django.core.mail import send_mail
            signbank_name = settings.LANGUAGE_NAME + ' Signbank'

            subject = render_to_string('registration/activation_email_subject.txt',
                                       context={ 'signbank_name': signbank_name})
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            
            message = render_to_string('registration/activation_email.txt',
                                       context={ 'activation_key': registration_profile.activation_key,
                                         'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                                         'signbank_name': signbank_name,
                                         'url': settings.URL})

            # for debug purposes on local machine
            if settings.DEBUG_EMAILS_ON:
                print('register subject: ', subject)
                print('message: ', message)

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [new_user.email])
        return new_user
    
    def create_profile(self, user):
        """
        Creates a ``RegistrationProfile`` for a given
        ``User``. Returns the ``RegistrationProfile``.
        
        The activation key for the ``RegistrationProfile`` will be a
        SHA1 hash, generated from a combination of the ``User``'s
        username and a random salt.
        
        """
        salt = hashlib.sha1(str(random.random()).encode('utf-8')).hexdigest()[:5]
        string_to_hash = str(salt) + str(user.username)
        activation_key = hashlib.sha1(string_to_hash.encode('utf-8')).hexdigest()
        return self.create(user=user,
                           activation_key=activation_key)
        
    def delete_expired_users(self):
        """
        Removes expired instances of ``RegistrationProfile`` and their
        associated ``User``s.
        
        Accounts to be deleted are identified by searching for
        instances of ``RegistrationProfile`` with expired activation
        keys, and then checking to see if their associated ``User``
        instances have the field ``is_active`` set to ``False``; any
        ``User`` who is both inactive and has an expired activation
        key will be deleted.
        
        It is recommended that this method be executed regularly as
        part of your routine site maintenance; the file
        ``bin/delete_expired_users.py`` in this application provides a
        standalone script, suitable for use as a cron job, which will
        call this method.
        
        Regularly clearing out accounts which have never been
        activated serves two useful purposes:
        
        1. It alleviates the ocasional need to reset a
           ``RegistrationProfile`` and/or re-send an activation email
           when a user does not receive or does not act upon the
           initial activation email; since the account will be
           deleted, the user will be able to simply re-register and
           receive a new activation key.
        
        2. It prevents the possibility of a malicious user registering
           one or more accounts and never activating them (thus
           denying the use of those usernames to anyone else); since
           those accounts will be deleted, the usernames will become
           available for use again.
        
        If you have a troublesome ``User`` and wish to disable their
        account while keeping it in the database, simply delete the
        associated ``RegistrationProfile``; an inactive ``User`` which
        does not have an associated ``RegistrationProfile`` will not
        be deleted.
        
        """
        for profile in self.all():
            if profile.activation_key_expired():
                user = profile.user
                if not user.is_active:
                    user.delete()


class RegistrationProfile(models.Model):
    """
    A simple profile which stores an activation key for use during
    user account registration.
    
    Generally, you will not want to interact directly with instances
    of this model; the provided manager includes methods
    for creating and activating new accounts, as well as for cleaning
    out accounts which have never been activated.
    
    While it is possible to use this model as the value of the
    ``AUTH_PROFILE_MODULE`` setting, it's not recommended that you do
    so. This model's sole purpose is to store data temporarily during
    account registration and activation, and a mechanism for
    automatically creating an instance of a site-specific profile
    model is provided via the ``create_inactive_user`` on
    ``RegistrationManager``.
    
    """
    user = models.ForeignKey(User, verbose_name=_('user'))
    activation_key = models.CharField(_('activation key'), max_length=40)

    objects = RegistrationManager()
    
    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')
        app_label = 'registration'

    class Admin:
        list_display = ('__str__', 'activation_key_expired')
        search_fields = ('user__username', 'user__first_name')
        
    def __str__(self):
        return u"Registration information for %s" % self.user
    
    def activation_key_expired(self):
        """
        Determines whether this ``RegistrationProfile``'s activation
        key has expired.
        
        Returns ``True`` if the key has expired, ``False`` otherwise.
        
        Key expiration is determined by the setting
        ``ACCOUNT_ACTIVATION_DAYS``, which should be the number of
        days a key should remain valid after an account is registered.
        
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.user.date_joined + expiration_date <= timezone.now() 
    activation_key_expired.boolean = True
    

# The rest of this file is from Auslan, it's not used by Signbank

from django.contrib.auth import models as authmodels    

import string

def t(message):
    """Replace $country and $language in message with dat from settings"""
    
    tpl = string.Template(message)
    return tpl.substitute(country=settings.COUNTRY_NAME, language=settings.LANGUAGE_NAME)



backgroundChoices = ((0, 'deaf community'),
            	      (1, t('$language teacher')),
                     (2, 'teacher of the deaf'),
                     (3, 'parent of a deaf child'),
                     (4, 'sign language interpreter'),
                     (5, 'school or university student'),
                     (6, t('student learning $language')),
                     (7, 'other'),
                     )
                     
learnedChoices = ((0, 'Not Applicable'),
           (1, 'At home from my parent(s)'),
           (2, 'At kindergarten or at the beginning of primary school'),
           (3, 'At primary school'),
           (4, 'At high school'),
           (5, 'After I left school'),
           )

schoolChoices = ((0, 'a deaf school (boarder)'),
                 (1, 'a deaf school (day student)'),
                 (2, 'a deaf classroom or unit in a hearing school'),
                 (3, 'a regular classroom in a hearing school'),
                 )

teachercommChoices = ((0, 'mostly oral'),
                      (1, 'mostly Signed English'),
                      (2, t('mostly sign language ($language)')),
                      (3, 'mostly fingerspelling')
                      )

class UserProfile(models.Model):
    """Extended profile for users of the site"""
    
    user = models.ForeignKey(authmodels.User)
    yob = models.IntegerField("When were you born?")
    australian = models.BooleanField(t("Do you live in $country?"),default=False)
    postcode = models.CharField(t("If you live in $country, what is your postcode?"), max_length=20, blank=True)
    background = models.CommaSeparatedIntegerField("What is your background?", max_length=20, choices=backgroundChoices)
    auslan_user = models.BooleanField(t("Do you use $language?"),default=False)
    learned = models.IntegerField(t("If you use $language, when did you learn sign language?"), 
                                  choices=learnedChoices)
    deaf = models.BooleanField("Are you a deaf person?",default=False)
    schooltype = models.IntegerField("What sort of school do you (or did you) attend?", 
                                     choices=schoolChoices)
    school = models.CharField("Which school do you (or did you) attend?", max_length=50, blank=True)                             
    teachercomm = models.IntegerField("How do (or did) your teachers communicate with you?", 
                                      choices=teachercommChoices)
    
                                      
    class Admin:
        list_display = ['user', 'deaf', 'auslan_user']
            
    class Meta:
        app_label = 'registration'
