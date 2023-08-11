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
        parser.add_argument('path_type', type=str, help='Indicates the type of media to delete')

    def handle(self, *args, **kwargs):
        """Remove all video files that are not used in db"""
        path_type = kwargs['path_type']

        # Check path path_type
        if path_type != "other_media" and path_type != "video":
            self.stdout.write("Wrong argument: try 'video' or 'other_media'")
            return

        # Make list of all files to search for in db
        file_names, chosen_path = find_file_names(self, path_type)

        # Make list of files that are not used in db
        non_existent_file_names = find_unused_files(self, chosen_path, file_names)

        # Delete files that are not used in db
        delete_files(self, non_existent_file_names, chosen_path)

def find_file_names(self, path_type):
    """Return list of file_names that are not found in file list of db"""

    file_names = []

    if path_type == "other_media":
        chosen_path = os.path.join(os.path.join(settings.WRITABLE_FOLDER),settings.OTHER_MEDIA_DIRECTORY)
        for other_media_file in OtherMedia.objects.all().iterator():
            file_names.append(other_media_file.path.split("/")[-1])
    elif path_type == "video":
        chosen_path = os.path.join(os.path.join(settings.WRITABLE_FOLDER),settings.GLOSS_VIDEO_DIRECTORY)
        for gloss_video in GlossVideo.objects.all().iterator():
            file_names.append(gloss_video.videofile.name.split("/")[-1])

    return file_names, chosen_path

def find_unused_files(self, chosen_path, file_names):
    """Return list of file_names that are not found in file list of db"""

    non_existent_file_names = []

    for subdir, dirs, files in os.walk(chosen_path):
        for file in files:
            if file not in file_names:
                non_existent_file_names.append(file)

    return non_existent_file_names

def delete_files(self, non_existent_file_names, chosen_path):
    """Delete list of unused files, if user agrees"""

    # First condition: no unused files
    if len(non_existent_file_names)<=0:
        self.stdout.write('No unused files found')
        return

    # Show list of files to delete to users
    self.stdout.write("\nUnused files found are:\n")
    for non_existent_file in non_existent_file_names:
        self.stdout.write(non_existent_file)

    # First condition: ask user to agree
    if input("Delete files? [Y/N]").lower() != 'y':
        self.stdout.write('Files are not deleted')
        return

    # Delete files
    for subdir, dirs, files in os.walk(chosen_path):
        for file in files:
            if file in non_existent_file_names:
                os.remove(os.path.join(subdir, file))

    self.stdout.write('Files are deleted')
