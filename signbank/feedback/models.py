from django.db import models, OperationalError, ProgrammingError
from django.contrib.auth import models as authmodels
from django.conf import settings
from signbank.settings.base import COMMENT_VIDEO_LOCATION, WRITABLE_FOLDER
import os
from signbank.video.fields import VideoUploadToFLVField

from signbank.dictionary.models import *
#from signbank.dictionary.models import Gloss
# models to represent the feedback from users in the site

import string

def t(message):
    """Replace $country and $language in message with dat from settings"""
    
    tpl = string.Template(message)
    return tpl.substitute(country=settings.COUNTRY_NAME, language=settings.LANGUAGE_NAME)



from django import forms

STATUS_CHOICES = ( ('unread', 'unread'),
                   ('read', 'read'),
                   ('deleted', 'deleted'),
                 )



class InterpreterFeedback(models.Model):
    """Feedback on a sign from an interpreter"""                

    class Meta:
        ordering = ['-date']
        permissions = (('view_interpreterfeedback', "Can View Interpreter Feedback"),)

    #gloss = models.ForeignKey(Gloss)
    comment = models.TextField('Note')
    user = models.ForeignKey(authmodels.User)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
    
class InterpreterFeedbackForm(forms.ModelForm):
    
    class Meta:
        model = InterpreterFeedback
        fields = ['comment']
        widgets={'comment': forms.Textarea(attrs={'rows':6, 'cols':80})}
    

class GeneralFeedback(models.Model):
 
    comment = models.TextField(blank=True)
    video = models.FileField(upload_to=settings.COMMENT_VIDEO_LOCATION, blank=True) 
    user = models.ForeignKey(authmodels.User)
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
    

try:
	signLanguageChoices = [ (0, '---------') ] + [ ( sl.id, sl.name ) for sl in SignLanguage.objects.all() ]
except (OperationalError, ProgrammingError) as e:
	signLanguageChoices = []

if settings.LANGUAGE_NAME == "BSL":
    whereusedChoices = (('Belfast', 'Belfast'),
                        ('Birmingham', 'Birmingham'),
                        ('Bristol', 'Bristol'),
                        ('Cardiff', 'Cardiff'),
                        ('Glasgow', 'Glasgow'),
                        ('London', 'London'),
                        ('Manchester', 'Manchester'),
                        ('Newcastle', 'Newcastle'),
                        ('Other', 'Other (note in comments)'),
                        ("Don't Know", "Don't Know"),
                        ('N/A', 'N/A'),
                        )
elif settings.LANGUAGE_NAME == "Global":
    whereusedChoices = (
                            (0, (
                                    ('n/a', 'N/A'),
                                )
                             ),
                            (1, (
                                        ('1', 'Groningen'),
                                        ('2', 'Amsterdam'),
                                        ('3', 'Voorburg'),
                                        ('4', 'Rotterdam'),
                                        ('5', 'Gestel'),
                                        ('6', 'Unknown'),
                                )
                            ),
                            (4, (
                                        ('7', 'Beijing'),
                                        ('8', 'Shanghai'),
                                        ('9', 'Nanjing'),
                                        ('10', 'Unknown'),
                                )
                             ),
                            (7, (
                                        ('11', 'Ambon'),
                                        ('12', 'Makassar'),
                                        ('13', 'Padang'),
                                        ('14', 'Pontianak'),
                                        ('15', 'Singaradja'),
                                        ('16', 'Solo'),
                                )
                             ),
                        )
else:
    whereusedChoices = (('auswide', 'Australia Wide'),
                        ('dialectN', 'Dialect Sign (North)'),
                        ('dialectS', 'Dialect Sign (South)'),
                        ('nsw', "New South Wales"),
                        ('vic', "Victoria"),
                        ('qld', "Queensland"),
                        ('wa', "Western Australia"),
                        ('sa', "South Australia"),
                        ('tas', "Tasmania"),
                        ('nt', "Northern Territory"),
                        ('act', "Australian Capital Territory"),
                        ('dk', "Don't Know"),
                        ('n/a', "N/A")
                        )

likedChoices =    ( (1, "Morpheme"),
                    (0, "Sign")
                    )
                                        
useChoices =      ( (1, "Yes"),
                    (2, "Sometimes"), 
                    (3, "Not Often"),
                    (4, "No"),
                    (0, "N/A") 
                    )
                         
suggestedChoices =( (1, "Yes"),
                    (2, "Sometimes"), 
                    (3, "Don't Know"),
                    (4, "Perhaps"),
                    (5, "No"),
                    (0, "N/A")
                    )
                    
correctChoices =  ( (1, "Yes"),
                    (2, "Mostly Correct"), 
                    (3, "Don't Know"),
                    (4, "Mostly Wrong"),
                    (5, "No"),
                    (0, "N/A") 
                    )
                    
class SignFeedback(models.Model):
    """Store feedback on a particular sign"""
    
    user = models.ForeignKey(authmodels.User, editable=False)
    date = models.DateTimeField(auto_now_add=True)
    
    translation = models.ForeignKey(Translation, editable=False)
    
    comment = models.TextField("Comment or new keywords.", blank=True)
    kwnotbelong = models.TextField("List of keywords that DO NOT belong", blank=True)

    isAuslan = models.IntegerField(t("Is this sign an $language Sign?"), choices=signLanguageChoices)
    whereused = models.CharField("Where is this sign used?", max_length=10, choices=whereusedChoices)
    like = models.IntegerField("Do you like this sign?", choices=likedChoices)
    use = models.IntegerField("Do you use this sign?", choices=useChoices)
    suggested = models.IntegerField("If this sign is a suggested new sign, would you use it?", default=3, choices=suggestedChoices)
    correct = models.IntegerField("Is the information about the sign correct?", choices=correctChoices)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
    
    def __str__(self):
        return str(self.translation.translation) + " by " + str(self.user) + " on " + str(self.date)

    class Meta:
        ordering = ['-date']


