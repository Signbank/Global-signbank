from django.db import models
from django.contrib.auth import models as authmodels
from django.conf import settings
from signbank.video.fields import VideoUploadToFLVField

from signbank.dictionary.models import *
from signbank.dictionary.models import Gloss
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

    gloss = models.ForeignKey(Gloss)
    comment = models.TextField('Note')
    user = models.ForeignKey(authmodels.User)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
    
class InterpreterFeedbackForm(forms.ModelForm):
    
    class Meta:
        model = InterpreterFeedback
        fields = ['comment']
        widgets={'comment': forms.Textarea(attrs={'cols': 30, 'rows': 2})}
    

class GeneralFeedback(models.Model):
 
    comment = models.TextField(blank=True)
    video = models.FileField(upload_to=settings.COMMENT_VIDEO_LOCATION, blank=True) 
    user = models.ForeignKey(authmodels.User)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
           
    class Meta:
        ordering = ['-date']

class GeneralFeedbackForm(forms.Form):
    """Form for general feedback"""
    
    comment = forms.CharField(widget=forms.Textarea(attrs={'cols':'64'}), required=False)
    video = VideoUploadToFLVField(required=False, widget=forms.FileInput(attrs={'size':'60'}))

    
    
isAuslanChoices = ( (1, "yes"), 
                    (2, "Perhaps"), 
                    (3, "Don't know"),
                    (4, "Don't think so"),
                    (5, "No"),
                    (0, "N/A")
                    )

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

likedChoices =    ( (1, "yes"), 
                    (2, "A little"), 
                    (3, "Don't care"),
                    (4, "Not much"),
                    (5, "No"),
                    (0, "N/A")
                    )
                                        
useChoices =      ( (1, "yes"), 
                    (2, "Sometimes"), 
                    (3, "Not Often"),
                    (4, "No"),
                    (0, "N/A") 
                    )
                         
suggestedChoices =( (1, "yes"), 
                    (2, "Sometimes"), 
                    (3, "Don't Know"),
                    (4, "Perhaps"),
                    (5, "No"),
                    (0, "N/A")
                    )
                    
