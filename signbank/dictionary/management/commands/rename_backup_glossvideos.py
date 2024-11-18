"""Convert gloss videos to mp4."""

import os
import shutil
from django.core.management.base import BaseCommand
from django.core.exceptions import *
from signbank.settings.server_specific import WRITABLE_FOLDER, BACKUP_VIDEOS_FOLDER
from signbank.dictionary.models import Dataset
from signbank.video.models import GlossVideo, GlossVideoNME, GlossVideoPerspective
from signbank.dataset_checks import gloss_backup_videos, rename_backup_videos


class Command(BaseCommand):
    help = 'Rename gloss backup videos that have bak sequences.'

    def add_arguments(self, parser):
        parser.add_argument('dataset-acronym', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        if 'dataset-acronym' in kwargs:
            for dataset_acronym in kwargs['dataset-acronym']:
                try:
                    dataset = Dataset.objects.get(acronym=dataset_acronym)
                    backup_videos = gloss_backup_videos(dataset)
                    # use a separate variable because we are going to filter out objects without a file
                    gloss_videos_to_move = backup_videos
                    checked_gloss_videos = []
                    for gloss, glossvideos in gloss_videos_to_move:
                        gloss_video_objects = glossvideos
                        checked_videos_for_gloss = []
                        for gloss_video in gloss_video_objects:
                            source = os.path.join(WRITABLE_FOLDER, str(gloss_video.videofile))
                            if not os.path.exists(source):
                                continue
                            checked_videos_for_gloss.append(gloss_video)
                        checked_gloss_videos.append((gloss, checked_videos_for_gloss))
                    for gloss, glossvideos in checked_gloss_videos:
                        rename_backup_videos(gloss, glossvideos)
                except ObjectDoesNotExist as e:
                    print("Dataset '{}' not found.".format(dataset_acronym), e)
