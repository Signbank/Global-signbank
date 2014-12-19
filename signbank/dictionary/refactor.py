#!/usr/bin/python

# script to refactor the database from the old schema to the new

import sys, os.path
thispath = os.path.dirname( os.path.dirname( os.path.realpath(sys.argv[0])))
sys.path.append(thispath)


from django.core.management import setup_environ
import settings 

setup_environ(settings)


import dictionary.models_legacy as lmodels
import dictionary.models as models

def makeFields(prefix, n):
    """Generate a list of field names with this prefix up to n"""
    
    return [prefix+str(n) for n in range(1,n+1)]

import csv

def importCSV(csvfile):
    """Import the original database from the csv file"""

    print "Reading database from ", csvfile, "..."

    lmodels.Sign.objects.all().delete()
    
    fields = lmodels.Sign._meta.fields
    
    reader = csv.DictReader(open(csvfile))
    
    for row in reader:
        if row['idgloss'] == '':
            print "skipping empty gloss"
            continue
            
        #print row['idgloss']
        
        sign = lmodels.Sign()
        for field in fields:
            # db fields have space replaced by _
            key = field.name.replace("_", " ")

                
            if row.has_key(key):
                # map T,F to True, False
                if row[key] is "T":
                    row[key] = True
                elif row[key] is "F":
                    row[key] = False
                
                if row[key] != '':
                    # convert the the appropriate type
                    value = field.to_python(row[key])
                    setattr(sign, field.name, value) 


            else:
                print "No ", field, " field for ", row['idgloss']
        sign.save()
        
 
                
        
    
    
def refactor_glosses():
    """Perform the refactor of the main table"""
             
    models.Gloss.objects.all().delete()
    models.Translation.objects.all().delete()
    models.Definition.objects.all().delete()
    models.Keyword.objects.all().delete()
    
    
    # find all the fields in models.Sign
    # we copy these over from lmodels.Lexicon
    glossFields = models.Gloss._meta.fields
    
    for lex in lmodels.Sign.objects.all():
       
        newsign = models.Gloss()
        for field in glossFields: 
            try:
                value = getattr(lex, field.name)
                setattr(newsign, field.name, value)
            except:
                pass
        # create the new inDict field
        newsign.inWeb = newsign.inCD
        newsign.save()
                
        # make a translation for every transField
        for field in makeFields('english', 12):
            translation = getattr(lex, field)
            if translation != '':
                # make a keyword..
                (kwd, created) = models.Keyword.objects.get_or_create(text=translation)
                tran = newsign.translation_set.create(translation=kwd)
        
        copy_definitions(lex, newsign, 'nom', 5, 'noun')
        copy_definitions(lex, newsign, 'verb', 4, 'verb')
        copy_definitions(lex, newsign, 'deictic', 4, 'deictic')
        copy_definitions(lex, newsign, 'interact', 3, 'interact')
        copy_definitions(lex, newsign, 'modifier', 3, 'modifier')
        copy_definitions(lex, newsign, 'question', 2, 'question')
        copy_definitions(lex, newsign, 'augment', 1, 'augment')

        # PopExplain is a bit different
        text = getattr(lex, "PopExplain")
        if text != '': 
            if text.startswith("Popular explanation:"):
                text = text.replace("Popular explanation:", "") 
            definition = newsign.definition_set.create(text=text, role='popexplain', count=1)
    
    # two keywords have bad characters in them 
    # find them without mentioning the offending characters
    k = models.Keyword.objects.filter(text__startswith="Mont").exclude( text="Montreal")[0]
    k.text = "Montr&eacute;al"
    k.save()
    k = models.Keyword.objects.get(text__startswith="risqu")
    k.text = "risqu&eacute;"
    k.save()

def refactor_relations():
    

    models.Relation.objects.all().delete()      
    # when we've created all of the glosses, we can do the relations between
    # them, this needs a second pass through the Signs
    for lex in lmodels.Sign.objects.all():
     
        print "copying relations for '%s'..." % (lex.idgloss),
        
        newsign = models.Gloss.objects.get(idgloss=lex.idgloss)
        
        copy_relations(lex, newsign, 'ant', range(1,4), 'antonym')
        copy_relations(lex, newsign, 'syn', range(1,4), 'synonym')
        copy_relations(lex, newsign, 'cf', range(1,4), 'seealso')
        copy_relations(lex, newsign, 'var', ['b', 'c', 'd', 'e', 'f'], 'variant')
        
        print "done"
        
        
def copy_relations(lex, newsign, field, suffixes, role):
    """Copy over a relation field to a Relation object"""
  
    
    for count in suffixes:
        
        
            other = getattr(lex, field+str(count))
            if other == None:
                continue
            # in some cases the value is a string, in others it's a Sign
            # we convert to the idgloss if it's a sign
            if type(other) != unicode:
                other = other.idgloss
            
            if other != '':
                try:                        
                    othergloss = models.Gloss.objects.get(idgloss=other)
                    relation = models.Relation(source=newsign, target=othergloss, role=role)
                    relation.save() 
                except:
                    print "Can't find sign for gloss ", other
        
                   
        
def copy_definitions(lex, newsign, field, N, role):
    """Copy over one of the definition fields"""

    print "copy_definitions", lex, newsign, field, N, role
    
    if field=='augment':
        text = getattr(lex, field)
        
        if text != '':
            # may begin with "Augmentation: "
            if text.startswith("Augmentation: "):
                text = text.replace("Augmentation:", "")
                # then strip leading space and capitalise
                text = text.lstrip()
                text = text.capitalize()
                
            definition = newsign.definition_set.create(text=text, role=role, count=1)
        return
    
    for count in range(1,N+1):
        text = getattr(lex, field+str(count))
        
        if text != '':
            # remove the number from the start of the defn
            # since we can generate it from count
            if text.startswith(str(count)+"."):
                text = text.replace(str(count)+".", "") 
            definition = newsign.definition_set.create(text=text, role=role, count=count)

            
            
def build_homosign_relation():
    """Generate the Homosign relation between glosses
    
    A homosign is a gloss that uses the same sign as 
    another gloss. The target gloss is the 'base' sign
    in the sense that it has the associated video for
    the sign.
    
    The relation is made for every sign with a sense
    greater than 1 back to the sign with sense=1 who's
    sense number (sn) is closest to this sign.
    """
    
    
    models.Relation.objects.filter(role="homophone").delete()
    
    glosses = models.Gloss.objects.filter(sense__in=[1,2,3,4,5,6]).order_by("sn")
    
    last_one = None
    for gloss in glosses: 
        if gloss.sense == 1:
            last_one = gloss
        elif last_one != None:
            print gloss.sn, "->", last_one.sn
            rel = models.Relation(source=gloss, target=last_one, role="homophone")
            rel.save()
        else:
            print "No base homosign for gloss: ", gloss
    


                 
csvfile = sys.argv[1]
importCSV(csvfile)

refactor_glosses()
refactor_relations()

build_homosign_relation()