class SignFeedbackForm(forms.Form):
    """Form for input of sign feedback"""

    # isAuslan now stores Sign Language
    isAuslan = forms.ChoiceField(choices=signLanguageChoices, initial=0)
    # whereused now stores Dialect
    whereused = forms.ChoiceField(choices=whereusedChoices, initial="n/a")
    #whereused = forms.CharField(initial='n/a', widget=forms.HiddenInput)
    like = forms.ChoiceField(choices=likedChoices, widget=forms.RadioSelect)
    #like = forms.IntegerField(initial=0, widget=forms.HiddenInput)
    use = forms.ChoiceField(choices=useChoices, initial=0,  widget=forms.RadioSelect)
    #use = forms.IntegerField(initial=0, widget=forms.HiddenInput)
    suggested = forms.ChoiceField(choices=suggestedChoices, initial=3, required=False, widget=forms.RadioSelect)
    #suggested = forms.IntegerField(initial=0, widget=forms.HiddenInput)
    correct = forms.ChoiceField(choices=correctChoices, initial=0, widget=forms.RadioSelect)
    #correct = forms.IntegerField(initial=0, widget=forms.HiddenInput)
    kwnotbelong = forms.CharField(label="List keywords", required=False, widget=forms.Textarea(attrs={'rows':6, 'cols':80}))
    comment = forms.CharField(label="Comment or new keywords", required=True, widget=forms.Textarea(attrs={'rows':6, 'cols':80}))

 
handformChoices = build_choice_list("Handedness")

handshapeChoices = build_choice_list("Handshape")

locationChoices = build_choice_list("Location")

handbodycontactChoices = build_choice_list("ContactType")

directionChoices = build_choice_list("MovementDir")

movementtypeChoices = build_choice_list("MovementShape")

smallmovementChoices = build_choice_list("JointConfiguration")

repetitionChoices = ((0, 'None'),
                      (493, 'Do the movement once'),
                      (494, 'Do the movement twice'),
                      (495, 'Repeat the movement several times')
                      )

relativelocationChoices = build_choice_list("Location")

handinteractionChoices = build_choice_list("RelatArtic")

                       
class MissingSignFeedbackForm(forms.Form):   
    handform = forms.ChoiceField(choices=handformChoices,  required=False,
        label='How many hands are used to make this sign?')
    handshape = forms.ChoiceField(choices=handshapeChoices, required=False,
        label='What is the handshape?')
    althandshape = forms.ChoiceField(choices=handshapeChoices, required=False, 
        label='What is the handshape of the left hand?')    
    location = forms.ChoiceField(choices=locationChoices, required=False,
        label='Choose the location of the sign on, or near the body')
    relativelocation = forms.ChoiceField(choices=relativelocationChoices, 
        label='Choose the location of the right hand on, or near the left hand', required=False)
    handbodycontact = forms.ChoiceField(choices=handbodycontactChoices, 
        label='Contact between hands and body', required=False)
    handinteraction = forms.ChoiceField(choices=handinteractionChoices, 
        label='Interaction between hands', required=False)
    direction = forms.ChoiceField(choices=directionChoices, 
        label='Movement direction of the hand(s)', required=False)
    movementtype = forms.ChoiceField(choices=movementtypeChoices, 
        label='Type of movement', required=False)
    smallmovement = forms.ChoiceField(choices=smallmovementChoices, 
        label='Small movements of the hand(s) and fingers', required=False)
    repetition = forms.ChoiceField(choices=repetitionChoices, 
        label='Number of movements', required=False)
    
    meaning = forms.CharField(label='Sign Meaning', widget=forms.Textarea(attrs={'rows':6, 'cols':80}))
    video = forms.FileField(required=False, widget=forms.FileInput(attrs={'size':'60'}))
    comments = forms.CharField(label='Further Details', widget=forms.Textarea(attrs={'rows':6, 'cols':80}), required=True)
    

class MissingSignFeedback(models.Model):    
    user = models.ForeignKey(authmodels.User)
    date = models.DateTimeField(auto_now_add=True)
    handform = models.IntegerField(choices=handformChoices, blank=True, default=0)
    handshape = models.IntegerField(choices=handshapeChoices, blank=True, default=0)
    althandshape = models.IntegerField(choices=handshapeChoices, blank=True, default=0)    
    location = models.IntegerField(choices=locationChoices, blank=True, default=0)
    relativelocation = models.IntegerField(choices=relativelocationChoices, blank=True, default=0)
    handbodycontact = models.IntegerField(choices=handbodycontactChoices, blank=True, default=0)
    handinteraction = models.IntegerField(choices=handinteractionChoices, blank=True, default=0)
    direction = models.IntegerField(choices=directionChoices, blank=True, default=0)
    movementtype = models.IntegerField(choices=movementtypeChoices, blank=True, default=0)
    smallmovement = models.IntegerField(choices=smallmovementChoices, blank=True, default=0)
    repetition = models.IntegerField(choices=repetitionChoices, blank=True, default=0)
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
