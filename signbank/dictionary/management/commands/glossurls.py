"""Convert a video file to flv"""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError  
from signbank.dictionary.models import Gloss


class Command(BaseCommand):
     
    help = 'generate a list of gloss IDs and their video URLs'
    args = ''

    def handle(self, *args, **options):

        for gloss in Gloss.objects.all():
            print gloss.id, gloss.get_video_url()
            
            