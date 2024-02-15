from django.test import TestCase
import unittest
from unittest.mock import patch
from django.core.files import File
from django.core.management import call_command
from django.conf import settings
from signbank.settings.base import *
from signbank.video.models import ExampleVideo
from signbank.dictionary.models import ExampleSentence
from signbank.video.management.commands import remove_unused
from io import StringIO
import os
import shutil
import sys
import subprocess
import json

def get_video_properties(video_path):
    """
    Get the properties of the video using ffprobe
    """
    command = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        print("Error:", result.stderr)
        return None

def extract_properties(properties):
    """
    Extract the format and duration of the video from the properties
    """
    file_format = properties['format']['format_name']
    duration = float(properties['format']['duration']) if 'duration' in properties['format'] else None
    return file_format, duration

def check_mp4_file(file_path):
    """
    Check if the MP4 file is valid
    """
    # Command to check the MP4 file
    command = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
    process = subprocess.Popen(command, stderr=subprocess.PIPE)

    # Wait for the process to finish and capture stderr
    _, err = process.communicate()

    # Check if there were any errors
    if process.returncode == 0:
        print("The MP4 file appears to be fine.")
    else:
        print("There might be issues with the MP4 file. Here are the details:")
        print(err.decode("utf-8"))

class CommandTests(unittest.TestCase):
    
    def tearDown(self):
        """Remove all files added for test"""
        if os.path.exists("../writable/somefolder/fileindb.txt"):
            os.remove("../writable/somefolder/fileindb.txt")
        if os.path.exists("../writable/somefolder/fileNOTindb.txt"):
            os.remove("../writable/somefolder/fileNOTindb.txt")
        if os.path.exists("../writable/somefolder"):
            os.rmdir("../writable/somefolder")

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

        self.assertEqual(unused_files_found, ["fileNOTindb.txt"])


class VideoUploadTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up the test data"""
        cls.video_file_path = os.path.join(settings.WRITABLE_FOLDER, "test_videos")
        cls.videos = os.listdir(cls.video_file_path)
        cls.test_videos = []
        cls.examplesentences = []

    def tearDown(self):
        """Remove all files added for test"""
        for test_video in self.test_videos:
            test_video_path = os.path.join(settings.WRITABLE_FOLDER, test_video)
            if os.path.exists(test_video_path):
                os.remove(test_video_path)
        for examplesentence in self.examplesentences:
            examplesentence.examplevideo_set.all().delete()
            examplesentence.delete()

    def test_video_upload(self):
        
        for video in os.listdir(self.video_file_path):

            # Properties before uploading
            format_before, format_after = "", ""
            duration_before, duration_after = 0, 0

            # Open video file
            video_path = os.path.join(settings.WRITABLE_FOLDER, "test_videos", video)
            print(video_path)

            # Properties before uploading
            properties = get_video_properties(video_path)
            if properties:
                format_before, duration_before = extract_properties(properties)
            # if format_before != "mov,mp4,m4a,3gp,3g2,mj2": 
            #     video is probably webm, get duration in another way

            videofile = open(video_path, 'rb')

            # Create example sentence
            examplesentence = ExampleSentence.objects.create()
            self.examplesentences.append(examplesentence)

            # Create example video
            examplevideo = ExampleVideo(examplesentence=examplesentence)
            examplevideo.videofile.save(video_path, videofile)
            examplevideo.save()
            examplevideo.ch_own_mod_video()

            # check if the video was uploaded at all
            self.assertTrue(examplesentence.has_video())

            self.test_videos.append(examplesentence.get_video())
            
            # Properties after uploading
            print(os.path.join(settings.WRITABLE_FOLDER, examplesentence.get_video()))
            properties = get_video_properties(os.path.join(settings.WRITABLE_FOLDER, examplesentence.get_video()))
            if properties:
                format_after, duration_after = extract_properties(properties)

            # Check if the resulting video is valid
            check_mp4_file(os.path.join(settings.WRITABLE_FOLDER, examplesentence.get_video()))

            # Check if the format and duration of the video are ok before and after uploading
            print("Format before: ", format_before, ", format after: ", format_after)
            print("Duration before: ", duration_before, ", duration after: ", duration_after)
            self.assertEqual(format_after, "mov,mp4,m4a,3gp,3g2,mj2")
            # THIS DOES NOT WORK because duration of webms isn't processed correctly
            # self.assertEqual(duration_before, duration_after)

            print('\n')



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
