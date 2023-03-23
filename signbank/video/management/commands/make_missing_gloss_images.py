"""Make missing (thumbnail) images for existing videos"""

from django.core.management.base import BaseCommand  
from django.conf import settings
from signbank.video.models import GlossVideo
from signbank.video.convertvideo import extract_frame, run_ffmpeg, get_middle_timecode
import os

class Command(BaseCommand):
     
    help = 'Create missing PNG images for all videos'

    def splitext_recurse(self, path):
        """In case of multiple extentions, find the base name"""
        base, ext = os.path.splitext(path)
        if ext == '':
            return base
        else:
            return self.splitext_recurse(base)

    def handle(self, *args, **options):
        
        images_created = []
        for vid in GlossVideo.objects.all():

            video_path = vid.videofile.path

            # if the videofile for this gloss exists
            if not os.path.exists(video_path):
                continue
                
            # Make the expected image path
            image_path = self.splitext_recurse(video_path) + ".png"
            image_path = str(image_path.replace(settings.GLOSS_VIDEO_DIRECTORY, settings.GLOSS_IMAGE_DIRECTORY, 1))

            # Check if it does not have an image
            if not os.path.exists(image_path):
                
                # If a folder for the image does not exist yet, add one
                image_dir = os.path.dirname(image_path)
                if not os.path.isdir(image_dir):
                    os.makedirs(image_dir)

                try:
                    # make the missing image from the middle frame of the video
                    ss = get_middle_timecode(video_path)
                    run_ffmpeg(video_path, image_path, options=["-r", "1", "-f", "mjpeg", "-ss", ss])
                    images_created.append(os.path.basename(image_path))
                except:
                    print("Error in creating an image for the following video: ", os.path.basename(video_path))

        # Feedback about which images were created
        if len(images_created) == 0:
            print("No new images were added")
        else:
            print("The following images were added: ")
            for im in images_created:
                print(im)
        

    

    