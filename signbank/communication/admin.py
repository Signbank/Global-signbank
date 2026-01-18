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
from joblib.externals.cloudpickle import instance
from django.contrib.sites.models import Site
from numpy.ma.core import not_equal

from signbank.communication.models import Communication, COMMUNICATION_TYPES, typed_context


CONTEXT_COMMUNICATION_TYPES = [
    ('', 'CONTEXT VARIABLES PER COMMUNICATION TYPE'),
    ('Mail to New User: Welcome to Signbank', [('1', 'Mail to New User: Welcome to Signbank'),
                          ('2', '{{site.name}}'),
                          ('3', '{{site.domain}}'),
                          ('4', '{{activation_key}}'),
                          ('5', '{{expiration_days}}'),
                          ('6', '{{url}}')]),
    ('Mail to Dataset Owner: Existing User Given Access',
                         [('1', 'Mail to Dataset Owner: Existing User Given Access'),
                          ('2', '{{dataset}}'),
                          ('3', '{{user.username}}'),
                          ('4', '{{user.firstname}}'),
                          ('5', '{{user.lastname}}'),
                          ('6', '{{user.email}}'),
                          ('7', '{{motivation}}'),
                          ('8', '{{site.name}}'),
                          ('9', '{{site.domain}}')]),
    ('Mail to Dataset Owner: New User Given Access',
                         [('1', 'Mail to Dataset Owner: New User Given Access'),
                          ('2', '{{dataset}}'),
                          ('3', '{{user.username}}'),
                          ('4', '{{user.firstname}}'),
                          ('5', '{{user.lastname}}'),
                          ('6', '{{user.email}}'),
                          ('7', '{{motivation}}'),
                          ('8', '{{site.name}}'),
                          ('9', '{{site.domain}}')
                          ]),
    ('Mail to Dataset Owner: User Requested Access',
                         [('1', 'Mail to Dataset Owner: User Requested Access'),
                          ('2', '{{dataset}}'),
                          ('3', '{{user.username}}'),
                          ('4', '{{user.firstname}}'),
                          ('5', '{{user.lastname}}'),
                          ('6', '{{user.email}}'),
                          ('7', '{{motivation}}'),
                          ('8', '{{site.name}}'),
                          ('9', '{{site.domain}}')
                          ]),
    ('Mail to Existing User: Access Granted',
                         [('1', 'Mail to Existing User: Access Granted'),
                          ('2', '{{dataset}}'),
                          ('3', '{{site.name}}'),
                          ('4', '{{site.domain}}')
                          ])
]


def template_context():
    # this contains all of the possible context variables
    placeholders = {'url': 'URL',
                    'activation_key': 'ACTIVATION KEY',
                    'expiration_days': 'EXPIRATION DAYS',
                    'user': {'firstname': 'FIRST NAME',
                             'lastname': 'LAST NAME',
                             'email': 'EMAIL',
                             'username': 'USERNAME'},
                    'dataset': 'DATASET',
                    'motivation': 'MOTIVATION',
                    'site': {'name': 'SITE NAME',
                             'domain': 'SITE DOMAIN'}
                    }
    return placeholders


class CommunicationAdminForm(forms.ModelForm):
    label = forms.CharField(label=_("Description of type of communication"), required=True, initial="-",
                            widget=forms.Select(attrs={'class': 'form-control'},
                                                choices=COMMUNICATION_TYPES),
                            help_text="""Choose a type of communication""")
    instructions = forms.CharField(label=_("Instructions"), required=False,
                                   widget=forms.Select(attrs={'class': 'form-control'},
                                                       choices=CONTEXT_COMMUNICATION_TYPES))
    subject = forms.CharField(label=_("Subject (edit)"), required=True, initial="",
                              widget=forms.Textarea(attrs={'cols': 60, 'rows': 1}))
    rendered_subject = forms.CharField(label=_("Subject (rendered)"), required=False, initial="",
                                       widget=forms.Textarea(attrs={'cols': 60, 'rows': 1}))
    text = forms.CharField(label=_("Text (edit)"), required=True, initial="",
                           widget=forms.Textarea(attrs={'cols': 80, 'rows': 18}))
    rendered_text = forms.CharField(label=_("Text (rendered)"), required=False, initial="",
                                    widget=forms.Textarea(attrs={'cols': 80, 'rows': 18}))

    class Meta:
        model = Communication
        fields = ['label', 'instructions', 'rendered_subject', 'subject', 'rendered_text', 'text']

    def __init__(self, *args, **kwargs):
        super(CommunicationAdminForm, self).__init__(*args, **kwargs)
        if not self.instance:
            self.fields['label'] = '-'
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
        highlight = template.render(Context(typed_context()[obj.label]))
        return highlight
    subject_rendered.short_description = "Subject (rendered)"

    admin.display(empty_value="EMPTY")
    def text_rendered(self, obj):
        template = Template(obj.text)
        highlight = template.render(Context(typed_context()[obj.label]))
        highlight_lines = highlight.splitlines()
        html_output = format_html_join(mark_safe("<br><br>"),"{}", ((row, row) for row in highlight_lines if row != ""))
        return html_output
    text_rendered.short_description = "Text (rendered)"

admin.site.register(Communication, CommunicationAdmin)
