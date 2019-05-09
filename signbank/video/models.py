""" Models for the video application
keep track of uploaded videos and converted versions
"""

from django.db import models
from django.conf import settings
import sys, os, time, shutil

from signbank.video.convertvideo import extract_frame, convert_video, ffmpeg

from django.core.files.storage import FileSystemStorage
from django.contrib.auth import models as authmodels
# from django.contrib.auth.models import User
from datetime import datetime

from signbank.dictionary.models import *

if sys.argv[0] == 'mod_wsgi':
    from signbank.dictionary.models import *
else:
    from signbank.dictionary.models import Gloss


class Video(models.Model):
    """A video file stored on the site"""

    # video file name relative to MEDIA_ROOT
    videofile = models.FileField("Video file in h264 mp4 format", upload_to=settings.VIDEO_UPLOAD_LOCATION)

    def __str__(self):
        return self.videofile.name

    def process(self):
        """The clean method will try to validate the video
        file format, optimise for streaming and generate
        the poster image"""

        self.poster_path()
        # self.ensure_mp4()


    def poster_path(self, create=True):
        """Return the path of the poster image for this
        video, if create=True, create the image if needed
        Return None if create=False and the file doesn't exist"""

        vidpath, ext = os.path.splitext(self.videofile.path)
        poster_path = vidpath + ".jpg"

        if not os.path.exists(poster_path):
            if create:
                # need to create the image
                extract_frame(self.videofile.path, poster_path)
            else:
                return None

        return poster_path


    def poster_url(self):
        """Return the URL of the poster image for this video"""

        # generate the poster image if needed
        path = self.poster_path()

        # splitext works on urls too!
        vidurl, ext = os.path.splitext(self.videofile.url)
        poster_url = vidurl + ".jpg"

        return poster_url


    def get_absolute_url(self):
        return self.videofile.url


    def ensure_mp4(self):
        """Ensure that the video file is an h264 format
        video, convert it if necessary"""

        # convert video to use the right size and iphone/net friendly bitrate
        # create a temporary copy in the new format
        # then move it into place

        # print "ENSURE: ", self.videofile.path

        (basename, ext) = os.path.splitext(self.videofile.path)
        tmploc = basename + "-conv.mp4"
        err = convert_video(self.videofile.path, tmploc, force=True)
        # print tmploc
        shutil.move(tmploc, self.videofile.path)


    def delete_files(self):
        """Delete the files associated with this object"""

        try:
            os.unlink(self.videofile.path)
            poster_path = self.poster_path(create=False)
            if poster_path:
                os.unlink(poster_path)
        except:
            pass


import shutil

class GlossVideoStorage(FileSystemStorage):
    """Implement our shadowing video storage system"""

    def __init__(self, location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL):
        super(GlossVideoStorage, self).__init__(location, base_url)


    def get_valid_name(self, name):
        """Generate a valid name, we use directories named for the
        first two digits in the filename to partition the videos"""

        (targetdir, basename) = os.path.split(name)
        
        path = os.path.join(str(basename)[:2], str(basename))

        result = os.path.join(targetdir, path)

        return result


storage = GlossVideoStorage()

# The 'action' choices are used in the GlossVideoHistory class
ACTION_CHOICES = (('delete', 'delete'),
                  ('upload', 'upload'),
                  ('rename', 'rename'),
                  ('watch', 'watch'),
                  )


class GlossVideoHistory(models.Model):
    """History of video uploading and deletion"""

    action = models.CharField("Video History Action",max_length=6, choices=ACTION_CHOICES, default='watch')
    # When was this action done?
    datestamp = models.DateTimeField("Date and time of action", auto_now_add=True)  # WAS: default=datetime.now()
    # See 'vfile' in video.views.addvideo
    uploadfile = models.TextField("User upload path", default='(not specified)')
    # See 'goal_location' in addvideo
    goal_location = models.TextField("Full target path", default='(not specified)')

    # WAS: Many-to-many link: to the user that has uploaded or deleted this video
    # WAS: actor = models.ManyToManyField("", User)
    # The user that has uploaded or deleted this video
    actor = models.ForeignKey(authmodels.User)

    # One-to-many link: to the Gloss in dictionary.models.Gloss
    gloss = models.ForeignKey(Gloss)

    def __str__(self):

        # Basic feedback from one History item: gloss-action-date
        name = self.gloss.idgloss + ': ' + self.action + ', (' + str(self.datestamp) + ')'
        return name.encode('ascii', errors='replace')

    class Meta:
        ordering = ['datestamp']