correctChoices =  ( (1, "yes"), 
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
    
    comment = models.TextField("Please give us your comments about this sign. For example: do you think there are other keywords that belong with this sign? Please write your comments or new keyword/s below.", blank=True)
    kwnotbelong = models.TextField("Is there a keyword or keyword/s that DO NOT belong with this sign? Please provide the list of keywords below", blank=True)
     
    isAuslan = models.IntegerField(t("Is this sign an $language Sign?"), choices=isAuslanChoices)
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
    
    isAuslan = forms.ChoiceField(choices=isAuslanChoices, initial=0, widget=forms.RadioSelect)
    #isAuslan = forms.IntegerField(initial=0, widget=forms.HiddenInput)
    whereused = forms.ChoiceField(choices=whereusedChoices, initial="n/a")
    #whereused = forms.CharField(initial='n/a', widget=forms.HiddenInput)
    like = forms.ChoiceField(choices=likedChoices,  initial=0, widget=forms.RadioSelect)
    #like = forms.IntegerField(initial=0, widget=forms.HiddenInput)
    use = forms.ChoiceField(choices=useChoices, initial=0,  widget=forms.RadioSelect)
    #use = forms.IntegerField(initial=0, widget=forms.HiddenInput)
    suggested = forms.ChoiceField(choices=suggestedChoices, initial=3, required=False, widget=forms.RadioSelect)
    #suggested = forms.IntegerField(initial=0, widget=forms.HiddenInput)
    correct = forms.ChoiceField(choices=correctChoices, initial=0, widget=forms.RadioSelect)
    #correct = forms.IntegerField(initial=0, widget=forms.HiddenInput)
    kwnotbelong = forms.CharField(label="List keywords", required=False, widget=forms.Textarea) 
    comment = forms.CharField(required=False, widget=forms.Textarea)

 
handformChoices = (
                    (1, 'One handed'),
                    (2, 'Two handed (same shape for each hand)'),
                    (3, 'Two handed (diffent shapes for each hand)')
                    )
  
handshapeChoices = ((0, 'None'),
                     (291, 'Animal'),
                     (292, 'Animal-flick'),
                     (293, 'Bad'),
                     (294, 'Ball'),
                     (295, 'Cup'),
                     (296, 'Cup-flush'),
                     (297, 'Cup-thumb'),
                     (298, 'Eight'),
                     (299, 'Eight-hook'),
                     (300, 'Fist-A'),
                     (301, 'Fist-S'),
                     (302, 'Flat'),
                     (303, 'Flat-bent'),
                     (304, 'Flat-B'),
                     (305, 'Flat-flush'),
                     (306, 'Flick'),
                     (307, 'Flick-gay'),
                     (308, 'Four'),
                     (309, 'Five'),
                     (310, 'Good'),
                     (311, 'Good-6'),
                     (312, 'Gun'),
                     (313, 'Gun-hook'),
                     (314, 'Hook'),
                     (315, 'Kneel'),
                     (316, 'Letter-C'),
                     (317, 'Letter-M'),
                     (318, 'Letter-N'),
                     (319, 'Love'),
                     (320, 'Middle'),
                     (321, 'Mother'),
                     (322, 'Nine'),
                     (323, 'Point-1'),
                     (324, 'Point-D'),
                     (325, 'Point-flush'),
                     (326, 'Okay-flat'),
                     (327, 'Okay-F'),
                     (328, 'Okay-O'),
                     (329, 'Old-seven'),
                     (330, 'Plane'),
                     (331, 'Perth'),
                     (332, 'Round-O'),
                     (333, 'Round-flat'),
                     (334, 'Round-E'),
                     (335, 'Rude'),
                     (336, 'Salt'),
                     (337, 'Salt-flick'),
                     (338, 'Small'),
                     (339, 'Soon'),
                     (340, 'Spoon'),
                     (341, 'Spoon-hook'),
                     (342, 'Spoon-thumb'),
                     (343, 'Thick'),
                     (344, 'Three'),
                     (345, 'Three-hook'),
                     (346, 'Two'),
                     (347, 'Wish'),
                     (348, 'Write'),
                     (349, 'Write-flat')
                     )
                     
locationChoices = ((0, 'None'),
                    (257, 'Top of head'),
                    (258, 'Forehead'),
                    (259, 'Temple'),
                    (260, 'Eyes'),
                    (261, 'Nose'),
                    (262, 'Whole of face'),
                    (263, 'Cheekbone'),
                    (264, 'Ear'),
                    (265, 'Cheek'),
                    (266, 'Mouth and lips'),
                    (267, 'Chin'),
                    (268, 'Neck'),
                    (269, 'Shoulder'),
                    (270, 'Chest'),
                    (271, 'Stomach'),
                    (272, 'Waist'),
                    (273, 'Lower waist'),
                    (274, 'Upper arm'),
                    (275, 'Elbow')
                    )

handbodycontactChoices = ((0, 'None'),
                           (240, 'Contact at start of movement'),
                           (241, 'Contact at end of movement'),
                           (242, 'Two contacts (tap)'),
                           (243, 'Contact during (rub/stroke)')
                           )

directionChoices = ((0, 'None'),
                     (472, 'Up'),
                     (473, 'Down'),
                     (474, 'Up and down'),
                     (475, 'Left'),
                     (476, 'Right'),
                     (477, 'Side to side'),
                     (478, 'Away'),
                     (479, 'Towards'),
                     (480, 'To and fro')
                     )
                     
movementtypeChoices = ((0, 'None'),
                        (481, 'Straight'),
                        (482, 'Curved'),
                        (483, 'Circle'),
                        (484, 'Zig-zag')
                        )

smallmovementChoices = ((0, 'None'),
                         (485, 'Straighten from bent'),
                         (486, 'Bend fingers'),
                         (487, 'Nod at wrist'),
                         (488, 'Straighten fingers'),
                         (489, 'Open handshape'),
                         (490, 'Close handshape'),
                         (491, 'Wriggle fingers'),
                         (492, 'Crumble fingers')
                         )

repetitionChoices = ((0, 'None'),
                      (493, 'Do the movement once'),
                      (494, 'Do the movement twice'),
                      (495, 'Repeat the movement several times')
                      )

relativelocationChoices = ((0, 'None'),
                            (283, 'Forearm'),
                            (284, 'Wrist'),
                            (285, 'Pulse'),
                            (286, 'Back of hand'),
                            (287, 'Palm'),
                            (288, 'Sides of hand'),
                            (289, 'Fingertips')
                            )

handinteractionChoices = ((0, 'None'),
                       (468, 'Alternate hands (one moves, then the other moves)'),
                       (469, 'Move the hands towards each other'),
                       (470, 'Move the hands away from each other'),
                       (471, 'The hands cross over each other')
                       )

                       
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
    
    meaning = forms.CharField(label='Sign Meaning', 
        widget=forms.Textarea(attrs={'cols':'55', 'rows':'8'}))
    video = forms.FileField(required=False, 
        widget=forms.FileInput(attrs={'size':'60'}))
    comments = forms.CharField(label='Further Details', 
        widget=forms.Textarea(attrs={'cols':'55', 'rows':'8'}), required=False)
    

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
    