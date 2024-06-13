from django import forms
from signbank.video.models import GlossVideo, Gloss
import json
from django.utils.translation import gettext_lazy as _


class VideoUploadForm(forms.ModelForm):
    """Form for video upload"""
    
    class Meta:
        model = GlossVideo
        fields = '__all__'


ATTRS_FOR_FORMS = {'class': 'form-control'}


class VideoUploadForObjectForm(forms.Form):
    """Form for video upload for a particular example sentence"""
    
    videofile = forms.FileField(label="Upload Video", widget=forms.FileInput(attrs={'accept':'video/mp4, video/quicktime'}))
    object_id = forms.CharField(widget=forms.HiddenInput)
    object_type = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)
    recorded = forms.BooleanField(initial=False, required=False)
    offset = forms.IntegerField(required=False)
    eaffile = forms.FileField(label="Upload EAF", widget=forms.FileInput(attrs={'accept':'text/xml'}), required=False)
    feedbackdata = forms.CharField(widget=forms.HiddenInput, required=False)
    translations = forms.CharField(widget=forms.HiddenInput, required=False)
    contexts = forms.CharField(widget=forms.HiddenInput, required=False)
    corpus_name = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        languages = kwargs.pop('languages')
        super(VideoUploadForObjectForm, self).__init__(*args, **kwargs)
        for language in languages:
            description_field_name = 'description_' + language.language_code_2char
            self.fields[description_field_name] = forms.CharField(label=_('Description'),
                                                                  widget=forms.TextInput(attrs=ATTRS_FOR_FORMS))
