from django import forms
from signbank.video.models import Video, GlossVideo, Gloss
import json

class VideoUploadForm(forms.ModelForm):
    """Form for video upload"""
    
    class Meta:
        model = GlossVideo
        fields = '__all__'

class VideoUploadForObjectForm(forms.Form):
    """Form for video upload for a particular example sentence"""
    
    videofile = forms.FileField(label="Upload Video", widget=forms.FileInput(attrs={'accept':'video/mp4, video/quicktime'}))
    object_id = forms.CharField(widget=forms.HiddenInput)
    object_type = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)
    recorded = forms.BooleanField(initial=False, required=False)
    eaffile = forms.FileField(label="Upload EAF", widget=forms.FileInput(attrs={'accept':'text/xml'}), required=False)
    feedbackdata = forms.CharField(widget=forms.HiddenInput, required=False)
    translations = forms.CharField(widget=forms.HiddenInput, required=False)
    contexts = forms.CharField(widget=forms.HiddenInput, required=False)
