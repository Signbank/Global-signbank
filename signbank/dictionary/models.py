"""Models for the NGT database.

These are refactored from the original database to 
normalise the data and hopefully make it more
manageable.  

"""

from django.db.models import Q
from django.db import models
from django.conf import settings
from django.http import Http404 
import tagging

import sys, os
import json
from collections import OrderedDict

#from signbank.video.models import GlossVideo

#from models_legacy import Sign


class Translation(models.Model):
    """A Dutch translation of NGT signs"""
     
    gloss = models.ForeignKey("Gloss")
    translation = models.ForeignKey("Keyword")
    index = models.IntegerField("Index")
    
    def __str__(self):
        #return unicode(self.gloss).encode('ascii','ignore')+"-"+unicode(self.translation).encode('ascii','ignore')
        return self.gloss.idgloss.encode('utf-8') + '-' + self.translation.text.encode('utf-8')

    def get_absolute_url(self):
        """Return a URL for a view of this translation."""
        
        alltrans = self.translation.translation_set.all()
        idx = 0
        for tr in alltrans: 
            if tr == self:
                return "/dictionary/words/"+str(self.translation)+"-"+str(idx+1)+".html"
            idx += 1
        return "/dictionary/"
        
    
    class Meta:
        ordering = ['gloss', 'index']
        
    class Admin:
        list_display = ['gloss', 'translation']
        search_fields = ['gloss__idgloss']
    
    
    
class Keyword(models.Model):
    """A Dutch keyword that is a possible translation equivalent of a sign"""
    
    def __str__(self):
        return self.text.encode('utf-8')
    
    text = models.CharField(max_length=100, unique=True)
    
    def inWeb(self):
        """Return True if some gloss associated with this
        keyword is in the web version of the dictionary"""
        
        return len(self.translation_set.filter(gloss__inWeb__exact=True)) != 0
            
    class Meta:
        ordering = ['text']
        
    class Admin:
        search_fields = ['text']
        
        
        
    def match_request(self, request, n):
        """Find the translation matching a keyword request given an index 'n'
        response depends on login status
        Returns a tuple (translation, count) where count is the total number
        of matches."""
        
        if request.user.has_perm('dictionary.search_gloss'):
            alltrans = self.translation_set.all()
        else:
            alltrans = self.translation_set.filter(gloss__inWeb__exact=True)
        
        # remove crude signs for non-authenticated users if ANON_SAFE_SEARCH is on
        try:
            crudetag = tagging.models.Tag.objects.get(name='lexis:crude')
        except:
            crudetag = None
            
        safe = (not request.user.is_authenticated()) and settings.ANON_SAFE_SEARCH
        if safe and crudetag:
            alltrans = [tr for tr in alltrans if not crudetag in tagging.models.Tag.objects.get_for_object(tr.gloss)]
        
        # if there are no translations, generate a 404
        if len(alltrans) == 0:
            raise Http404
        
        # take the nth translation if n is in range
        # otherwise take the last
        if n-1 < len(alltrans):
            trans = alltrans[n-1]
        else:
            trans = alltrans[len(alltrans)-1]
        
        return (trans, len(alltrans))
    
    
DEFN_ROLE_CHOICES = (('note', 'Note'),
                     ('privatenote', 'Private Note'),
                     ('phon', 'Phonology'),
                     ('todo', 'To Do'),
                     ('sugg', 'Suggestion for other gloss'),
                     )


class Definition(models.Model):
    """An English text associated with a gloss. It's called a note in the web interface"""
    
    def __str__(self):
        return str(self.gloss)+"/"+self.role
        
    gloss = models.ForeignKey("Gloss")
    text = models.TextField()
    role = models.CharField("Type",max_length=20, choices=DEFN_ROLE_CHOICES)
    count = models.IntegerField()
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ['gloss', 'role', 'count']
        
    class Admin:
        list_display = ['gloss', 'role', 'count', 'text']
        list_filter = ['role']
        search_fields = ['gloss__idgloss']
        
class Language(models.Model):
    """A sign language name"""
        
    class Meta:
        ordering = ['name']
        
    name = models.CharField(max_length=20)
    description = models.TextField()
    
    def __str__(self):
        return self.name

class Dialect(models.Model):
    """A dialect name - a regional dialect of a given Language"""
    
    class Meta:
        ordering = ['language', 'name']
    
    language = models.ForeignKey(Language)
    name = models.CharField(max_length=20)
    description = models.TextField()
    
    def __str__(self):
        return self.language.name+"/"+self.name  

class RelationToForeignSign(models.Model):
    """Defines a relationship to another sign in another language (often a loan)"""
    
    def __str__(self):
        return str(self.gloss)+"/"+self.other_lang+','+self.other_lang_gloss;
        
    gloss = models.ForeignKey("Gloss")
    loan = models.BooleanField("Loan Sign",default=False)
    other_lang = models.CharField("Related Language",max_length=20)  
    other_lang_gloss = models.CharField("Gloss in related language",max_length=50)

    class Meta:
        ordering = ['gloss', 'loan', 'other_lang','other_lang_gloss']
        
    class Admin:
        list_display = ['gloss', 'loan', 'other_lang','other_lang_gloss']
        list_filter = ['other_lang']
        search_fields = ['gloss__idgloss']

handednessChoices = (('0','No Value Set'),
		     ('1','N/A'),
                     ('2','1'),
                     ('3','2'),
                     ('4','2a'),
                     ('5','2s'),
                     ('6','X'));
  
