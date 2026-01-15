import os
import unittest
from io import StringIO

from django.core.management import call_command
from django.conf import settings

from signbank.video.management.commands import remove_unused


class CommandTests(unittest.TestCase):
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
        with open(os.path.join(some_folder_path, "fileNOTindb.txt"), 'a'):
            pass
        with open(os.path.join(some_folder_path, "fileindb.txt"), 'a'):
            pass

        # files in database
        filenames_in_db = ['fileindb.txt']

        # compare test files with db filenames
        unused_files_found = remove_unused.find_unused_files(self, some_folder_path, filenames_in_db)
        self.assertEqual(unused_files_found, ["fileNOTindb.txt"])
