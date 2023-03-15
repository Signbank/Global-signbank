"""Create other media files."""

import os
import shutil
from django.core.management.base import BaseCommand
from django.core.exceptions import *
from signbank.settings.server_specific import WRITABLE_FOLDER, BACKUP_VIDEOS_FOLDER, OTHER_MEDIA_DIRECTORY
from signbank.dictionary.models import Dataset
from signbank.video.models import OtherMedia


class Command(BaseCommand):
    help = 'Convert other media videos that are not mp4.'

    def add_arguments(self, parser):
        parser.add_argument('dataset-acronym', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        if 'dataset-acronym' in kwargs:
            for dataset_acronym in kwargs['dataset-acronym']:
                try:
                    dataset = Dataset.objects.get(acronym=dataset_acronym)
                    for om in OtherMedia.objects.filter(parent_gloss__lemma__dataset=dataset):
                        # If there is no small version and original exists,
                        # create a small version.
                        filepath = os.path.join(WRITABLE_FOLDER, OTHER_MEDIA_DIRECTORY, om.path)
                        if os.path.exists(filepath.encode('utf-8')):
                            import magic
                            magic_file_type = magic.from_buffer(open(filepath, "rb").read(2040), mime=True)
                            media_type = magic_file_type.split('/')[0]
                            if media_type != 'video':
                                # skip
                                continue
                            if os.path.getsize(filepath.encode('utf-8')) == 0:
                                print('Other media video file is empty: ', filepath)
                                continue
                            if magic_file_type not in ['video/mp4', 'video/x-m4v']:
                                # if the video has the wrong type
                                print('Non-MP4 video file found: ', filepath, magic_file_type)
                                video_file_name = os.path.basename(filepath)
                                (video_file_basename, video_file_ext) = os.path.splitext(video_file_name)
                                temp_video_copy = video_file_basename + '-conv' + video_file_ext
                                temp_filepath = os.path.join(WRITABLE_FOLDER, BACKUP_VIDEOS_FOLDER, temp_video_copy)
                                try:
                                    shutil.copy(filepath, temp_filepath)
                                    print('Backup of file copied to: ', temp_filepath)
                                except (PermissionError, shutil.SameFileError):
                                    print('File could not be copied for backup. Skipping: ', filepath)
                                    continue
                                from signbank.video.convertvideo import convert_video
                                # convert the video to h264
                                success = convert_video(temp_filepath, filepath)
                                if not success:
                                    print('Conversion to mp4 failed: ', filepath)
                                    continue
                        else:
                            print('OtherMedia file not found: ', filepath)
                except ObjectDoesNotExist as e:
                    print("Dataset '{}' not found.".format(dataset_acronym), e)

