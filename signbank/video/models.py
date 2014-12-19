""" Models for the video application
keep track of uploaded videos and converted versions
"""

from django.db import models
from django.conf import settings
import sys, os, time, shutil

from convertvideo import extract_frame, convert_video, ffmpeg

from django.core.files.storage import FileSystemStorage
from signbank.dictionary.models import Gloss


class VideoPosterMixin:
    """Base class for video models that adds a method
    for generating poster images

    Concrete class should have fields 'videofile' and 'poster'
    """

    def process(self):
        """The clean method will try to validate the video
        file format, optimise for streaming and generate
        the poster image"""

        self.poster_path()
        #self.ensure_mp4()


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

        #print "ENSURE: ", self.videofile.path
        
        (basename, ext) = os.path.splitext(self.videofile.path)
        tmploc = basename + "-conv.mp4"
        err = convert_video(self.videofile.path, tmploc, force=True)
        #print tmploc
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


class Video(models.Model, VideoPosterMixin):
    """A video file stored on the site"""

    # video file name relative to MEDIA_ROOT
    videofile = models.FileField("Video file in h264 mp4 format", upload_to=settings.VIDEO_UPLOAD_LOCATION)

    def __unicode__(self):
        return self.videofile.name


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

class GlossVideo(models.Model, VideoPosterMixin):
    """A video that represents a particular idgloss"""

    videofile = models.FileField("video file", upload_to=settings.GLOSS_VIDEO_DIRECTORY, storage=storage)
    gloss = models.ForeignKey(Gloss)
    
    
    
    ## video version, version = 0 is always the one that will be displayed
    # we will increment the version (via reversion) if a new video is added
    # for this gloss
    version = models.IntegerField("Version", default=0)

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
            print "REVERT VIDEO", self.videofile.name, self.version
            if self.version==0:
                print "DELETE VIDEO VIA REVERSION", self.videofile.name
                self.delete_files()
                self.delete()
                return
            else:
                # remove .bak from filename and decrement the version
                (newname, bak) = os.path.splitext(self.videofile.name)
                if bak != '.bak':
                    # hmm, something bad happened
                    raise Http500()
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


    def __unicode__(self):
        return self.videofile.name




