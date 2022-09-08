"""Remove unused video files (that are not found in de database)"""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError  
from django.conf import settings
from signbank.video.models import GlossVideo
from signbank.dictionary.models import OtherMedia
import os

class Command(BaseCommand):
     
    help = 'Remove unused files'

    def add_arguments(self, parser):
        parser.add_argument('pathtype', type=str, help='Indicates the type of media to delete')

    def handle(self, *args, **kwargs):
        """Remove all video files that are not used in db"""
        pathtype = kwargs['pathtype']
        filenames = []
        if pathtype == "other_media":
            chosen_path = os.path.join(os.path.join(settings.WRITABLE_FOLDER),settings.OTHER_MEDIA_DIRECTORY)
            for other_media_file in OtherMedia.objects.all().iterator():
                filenames.append(other_media_file.path.split("/")[-1])
        elif pathtype == "video":
            chosen_path = os.path.join(os.path.join(settings.WRITABLE_FOLDER),settings.GLOSS_VIDEO_DIRECTORY)
            for gloss_video in GlossVideo.objects.all().iterator():
                filenames.append(gloss_video.videofile.name.split("/")[-1])     
        else: 
            self.stdout.write("Wrong argument: try 'video' or 'other_media'")
            return
        
        # Make list of files that are not used
        notexist = find_unused_files(self, chosen_path, filenames)

        # Delete files that are not used
        delete_files(self, notexist, chosen_path)
 
def find_unused_files(self, chosen_path, filenames):
    """Return list of filenames that are not found in file list of db"""
    notexist = []
    for subdir, dirs, files in os.walk(chosen_path):
        for file in files:
            if file not in filenames:
                notexist.append(file)
    return notexist
    
def delete_files(self, notexist, chosen_path):
    """Delete list of unused files, if user agrees"""
    # Show list of files to delete to users
    self.stdout.write("\nUnused files found are:\n")
    for unknown_file in notexist:
        self.stdout.write(unknown_file)
    if len(notexist)>0:
        # Ask user to agree
        todelete = input("Delete files? [Y/N]")
        if todelete.lower() == "y":
            for subdir, dirs, files in os.walk(chosen_path):
                for file in files:
                    if file in notexist:
                        os.remove(os.path.join(subdir, file))
            self.stdout.write('Files are deleted')
        else: 
            self.stdout.write('Files are not deleted')
    else: 
        self.stdout.write('No unused files found')
    
        
        
        
        
