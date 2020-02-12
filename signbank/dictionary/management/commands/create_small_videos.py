"""Create small videos for GlossVideos that have no small version."""

import os
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from signbank.settings.base import WRITABLE_FOLDER
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
                        # If there is no small version and original does exist,
                        # create a small version.
                        filepath = os.path.join(WRITABLE_FOLDER, gv.videofile.name)
                        if not gv.small_video() and os.path.exists(filepath.encode('utf-8')):
                            gv.make_small_video()
                except ObjectDoesNotExist as e:
                    print("Dataset '{}' not found.".format(dataset_acronym), e)

