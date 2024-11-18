from django.test import TestCase
import unittest
from unittest.mock import patch
from django.core.files import File
from django.core.management import call_command
from django.conf import settings
from signbank.settings.base import *
from signbank.video.models import GlossVideo
from signbank.video.management.commands import remove_unused
from io import StringIO
import os
import shutil
import sys


class CommandTests(unittest.TestCase):

    @classmethod
    def setUpTestData(cls):
        print("setting up - not used")

    def tearDown(self):
        """Remove all files added for test"""
        print("\n\nTeardown:")
        if os.path.exists("../writable/somefolder/fileindb.txt"):
            os.remove("../writable/somefolder/fileindb.txt")
            print("test fileindb removed")
        else:
            print("fileindb does not exist")
        if os.path.exists("../writable/somefolder/fileNOTindb.txt"):
            os.remove("../writable/somefolder/fileNOTindb.txt")
            print("test fileNOTindb removed")
        else:
            print("fileNOTindb does not exist")
        if os.path.exists("../writable/somefolder"):
            os.rmdir("../writable/somefolder")
            print("somefolder removed")
        else:
            print("somefolder does not exist")

    def test_remove_unused_other_path_type(self):
        """Check argument given"""
        out = StringIO()
        args = ['image']
        kwargs = {'stdout': out}
        call_command('remove_unused', *args, **kwargs)
        self.assertEqual(out.getvalue(), "Wrong argument: try 'video' or 'other_media'\n")

    def test_find_unused_files(self):
        """Check if right files are found to be removed"""

        # Make test folder + files
        some_folder_path = os.path.join(settings.WRITABLE_FOLDER, "somefolder")
        if not os.path.exists(some_folder_path):
            os.mkdir(some_folder_path)
        glossvideofile = open(some_folder_path+os.sep+"fileNOTindb.txt", "a")    # file that is not in database
        glossvideofile.close()
        glossvideofile2 = open(some_folder_path+os.sep+"fileindb.txt", "a")      # file that is in database
        glossvideofile2.close()

        # files in database
        filenames_in_db = ['fileindb.txt']

        # compare test files with db filenames
        unused_files_found = remove_unused.find_unused_files(self, some_folder_path, filenames_in_db)

        # account for extra folder parameters in result
        list_unused_files = [filename for (subdir, dirs, filename) in unused_files_found]

        self.assertEqual(list_unused_files, ["fileNOTindb.txt"])


class VideoTests(unittest.TestCase):
    # These tests are causing UnicodeDecodeError errors.
    def setUp(self):
        sys.stderr.write('inside of VideoTests setUp\n')
        self.vidfilename = "signbank/video/testmedia/video.mp4"
        self.videofile = File(open(self.vidfilename), "12345.mp4")

    # def test_Video_create(self):
    #     """We can create a video object"""
    #     sys.stderr.write('inside of VideoTests test_Video_create\n')
    #
    #     vid = Video.objects.create(videofile=self.videofile)
    #
    #     # new file should be located in upload
    #     self.assertEqual(os.path.dirname(vid.videofile.name), settings.VIDEO_UPLOAD_LOCATION)
    #     self.assertTrue(os.path.exists(vid.videofile.path), "vidfile doesn't exist at %s" % (vid.videofile.path,))
    #
    #     # test deletion of files
    #
    #     vid.delete_files()
    #     self.assertFalse(os.path.exists(vid.videofile.path), "vidfile still exists after delete at %s" % (vid.videofile.path,))
    #
    # def test_GlossVideo_create(self):
    #     """We can create a GlossVideo object"""
    #     sys.stderr.write('inside of VideoTests test_GlossVideo_create\n')
    #
    #     vid = GlossVideo.objects.create(videofile=self.videofile)
    #
    #
    #     self.assertTrue(os.path.exists(vid.videofile.path), "vidfile doesn't exist at %s" % (vid.videofile.path,))
    #
    #     vid.delete_files()
    #     self.assertFalse(os.path.exists(vid.videofile.path), "vidfile still exists after delete at %s" % (vid.videofile.path,))
    #
    #
    #
    # def test_Video_poster_path(self):
    #     """We can generate a poster image for a video"""
    #     sys.stderr.write('inside of VideoTests test_Video_poster_path\n')
    #
    #     vid = Video.objects.create(videofile=self.videofile)
    #     # remove video file when done
    #     self.addCleanup(lambda: os.unlink(vid.videofile.path))
    #
    #     poster = vid.poster_path()
    #     poster_abs = os.path.join(settings.MEDIA_ROOT, poster)
    #     # remove poster image when done
    #     self.addCleanup(lambda: os.unlink(poster_abs))
    #
    #     self.assertTrue(os.path.exists(poster_abs), "poster image %s is missing" % (poster_abs,))
    #
    #     # do it again should give the same result, but won't have created the file
    #     poster2 = vid.poster_path()
    #     self.assertEqual(poster, poster2)
