"""Create small videos for GlossVideos that have no small version."""

import os
import magic
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from signbank.settings.server_specific import WRITABLE_FOLDER
from signbank.dictionary.models import Dataset
from signbank.video.models import GlossVideo


class Command(BaseCommand):
    help = 'Create small videos for GlossVideos that have no small version.'

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
                                continue
                            if not gv.small_video():
                                # the following prints an error message if unsuccessful
                                gv.make_small_video()
                        else:
                            print('GlossVideo file not found: ', filepath)
                except ObjectDoesNotExist as e:
                    print("Dataset '{}' not found.".format(dataset_acronym), e)
                    continue