handshapeChoices =  (('0', 'No Value Set'),
                    ('1', 'N/A'),
                    ('2', 'J + beak2'),
                    ('3', '5'),
                    ('4', 'Money'),
                    ('5', 'V'),
                    ('6', 'B'),
                    ('7', 'Y'),
                    ('8', 'S'),
                    ('9', 'L'),
                    ('10', 'Baby-c'),
                    ('11', 'B-relaxed'),
                    ('12', 'C-spread'),
                    ('13', 'B-curved'),
                    ('14', 'N'),
                    ('15', '1'),
                    ('16', 'W'),
                    ('17', 'Beak2'),
                    ('18', 'Q'),
                    ('19', '5r'),
                    ('20', 'V-curved'),
                    ('21', '1-curved'),
                    ('22', 'Beak'),
                    ('23', 'Beak2-spread'),
                    ('24', 'A'),
                    ('25', 'I'),
                    ('26', 'B-bent'),
                    ('27', 'C'),
                    ('28', 'T'),
                    ('29', 'Baby-beak'),
                    ('30', '5m'),
                    ('31', 'Shower'),
                    ('32', 'O'),
                    ('33', 'Flexed arm'),
                    ('34', 'D'),
                    ('35', '4'),
                    ('36', 'M + v'),
                    ('37', '3'),
                    ('38', 'Baby-o'),
                    ('39', 'F'),
                    ('40', 'M'),
                    ('41', 'Flower'),
                    ('42', 'K'),
                    ('43', '5mx'),
                    ('44', 'B + s'),
                    ('45', 'Asl-t'),
                    ('46', 'O2'),
                    ('47', 'R'),
                    ('48', '9'),
                    ('49', '5rx'),
                    ('50', 'Beak, pinkie extended'),
                    ('51', 'S + w'),
                    ('52', 'L2'),
                    ('53', 'L-curved'),
                    ('54', 'W-curved'),
                    ('55', 'Q5'),
                    ('56', 'E'),
                    ('57', 'T + l'),
                    ('58', 'N + e'),
                    ('59', 'Horns'),
                    ('60', 'P'),
                    ('61', 'C-spread, index extended'),
                    ('62', 'Baby-c'),
                    ('63', 'Money-open'),
                    ('64', 'Beak, index extended'),
                    ('65', '5px'),
                    ('66', 'Y mrp-bent'),
                    ('67', 'Mrp-bent'),
                    ('68', 'Mrp-curved'),
                    ('69', 'O3'),
                    ('70', 'T + v'),
                    ('71', 'V + o'),
                    ('72', 'C, extended index'),
                    ('73', '5 + v'),
                    ('74', 'A-curved'),
                    ('75', 'C-spread-2'),
                    ('76', 'J + l'),
                    ('77', 'J + n'),
                    ('78', 'L + mrp bent'),
                    ('79', 'O + k'),
                    ('80', 'Middle finger'),
                    ('81', '1 + m'),
                    ('82', 'S + i'));
                     
locationChoices = ( ('0', 'No Value Set'),
                    ('1', 'N/A'),
                    ('2', 'Neutral space > head'),
                    ('3', 'Neutral space'),
                    ('4', 'Shoulder'),
                    ('5', 'Weak hand'),
                    ('6', 'Weak hand > arm'),
                    ('7', 'Forehead'),
                    ('8', 'Chest'),
                    ('9', 'Neck'),
                    ('10', 'Head'),
                    ('11', 'Weak hand: back'),
                    ('12', 'Chin'),
                    ('13', 'Ring finger'),
                    ('14', 'Forehead, belly'),
                    ('15', 'Eye'),
                    ('16', 'Cheekbone'),
                    ('17', 'Face'),
                    ('18', 'Ear'),
                    ('19', 'Mouth'),
                    ('20', 'Low in neutral space'),
                    ('21', 'Arm'),
                    ('22', 'Nose'),
                    ('23', 'Cheek'),
                    ('24', 'Heup'),
                    ('25', 'Body'),
                    ('26', 'Belly'),
                    ('27', 'Tongue'),
                    ('28', 'Chin > neutral space'),
                    ('29', 'Locative'),
                    ('30', 'Head ipsi'),
                    ('31', 'Forehead > chin'),
                    ('32', 'Head > shoulder'),
                    ('33', 'Chin > weak hand'),
                    ('34', 'Forehead > chest'),
                    ('35', 'Borst contra'),
                    ('36', 'Weak hand: palm'),
                    ('37', 'Back of head'),
                    ('38', 'Above head'),
                    ('39', 'Next to trunk'),
                    ('40', 'Under chin'),
                    ('41', 'Head > weak hand'),
                    ('42', 'Borst ipsi'),
                    ('43', 'Temple'),
                    ('44', 'Upper leg'),
                    ('45', 'Leg'),
                    ('46', 'Mouth ipsi'),
                    ('47', 'High in neutral space'),
                    ('48', 'Mouth > chest'),
                    ('49', 'Chin ipsi'),
                    ('50', 'Wrist'),
                    ('51', 'Lip'),
                    ('52', 'Neck > chest'),
                    ('53', 'Cheek + chin'),
                    ('54', 'Upper arm'),
                    ('55', 'Shoulder contra'),
                    ('56', 'Forehead > weak hand'),
                    ('57', 'Neck ipsi'),
                    ('58', 'Mouth > weak hand'),
                    ('59', 'Weak hand: thumb side'),
                    ('60', 'Between thumb and index finger'),
                    ('61', 'Neutral space: high'),
                    ('62', 'Chin contra'),
                    ('63', 'Upper lip'),
                    ('64', 'Forehead contra'),
                    ('65', 'Side of upper body'),
                    ('66', 'Weak hand: tips'),
                    ('67', 'Mouth + chin'),
                    ('68', 'Side of head'),
                    ('69', 'Head > neutral space'),
                    ('70', 'Chin > chest'),
                    ('71', 'Face + head'),
                    ('72', 'Cheek contra'),
                    ('73', 'Belly ipsi'),
                    ('74', 'Chest contra'),
                    ('75', 'Neck contra'),
                    ('76', 'Back of the head'),
                    ('77', 'Elbow'),
                    ('78', 'Temple > chest'),
                    ('79', 'Thumb'),
                    ('80', 'Middle finger'),
                    ('81', 'Pinkie'),
                    ('82', 'Index finger'),
                    ('83', 'Back'),
                    ('84', 'Ear > cheek'),
                    ('85', 'Knee'),
                    ('86', 'Shoulder contra > shoulder ipsi'),
                    ('87', 'Mouth + cheek'))

