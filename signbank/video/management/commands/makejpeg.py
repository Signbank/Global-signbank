"""Convert a video file to flv"""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError  
from django.conf import settings
from signbank.video.models import GlossVideo
import os, time

class Command(BaseCommand):
     
    help = 'Create JPEG images for all videos'
    args = ''

    def handle(self, *args, **options):
        
        # just access the poster path for each video
        for vid in GlossVideo.objects.all():
            print vid.poster_path()
            time.sleep(20)


    