from django.db import models
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django import template
from django.template import Context, Template
from django.template.base import VariableNode, NodeList
from django.forms.utils import ValidationError


COMMUNICATION_TYPES = [('-', 'Type of Communication'),
                       ('activation_email', 'Mail to New User: Welcome to Signbank'),
                       ('dataset_to_owner_existing_user_given_access', 'Mail to Dataset Owner: Existing User Given Access'),
                       ('dataset_to_owner_new_user_given_access', 'Mail to Dataset Owner: New User Given Access'),
                       ('dataset_to_owner_user_requested_access', 'Mail to Dataset Owner: User Requested Access'),
                       ('dataset_to_user_existing_user_given_access', 'Mail to Existing User: Access Granted')]


def typed_context():
    # template context with strings per email type
    placeholders = {'-': {},
                    'activation_email': {'site': {'name': 'SITE NAME',
                                                  'domain': 'SITE DOMAIN'},
                                         'activation_key': 'ACTIVATION KEY',
                                         'expiration_days': 'EXPIRATION DAYS',
                                         'url': 'URL'},
                    'dataset_to_owner_existing_user_given_access': {'user': {'first_name': 'FIRST NAME',
                                                                             'last_name': 'LAST NAME',
                                                                             'email': 'EMAIL',
                                                                             'username': 'USERNAME'},
                                                                    'dataset': 'DATASET',
                                                                    'motivation': 'MOTIVATION',
                                                                    'site': {'name': 'SITE NAME',
                                                                             'domain': 'SITE DOMAIN'}
                                                                    },
                    'dataset_to_owner_new_user_given_access': {'dataset': 'DATASET',
                                                               'user': {'first_name': 'FIRST NAME',
                                                                        'last_name': 'LAST NAME',
                                                                        'email': 'EMAIL',
                                                                        'username': 'USERNAME'},
                                                               'motivation':'MOTIVATION',
                                                               'site': {'name': 'SITE NAME',
                                                                        'domain': 'SITE DOMAIN'}
                                                               },
                    'dataset_to_owner_user_requested_access': {'dataset': 'DATASET',
                                                               'user': {'first_name': 'FIRST NAME',
                                                                        'last_name': 'LAST NAME',
                                                                        'email': 'EMAIL',
                                                                        'username': 'USERNAME'},
                                                               'motivation':'MOTIVATION',
                                                               'site': {'name': 'SITE NAME',
                                                                        'domain': 'SITE DOMAIN'}
                                                               },
                    'dataset_to_user_existing_user_given_access': {'dataset': 'DATASET',
                                                                   'site': {'name': 'SITE NAME',
                                                                            'domain': 'SITE DOMAIN'}
                                                                   }
                    }
    return placeholders


def check_nesting_structure_of_context_variable(label, lookup_pattern):
    context_lookup = typed_context()
    if label not in context_lookup.keys():
        return False
    typed_lookup = context_lookup[label]
    allowed_patterns = []
    for outer_key, value in typed_lookup.items():
        if isinstance(value, dict):
            for inner_key in value.keys():
                allowed_patterns.append(f'{outer_key}.{inner_key}')
        else:
            allowed_patterns.append(outer_key)
    return lookup_pattern in allowed_patterns


class Communication(models.Model):
    label = models.CharField(_("Description of type of communication"),
                             max_length=50,
                             choices=COMMUNICATION_TYPES,
                             help_text="""Label without spaces""")
    subject = models.TextField(_("Site communication subject"), help_text="""The communication subject.""")
    text = models.TextField(_("Site communication text"), help_text="""The communication text.""")

    class Meta:
        app_label = 'communication'

    def clean_label(self, *args, **kwargs):
        if self.label == '-':
            raise ValidationError(_('The label is required'))
        return self.label

    def clean_subject(self, *args, **kwargs):
        input_subject = Template(self.subject)
        variables = extract_variables(input_subject.nodelist)
        not_okay = []
        for variable in variables:
            is_okay = check_nesting_structure_of_context_variable(self.label, variable)
            if not is_okay:
                not_okay.append("{{"+variable+"}}")
        if not_okay:
            raise ValidationError(_('Some context variables are unavailable: ')+', '.join(not_okay))
        return self.subject

    def clean_text(self, *args, **kwargs):
        input_text = Template(self.text)
        variables = extract_variables(input_text.nodelist)
        not_okay = []
        for variable in variables:
            is_okay = check_nesting_structure_of_context_variable(self.label, variable)
            if not is_okay:
                not_okay.append("{{"+variable+"}}")
        if not_okay:
            raise ValidationError(_('Some context variables are unavailable: ')+', '.join(not_okay))
        return self.text

    def clean(self):
        errors = {}
        try:
            self.clean_label()
        except ValidationError as e:
            errors['label'] = e
        try:
            self.clean_subject()
        except ValidationError as e:
            errors['subject'] = e
        try:
            self.clean_text()
        except ValidationError as e:
            errors['text'] = e
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Communication, self).save(*args, **kwargs)


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


def extract_variables(nodelist, found=None):
    """
    Recursively extract variable names from a Django template NodeList. Thanks, CoPilot.
    """
    if found is None:
        found = set()

    for node in nodelist:
        # Direct variable usage: {{ variable }}
        if isinstance(node, VariableNode):
            found.add(node.filter_expression.token)

        # Some nodes (like for loops, if statements) have their own nodelists
        for attr in dir(node):
            value = getattr(node, attr, None)
            if isinstance(value, NodeList):
                extract_variables(value, found)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, NodeList):
                        extract_variables(item, found)

    return found
