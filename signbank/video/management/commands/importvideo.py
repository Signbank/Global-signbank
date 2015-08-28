"""Convert a video file to flv"""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError  
from django.conf import settings
from signbank.video.models import GlossVideo
import os

class Command(BaseCommand):
     
    help = 'import existing videos into the database'
    args = 'path'

    def handle(self, *args, **options):
        
        if len(args) == 1:
            path = args[0]  
            
            import_existing_gloss_videos(path)
     
        else:
            print "Usage importvideo", self.args


def import_existing_gloss_videos(path):
    from django.db import connection, transaction
    from django.db.models import Max
    
    cursor = connection.cursor()
    
    # delete all existing videos
    GlossVideo.objects.all().delete()
    
    # find the largest currently used id 
    id = GlossVideo.objects.all().aggregate(Max('id'))['id__max']
    if id==None:
        id = 0
    
    basedir = settings.MEDIA_ROOT

    # scan the directory and make an entry for each video file found
    for dir in os.listdir(os.path.join(basedir, path)):
        if os.path.isdir(os.path.join(basedir, path, dir)):
            for videofile in os.listdir(os.path.join(basedir, path, dir)):
                (gloss_sn, ext) = os.path.splitext(videofile)
                if ext in ['.mp4']:
                    id += 1
                    fullpath = os.path.join(path, dir, videofile)
                    try:
                        gloss = Gloss.objects.get(sn=gloss_sn)
                    
                        version = 0
                        print id, fullpath, gloss
                        cursor.execute("insert into video_glossvideo (id, videofile, gloss, version) values (%s, %s, %s, %s)", [id, fullpath, gloss.pk, version])
                    except:
                        print "No gloss for ", gloss_sn
                else:
                    print 'skipping ', videofile
    
    transaction.commit_unless_managed()
    
    
    
    