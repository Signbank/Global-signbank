"""Convert gloss videos to mp4."""

import os
import shutil
import magic
from django.core.management.base import BaseCommand
from django.core.exceptions import *
from signbank.settings.server_specific import WRITABLE_FOLDER, BACKUP_VIDEOS_FOLDER
from signbank.dictionary.models import Dataset
from signbank.video.models import GlossVideo


class Command(BaseCommand):
    help = 'Convert gloss videos that are not mp4.'

    def add_arguments(self, parser):
        parser.add_argument('dataset-acronym', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        if 'dataset-acronym' in kwargs:
            for dataset_acronym in kwargs['dataset-acronym']:
                try:
                    dataset = Dataset.objects.get(acronym=dataset_acronym)
                    for gv in GlossVideo.objects.filter(gloss__lemma__dataset=dataset, version=0):
                        # If there is no small version and original exists,
                        # create a small version.
                        filepath = os.path.join(WRITABLE_FOLDER, gv.videofile.name)
                        if os.path.exists(filepath.encode('utf-8')):
                            file_type = magic.from_buffer(open(filepath, "rb").read(2040), mime=True)
                            video_type = file_type.split('/')[0] if file_type else None
                            if video_type != 'video':
                                print('File is not a video: ', filepath)
                                continue
                            if os.path.getsize(filepath.encode('utf-8')) == 0:
                                print('File is empty: ', filepath)
                                continue
                            if file_type not in ['video/mp4', 'video/x-m4v']:
                                # if the video has the wrong type
                                print('Non-MP4 video file found: ', filepath, file_type)
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
                                # the following may not work on quicktime nor on mpeg
                                try:
                                    gv.convert_to_mp4()
                                except (PermissionError, ObjectDoesNotExist, ChildProcessError, Exception) as e:
                                    print('Conversion to mp4 failed: ', filepath)
                                    print(e)
                                    continue
                        else:
                            print('GlossVideo file not found: ', filepath)
                except ObjectDoesNotExist as e:
                    print("Dataset '{}' not found.".format(dataset_acronym), e)

