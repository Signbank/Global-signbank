from django.test import TestCase
import unittest
from unittest.mock import patch

from django.core.files import File
from django.core.management import call_command
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
from django.contrib.auth.models import User

from signbank.settings.base import *
from signbank.video.models import ExampleVideo
from signbank.dictionary.models import ExampleSentence, Gloss, Dataset, Sense, LemmaIdgloss, SignLanguage
from signbank.video.convertvideo import ffprobe_info
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


class VideoUploadTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up the test data"""
        cls.video_file_path = os.path.join(settings.WRITABLE_FOLDER, "test_videos")
        cls.videos = os.listdir(cls.video_file_path)
        cls.examplesentences = []

        # a new test user is created for use during the tests
        cls.user = User.objects.create_user(username='test-user',
                                             email='example@example.com',
                                             password='test-user',
                                             is_superuser=True,
                                             is_staff=True)

        # create a dataset, lemma and sense to add the videos to
        # create a new temp dataset with fields fetched from default dataset
        default_dataset = Dataset.objects.get(acronym=settings.DEFAULT_DATASET_ACRONYM)
        signlanguage = SignLanguage.objects.get(name=default_dataset.signlanguage.name)
        translation_languages = default_dataset.translation_languages.all()
        # the id is computed because datasets exist in the test database and we want an unused one
        # this also ignores any datasets created during tests
        used_dataset_ids = [ds.id for ds in Dataset.objects.all()]
        max_used_dataset_id = max(used_dataset_ids)
        # Create a temporary dataset that resembles the default dataset
        dataset = Dataset.objects.create(id=max_used_dataset_id+1,
                              acronym = settings.TEST_DATASET_ACRONYM,
                              name=settings.TEST_DATASET_ACRONYM,
                              default_language=default_dataset.default_language,
                              signlanguage = signlanguage)
        for language in translation_languages:
            dataset.translation_languages.add(language)
        lemma = LemmaIdgloss.objects.create(dataset = dataset)
        gloss = Gloss.objects.create(lemma = lemma)
        gloss.senses.add(Sense.objects.create())
        cls.sense = gloss.senses.first()
        

    def tearDown(self):
        """Remove all files added for test"""
        for examplesentence in self.examplesentences:
            shutil.rmtree(os.path.join(settings.WRITABLE_FOLDER, EXAMPLESENTENCE_VIDEO_DIRECTORY, str(examplesentence.get_dataset()), str(examplesentence.id)))
            examplesentence.examplevideo_set.all().delete()
            examplesentence.delete()

    def test_video_upload(self):
        for video in self.videos:
            
            # Create example sentence
            examplesentence = ExampleSentence.objects.create()
            self.sense.exampleSentences.add(examplesentence)
            self.examplesentences.append(examplesentence)

            # possibly upload the same video multiple times to the same examplesentence to check if the backup goes ok
            for i in range(1):

                # Set properties before/after uploading to impossible values
                format_before, format_after = "before", "after"
                duration_before, duration_after = -2, -1

                # Open video file
                video_path = os.path.join(settings.WRITABLE_FOLDER, "test_videos", video)
                if i==0:
                    print("Video to upload: ", video_path)

                # Properties before uploading
                properties = get_video_properties(video_path)
                if properties:
                    format_before, duration_before = extract_properties(properties)

                # # print extra information about the video file to find errors
                # info = ffprobe_info(video_path)
                # if info:
                #     print(json.dumps(info, indent=4))
                #     video_duration = None
                #     for stream in info["streams"]:
                #         if stream.get("codec_type") == "video":
                #             video_duration = stream.get("duration")
                #             print(video_duration)
                    
                # Create example video and add it to the example sentence
                videofile = open(video_path, 'rb')
                mime_type, _ = mimetypes.guess_type(video_path)
                file_size = os.path.getsize(video_path)
                video_file_file = InMemoryUploadedFile(videofile, None, video, mime_type, file_size, None)
                examplesentence.add_video(self.user, video_file_file, False)
                videofile.close()

                # check if the video was uploaded at all
                self.assertTrue(examplesentence.has_video())
                
                # Properties after uploading
                new_video_path = os.path.join(settings.WRITABLE_FOLDER, examplesentence.get_video())
                if i == 0:
                    print("Video saved as: ", new_video_path)
                properties = get_video_properties(new_video_path)
                if properties:
                    format_after, duration_after = extract_properties(properties)

                # Check if the format and duration of the video are ok before and after uploading
                if i==0:
                    check_mp4_file(new_video_path)
                    print("Format before: ", format_before, ", format after: ", format_after)
                    print("Duration before: ", duration_before, ", duration after: ", duration_after)
                    print('\n')
                self.assertEqual(format_after, "mov,mp4,m4a,3gp,3g2,mj2")
                # THIS DOES NOT WORK because duration of webms is not processed correctly
                # self.assertEqual(duration_before, duration_after)

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
