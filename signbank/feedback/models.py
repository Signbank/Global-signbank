from django.db import models, OperationalError, ProgrammingError
from django.contrib.auth import models as authmodels
from django.conf import settings
from signbank.settings.base import COMMENT_VIDEO_LOCATION, WRITABLE_FOLDER
import os
from signbank.video.fields import VideoUploadToFLVField
from django import forms

from django.utils.translation import gettext_lazy as _
from django.utils.encoding import escape_uri_path

from signbank.dictionary.models import *

# models to represent the feedback from users in the site

import string


def t(message):
    """Replace $country and $language in message with dat from settings"""
    
    tpl = string.Template(message)
    return tpl.substitute(country=settings.COUNTRY_NAME, language=settings.LANGUAGE_NAME)


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
            filepath = os.path.join(settings.COMMENT_VIDEO_LOCATION, self.video.name)
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

    meaning = forms.CharField(label=_('Sign Meaning'), widget=forms.Textarea(attrs={'rows': 6, 'cols': 80}),
                              required=True)
    video = forms.FileField(label=_('Video of the Sign'), required=True,
                            widget=forms.FileInput(attrs={'size': '60', 'accept': 'video/*'}))
    comments = forms.CharField(label=_('Other Remarks'), widget=forms.Textarea(attrs={'rows': 6, 'cols': 80}),
                               required=False)
    sentence = forms.FileField(label=_('Example Sentence'), required=False,
                               widget=forms.FileInput(attrs={'size': '60', 'accept': 'video/*'}))

    def __init__(self, *args, **kwargs):
        sign_languages = kwargs.pop('sign_languages')

        super(MissingSignFeedbackForm, self).__init__(*args, **kwargs)

        self.fields['signlanguage'] = forms.ModelChoiceField(label=_("Sign Language"), required=True,
                                                             queryset=SignLanguage.objects.filter(id__in=sign_languages),
                                                             widget=forms.Select(attrs={'class': 'form-control'}))
        self.fields['signlanguage'].initial = sign_languages[0]


def get_video_file_path(instance, filename, signlanguage, comment_type):
    (base, ext) = os.path.splitext(filename)

    filename = comment_type + '_' + signlanguage + '_' + str(instance.id) + ext

    signlanguage_directory = os.path.join(settings.WRITABLE_FOLDER, settings.COMMENT_VIDEO_LOCATION, signlanguage)
    path = os.path.join(settings.COMMENT_VIDEO_LOCATION, signlanguage, filename)

    if not os.path.isdir(signlanguage_directory):
        os.mkdir(signlanguage_directory)

    if hasattr(settings, 'ESCAPE_UPLOADED_VIDEO_FILE_PATH') and settings.ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        from django.utils.encoding import escape_uri_path
        path = escape_uri_path(path)
    return path


class MissingSignFeedback(models.Model):    
    user = models.ForeignKey(authmodels.User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    signlanguage = models.ForeignKey(SignLanguage, verbose_name=_("Sign Language"),
                                     help_text=_("Sign Language of the missing sign"), null=True,
                                     on_delete=models.CASCADE)
    meaning = models.TextField()
    comments = models.TextField(blank=True)
    video = models.FileField(upload_to=settings.VIDEO_UPLOAD_LOCATION, blank=True)
    sentence = models.FileField(upload_to=settings.VIDEO_UPLOAD_LOCATION, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')

    class Meta:
        ordering = ['-date']

    def has_video(self):
        """Return the video object for this Feedback or None if no video available"""
        if self.video:
            filepath = os.path.join(settings.WRITABLE_FOLDER, self.video.name)
        else:
            filepath = ''
        if filepath and os.path.exists(filepath.encode('utf-8')):
            return self.video
        else:
            return ''

    def has_sentence_video(self):
        """Return the sentence object for this Feedback or None if no sentence available"""
        if self.sentence:
            filepath = os.path.join(settings.WRITABLE_FOLDER, self.sentence.name)
        else:
            filepath = ''
        if filepath and os.path.exists(filepath.encode('utf-8')):
            return self.sentence
        else:
            return ''

    def save_video(self, *args, **kwargs):
        if not self.video:
            return
        filename = self.video.name
        signlanguage = self.signlanguage.name
        newloc = get_video_file_path(self, filename, signlanguage, 'missing_sign')
        newpath = os.path.join(settings.WRITABLE_FOLDER, newloc)
        oldpath = os.path.join(settings.WRITABLE_FOLDER, self.video.name)
        os.rename(oldpath, newpath)
        self.video.name = newloc
        self.save()

    def save_sentence_video(self, *args, **kwargs):
        if not self.sentence:
            return
        filename = self.sentence.name
        signlanguage = self.signlanguage.name
        newloc = get_video_file_path(self, filename, signlanguage, 'meaning_missing_sign')
        newpath = os.path.join(settings.WRITABLE_FOLDER, newloc)
        oldpath = os.path.join(settings.WRITABLE_FOLDER, self.sentence.name)
        os.rename(oldpath, newpath)
        self.sentence.name = newloc
        self.save()
