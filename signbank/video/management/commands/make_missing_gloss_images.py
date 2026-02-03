"""Make missing (thumbnail) images for existing videos"""

import os
import ffmpeg

from django.core.management.base import BaseCommand  
from django.conf import settings

from signbank.video.models import GlossVideo
from signbank.video.convertvideo import get_middle_timecode


class Command(BaseCommand):
    help = 'Create missing PNG images for all videos'

    def splitext_recurse(self, path):
        """In case of multiple extentions, find the base name"""
        base, ext = os.path.splitext(path)
        if ext == '':
            return base
        return self.splitext_recurse(base)

    def handle(self, *args, **options):
        images_created = [
            created_image for gloss_video in GlossVideo.objects.all()
            if os.path.exists(gloss_video.videofile.path)
               and (created_image := self.create_image(gloss_video))
        ]

        if len(images_created) == 0:
            print("No new images were added")
        else:
            print("The following images were added:")
            print("\n".join(images_created))

    def create_image(self, gloss_video):
        video_path = gloss_video.videofile.path
        image_path = self.splitext_recurse(video_path).replace(settings.GLOSS_VIDEO_DIRECTORY,
                                                               settings.GLOSS_IMAGE_DIRECTORY, 1) + ".png"
        if os.path.exists(image_path):
            return None
        image_dir = os.path.dirname(image_path)
        if not os.path.isdir(image_dir):
            os.makedirs(image_dir)
        try:
            (ffmpeg
             .input(video_path)
             .output(image_path, r=1, f="mjpeg", ss=get_middle_timecode(video_path))
             .run(overwrite_output=True, quiet=True))
            return os.path.basename(image_path)
        except ffmpeg.Error:
            print("Error in creating an image for the following video: ", os.path.basename(video_path))
            return None
    