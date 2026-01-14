from django.db import models
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django import template
from django.template import Context


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


def generate_communication(label, context):
    # grabs the newest matching object with the label
    access_email = Communication.objects.filter(label=label).last()

    if access_email:
        subject_template = template.Template(access_email.subject)
        subject = subject_template.render(Context(context))
    else:
        subject = render_to_string(f'registration/{label}_subject.txt',
                                   context=context)

    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())

    if access_email:
        message_template = template.Template(access_email.text)
        message = message_template.render(Context(context))
    else:
        message = render_to_string(f'registration/{label}.txt',
                                   context=context)
    return subject, message
