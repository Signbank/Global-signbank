import json

from django.contrib import admin
from django.db import models
from django import forms
from django.forms import Textarea
from django.template.loader import render_to_string
from django import template
from django.template import Context, Template
from django.utils.safestring import mark_safe
from django.utils.translation import  gettext_lazy as _, gettext
from django.utils.html import format_html, format_html_join

from signbank.communication.models import Communication, COMMUNICATION_TYPES


def typed_context():
    # template context with strings per email type
    placeholders = {'activation_email': {'signbank_name': 'SIGNBANK',
                                         'activation_key': 'ACTIVATION KEY',
                                         'expiration_days': 'EXPIRATION DAYS',
                                         'url': 'url'},
                    'dataset_to_owner_existing_user_given_access': {'user': 'USER',
                                                                    'dataset': 'DATASET',
                                                                    'motivation': 'MOTIVATION',
                                                                    'site': 'SITE'},
                    'dataset_to_owner_new_user_given_access': {'dataset': 'DATASET',
                                                               'new_user_username': 'NEW USER USERNAME',
                                                               'new_user_firstname': 'NEW USER FIRST NAME',
                                                               'new_user_lastname': 'NEW USER LAST NAME',
                                                               'new_user_email': 'NEW USER EMAIL',
                                                               'motivation':'MOTIVATION',
                                                               'site': 'SITE'},
                    'dataset_to_owner_user_requested_access': {'dataset': 'DATASET',
                                                               'new_user_username': 'NEW USER USERNAME',
                                                               'new_user_firstname': 'NEW USER FIRST NAME',
                                                               'new_user_lastname': 'NEW USER LAST NAME',
                                                               'new_user_email': 'NEW USER EMAIL',
                                                               'motivation':'MOTIVATION',
                                                               'site': 'SITE'},
                    'dataset_to_user_existing_user_given_access': {'dataset': 'DATASET',
                                                                   'site': 'SITE'}
                    }
    return placeholders


def template_context():
    # template context with strings
    placeholders = {'site_name': 'SITE NAME',
                    'signbank_name': 'SIGNBANK',
                    'url': 'URL',
                    'user': {'firstname': 'FIRST NAME',
                             'lastname': 'LAST NAME',
                             'email': 'EMAIL',
                             'username': 'USERNAME'},
                    'new_user_firstname': 'NEW USER FIRST NAME',
                    'new_user_lastname': 'NEW USER LAST NAME',
                    'new_user_email': 'NEW USER EMAIL',
                    'dataset': 'DATASET',
                    'motivation': 'MOTIVATION',
                    'site': {'name': 'SITE NAME'}}
    return placeholders


class CommunicationAdminForm(forms.ModelForm):
    label = forms.CharField(label=_("Description of type of communication"),
                            widget=forms.Select(attrs={'class': 'form-control'},
                                                choices=COMMUNICATION_TYPES),
                            help_text="""Choose a type of communication""")
    instructions = forms.CharField(label=_("Instructions"), required=False,
                                   widget=Textarea(attrs={'cols': 80, 'rows': 18}))
    subject = forms.CharField(label=_("Subject (edit)"),
                              widget=forms.Textarea(attrs={'cols': 60, 'rows': 1}))
    rendered_subject = forms.CharField(label=_("Subject (rendered)"), required=False,
                                       widget=forms.Textarea(attrs={'cols': 60, 'rows': 1}))
    text = forms.CharField(label=_("Text (edit)"),
                           widget=forms.Textarea(attrs={'cols': 80, 'rows': 18}))
    rendered_text = forms.CharField(label=_("Text (rendered)"), required=False,
                                    widget=forms.Textarea(attrs={'cols': 80, 'rows': 18}))

    class Meta:
        model = Communication
        fields = ['label', 'instructions', 'rendered_subject', 'subject', 'rendered_text', 'text']

    def __init__(self, *args, **kwargs):
        super(CommunicationAdminForm, self).__init__(*args, **kwargs)
        self.fields['instructions'].disabled = True
        context_string = '\n'.join(json.dumps(template_context(), indent=4).split(','))
        self.fields['instructions'].initial = format_html("{}\n\n{}\n\n{}\n\n{}",
                                                          "The available context variables are shown below in JSON with mockup values.",
                                                          "Add curly brackets to use them in your text: {{user.username}}",
                                                          "You can preview your text using the button 'Save and continue editing' below",
                                                          context_string)
        if not self.instance:
            self.fields['label'].initial = '-'
            self.fields['rendered_subject'].initial = "Email Subject"
            self.fields['rendered_text'].initial = "Email Text"
        else:
            subject_template = Template(self.instance.subject)
            self.fields['rendered_subject'].initial = subject_template.render(Context(template_context()))
            self.fields['rendered_subject'].disabled = True
            subject_template = Template(self.instance.text)
            self.fields['rendered_text'].initial = subject_template.render(Context(template_context()))
            self.fields['rendered_text'].disabled = True


class CommunicationAdmin(admin.ModelAdmin):
    form = CommunicationAdminForm

    list_display = ['label', 'subject_rendered', 'text_rendered']

    fieldsets = (('INSTRUCTIONS FOR CONTEXT VARIABLES', {'fields': ['instructions']}, ),
                 ('EDIT COMMUNICATION', {'fields': ('label', 'subject', 'rendered_subject', 'text', 'rendered_text'), }),

    )

    admin.display(empty_value="EMPTY")
    def subject_rendered(self, obj):
        template = Template(obj.subject)
        highlight = template.render(Context(template_context()))
        return highlight
    subject_rendered.short_description = "Subject (rendered)"

    admin.display(empty_value="EMPTY")
    def text_rendered(self, obj):
        template = Template(obj.text)
        highlight = template.render(Context(template_context()))
        highlight_lines = highlight.splitlines()
        html_output = format_html_join(mark_safe("<br><br>"),"{}", ((row, row) for row in highlight_lines if row != ""))
        return html_output
    text_rendered.short_description = "Text (rendered)"

admin.site.register(Communication, CommunicationAdmin)
