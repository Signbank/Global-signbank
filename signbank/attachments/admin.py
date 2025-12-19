from django.contrib import admin
from django.db import models
from django import forms
from django.forms import Textarea
from django.template.loader import render_to_string
from django import template
from django.template import Context, Template
from django.utils.translation import  gettext_lazy as _, gettext
from joblib.externals.cloudpickle import instance

from signbank.attachments.models import Attachment, Communication, COMMUNICATION_TYPES


class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['file', 'date', 'uploader']


class CommunicationAdminForm(forms.ModelForm):
    label = forms.CharField(label=_("Description of type of communication"),
                            widget=forms.Select(attrs={'class': 'form-control'},
                                                choices=COMMUNICATION_TYPES),
                            help_text="""Label without spaces""")

    template_subject = forms.CharField(label=_("Subject (rendered)"),
                                       widget=forms.Textarea(attrs={'cols': 60, 'rows': 1}))
    subject = forms.CharField(label=_("Subject (template)"),
                              widget=forms.Textarea(attrs={'cols': 60, 'rows': 1}))
    template_text = forms.CharField(label=_("Text (rendered)"),
                                    widget=forms.Textarea(attrs={'cols': 80, 'rows': 18}))
    text = forms.CharField(label=_("Text (template"),
                           widget=forms.Textarea(attrs={'cols': 80, 'rows': 18}))

    class Meta:
        model = Communication
        fields = ['label', 'subject', 'template_subject', 'text', 'template_text']

    def template_context(self):
        # template context with strings
        placeholders = {'site_name': 'SITE NAME',
                        'signbank_name': 'SIGNBANK',
                        'url' : 'URL',
                        'user' : {'firstname': 'FIRST NAME',
                                  'lastname': 'LAST NAME',
                                  'email': 'EMAIL',
                                  'username': 'USERNAME'},
                        'new_user_firstname': 'NEW USER FIRST NAME',
                        'new_user_lastname': 'NEW USER LAST NAME',
                        'new_user_email': 'NEW USER EMAIL',
                        'dataset': 'DATASET',
                        'motivation': 'MOTIVATION',
                        'site': {'name': 'SITE NAME'}}
        return Context(placeholders)

    def __init__(self, *args, **kwargs):
        super(CommunicationAdminForm, self).__init__(*args, **kwargs)
        if not self.instance:
            self.fields['label'].initial = '-'
            self.fields['template_subject'].initial = "Email Subject"
            self.fields['template_text'].initial = "Email Text"
        else:
            subject_template = Template(self.instance.subject)
            self.fields['template_subject'].initial = subject_template.render(self.template_context())
            self.fields['template_subject'].disabled = True
            subject_template = Template(self.instance.text)
            self.fields['template_text'].initial = subject_template.render(self.template_context())
            self.fields['template_text'].disabled = True


class CommunicationAdmin(admin.ModelAdmin):
    form = CommunicationAdminForm

    list_display = ['label', 'subject', 'subject_help', 'text', 'text_help']

    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 60})}
    }

    def template_context(self):
        # template context with strings
        placeholders = {'site_name': 'SITE NAME',
                        'signbank_name': 'SIGNBANK',
                        'url' : 'URL',
                        'user' : {'firstname': 'FIRST NAME',
                                  'lastname': 'LAST NAME',
                                  'email': 'EMAIL',
                                  'username': 'USERNAME'},
                        'new_user_firstname': 'NEW USER FIRST NAME',
                        'new_user_lastname': 'NEW USER LAST NAME',
                        'new_user_email': 'NEW USER EMAIL',
                        'dataset': 'DATASET',
                        'motivation': 'MOTIVATION',
                        'site': {'name': 'SITE NAME'}}
        return Context(placeholders)

    admin.display(empty_value="EMPTY")
    def subject_help(self, obj):
        template = Template(obj.subject)
        highlight = template.render(self.template_context())
        return highlight
    subject_help.short_description = "Subject (rendered)"

    admin.display(empty_value="EMPTY")
    def text_help(self, obj):
        template = Template(obj.text)
        highlight = template.render(self.template_context())
        return highlight
    text_help.short_description = "Text (rendered)"

admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(Communication, CommunicationAdmin)