# these are values for prim2ndloc fin2ndloc introduced for BSL, the names might change
BSLsecondLocationChoices = (
                    ('notset', 'No Value Set'),
                    ('0', 'N/A'),
                    ('back', 'Back'),
                    ('palm', 'Palm'),
                    ('radial', 'Radial'),
                    ('ulnar', 'Ulnar'),
                    ('fingertip(s)', 'Fingertips'),
                    ('root', 'Root')
                    )

palmOrientationChoices = (
                    ('notset', 'No Value Set'),
                    ('prone','Prone'),
                    ('neutral', 'Neutral'),
                    ('supine', 'Supine'),
                    ('0', 'N/A'),      
                          )

relOrientationChoices = (
                    ('notset', 'No Value Set'),
                    ('palm', 'Palm'),
                    ('back', 'Back'),
                    ('root', 'Root'), 
                    ('radial', 'Radial'),
                    ('ulnar', 'Ulnar'),
                    ('fingertip(s)', 'Fingertips'),
                    ('0', 'N/A'),  
                        )

relatArticChoices=(
                    ("0", 'No Value Set'),
                    ("1", 'N/A'),
                    ("2", 'One hand behind the other'),
                    ("3", 'One hand above the other'),
                    ("4", 'Hands move around each other'),
                    ("5", 'Strong hand passes through weak hand'),
                    ("6", 'One hand after the other'),
                    ("7", 'One hand on top of the other'),
                    ("8", 'Around the weak hand'),
                    ("9", 'Strong hand moves through weak hand'),
                    ("10", 'Fingers interwoven'),
                    ("11", 'Weak hand within strong hand'),
                    ("12", 'Hands rotate around each other'),
                    ("13", 'Fingertips touching'),
                    ("14", 'Passing under the weak hand'),
                    ("15", 'Passing above the wrist'),
                    ("16", 'Passing over the weak hand'),
                    ("17", 'Strong hand behind weak hand'),
                    ("18", 'Strong hand around weak hand'),
                    ("19", 'Hands interlocked between thumb and index'),
                    ("20", 'Hands cross'),
                    ("21", 'Hands overlap'),
                    ("22", 'Hand appears behind weak hand'),
                    ("23", 'Strong hand under weak hand'),
                    ("24", 'One hand above or beside the other'),
                    ("25", 'Hands start crossed'),
                    ("26", 'Hands move in tandem'),
                    ("27", 'Interlocked'),
                    ("28", 'One hand a bit higher'),
                    ("29", 'Strong hand hangs across weak hand'),
                    ("30", 'Strong hand moves over tips of weak hand'),
                    ("31", 'Fingers interlocked'),
                    ("32", 'Weak hand around thumb'),
                    ("33", 'Movement mirrored'),
                    ("34", 'Hands rotate around each other, then contacting movement'),
                    ("35", 'Thumbs rotate about each other'),
                    ("36", 'Hands rotate in the same direction'),
                    ("37", 'Crossed'),
                    ("38", 'Below the weak hand'),
		)

absOriPalmChoices = (
                    ('0', 'No Value Set'),
                    ('1', 'N/A'),
                    ('2', 'Downwards'),
                    ('3', 'Towards each other'),
                    ('4', 'Backwards'),
                    ('5', 'Upwards'),
                    ('6', 'Inwards'),
                    ('7', 'Forwards'),
                    ('8', 'Backwards > forwards'),
                    ('9', 'Inwards, forwards'),
                    ('10', 'Forwards, sidewards'),
                    ('11', 'Downwards, sidewards'),
                    ('12', 'Variable'),
                    ('13', 'Outwards'),
                    ('14', 'Backs towards each other'),
                    ('15', 'Inwards > backwards'),
                    ('16', 'Sidewards'),
                    ('17', 'Forwards, downwards'),
)

absOriFingChoices = (
                    ('0', 'No Value Set'),
                    ('1', 'N/A'),
                    ('2', 'Inwards'),
                    ('3', 'Downwards'),
                    ('4', 'Upwards'),
                    ('5', 'Upwards, forwards'),
                    ('6', 'Forwards'),
                    ('7', 'Backwards'),
                    ('8', 'Towards location'),
                    ('9', 'Inwards, upwards'),
                    ('10', 'Back/palm'),
                    ('11', 'Towards each other'),
                    ('12', 'Neutral'),
                    ('13', 'Forwards > inwards'),
                    ('14', 'Towards weak hand'),
)

