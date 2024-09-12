from django import forms
from signbank.animation.models import GlossAnimation
from signbank.dictionary.models import Gloss
import json
from django.utils.translation import gettext_lazy as _


class AnimationUploadForm(forms.ModelForm):
    """Form for animation upload"""

    class Meta:
        model = GlossAnimation
        fields = '__all__'


ATTRS_FOR_FORMS = {'class': 'form-control'}


class AnimationUploadForObjectForm(forms.Form):
    """Form for animation upload"""

    fbxfile = forms.FileField(label=_("Upload FBX File"),
                              widget=forms.FileInput(attrs={'accept': 'application/octet-stream'}))
    object_id = forms.CharField(widget=forms.HiddenInput)
    object_type = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput, required=False)
    recorded = forms.BooleanField(initial=False, required=False)
    offset = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        languages = kwargs.pop('languages', [])
        dataset = kwargs.pop('dataset', None)
        super(AnimationUploadForObjectForm, self).__init__(*args, **kwargs)
