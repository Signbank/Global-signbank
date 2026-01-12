from django.db import models
from django.utils.translation import gettext_lazy as _


COMMUNICATION_TYPES = [('-', 'Type of Communication'),
                       ('activation_email', 'Mail to New User: Welcome to Signbank'),
                       ('dataset_to_owner_existing_user_given_access', 'Mail to Dataset Owner: Existing User Given Access'),
                       ('dataset_to_owner_new_user_given_access', 'Mail to Dataset Owner: New User Given Access'),
                       ('dataset_to_owner_user_requested_access', 'Mail to Dataset Owner: User Requested Access'),
                       ('dataset_to_user_existing_user_given_access', 'Mail to Existing User: Access Granted')]


class Communication(models.Model):
    label = models.CharField(_("Description of type of communication"),
                             max_length=50,
                             choices=COMMUNICATION_TYPES,
                             help_text="""Label without spaces""")
    subject = models.TextField(_("Site communication subject"), help_text="""The communication subject.""")
    text = models.TextField(_("Site communication text"), help_text="""The communication text.""")

    class Meta:
        app_label = 'communication'