relOriMovChoices = (
                    ('0', 'No Value Set'),
                    ('1', 'N/A'),
                    ('2', 'Pinkie'),
                    ('3', 'Palm'),
                    ('4', 'Tips'),
                    ('5', 'Thumb'),
                    ('6', 'Basis'),
                    ('7', 'Back'),
                    ('8', 'Thumb/pinkie'),
                    ('9', 'Variable'),
                    ('10', 'Basis + palm'),
                    ('11', 'Basis + basis'),
                    ('12', 'Pinkie + back'),
                    ('13', 'Palm > basis'),
                    ('14', 'Palm > back'),
                    ('15', 'Back > palm'),
                    ('16', 'Basis, pinkie'),
                    ('17', 'Pinkie > palm'),
                    ('18', 'Basis > pinkie'),
                    ('19', 'Pinkie > palm > thumb'),
                    ('20', 'Back > basis'),
                    ('21', 'Thumb > pinkie'),
)

relOriLocChoices = (
                    ('0', 'No Value Set'),
                    ('1', 'N/A'),
                    ('2', 'Pinkie/thumb'),
)

handChChoices= (
                    ("0", 'No Value Set'),
                    ("1", 'N/A'),
                    ("2", '+ closing'),
                    ("3", 'Closing, opening'),
                    ("4", 'Closing a little'),
                    ("5", 'Opening'),
                    ("6", 'Closing'),
                    ("7", 'Bending'),
                    ("8", 'Curving'),
                    ("9", 'Wiggle'),
                    ("10", 'Unspreading'),
                    ("11", 'Extension'),
                    ("12", '>5'),
                    ("13", 'Partly closing'),
                    ("14", 'Closing one by one'),
                    ("15", '>s'),
                    ("16", '>b'),
                    ("17", '>a'),
                    ("18", '>1'),
                    ("19", 'Wiggle, closing'),
                    ("20", 'Thumb rubs finger'),
                    ("21", 'Spreading'),
                    ("22", '>i'),
                    ("23", '>l'),
                    ("24", '>5m'),
                    ("25", 'Thumb rubs fingers'),
                    ("26", 'Thumb curving'),
                    ("27", 'Thumbfold'),
                    ("28", 'Finger rubs thumb'),
                    ("29", '>o'),
                    ("30", '>t'),
                    ("31", 'Extension one by one'),
                )

movShapeChoices = (
                    ("0", 'No Value Set'),
                    ("1", 'N/A'),
                    ("2", 'Circle sagittal > straight'),
                    ("3", 'Rotation > straight'),
                    ("4", 'Arc'),
                    ("5", 'Rotation'),
                    ("6", 'Straight'),
                    ("7", 'Flexion'),
                    ("8", 'Circle sagittal'),
                    ("9", 'Arc horizontal'),
                    ("10", 'Arc up'),
                    ("11", 'Question mark'),
                    ("12", 'Zigzag'),
                    ("13", 'Arc outside'),
                    ("14", 'Circle horizontal'),
                    ("15", 'Extension'),
                    ("16", 'Abduction'),
                    ("17", 'Straight > abduction'),
                    ("18", 'Z-shape'),
                    ("19", 'Straight + straight'),
                    ("20", 'Arc > straight'),
                    ("21", 'Parallel arc > straight'),
                    ("22", 'Zigzag > straight'),
                    ("23", 'Arc down'),
                    ("24", 'Arc + rotation'),
                    ("25", 'Arc + flexion'),
                    ("26", 'Circle parallel'),
                    ("27", 'Arc front'),
                    ("28", 'Circle horizontal small'),
                    ("29", 'Arc back'),
                    ("30", 'Waving'),
                    ("31", 'Straight, rotation'),
                    ("32", 'Circle parallel + straight'),
                    ("33", 'Down'),
                    ("34", 'Thumb rotation'),
                    ("35", 'Circle sagittal small'),
                    ("36", 'Heart-shape'),
                    ("37", 'Circle'),
                    ("38", 'Cross'),
                    ("39", 'Supination'),
                    ("40", 'Pronation'),
                    ("41", 'M-shape'),
                    ("42", 'Circle sagittal big'),
                    ("43", 'Circle parallel small'),
                 )

movDirChoices = (
                    ("0", 'No Value Set'),
                    ("1", 'N/A'),
                    ("2", '+ forward'),
                    ("3", '> downwards'),
                    ("4", '> forwards'),
                    ("5", 'Backwards'),
                    ("6", 'Backwards > downwards'),
                    ("7", 'Directional'),
                    ("8", 'Downwards'),
                    ("9", 'Downwards + inwards'),
                    ("10", 'Downwards + outwards'),
                    ("11", 'Downwards > inwards'),
                    ("12", 'Downwards > outwards'),
                    ("13", 'Downwards > outwards, downwards'),
                    ("14", 'Downwards, inwards'),
                    ("15", 'Forward'),
                    ("16", 'Forwards'),
                    ("17", 'Forwards > downwards'),
                    ("18", 'Forwards > inwards'),
                    ("19", 'Forwards > sidewards > forwards'),
                    ("20", 'Forwards-backwards'),
                    ("21", 'Forwards, downwards'),
                    ("22", 'Forwards, inwards'),
                    ("23", 'Forwards, outwards'),
                    ("24", 'Forwards, upwards'),
                    ("25", 'Hands approach vertically'),
                    ("26", 'Inwards'),
                    ("27", 'Inwards > forwards'),
                    ("28", 'Inwards, downwards'),
                    ("29", 'Inwards, forwards'),
                    ("30", 'Inwards, upwards'),
                    ("31", 'No movement'),
                    ("32", 'Upwards'),
                    ("33", 'Upwards > downwards'),
                    ("34", 'Up and down'),
                    ("35", 'Upwards, inwards'),
                    ("36", 'Upwards, outwards'),
                    ("37", 'Upwards, forwards'),
                    ("38", 'Outwards'),
                    ("39", 'Outwards > downwards'),
                    ("40", 'Outwards > downwards > inwards'),
                    ("41", 'Outwards > upwards'),
                    ("42", 'Outwards, downwards > downwards'),
                    ("43", 'Outwards, forwards'),
                    ("44", 'Outwards, upwards'),
                    ("45", 'Rotation'),
                    ("46", 'To and fro'),
                    ("47", 'To and fro, forwards-backwards'),
                    ("48", 'Upwards/downwards'),
                    ("49", 'Variable'),
)

