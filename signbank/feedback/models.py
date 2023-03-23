from django.db import models, OperationalError, ProgrammingError
from django.contrib.auth import models as authmodels
from django.conf import settings
from signbank.settings.base import COMMENT_VIDEO_LOCATION, WRITABLE_FOLDER
import os
from signbank.video.fields import VideoUploadToFLVField

from django.utils.translation import gettext_lazy as _
from django.utils.encoding import escape_uri_path

from signbank.dictionary.models import *

# models to represent the feedback from users in the site

import string

def t(message):
    """Replace $country and $language in message with dat from settings"""
    
    tpl = string.Template(message)
    return tpl.substitute(country=settings.COUNTRY_NAME, language=settings.LANGUAGE_NAME)



from django import forms

STATUS_CHOICES = (('unread', 'unread'),
                  ('read', 'read'),
                  ('deleted', 'deleted'),
                  )


class GeneralFeedback(models.Model):
 
    comment = models.TextField(blank=True)
    video = models.FileField(upload_to=settings.COMMENT_VIDEO_LOCATION, blank=True) 
    user = models.ForeignKey(authmodels.User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
           
    class Meta:
        ordering = ['-date']

    def has_video(self):
        """Return the video object for this Feedback or None if no video available"""
        if self.video:
            filepath = os.path.join(settings.COMMENT_VIDEO_LOCATION, os.sep, self.video.path)
        else:
            filepath = ''
        if filepath and os.path.exists(filepath.encode('utf-8')):
            return self.video
        else:
            return ''

class GeneralFeedbackForm(forms.Form):
    """Form for general feedback"""
    
    comment = forms.CharField(widget=forms.Textarea(attrs={'rows':6, 'cols':80}), required=True)
    video = forms.FileField(required=False, widget=forms.FileInput(attrs={'size':'60'}))


class SignFeedback(models.Model):
    """Store feedback on a particular sign"""
    
    user = models.ForeignKey(authmodels.User, editable=False, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    
    gloss = models.ForeignKey(Gloss, on_delete=models.SET_NULL, null=True, editable=False)
    
    comment = models.TextField("Comment or new keywords.", blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
    
    def __str__(self):
        return str(self.gloss) + " by " + str(self.user) + " on " + str(self.date)

    class Meta:
        ordering = ['-date']


class MorphemeFeedback(models.Model):
    """Store feedback on a particular sign"""

    user = models.ForeignKey(authmodels.User, editable=False, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    morpheme = models.ForeignKey(Morpheme, on_delete=models.SET_NULL, null=True, editable=False)

    comment = models.TextField("Comment or new keywords.", blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')

    def __str__(self):
        return str(self.morpheme) + " by " + str(self.user) + " on " + str(self.date)

    class Meta:
        ordering = ['-date']

class SignFeedbackForm(forms.Form):
    """Form for input of sign feedback"""

    comment = forms.CharField(label="Comment or new keywords", required=True, widget=forms.Textarea(attrs={'rows':6, 'cols':80}))

    def __init__(self, *args, **kwargs):
        super(SignFeedbackForm, self).__init__(*args, **kwargs)

class MorphemeFeedbackForm(forms.Form):
    """Form for input of sign feedback"""

    comment = forms.CharField(label="Comment or new keywords", required=True, widget=forms.Textarea(attrs={'rows':6, 'cols':80}))

    def __init__(self, *args, **kwargs):
        super(MorphemeFeedbackForm, self).__init__(*args, **kwargs)


class MissingSignFeedbackForm(forms.Form):

    meaning = forms.CharField(label='Sign Meaning', widget=forms.Textarea(attrs={'rows':6, 'cols':80}))
    video = forms.FileField(required=False, widget=forms.FileInput(attrs={'size':'60'}))
    comments = forms.CharField(label='Further Details', widget=forms.Textarea(attrs={'rows':6, 'cols':80}), required=True)

    def __init__(self, *args, **kwargs):
        sign_languages = kwargs.pop('sign_languages')

        super(MissingSignFeedbackForm, self).__init__(*args, **kwargs)

        self.fields['signlanguage'] = forms.ModelChoiceField(label=_("Sign Language"),
                                                             queryset=SignLanguage.objects.filter(id__in=sign_languages),
                                                             widget=forms.Select(attrs={'class': 'form-control'}))
        self.fields['signlanguage'].initial = sign_languages[0]


class MissingSignFeedback(models.Model):    
    user = models.ForeignKey(authmodels.User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    signlanguage = models.ForeignKey(SignLanguage, verbose_name=_("Sign Language"),
                                help_text=_("Sign Language of the missing sign"), null=True, on_delete=models.CASCADE)
    meaning = models.TextField()
    comments = models.TextField(blank=True)
    video = models.FileField(upload_to=settings.COMMENT_VIDEO_LOCATION, blank=True) 

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')

    class Meta:
        ordering = ['-date']

    def has_video(self):
        """Return the video object for this Feedback or None if no video available"""
        if self.video:
            filepath = os.path.join(settings.COMMENT_VIDEO_LOCATION, os.sep, self.video.path)
        else:
            filepath = ''
        if filepath and os.path.exists(filepath.encode('utf-8')):
            return self.video
        else:
            return ''
