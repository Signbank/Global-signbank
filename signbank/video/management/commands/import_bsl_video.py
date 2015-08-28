"""Convert a video file to flv"""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError  
from django.core.files.uploadedfile import UploadedFile

from django.conf import settings
from signbank.video.models import GlossVideo
from signbank.dictionary.models import Gloss
import os

class Command(BaseCommand):
     
    help = 'import existing videos for BSL into the database'
    args = 'path'

    def handle(self, *args, **options):
        
        if len(args) == 1:
            path = args[0]  
            
            import_existing_gloss_videos(path)
     
        else:
            print "Usage import_bsl_video", self.args


def import_existing_gloss_videos(path):
    
    # delete all existing videos
    GlossVideo.objects.all().delete()

    # scan the directory and make an entry for each video file found
    for videofile in os.listdir(path):
        (idgloss, ext) = os.path.splitext(videofile)
        if ext in ['.mov', '.MOV', '.mp4']:

            fullpath = os.path.join(path, videofile)
        
            glosses = Gloss.objects.filter(idgloss=idgloss)
            
            if len(glosses) == 0 and '-' in idgloss:
                # try replacing the first - with :

                idgloss = idgloss.replace('-', ':', 1)
                
                glosses = Gloss.objects.filter(idgloss=idgloss)

            if len(glosses) == 1:
                gloss = glosses[0]
                
                print fullpath, gloss
                
                # replace apostrophe to make nicer URLs
                cleanname = videofile.replace("'", '1')
                
                h = open(fullpath)
                uf = UploadedFile(h, name=cleanname)
                gv = GlossVideo(gloss=gloss, videofile=uf)
            
                gv.save()

            else:
                print "gloss matches for", videofile, glosses
            
        else:
            print 'skipping ', videofile

    
    
    