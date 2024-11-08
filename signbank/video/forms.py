from django import forms
from signbank.video.models import GlossVideo, Gloss
from signbank.dictionary.models import AnnotatedSentenceSource
import json
from django.utils.translation import gettext_lazy as _


class VideoUploadForm(forms.ModelForm):
    """Form for video upload"""
    
    class Meta:
        model = GlossVideo
        fields = '__all__'


ATTRS_FOR_FORMS = {'class': 'form-control'}

PERSPECTIVE_CHOICES = (('left', 'Left'),
                       ('right', 'Right')
                       )


class VideoUploadForObjectForm(forms.Form):
    """Form for video upload for all video types"""
    
    videofile = forms.FileField(label="Upload Video", widget=forms.FileInput(attrs={'accept':'video/mp4, video/quicktime'}))
    object_id = forms.CharField(widget=forms.HiddenInput)
    object_type = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)
    recorded = forms.BooleanField(initial=False, required=False)
    offset = forms.IntegerField(required=False)
    perspective = forms.ChoiceField(label=_('Video Perspective'),
                                    choices=PERSPECTIVE_CHOICES, required=False,
                                    widget=forms.Select(attrs=ATTRS_FOR_FORMS))
    eaffile = forms.FileField(label="Upload EAF", widget=forms.FileInput(attrs={'accept':'text/xml'}), required=False)
    feedbackdata = forms.CharField(widget=forms.HiddenInput, required=False)
    translations = forms.CharField(widget=forms.HiddenInput, required=False)
    contexts = forms.CharField(widget=forms.HiddenInput, required=False)
    source_id = forms.ModelChoiceField(queryset=AnnotatedSentenceSource.objects.none(), required=False)
    url = forms.URLField(label="URL", required=False)

    def __init__(self, *args, **kwargs):
        languages = kwargs.pop('languages', [])
        dataset = kwargs.pop('dataset', None)
        super(VideoUploadForObjectForm, self).__init__(*args, **kwargs)

        self.fields['offset'].initial = 0
        for language in languages:
            description_field_name = 'description_' + language.language_code_2char
            self.fields[description_field_name] = forms.CharField(
                label=_('Description'),
                widget=forms.Textarea(attrs={'cols': 200, 'rows': 2, 'placeholder': _('Description')}),
                required=False
            )
        
        if dataset:
            self.fields['source_id'].queryset = AnnotatedSentenceSource.objects.filter(dataset=dataset)