movManChoices = (
                    ("0", 'No Value Set'),
                    ("1", 'N/A'),
                    ("2", 'Short'),
                    ("3", 'Strong'),
                    ("4", 'Slow'),
                    ("5", 'Large, powerful'),
                    ("6", 'Long'),
                    ("7", 'Relaxed'),
                    ("8", 'Trill'),
                    ("9", 'Small'),
                    ("10", 'Tense'),
)

contTypeChoices = (
                    ("0", 'No Value Set'),
                    ("1", 'N/A'),
                    ("2", 'Brush'),
                    ("3", 'Initial > final'),
                    ("4", 'Final'),
                    ("5", 'Initial'),
                    ("6", 'Continuous'),
                    ("7", 'Contacting hands'),
                    ("8", 'Continuous + final'),
                    ("9", 'None + initial'),
                    ("10", '> final'),
                    ("11", 'None + final'),
)

namedEntChoices = (
                    ("0", 'No Value Set'),
                    ("1", 'N/A'),
                    ("2", 'Person'),
                    ("3", 'Public figure'),
                    ("4", 'Place'),
                    ("5", 'Region'),
                    ("6", 'Brand'),
                    ("7", 'Country'),
                    ("8", 'Device'),
                    ("9", 'Product'),
                    ("10", 'Project'),
                    ("11", 'Place nickname'),
                    ("12", 'Event'),
                    ("13", 'Newspaper'),
                    ("14", 'Story character'),
                    ("15", 'Continent'),
                    ("16", 'Organisation'),
                    ("17", 'Company'),
                    ("18", 'Team'),
                    ("19", 'Drink'),
                    ("20", 'Magazine'),
)

class FieldChoice(models.Model):

    field = models.CharField(max_length=50)
    english_name = models.CharField(max_length=50)
    machine_value = models.IntegerField()

    def __str__(self):

        return self.field + ': ' + self.english_name + ' (' + str(self.machine_value) + ')';

    class Meta:
        ordering = ['field','machine_value']

def build_choice_list(field):

    choice_list = [('0','-'),('1','N/A')];

    for choice in FieldChoice.objects.filter(field=field):
        choice_list.append((str(choice.machine_value),choice.english_name));

    return choice_list

