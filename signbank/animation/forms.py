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

    file = forms.FileField(label=_("Upload Animation File"),
                              widget=forms.FileInput(attrs={'accept': 'application/octet-stream'}))
    gloss_id = forms.CharField(widget=forms.HiddenInput)
    object_type = forms.CharField(widget=forms.HiddenInput)
    redirect = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        languages = kwargs.pop('languages', [])
        dataset = kwargs.pop('dataset', None)
        super(AnimationUploadForObjectForm, self).__init__(*args, **kwargs)
