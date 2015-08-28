from django.utils import unittest
from django.core.files import File
from django.conf import settings
from models import Video, GlossVideo
import os, shutil

class VideoTests(unittest.TestCase):

    def setUp(self):
        
        self.vidfilename = "signbank/video/testmedia/video.mp4"
        self.videofile = File(open(self.vidfilename), "12345.mp4")
    
    def test_Video_create(self):
        """We can create a video object"""
        
        vid = Video.objects.create(videofile=self.videofile)

        # new file should be located in upload
        self.assertEquals(os.path.dirname(vid.videofile.name), settings.VIDEO_UPLOAD_LOCATION)
        self.assertTrue(os.path.exists(vid.videofile.path), "vidfile doesn't exist at %s" % (vid.videofile.path,))
        
        # test deletion of files
        
        vid.delete_files()
        self.assertFalse(os.path.exists(vid.videofile.path), "vidfile still exists after delete at %s" % (vid.videofile.path,))
        
    def test_GlossVideo_create(self):
        """We can create a GlossVideo object"""
        
        vid = GlossVideo.objects.create(videofile=self.videofile) 
 
        
        self.assertTrue(os.path.exists(vid.videofile.path), "vidfile doesn't exist at %s" % (vid.videofile.path,))
        
        vid.delete_files()
        self.assertFalse(os.path.exists(vid.videofile.path), "vidfile still exists after delete at %s" % (vid.videofile.path,))
        
        
        
    def test_Video_poster_path(self):
        """We can generate a poster image for a video"""
        
        vid = Video.objects.create(videofile=self.videofile)
        # remove video file when done
        self.addCleanup(lambda: os.unlink(vid.videofile.path))
        
        poster = vid.poster_path()
        poster_abs = os.path.join(settings.MEDIA_ROOT, poster)
        # remove poster image when done
        self.addCleanup(lambda: os.unlink(poster_abs))
        
        self.assertTrue(os.path.exists(poster_abs), "poster image %s is missing" % (poster_abs,))
        
        # do it again should give the same result, but won't have created the file
        poster2 = vid.poster_path()
        self.assertEqual(poster, poster2) 

        