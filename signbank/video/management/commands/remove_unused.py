"""Remove unused video files (that are not found in de database)"""

import os

from django.core.management.base import BaseCommand
from django.conf import settings

from signbank.video.models import GlossVideo
from signbank.dictionary.models import OtherMedia


class Command(BaseCommand):
    help = 'Remove unused files'

    def add_arguments(self, parser):
        parser.add_argument('path_type', type=str, help='Indicates the type of media to delete')

    def handle(self, *args, **kwargs):
        """Remove all video files that are not used in db"""
        path_type = kwargs['path_type']

        # Check path path_type
        if path_type not in ("other_media", "video"):
            print("Wrong argument: try 'video' or 'other_media'")
            return

        # Make list of all files to search for in db
        file_names, chosen_path = find_file_names(path_type)

        # Make list of files that are not used in db
        non_existent_file_names = find_unused_files(chosen_path, file_names)

        # Delete files that are not used in db
        delete_files(non_existent_file_names, chosen_path)


def find_file_names(path_type):
    """Return list of file_names that are not found in file list of db"""
    chosen_path = None
    file_names = []
    if path_type == "other_media":
        chosen_path = os.path.join(os.path.join(settings.WRITABLE_FOLDER), settings.OTHER_MEDIA_DIRECTORY)
        file_names = [other_media.path.split("/")[-1] for other_media in OtherMedia.objects.all()]
    elif path_type == "video":
        chosen_path = os.path.join(os.path.join(settings.WRITABLE_FOLDER), settings.GLOSS_VIDEO_DIRECTORY)
        file_names = [gloss_video.videofile.name.split("/")[-1] for gloss_video in GlossVideo.objects.all()]
    return file_names, chosen_path


def find_unused_files(chosen_path, file_names):
    """Return list of file_names that are not found in file list of db"""
    non_existent_file_names = []
    for _, _, files in os.walk(chosen_path):
        non_existent_file_names.extend([file for file in files if file not in file_names])
    return non_existent_file_names


def delete_files(non_existent_file_names, chosen_path):
    """Delete list of unused files, if user agrees"""
    if not non_existent_file_names:
        print('No unused files found')
        return

    # Show list of files to delete to users
    print("\nUnused files found are:\n")
    print("\n".join(non_existent_file_names))

    # First condition: ask user to agree
    if input("Delete files? [Y/N]").lower() != 'y':
        print('Files are not deleted')
        return

    # Delete files
    for subdir, _, files in os.walk(chosen_path):
        for file in files:
            if file in non_existent_file_names:
                os.remove(os.path.join(subdir, file))

    print('Files are deleted')