class Gloss(models.Model):
    
    class Meta:
        verbose_name_plural = "Glosses"
        ordering = ['idgloss']
        permissions = (('update_video', "Can Update Video"),
                       ('search_gloss', 'Can Search/View Full Gloss Details'),
                       ('export_csv', 'Can export sign details as CSV'),
                       ('can_publish', 'Can publish signs and definitions'),
                       ('can_delete_unpublished', 'Can delete unpub signs or defs'),
                       ('can_delete_published', 'Can delete pub signs and defs'),
                       ('view_advanced_properties', 'Include all properties in sign detail view'),
                        )

    def __str__(self):
        return "%s" % (self.idgloss)
    
    def field_labels(self):
        """Return the dictionary of field labels for use in a template"""
        
        d = dict()
        for f in self._meta.fields:
            try:
                d[f.name] = self._meta.get_field(f.name).verbose_name
            except:
                pass
            
        return d
    
    def admin_fields(self):
        """Return a list of field values in settings.ADMIN_RESULT_FIELDS 
        for use in the admin list view"""
        
        result = []
        for field in settings.ADMIN_RESULT_FIELDS:
            fname = self._meta.get_field(field).verbose_name

            #First, try to give the human readable choice value back
            try:
                result.append((fname, getattr(self, 'get_'+field+'_display')()))

            #If that doesn't work, give the raw value back
            except AttributeError:
                result.append((fname, getattr(self, field)))


        return result
        
    
    idgloss = models.CharField("ID Gloss", max_length=50, help_text="""
    This is the unique identifying name of an entry of a sign form in the
database. No two Sign Entry Names can be exactly the same, but a "Sign
Entry Name" can be (and often is) the same as the Annotation Idgloss.""")    
  
    annotation_idgloss = models.CharField("Annotation ID Gloss: Dutch", blank=True, max_length=30, help_text="""
    This is the Dutch name of a sign used by annotators when glossing the corpus in
an ELAN annotation file. The Annotation Idgloss may be the same for two or
more entries (each with their own 'Sign Entry Name'). If two sign entries
have the same 'Annotation Idgloss' that means they differ in form in only
minor or insignificant ways that can be ignored.""") 
    # the idgloss used in transcription, may be shared between many signs

    annotation_idgloss_en = models.CharField("Annotation ID Gloss: English", blank=True, max_length=30, help_text="""
    This is the English name of a sign used by annotators when glossing the corpus in
an ELAN annotation file. The Annotation Idgloss may be the same for two or
more entries (each with their own 'Sign Entry Name'). If two sign entries
have the same 'Annotation Idgloss' that means they differ in form in only
minor or insignificant ways that can be ignored.""") 

    # languages that this gloss is part of
    language = models.ManyToManyField(Language)

    # these language fields are subsumed by the language field above
    bsltf = models.NullBooleanField("BSL sign", null=True, blank=True)
    asltf = models.NullBooleanField("ASL sign", null=True, blank=True)

    # these fields should be reviewed - do we put them in another class too?
    aslgloss = models.CharField("ASL gloss", blank=True, max_length=50) # American Sign Language gloss
    asloantf = models.NullBooleanField("ASL loan sign", null=True, blank=True)
 
    # loans from british sign language
    bslgloss = models.CharField("BSL gloss", max_length=50, blank=True) 
    bslloantf = models.NullBooleanField("BSL loan sign", null=True, blank=True)
 
    useInstr = models.CharField("Annotation instructions", max_length=50, blank=True) 
    rmrks = models.CharField("Remarks", max_length=50, blank=True) 

    ########
    
    # one or more regional dialects that this gloss is used in
    dialect = models.ManyToManyField(Dialect)
    
    
    blend = models.CharField("Blend of", max_length=100, null=True, blank=True) # This field type is a guess.
    blendtf = models.NullBooleanField("Blend", null=True, blank=True)
    
    compound = models.CharField("Compound of", max_length=100, blank=True) # This field type is a guess.
    comptf = models.NullBooleanField("Compound", null=True, blank=True)
    

    # Phonology fields
    handedness = models.CharField("Handedness", blank=True,  null=True, choices=build_choice_list("Handedness"), max_length=5)
    
    domhndsh = models.CharField("Strong Hand", blank=True,  null=True, choices=build_choice_list("Handshape"), max_length=5)
    subhndsh = models.CharField("Weak Hand", null=True, choices=build_choice_list("Handshape"), blank=True, max_length=5)
   
    final_domhndsh = models.CharField("Final Dominant Handshape", blank=True,  null=True, choices=build_choice_list("Handshape"), max_length=5)
    final_subhndsh = models.CharField("Final Subordinate Handshape", null=True, choices=build_choice_list("Handshape"), blank=True, max_length=5)
 
    locprim = models.CharField("Location", choices=build_choice_list("Location"), null=True, blank=True,max_length=20)
    final_loc = models.IntegerField("Final Primary Location", choices=build_choice_list("Location"), null=True, blank=True)
    locVirtObj = models.CharField("Virtual Object", blank=True, null=True, max_length=50)

    locsecond = models.IntegerField("Secondary Location", choices=build_choice_list("Location"), null=True, blank=True)
    
    initial_secondary_loc = models.CharField("Initial Subordinate Location", max_length=20, choices=BSLsecondLocationChoices, null=True, blank=True) 
    final_secondary_loc = models.CharField("Final Subordinate Location", max_length=20, choices=BSLsecondLocationChoices, null=True, blank=True)      
    
    initial_palm_orientation = models.CharField("Initial Palm Orientation", max_length=20, null=True, blank=True, choices=palmOrientationChoices) 
    final_palm_orientation = models.CharField("Final Palm Orientation", max_length=20, null=True, blank=True, choices=palmOrientationChoices)
  
    initial_relative_orientation = models.CharField("Initial Interacting Dominant Hand Part", null=True, max_length=20, blank=True, choices=relOrientationChoices) 
    final_relative_orientation = models.CharField("Final Interacting Dominant Hand Part", null=True, max_length=20, blank=True, choices=relOrientationChoices)
 
    
    inWeb = models.NullBooleanField("In the Web dictionary", default=False)
    isNew = models.NullBooleanField("Is this a proposed new sign?", null=True, default=False)
    
    inittext = models.CharField(max_length="50", blank=True) 

    morph = models.CharField("Morphemic Analysis", max_length=50, blank=True)  

    sedefinetf = models.TextField("Signed English definition available", null=True, blank=True)  # TODO: should be boolean
    segloss = models.CharField("Signed English gloss", max_length=50, blank=True,  null=True) 

    sense = models.IntegerField("Sense Number", null=True, blank=True, help_text="If there is more than one sense of a sign enter a number here, all signs with sense>1 will use the same video as sense=1") 
    sense.list_filter_sense = True

    sn = models.IntegerField("Sign Number", help_text="Sign Number must be a unique integer and defines the ordering of signs in the dictionary", null=True, blank=True, unique=True)   
            # this is a sign number - was trying
            # to be a primary key, also defines a sequence - need to keep the sequence
            # and allow gaps between numbers for inserting later signs
            
    StemSN = models.IntegerField(null=True, blank=True) 

    relatArtic = models.CharField("Relation between Articulators", choices=build_choice_list("RelatArtic"), null=True, blank=True, max_length=5)

    absOriPalm = models.CharField("Absolute Orientation: Palm", choices=build_choice_list("AbsOriPalm"), null=True, blank=True, max_length=5)
    absOriFing = models.CharField("Absolute Orientation: Fingers", choices=build_choice_list("AbsOriFing"), null=True, blank=True, max_length=5)

    relOriMov = models.CharField("Relative Orientation: Movement", choices=build_choice_list("RelOriMov"), null=True, blank=True, max_length=5)
    relOriLoc = models.CharField("Relative Orientation: Location", choices=build_choice_list("RelOriLoc"), null=True, blank=True, max_length=5)

    oriCh = models.CharField("Orientation Change",choices=build_choice_list("OriChange"), null=True, blank=True, max_length=5)

    handCh = models.CharField("Handshape Change", choices=build_choice_list("HandshapeChange"), null=True, blank=True, max_length=5)

    repeat = models.NullBooleanField("Repeated Movement", null=True, default=False)
    altern = models.NullBooleanField("Alternating Movement", null=True, default=False)

    movSh = models.CharField("Movement Shape", choices=build_choice_list("MovementShape"), null=True, blank=True, max_length=5)
    movDir = models.CharField("Movement Direction", choices=build_choice_list("MovementDir"), null=True, blank=True, max_length=5)
    movMan = models.CharField("Movement Manner", choices=build_choice_list("MovementMan"), null=True, blank=True, max_length=5)
    contType = models.CharField("Contact Type", choices=build_choice_list("ContactType"), null=True, blank=True, max_length=5)

    phonOth = models.TextField("Phonology Other", null=True, blank=True)

    mouthG = models.CharField("Mouth Gesture", max_length=50, blank=True)     
    mouthing = models.CharField("Mouthing", max_length=50, blank=True)     
    phonetVar = models.CharField("Phonetic Variation", max_length=50, blank=True,)     

    #Semantic fields

    iconImg = models.CharField("Iconic Image", max_length=50, blank=True)     
    namEnt = models.CharField("Named Entity", choices=build_choice_list("NamedEntity"), null=True, blank=True, max_length=5)
    semField = models.CharField("Semantic Field", choices=build_choice_list("SemField"), null=True, blank=True, max_length=5)

    #Frequency fields

    tokNo = models.IntegerField("Total Number of Occurrences",null=True, blank=True) 
    tokNoSgnr = models.IntegerField("Total Number of Signers Using this Sign",null=True, blank=True) 
    tokNoA = models.IntegerField("Number of Occurrences in Amsterdam",null=True, blank=True) 
    tokNoV = models.IntegerField("Number of Occurrences in Voorburg",null=True, blank=True) 
    tokNoR = models.IntegerField("Number of Occurrences in Rotterdam",null=True, blank=True) 
    tokNoGe = models.IntegerField("Number of Occurrences in Gestel",null=True, blank=True) 
    tokNoGr = models.IntegerField("Number of Occurrences in Groningen",null=True, blank=True) 
    tokNoO = models.IntegerField("Number of Occurrences in Other Regions",null=True, blank=True) 

    tokNoSgnrA = models.IntegerField("Number of Amsterdam Signers",null=True, blank=True) 
    tokNoSgnrV = models.IntegerField("Number of Voorburg Signers",null=True, blank=True) 
    tokNoSgnrR = models.IntegerField("Number of Rotterdam Signers",null=True, blank=True) 
    tokNoSgnrGe = models.IntegerField("Number of Gestel Signers",null=True, blank=True) 
    tokNoSgnrGr = models.IntegerField("Number of Groningen Signers",null=True, blank=True) 
    tokNoSgnrO = models.IntegerField("Number of Other Region Signers",null=True, blank=True) 

    def get_fields(self):
        return [(field.name, field.value_to_string(self)) for field in Gloss._meta.fields]

    def navigation(self, is_staff):
        """Return a gloss navigation structure that can be used to
        generate next/previous links from within a template page"""
    
        result = dict() 
        result['next'] = self.next_dictionary_gloss(is_staff)
        result['prev'] = self.prev_dictionary_gloss(is_staff)
        return result
    
    def admin_next_gloss(self):
        """next gloss in the admin view, shortcut for next_dictionary_gloss with staff=True"""

        return self.next_dictionary_gloss(True)
        
    def admin_prev_gloss(self):
        """previous gloss in the admin view, shortcut for prev_dictionary_gloss with staff=True"""

        return self.prev_dictionary_gloss(True)

        
    def next_dictionary_gloss(self, staff=False):
        """Find the next gloss in dictionary order"""
        if self.sn == None:
            return None
        elif staff:
            set =  Gloss.objects.filter(sn__gt=self.sn).order_by('sn')
        else:
            set = Gloss.objects.filter(sn__gt=self.sn, inWeb__exact=True).order_by('sn')
        if set:
            return set[0]
        else:
            return None
 
    def prev_dictionary_gloss(self, staff=False):
        """Find the previous gloss in dictionary order"""
        if self.sn == None:
            return None
        elif staff:
            set = Gloss.objects.filter(sn__lt=self.sn).order_by('-sn')
        else:
            set = Gloss.objects.filter(sn__lt=self.sn, inWeb__exact=True).order_by('-sn')
        if set:
            return set[0]
        else:
            return None     
             
    def get_absolute_url(self):
        return "/dictionary/gloss/%s.html" % self.idgloss
    
    
    def homophones(self):
        """Return the set of homophones for this gloss ordered by sense number"""
        
        if self.sense == 1:
            relations = Relation.objects.filter(role="homophone", target__exact=self).order_by('source__sense')
            homophones = [rel.source for rel in relations]
            homophones.insert(0,self)
            return homophones
        elif self.sense > 1:
            # need to find the root and see how many senses it has
            homophones = self.relation_sources.filter(role='homophone', target__sense__exact=1)
            if len(homophones) > 0:   
                root = homophones[0].target
                return root.homophones()
        return []


    def get_video_gloss(self):
        """Work out the gloss that might have the video for this sign, usually the sign number but
        if we're a sense>1 then we look at the homophone with sense=1
        Return the gloss instance."""
        
        if self.sense > 1:
            homophones = self.relation_sources.filter(role='homophone', target__sense__exact=1)
            # should be only zero or one of these
            if len(homophones) > 0:   
                return homophones[0].target
        return self
                
    def get_video(self):
        """Return the video object for this gloss or None if no video available"""

        video_path = 'glossvideo/'+self.idgloss[:2]+'/'+self.idgloss+'-'+str(self.pk)+'.mp4';

        if os.path.isfile(settings.MEDIA_ROOT+'/'+video_path):
            return video_path;
        else:
            return None;

        video_with_gloss = self.get_video_gloss()
        
        try:
            video = video_with_gloss.glossvideo_set.get(version__exact=0)
            return video
        except:
            return None
        
    def count_videos(self):
        """Return a count of the number of videos we have 
        for this video - ie. the number of versions stored"""
        
        
        video_with_gloss = self.get_video_gloss()
        
        return video_with_gloss.glossvideo_set.count()
    
    
    def get_video_url(self):
        """return  the url of the video for this gloss which may be that of a homophone"""
         

	return '/home/wessel/signbank/signbank/video/testmedia/AANBELLEN-320kbits.mp4';
         
        video = self.get_video()
        if video != None:
            return video.get_absolute_url()
        else:
            return ""
        
    def has_video(self):
        """Test to see if the video for this sign is present"""
        
        return self.get_video() != None
    
    def published_definitions(self):
        """Return a query set of just the published definitions for this gloss
        also filter out those fields not in DEFINITION_FIELDS"""
        

        defs = self.definition_set.filter(published__exact=True)
    
        return [d for d in defs if d.role in settings.DEFINITION_FIELDS]
    
    
    def definitions(self):
        """gather together the definitions for this gloss"""
    
        defs = dict()
        for d in self.definition_set.all().order_by('count'):
            if not defs.has_key(d.role):
                defs[d.role] = []
            
            defs[d.role].append(d.text)
        return defs
   
    def options_to_json(self, options):
        """Convert an options list to a json dict"""
        
        result = []
        for k, v in options:
            result.append('"%s":"%s"' % (k, v))
        return "{" + ",".join(result) + "}"
    
    def handshape_choices_json(self):
        """Return JSON for the handshape choice list"""
        
        return self.options_to_json(handshapeChoices)
    
    
    def location_choices_json(self):
        """Return JSON for the location choice list"""
        
        return self.options_to_json(locationChoices)
    
    def palm_orientation_choices_json(self):
        """Return JSON for the palm orientation choice list"""
        
        return self.options_to_json(palmOrientationChoices)

    def relative_orientation_choices_json(self):
        """Return JSON for the relative orientation choice list"""
        
        return self.options_to_json(relOrientationChoices)
    
    def secondary_location_choices_json(self):
        """Return JSON for the secondary location (BSL) choice list"""
        
        return self.options_to_json(BSLsecondLocationChoices)
    
     
    def definition_role_choices_json(self):
        """Return JSON for the definition role choice list"""
        
        return self.options_to_json(DEFN_ROLE_CHOICES)
    
    def relation_role_choices_json(self):
        """Return JSON for the relation role choice list"""
        
        return self.options_to_json(RELATION_ROLE_CHOICES)    
    
    def language_choices(self):
        """Return JSON for langauge choices"""
        
        d = dict()
        for l in Language.objects.all():
            d[l.name] = l.name

        return json.dumps(d)

    def dialect_choices(self):
        """Return JSON for dialect choices"""
        
        d = dict()
        for l in Dialect.objects.all():
            d[l.name] = l.name

        return json.dumps(d)
    
    def get_choice_lists(self):
        """Return JSON for the location choice list"""
 
        choice_lists = {}; 

        #Start with your own choice lists
        for fieldname in ['handedness','locprim','domhndsh','subhndsh',
							'relatArtic','absOriPalm','absOriFing','relOriMov',
							'relOriLoc','handCh','repeat','altern','movSh',
							'movDir','movMan','contType','namEnt','oriCh','semField']:

            #Get the list of choices for this field
            li = self._meta.get_field(fieldname).choices;

            #Sort the list
            sorted_li = sorted(li,key=lambda x: x[1]);

            #Put it in another format
            reformatted_li = [('_'+str(value),text) for value,text in sorted_li]
            choice_lists[fieldname] = OrderedDict(reformatted_li);

        #Choice lists for other models
        choice_lists['morphology_role'] = [human_value for machine_value,human_value in build_choice_list('MorphologyType')];

        return json.dumps(choice_lists)

