"""Convert a video file to flv"""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError  
from signbank.video.convertvideo import convert_video

import os, time

class Command(BaseCommand):
     
    help = 'convert a video file to some format'
    args = 'source dest'

    def handle(self, *args, **options):
        
        if len(args) == 2:
            source = args[0] 
            dest = args[1]
            
            convert_video_collection(source, dest)
     
        else:
            print "Usage convertvideo", self.args
            
            
            

def convert_video_collection(sourcedir, destdir):
    """Convert all video files in this collection"""
    
    for dirpath, dirnames, filenames in os.walk(sourcedir):
        
        
        destpath = os.path.join(destdir, '/'.join(dirpath.split(os.sep)[1:]))
        
        if not os.path.exists(destpath):
            os.makedirs(destpath)
        
        for f in filenames:
        
            (name, ext) = os.path.splitext(os.path.basename(f))
            if ext in ['.mp4', '.flv', '.mov']:
                
                sourcefile = os.path.join(dirpath, f)
                
                destfile = os.path.join(destpath, name+".mp4")
                if not os.path.exists(destfile):
                    print sourcefile, destfile  
                    convert_video(sourcefile, destfile, force=True)

                