class GlossVideo(models.Model):
    """A video that represents a particular idgloss"""

    videofile = models.FileField("video file", upload_to=settings.GLOSS_VIDEO_DIRECTORY, storage=storage)

    gloss = models.ForeignKey(Gloss)

    ## video version, version = 0 is always the one that will be displayed
    # we will increment the version (via reversion) if a new video is added
    # for this gloss
    version = models.IntegerField("Version", default=0)

    def process(self):
        """The clean method will try to validate the video
        file format, optimise for streaming and generate
        the poster image"""

        self.poster_path()
        # self.ensure_mp4()

    def poster_path(self, create=True):
        """Return the path of the poster image for this
        video, if create=True, create the image if needed
        Return None if create=False and the file doesn't exist"""

        vidpath, ext = os.path.splitext(self.videofile.path)
        poster_path = vidpath + ".jpg"

        if not os.path.exists(poster_path):
            if create:
                # need to create the image
                extract_frame(self.videofile.path, poster_path)
            else:
                return None

        return poster_path

    def poster_url(self):
        """Return the URL of the poster image for this video"""

        # generate the poster image if needed
        path = self.poster_path()

        # splitext works on urls too!
        vidurl, ext = os.path.splitext(self.videofile.url)
        poster_url = vidurl + ".jpg"

        return poster_url

    def get_absolute_url(self):

        return self.videofile.url

    def ensure_mp4(self):
        """Ensure that the video file is an h264 format
        video, convert it if necessary"""

        # convert video to use the right size and iphone/net friendly bitrate
        # create a temporary copy in the new format
        # then move it into place

        # print "ENSURE: ", self.videofile.path

        (basename, ext) = os.path.splitext(self.videofile.path)
        tmploc = basename + "-conv.mp4"
        err = convert_video(self.videofile.path, tmploc, force=True)
        # print tmploc
        shutil.move(tmploc, self.videofile.path)

    def small_video(self):
        """Return the URL of the poster image for this video"""

        # generate the poster image if needed
        path = self.videofile.path
        filename = os.path.basename(path)
        fname, fext = os.path.splitext(filename)
        small_filename = fname + '_small' + fext
        folder = os.path.dirname(self.videofile.path)
        small_video_path = os.path.join(folder, small_filename)
        if os.path.exists(small_video_path):
            return small_video_path
        else:
            return None

    def delete_files(self):
        """Delete the files associated with this object"""

        small_video_path = self.small_video()
        try:
            os.unlink(self.videofile.path)
            poster_path = self.poster_path(create=False)
            if small_video_path:
                os.unlink(small_video_path)
            if poster_path:
                os.unlink(poster_path)
        except:
            pass

    def get_mobile_url(self):
        """Return a URL to serve the mobile version of this
        video, this uses MEDIA_MOBILE_URL as a prefix
        rather than MEDIA_URL but is otherwise the same"""

        url = self.get_absolute_url()
        return url.replace(settings.MEDIA_URL, settings.MEDIA_MOBILE_URL)


    def reversion(self, revert=False):
        """We have a new version of this video so increase
        the version count here and rename the video
        to video.mp4.bak.V where V is the version number

        unless revert=True, in which case we go the other
        way and decrease the version number, if version=0
        we delete ourselves"""


        if revert:
            print("REVERT VIDEO", self.videofile.name, self.version)
            if self.version==0:
                print("DELETE VIDEO VIA REVERSION", self.videofile.name)
                self.delete_files()
                self.delete()
                return
            else:
                # remove .bak from filename and decrement the version
                (newname, bak) = os.path.splitext(self.videofile.name)
                if bak != '.bak':
                    # hmm, something bad happened
                    raise Exception('Unknown suffix on stored video file. Expected .bak')
                self.version -= 1
        else:
            # find a name for the backup, a filename that isn't used already
            newname = self.videofile.name
            while os.path.exists(os.path.join(storage.location, newname)):
                self.version += 1
                newname = newname + ".bak"

        # now do the renaming
        
        os.rename(os.path.join(storage.location, self.videofile.name), os.path.join(storage.location, newname))
        # also remove the post image if present, it will be regenerated
        poster = self.poster_path(create=False)
        if poster != None:
            os.unlink(poster)
        self.videofile.name = newname
        self.save()


    def __str__(self):
        # this coercion to a string type sometimes causes special characters in the filename to be a problem
        # code has been introduced elsewhere to make sure paths are the correct encoding
        return self.videofile.name




