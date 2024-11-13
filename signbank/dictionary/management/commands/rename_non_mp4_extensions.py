"""Convert gloss videos to mp4."""

import os
import shutil
from django.core.management.base import BaseCommand
from django.core.exceptions import *
from signbank.settings.server_specific import WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, BACKUP_VIDEOS_FOLDER
from signbank.dictionary.models import Dataset, Gloss
from signbank.video.models import GlossVideo, GlossVideoNME, GlossVideoPerspective
from signbank.dataset_checks import gloss_backup_videos, rename_backup_videos


def get_two_letter_dir(idgloss):
    foldername = idgloss[:2]

    if len(foldername) == 1:
        foldername += '-'

    return foldername


def gloss_video_non_mp4_filename_check(dataset):

    non_mp4_videos = []

    default_language = dataset.default_language

    all_glosses = Gloss.objects.filter(lemma__dataset=dataset,
                                       lemma__lemmaidglosstranslation__language=default_language).order_by(
        'lemma__lemmaidglosstranslation__text').distinct()
    for gloss in all_glosses:
        glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                                glossvideonme=None,
                                                glossvideoperspective=None).order_by('version')
        version_0_videos = glossvideos.filter(version=0)
        mp4_pattern = '.mp4'
        mp4_in_filename = [gv for gv in version_0_videos if not str(gv.videofile).endswith(mp4_pattern)]
        if mp4_in_filename:
            non_mp4_videos.append((gloss, mp4_in_filename))

    return non_mp4_videos


def rename_extension_videos(gloss, glossvideos):

    idgloss = gloss.idgloss
    two_letter_dir = get_two_letter_dir(idgloss)
    dataset_dir = gloss.lemma.dataset.acronym
    desired_filename_without_extension = idgloss + '-' + str(gloss.id)
    for inx, gloss_video in enumerate(glossvideos, 0):
        _, bak = os.path.splitext(gloss_video.videofile.name)
        desired_extension = '.mp4'
        current_version = gloss_video.version
        if current_version > 0:
            continue
        desired_filename = desired_filename_without_extension + desired_extension
        current_relative_path = str(gloss_video.videofile)
        if bak == desired_extension:
            continue
        source = os.path.join(WRITABLE_FOLDER, current_relative_path)
        destination = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY,
                                   dataset_dir, two_letter_dir, desired_filename)
        print('rename_extension_videos move ', source, destination)
        os.rename(source, destination)
        gloss_video.videofile.name = desired_filename
        gloss_video.save()


class Command(BaseCommand):
    help = 'Rename gloss backup videos that have bak sequences.'

    def add_arguments(self, parser):
        parser.add_argument('dataset-acronym', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        if 'dataset-acronym' in kwargs:
            for dataset_acronym in kwargs['dataset-acronym']:
                try:
                    dataset = Dataset.objects.get(acronym=dataset_acronym)
                    backup_videos = gloss_video_non_mp4_filename_check(dataset)
                    # use a separate variable because we are going to filter out objects without a file
                    gloss_videos_to_move = backup_videos
                    checked_gloss_videos = []
                    for gloss, glossvideos in gloss_videos_to_move:
                        gloss_video_objects = glossvideos
                        checked_videos_for_gloss = []
                        for gloss_video in gloss_video_objects:
                            source = os.path.join(WRITABLE_FOLDER, str(gloss_video.videofile))
                            if not os.path.exists(source):
                                # skip non-existent files, don't put them in enumeration list
                                continue
                            checked_videos_for_gloss.append(gloss_video)
                        checked_gloss_videos.append((gloss, checked_videos_for_gloss))
                    for gloss, glossvideos in checked_gloss_videos:
                        rename_extension_videos(gloss, glossvideos)
                except ObjectDoesNotExist as e:
                    print("Dataset '{}' not found.".format(dataset_acronym), e)