# register Gloss for tags
try:
    tagging.register(Gloss)
except tagging.AlreadyRegistered:
    pass

RELATION_ROLE_CHOICES = (('homonym', 'Homonym'),
                         ('synonym', 'Synonym'),
                         ('variant', 'Variant'),
                         ('antonym', 'Antonym'),
                         ('hyponym', 'Hyponym'),
                         ('hypernym', 'Hypernym'),
                         ('seealso', 'See Also'),
                         )

class Relation(models.Model):
    """A relation between two glosses"""
     
    source = models.ForeignKey(Gloss, related_name="relation_sources")
    target = models.ForeignKey(Gloss, related_name="relation_targets")
    role = models.CharField(max_length=20, choices=RELATION_ROLE_CHOICES)  
                # antonym, synonym, cf (what's this? - see also), var[b-f]
                               # (what's this - variant (XXXa is the stem, XXXb is a variant)
                       
    class Admin:
        list_display = [ 'source', 'role','target']
        search_fields = ['source__idgloss', 'target__idgloss']        
        
    class Meta:
        ordering = ['source']

class MorphologyDefinition(models.Model):
    """Tells something about morphology of a gloss""";

    parent_gloss = models.ForeignKey(Gloss, related_name="parent_glosses");
    role = models.CharField(max_length=5,choices=build_choice_list('MorphologyType'))
    morpheme = models.ForeignKey(Gloss,related_name="morphemes");

    def __str__(self):

        return self.morpheme.idgloss + ' is ' + self.get_role_display() + ' of ' + self.parent_gloss.idgloss;