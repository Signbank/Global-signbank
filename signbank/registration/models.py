"""
A model (``RegistrationProfile``) for storing user-registration data,
and an associated custom manager (``RegistrationManager``).
"""
import datetime
import random
import re
import hashlib

from django.conf import settings
from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.core.mail import send_mail

SHA1_regex = re.compile('^[a-f0-9]{40}$')


class RegistrationManager(models.Manager):
    """Custom manager for the ``RegistrationProfile`` model."""
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
        if not SHA1_regex.search(activation_key):
            return False

        try:
            profile = self.get(activation_key=activation_key)
        except self.model.DoesNotExist:
            return False

        if profile.activation_key_expired():
            return False

        user = profile.user
        user.save()
        return user

    def create_user(self, username, password, email, firstname="", lastname="", send_email=True):
        """
        Creates a new ``User``, generates a ``RegistrationProfile`` and emails its activation key to the
        ``User``. Returns the new ``User``.
        """
        new_user = User.objects.create_user(username, email, password, is_active=True, first_name=firstname,
                                            last_name=lastname)
        group_guest = Group.objects.get(name='Guest')
        new_user.groups.add(group_guest)
        new_user.save()

        registration_profile = self.create_profile(new_user)

        if send_email:
            self.send_email_to_new_user(new_user, registration_profile)

        return new_user

    def send_email_to_new_user(self, new_user, registration_profile):
        signbank_name = settings.LANGUAGE_NAME + ' Signbank'
        subject = render_to_string('registration/activation_email_subject.txt',
                                   context={'signbank_name': signbank_name})
        subject = ''.join(subject.splitlines())

        message_context = {
            'activation_key': registration_profile.activation_key,
            'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
            'signbank_name': signbank_name,
            'url': settings.URL
        }
        message = render_to_string('registration/activation_email.txt', context=message_context)

        if not settings.DEBUG_EMAILS_ON:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [new_user.email])
        else:
            print('register subject: ', subject)
            print('message: ', message)

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
        return self.create(user=user, activation_key=activation_key)

    def delete_expired_users(self):
        """Removes expired instances of ``RegistrationProfile`` and their associated ``User``s."""
        for profile in self.all():
            if profile.activation_key_expired():
                user = profile.user
                if not user.is_active:
                    user.delete()


class RegistrationProfile(models.Model):
    """
    A simple profile which stores an activation key for use during user account registration.

    It is recommended that you do not interact directly with instances of this model. Use RegistrationManager instead.
    """
    user = models.ForeignKey(User, verbose_name=_('user'), on_delete=models.CASCADE)
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
        return f"Registration information for {self.user}"

    def activation_key_expired(self):
        """
        Determines whether this ``RegistrationProfile``'s activation
        key has expired.

        Key expiration is determined by the setting
        ``ACCOUNT_ACTIVATION_DAYS``, which should be the number of
        days a key should remain valid after an account is registered.
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.user.date_joined + expiration_date <= timezone.now()
