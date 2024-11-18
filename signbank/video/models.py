""" Models for the video application
keep track of uploaded videos and converted versions
"""

from django.db import models
from django.conf import settings
import sys
import os
import time
import stat
import shutil

from signbank.video.convertvideo import extract_frame, convert_video, probe_format, make_thumbnail_video

from django.core.files.storage import FileSystemStorage
from django.contrib.auth import models as authmodels
from signbank.settings.base import WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY, FFMPEG_PROGRAM
# from django.contrib.auth.models import User
from datetime import datetime

from signbank.dictionary.models import *


if sys.argv[0] == 'mod_wsgi':
    from signbank.dictionary.models import *
else:
    from signbank.dictionary.models import Gloss, Language


def get_two_letter_dir(idgloss):
    foldername = idgloss[:2]

    if len(foldername) == 1:
        foldername += '-'

    return foldername


class GlossVideoStorage(FileSystemStorage):
    """Implement our shadowing video storage system"""

    def __init__(self, location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL):
        super(GlossVideoStorage, self).__init__(location, base_url)

    def get_valid_name(self, name):
        return name


storage = GlossVideoStorage()

# The 'action' choices are used in the GlossVideoHistory class
ACTION_CHOICES = (('delete', 'delete'),
                  ('upload', 'upload'),
                  ('rename', 'rename'),
                  ('watch', 'watch'),
                  ('import', 'import'),
                  )


class ExampleVideoHistory(models.Model):
    """History of video uploading and deletion"""

    action = models.CharField("Video History Action", max_length=6, choices=ACTION_CHOICES, default='watch')
    # When was this action done?
    datestamp = models.DateTimeField("Date and time of action", auto_now_add=True)  # WAS: default=datetime.now()
    # See 'vfile' in video.views.addvideo
    uploadfile = models.TextField("User upload path", default='(not specified)')
    # See 'goal_location' in addvideo
    goal_location = models.TextField("Full target path", default='(not specified)')

    # WAS: Many-to-many link: to the user that has uploaded or deleted this video
    # WAS: actor = models.ManyToManyField("", User)
    # The user that has uploaded or deleted this video
    actor = models.ForeignKey(authmodels.User, on_delete=models.CASCADE)

    # One-to-many link: to the Gloss in dictionary.models.Gloss
    examplesentence = models.ForeignKey(ExampleSentence, on_delete=models.CASCADE)

    def __str__(self):

        # Basic feedback from one History item: gloss-action-date
        name = f"{self.examplesentence.id}: {self.action}, ({self.datestamp})"
        return name

    class Meta:
        ordering = ['datestamp']


class GlossVideoHistory(models.Model):
    """History of video uploading and deletion"""

    action = models.CharField("Video History Action", max_length=6, choices=ACTION_CHOICES, default='watch')
    # When was this action done?
    datestamp = models.DateTimeField("Date and time of action", auto_now_add=True)  # WAS: default=datetime.now()
    # See 'vfile' in video.views.addvideo
    uploadfile = models.TextField("User upload path", default='(not specified)')
    # See 'goal_location' in addvideo
    goal_location = models.TextField("Full target path", default='(not specified)')

    # WAS: Many-to-many link: to the user that has uploaded or deleted this video
    # WAS: actor = models.ManyToManyField("", User)
    # The user that has uploaded or deleted this video
    actor = models.ForeignKey(authmodels.User, on_delete=models.CASCADE)

    # One-to-many link: to the Gloss in dictionary.models.Gloss
    gloss = models.ForeignKey(Gloss, on_delete=models.CASCADE)

    def __str__(self):

        # Basic feedback from one History item: gloss-action-date
        name = f"{self.gloss.idgloss}: {self.action}, ({self.datestamp})"
        return name

    class Meta:
        ordering = ['datestamp']


# VIDEO PATH #
#
# The path of a video is constructed by
# 1. the acronym of the corresponding dataset
# 2. the first 2 characters of the idgloss
# 3. the idgloss (which is the lemmaidglosstranslation of the dataset default language)
#
# That means that if the dataset acronym, the dataset default language or the lemmaidgloss for the
# dataset default language is changed, the video path should also be changed.
#
# This is done by:
# * The video path: get_video_file_path(...)
# * Changes to the dataset, acronym of default language: process_dataset_changes(...)
# * Changes to the lemmaidglosstranslations: process_lemmaidglosstranslation_changes(...)


def get_gloss_path_to_video_file_on_disk(gloss):
    idgloss = gloss.idgloss
    two_letter_dir = get_two_letter_dir(idgloss)
    dataset_dir = gloss.lemma.dataset.acronym
    filename = idgloss + '-' + str(gloss.id) + '.mp4'
    relative_path = os.path.join(GLOSS_VIDEO_DIRECTORY, dataset_dir, two_letter_dir, filename)
    file_system_path = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, dataset_dir, two_letter_dir, filename)
    if os.path.exists(file_system_path):
        return relative_path
    else:
        return ""


def get_video_file_path(instance, filename, nmevideo=False, perspective='', offset=1, version=0):
    """
    Return the full path for storing an uploaded video
    :param instance: A GlossVideo instance
    :param filename: the original file name
    :param nmevideo: boolean whether this is an nme video
    :param perspective: optional string for either 'left' or 'right'
    :param offset: order in sequence of NME video
    :param version: the version to determine the number of .bak extensions
    :return: 
    """
    (base, ext) = os.path.splitext(filename)

    idgloss = instance.gloss.idgloss
    two_letter_dir = get_two_letter_dir(idgloss)

    video_dir = settings.GLOSS_VIDEO_DIRECTORY
    try:
        dataset_dir = instance.gloss.lemma.dataset.acronym
    except KeyError:
        dataset_dir = ""
        if settings.DEBUG_VIDEOS:
            print('get_video_file_path: dataset_dir is empty for gloss ', str(instance.gloss.pk))
    if nmevideo:
        nme_video_offset = '_nme_' + str(offset)
        filename = idgloss + '-' + str(instance.gloss.id) + nme_video_offset + ext
    elif perspective:
        video_perpsective = '_' + perspective
        filename = idgloss + '-' + str(instance.gloss.id) + video_perpsective + ext
    elif version > 0:
        filename = idgloss + '-' + str(instance.gloss.id) + ext + '.bak' + str(instance.id)
    else:
        filename = idgloss + '-' + str(instance.gloss.id) + ext

    path = os.path.join(video_dir, dataset_dir, two_letter_dir, filename)
    if hasattr(settings, 'ESCAPE_UPLOADED_VIDEO_FILE_PATH') and settings.ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        from django.utils.encoding import escape_uri_path
        path = escape_uri_path(path)
    if settings.DEBUG_VIDEOS:
        print('get_video_file_path: ', path)
    return path


small_appendix = '_small'


def add_small_appendix(path, reverse=False):
    path_no_extension, extension = os.path.splitext(path)
    if reverse and path_no_extension.endswith(small_appendix):
        return path_no_extension[:-len(small_appendix)] + extension
    elif not reverse and not path_no_extension.endswith(small_appendix):
        return path_no_extension + small_appendix + extension
    return path


def validate_file_extension(value):
    if value.file.content_type not in ['video/mp4', 'video/quicktime']:
        raise ValidationError(u'Error message')
    

# VIDEO PATH FOR AN EXAMPLESENTENCE #
#
# The path of a video is constructed by
# 1. the acronym of the corresponding dataset
# 2. the id of the examplesentence
#
# That means that if the dataset acronym, the dataset default language or the lemmaidgloss for the
# dataset default language is changed, the video path should also be changed.
#
# This is done by:
# * The video path: get_sentence_video_file_path(...)


def get_sentence_video_file_path(instance, filename, version=0):
    """
    Return the full path for storing an uploaded video
    :param instance: A ExampleVideo instance
    :param filename: the original file name
    :param version: the version to determine the number of .bak extensions
    :return: 
    """

    (base, ext) = os.path.splitext(filename)
    video_dir = settings.EXAMPLESENTENCE_VIDEO_DIRECTORY
    try:
        dataset_dir = os.path.join(instance.examplesentence.get_dataset().acronym, str(instance.examplesentence.id))
    except ObjectDoesNotExist:
        dataset_dir = ""

    if version > 0:
        filename = str(instance.examplesentence.id) + ext + '.bak' + str(instance.id)
    else:
        filename = str(instance.examplesentence.id) + ext

    path = os.path.join(video_dir, dataset_dir, filename)
    if hasattr(settings, 'ESCAPE_UPLOADED_VIDEO_FILE_PATH') and settings.ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        from django.utils.encoding import escape_uri_path
        path = escape_uri_path(path)
    return path


# VIDEO PATH FOR AN ANNOTATED SENTENCE #
#
# The path of a video is constructed by
# 1. the acronym of the corresponding dataset
# 2. the id of the annotated sentence
#
# That means that if the dataset acronym, the dataset default language or the lemmaidgloss for the
# dataset default language is changed, the video path should also be changed.
#
# This is done by:
# * The video path: get_annotated_video_file_path(...)
def get_annotated_video_file_path(instance, filename, version=0):
    """
    Return the full path for storing an uploaded video
    :param instance: An AnnotatedVideo instance
    :param filename: the original file name
    :param version: the version to determine the number of .bak extensions
    :return: 
    """

    (base, ext) = os.path.splitext(filename)
    video_dir = settings.ANNOTATEDSENTENCE_VIDEO_DIRECTORY
    dataset = instance.annotatedsentence.get_dataset().acronym
    dataset_dir = os.path.join(dataset, str(instance.annotatedsentence.id))
    if version > 0:
        filename = str(instance.examplesentence.id) + ext + '.bak' + str(instance.id)
    else:
        filename = str(instance.examplesentence.id) + ext

    path = os.path.join(video_dir, dataset_dir, filename)
    if hasattr(settings, 'ESCAPE_UPLOADED_VIDEO_FILE_PATH') and settings.ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        from django.utils.encoding import escape_uri_path
        path = escape_uri_path(path)

    return path


class ExampleVideo(models.Model):
    """A video that shows an example of the use of a particular sense"""

    videofile = models.FileField("video file", upload_to=get_sentence_video_file_path, storage=storage,
                                 validators=[validate_file_extension])

    examplesentence = models.ForeignKey(ExampleSentence, on_delete=models.CASCADE)

    # video version, version = 0 is always the one that will be displayed
    # we will increment the version (via reversion) if a new video is added
    # for this gloss
    version = models.IntegerField("Version", default=0)

    def save(self, *args, **kwargs):
        self.ensure_mp4()
        super(ExampleVideo, self).save(*args, **kwargs)

    def process(self):
        """The clean method will try to validate the video
        file format, optimise for streaming and generate
        the poster image"""

        self.poster_path()
        # self.ensure_mp4()

    def get_absolute_url(self):
        return self.videofile.url

    def ensure_mp4(self):
        """Ensure that the video file is an h264 format
        video, convert it if necessary"""

        # convert video to use the right size and iphone/net friendly bitrate
        # create a temporary copy in the new format
        # then move it into place

        (basename, ext) = os.path.splitext(self.videofile.path)
        if ext == '.mov' or ext == '.webm':
            oldloc = self.videofile.path
            newloc = basename + ".mp4"
            err = convert_video(oldloc, newloc, force=False)
            self.videofile.name = get_sentence_video_file_path(self, os.path.basename(newloc))
            os.remove(oldloc)

    def ch_own_mod_video(self):
        """Change owner and permissions"""
        location = self.videofile.path
        # make sure they're readable by everyone
        # os.chown(location, 1000, 1002)
        os.chmod(location, stat.S_IRWXU | stat.S_IRWXG)

    def small_video(self, use_name=False):
        """Return the URL of the small version for this video
        :param use_name: whether videofile.name should be used instead of videofile.path
        """
        small_video_path = add_small_appendix(self.videofile.path)
        if os.path.exists(small_video_path):
            if use_name:
                return add_small_appendix(self.videofile.name)
            return small_video_path
        else:
            return None

    def make_small_video(self):
        # this method is not called (bugs)
        from CNGT_scripts.python.resizeVideos import VideoResizer

        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(self.videofile))
        try:
            resizer = VideoResizer([video_file_full_path], FFMPEG_PROGRAM, 180, 0, 0)
            resizer.run()
        except Exception as e:
            print("Error resizing video: ", video_file_full_path)
            print(e)

    def make_poster_image(self):
        from signbank.tools import generate_still_image
        try:
            generate_still_image(self)
        except OSError:
            import sys
            print('Error generating still image', sys.exc_info())

    def convert_to_mp4(self):
        # this method is not called (bugs)
        print('Convert to mp4: ', self.videofile.path)
        name, _ = os.path.splitext(self.videofile.path)
        out_name = name + "_copy.mp4"
        import ffmpeg
        stream = ffmpeg.input(self.videofile.path)
        stream = ffmpeg.output(stream, out_name, vcodec='h264')
        ffmpeg.run(stream, quiet=True)
        os.rename(out_name, self.videofile.path)
        print("Finished converting {}".format(self.videofile.path))

    def delete_files(self):
        """Delete the files associated with this object"""

        small_video_path = self.small_video()
        try:
            os.unlink(self.videofile.path)
        except OSError:
            pass

    def reversion(self, revert=False):
        """We have a new version of this video so increase
        the version count here and rename the video
        to video.mp4.bak.V where V is the version number

        unless revert=True, in which case we go the other
        way and decrease the version number, if version=0
        we delete ourselves"""
        if revert:
            print("REVERT VIDEO", self.videofile.name, self.version)
            if self.version == 0:
                print("DELETE VIDEO VIA REVERSION", self.videofile.name)
                self.delete_files()
                self.delete()
                return
            if self.version == 1:
                # remove .bak from filename and decrement the version
                (newname, bak) = os.path.splitext(self.videofile.name)
                expected_extension = '.bak' + str(self.id)
                if bak != expected_extension:
                    print(f'Unknown suffix on stored video file. Expected {expected_extension}')
                    self.delete()
                    self.delete_files()
                    return
                if os.path.isfile(os.path.join(storage.location, self.videofile.name)):
                    os.rename(os.path.join(storage.location, self.videofile.name),
                            os.path.join(storage.location, newname))
                self.videofile.name = newname
            self.version -= 1
            self.save()
        else:
            if self.version == 0:
                # find a name for the backup, a filename that isn't used already
                newname = self.videofile.name + ".bak" + str(self.id)
                if os.path.isfile(os.path.join(storage.location, self.videofile.name)):
                    os.rename(os.path.join(storage.location, self.videofile.name), os.path.join(storage.location, newname))
                self.videofile.name = newname
            self.version += 1
            self.save()

    def __str__(self):
        # this coercion to a string type sometimes causes special characters in the filename to be a problem
        # code has been introduced elsewhere to make sure paths are the correct encoding
        return self.videofile.name

    def move_video(self, move_files_on_disk=True):
        """
        Calculates the new path, moves the video file to the new path and updates the videofile field
        :return: 
        """
        old_path = str(str(self.videofile))
        new_path = get_sentence_video_file_path(self, old_path, self.version)
        if old_path != new_path:
            if move_files_on_disk:
                source = os.path.join(settings.WRITABLE_FOLDER, old_path)
                destination = os.path.join(settings.WRITABLE_FOLDER, new_path)
                if os.path.exists(source):
                    destination_dir = os.path.dirname(destination)
                    if not os.path.exists(destination_dir):
                        os.makedirs(destination_dir)
                    if os.path.isdir(destination_dir):
                        shutil.move(source, destination)

                # Small video
                (source_no_extension, ext) = os.path.splitext(source)
                source_small = add_small_appendix(source)
                (destination_no_extension, ext) = os.path.splitext(destination)
                destination_small = add_small_appendix(destination)
                if os.path.exists(source_small):
                    shutil.move(source_small, destination_small)

            self.videofile.name = new_path
            self.save()

class AnnotatedVideo(models.Model):
    """A video that shows an example of the use of a particular sense"""

    annotatedsentence = models.OneToOneField(AnnotatedSentence, on_delete=models.CASCADE)
    videofile = models.FileField("video file", upload_to=get_annotated_video_file_path, storage=storage,
                                 validators=[validate_file_extension])
    eaffile = models.FileField("eaf file", upload_to=get_annotated_video_file_path, storage=storage)
    source = models.ForeignKey(AnnotatedSentenceSource, null=True, on_delete=models.SET_NULL)
    url = models.URLField("URL", null=True, blank=True)

    # video version, version = 0 is always the one that will be displayed
    # we will increment the version (via reversion) if a new video is added
    # for this gloss 
    # THIS IS NOT IMPLEMENTED YET
    version = models.IntegerField("Version", default=0)

    def save(self, *args, **kwargs):
        self.ensure_mp4()
        super(AnnotatedVideo, self).save(*args, **kwargs)

    def get_absolute_url(self):
        from urllib.parse import urlparse
        parsed_url = urlparse(self.url)
        if not parsed_url.scheme:
            return 'http://' + self.url
        return self.url

    def ensure_mp4(self):
        """Ensure that the video file is an h264 format
        video, convert it if necessary"""
        (basename, ext) = os.path.splitext(self.videofile.path)
        if ext == '.mov' or ext == '.webm':
            oldloc = self.videofile.path
            newloc = basename + ".mp4"
            err = convert_video(oldloc, newloc, force=False)
            self.videofile.name = get_annotated_video_file_path(self, os.path.basename(newloc))
            os.remove(oldloc)

    def ch_own_mod_video(self):
        """Change owner and permissions"""
        location = self.videofile.path
        # make sure they're readable by everyone
        # os.chown(location, 1000, 1002)
        os.chmod(location, stat.S_IRWXU | stat.S_IRWXG)

    def delete_files(self, only_eaf=False):
        """Delete the files associated with this object"""
        try:
            os.remove(self.eaffile.path)
            if not only_eaf:
                video_path = os.path.join(settings.WRITABLE_FOLDER, settings.ANNOTATEDSENTENCE_VIDEO_DIRECTORY, self.annotatedsentence.get_dataset().acronym, str(self.annotatedsentence.id))
                shutil.rmtree(video_path)
        except OSError:
            pass

    def get_eaffile_name(self):
        return os.path.basename(self.eaffile.name) if self.eaffile else ""

    def get_end_ms(self):
        """Get the duration of a video in ms using ffprobe."""
        import subprocess
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', self.videofile.path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return int(float(result.stdout)*1000)

    def __str__(self):
        # this coercion to a string type sometimes causes special characters in the filename to be a problem
        # code has been introduced elsewhere to make sure paths are the correct encoding
        return self.videofile.name
    
    def convert_milliseconds_to_time_format(self, ms):
        """Convert milliseconds to a time format HH:MM:SS.mmm"""
        milliseconds = ms % 1000
        seconds = (ms // 1000) % 60
        minutes = (ms // (1000 * 60)) % 60
        hours = (ms // (1000 * 60 * 60)) % 24
        return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

    def select_annotations(self, eaf, tier_name, start_ms, end_ms):
        """ Select annotations that are within the selected range """
        
        keys_to_remove = []
        for key in eaf.tiers[tier_name][0]:
            annotation_list = list(eaf.tiers[tier_name][0][key])
            time_ms_start = eaf.timeslots[annotation_list[0]]
            time_ms_end = eaf.timeslots[annotation_list[1]]
            # if resulting annotation is shorter than 10ms, remove it
            if (min(time_ms_end, end_ms) - max(time_ms_start, start_ms)) < 100:
                keys_to_remove.append(key)
            # if annotation is outside of the selected range, remove it
            elif time_ms_end < start_ms or time_ms_start > end_ms:
                keys_to_remove.append(key)
            # if annotation is partially outside of the selected range, adjust it
            elif time_ms_start < start_ms and time_ms_end > start_ms and time_ms_end < end_ms:
                annotation_list[0] = 'ts1000'
            elif time_ms_start > start_ms and time_ms_start < end_ms and time_ms_end > end_ms:
                annotation_list[1] = 'ts1001'
            # if annotation is completely overlapping the selected range, adjust it
            elif time_ms_start < start_ms and time_ms_end > end_ms:
                annotation_list[0] = 'ts1000'
                annotation_list[1] = 'ts1001'
            eaf.tiers[tier_name][0][key] = tuple(annotation_list)
        for key in keys_to_remove:
            del eaf.tiers[tier_name][0][key]

    def cut_video_and_eaf(self, start_ms, end_ms):
        """cut both the video and the annotation file (eaf) to the selected range"""

        import subprocess
        from pathlib import Path
        from pympi.Elan import Eaf

        start_ms, end_ms = int(start_ms), int(end_ms)
        start_time = self.convert_milliseconds_to_time_format(start_ms)
        end_time = self.convert_milliseconds_to_time_format(end_ms)
        
        # Cut the video
        input_file = Path(self.videofile.path)
        temp_output_file = Path(os.path.join(os.path.split(input_file)[0], 'temp.mp4'))
        command = ['ffmpeg', '-i', input_file, '-ss', start_time, '-to', end_time, '-c:v', 'libx264', '-c:a', 'aac', '-y', temp_output_file]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        stderr_str = stderr.decode('utf-8')
        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {stderr_str}")
        else:
            # Overwrite the original file with the cut video
            overwrite_command = ['mv', temp_output_file, input_file]
            process = subprocess.Popen(overwrite_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, stderr = process.communicate()
            stderr_str = stderr.decode('utf-8')
            if process.returncode != 0:
                raise RuntimeError(f"File overwrite error: {stderr_str}")
    
        # Cut the eaf
        eaf = Eaf(self.eaffile.path)
        eaf.timeslots['ts1000'] = start_ms
        eaf.timeslots['ts1001'] = end_ms
        self.select_annotations(eaf, 'Sentences', start_ms, end_ms)
        self.select_annotations(eaf, 'Glosses R', start_ms, end_ms)
        self.select_annotations(eaf, 'Glosses L', start_ms, end_ms)
        # shift the timeslots to start at 0
        for key in eaf.timeslots:
            eaf.timeslots[key] -= start_ms
        eaf.clean_time_slots()
        # link the new video file
        eaf.remove_linked_files()
        eaf.remove_secondary_linked_files()
        relpath = os.path.split(Path(self.videofile.path))[1]
        eaf.add_linked_file(str(self.videofile.path), str(relpath), 'video/mp4', 0)
        eaf.to_file(self.eaffile.path)


class GlossVideo(models.Model):
    """A video that represents a particular idgloss"""

    videofile = models.FileField("video file", storage=storage,
                                 validators=[validate_file_extension])

    gloss = models.ForeignKey(Gloss, on_delete=models.CASCADE)

    # video version, version = 0 is always the one that will be displayed
    # we will increment the version (via reversion) if a new video is added
    # for this gloss
    version = models.IntegerField("Version", default=0)

    def __init__(self, *args, **kwargs):
        if 'upload_to' in kwargs:
            self.upload_to = kwargs.pop('upload_to')
        else:
            self.upload_to = get_video_file_path
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        # self.ensure_mp4()
        super(GlossVideo, self).save(*args, **kwargs)

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

        vidpath, _ = os.path.splitext(self.videofile.path)
        poster_path = vidpath + ".png"
        # replace vidpath with imagepath!
        poster_path = str(poster_path.replace(GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY, 1))

        if not os.path.exists(poster_path):
            if create:
                # need to create the image
                extract_frame(self.videofile.path, poster_path)
            else:
                return None

        return poster_path
    
    def poster_file(self):
        vidpath, ext = os.path.splitext(self.videofile.name)
        poster_file = vidpath + ".png"
        # replace vidpath with imagepath!
        poster_file = str(poster_file.replace(GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY, 1))
        return poster_file

    def ensure_mp4(self):
        """Ensure that the video file is an h264 format
        video, convert it if necessary"""

        # convert video to use the right size and iphone/net friendly bitrate
        # create a temporary copy in the new format
        # then move it into place

        (basename, ext) = os.path.splitext(self.videofile.path)
        if ext == '.mov' or ext == '.webm':
            oldloc = self.videofile.path
            newloc = basename + ".mp4"
            err = convert_video(oldloc, newloc, force=False)
            self.videofile.name = get_video_file_path(self, os.path.basename(newloc))
            os.remove(oldloc)

    def ch_own_mod_video(self):
        """Change owner and permissions"""
        location = self.videofile.path

        # make sure they're readable by everyone
        # os.chown(location, 1000, 1002)
        os.chmod(location, stat.S_IRWXU | stat.S_IRWXG)

    def small_video(self, use_name=False):
        """Return the URL of the small version for this video
        :param use_name: whether videofile.name should be used instead of videofile.path
        """
        small_video_path = add_small_appendix(self.videofile.path)
        if os.path.exists(small_video_path):
            if use_name:
                return add_small_appendix(self.videofile.name)
            return small_video_path
        else:
            return None

    def make_small_video(self):
        # this method is not called (bugs)
        name, _ = os.path.splitext(self.videofile.path)
        small_name = name + "_small.mp4"
        make_thumbnail_video(self.videofile, small_name)

        # from CNGT_scripts.python.resizeVideos import VideoResizer
        # # ffmpeg_small = settings.FFMPEG_OPTIONS + ["-vf", "scale=180:-2"]
        # video_file_full_path = os.path.join(WRITABLE_FOLDER, str(self.videofile))
        # try:
        #     resizer = VideoResizer([video_file_full_path], FFMPEG_PROGRAM, 180, 0, 0)
        #     resizer.run()
        # except Exception as e:
        #     print("Error resizing video: ", video_file_full_path)
        #     print(e)

    def make_poster_image(self):
        from signbank.tools import generate_still_image
        try:
            generate_still_image(self)
        except OSError:
            import sys
            print('Error generating still image', sys.exc_info())

    def convert_to_mp4(self):
        # this method is not called (bugs)
        print('Convert to mp4: ', self.videofile.path)
        name, _ = os.path.splitext(self.videofile.path)
        out_name = name + "_copy.mp4"
        import ffmpeg
        stream = ffmpeg.input(self.videofile.path)
        stream = ffmpeg.output(stream, out_name, vcodec='h264')
        ffmpeg.run(stream, quiet=True)
        os.rename(out_name, self.videofile.path)
        print("Finished converting {}".format(self.videofile.path))

    def delete_files(self):
        """Delete the files associated with this object"""

        if settings.DEBUG_VIDEOS:
            print('delete_files GlossVideo: ', str(self.videofile))

        small_video_path = self.small_video()
        try:
            os.unlink(self.videofile.path)
            poster_path = self.poster_path(create=False)
            if small_video_path:
                os.unlink(small_video_path)
            if poster_path:
                os.unlink(poster_path)
        except (OSError, PermissionError):
            if settings.DEBUG_VIDEOS:
                print('delete_files exception GlossVideo OSError, PermissionError: ', str(self.videofile))
            pass

    def reversion(self, revert=False):
        """We have a new version of this video so increase
        the version count here and rename the video
        to video.mp4.bak.V where V is the version number

        unless revert=True, in which case we go the other
        way and decrease the version number, if version=0
        we delete ourselves"""

        if hasattr(self, 'glossvideonme') or hasattr(self, 'glossvideoperspective'):
            # make sure this is not applied to subclass objects
            return
        if revert:
            print("REVERT VIDEO", self.videofile.name, self.version)
            if self.version == 0:
                print("DELETE VIDEO VIA REVERSION", self.videofile.name)
                self.delete_files()
                self.delete()
                return
            else:
                if self.version == 1:
                    # remove .bak from filename and decrement the version
                    (newname, bak) = os.path.splitext(self.videofile.name)
                    expected_extension = '.bak' + str(self.id)
                    if bak != expected_extension:
                        # hmm, something bad happened
                        print(f'Unknown suffix on stored video file. Expected {expected_extension}')
                        self.delete()
                        self.delete_files()
                        return
                    if os.path.isfile(os.path.join(storage.location, self.videofile.name)):
                        os.rename(os.path.join(storage.location, self.videofile.name),
                                  os.path.join(storage.location, newname))
                    self.videofile.name = newname
                self.version -= 1
                self.save()
        else:
            if self.version == 0:
                # find a name for the backup, a filename that isn't used already
                newname = self.videofile.name + ".bak" + str(self.id)
                if os.path.isfile(os.path.join(storage.location, self.videofile.name)):
                    os.rename(os.path.join(storage.location, self.videofile.name),
                              os.path.join(storage.location, newname))
                self.videofile.name = newname
            self.version += 1
            self.save()

        # also remove the post image if present, it will be regenerated
        poster = self.poster_path(create=False)
        if poster is not None:
            os.unlink(poster)

    def __str__(self):
        # this coercion to a string type sometimes causes special characters in the filename to be a problem
        # code has been introduced elsewhere to make sure paths are the correct encoding
        glossvideoname = self.videofile.name
        if settings.DEBUG_VIDEOS:
            print('__str__ GlossVideo: ', self.videofile.name)
        return glossvideoname

    def is_glossvideonme(self):
        """Test if this instance is a NME Gloss Video"""
        return hasattr(self, 'glossvideonme')

    def is_glossvideoperspective(self):
        """Test if this instance is a Gloss Video Perspective"""
        return hasattr(self, 'glossvideoperspective')

    def move_video(self, move_files_on_disk=True):
        """
        Calculates the new path, moves the video file to the new path and updates the videofile field
        :return: 
        """
        old_path = str(self.videofile)
        new_path = get_video_file_path(self, old_path, version=self.version)
        if old_path != new_path:
            if move_files_on_disk:
                source = os.path.join(settings.WRITABLE_FOLDER, old_path)
                destination = os.path.join(settings.WRITABLE_FOLDER, new_path)
                if os.path.exists(source):
                    destination_dir = os.path.dirname(destination)
                    if not os.path.exists(destination_dir):
                        os.makedirs(destination_dir)
                    if os.path.isdir(destination_dir):
                        shutil.move(source, destination)

                # Small video
                (source_no_extension, ext) = os.path.splitext(source)
                source_small = add_small_appendix(source)
                (destination_no_extension, ext) = os.path.splitext(destination)
                destination_small = add_small_appendix(destination)
                if os.path.exists(source_small):
                    shutil.move(source_small, destination_small)

                # Image
                source_image = source_no_extension.replace(settings.GLOSS_VIDEO_DIRECTORY, settings.GLOSS_IMAGE_DIRECTORY)\
                               + '.png'
                destination_image = destination_no_extension.replace(settings.GLOSS_VIDEO_DIRECTORY, settings.GLOSS_IMAGE_DIRECTORY)\
                               + '.png'
                if os.path.exists(source_image):
                    destination_image_dir = os.path.dirname(destination_image)
                    if not os.path.exists(destination_image_dir):
                        os.makedirs(destination_image_dir)
                    if os.path.isdir(destination_image_dir):
                        shutil.move(source_image, destination_image)

            self.videofile.name = new_path
            self.save()


class GlossVideoDescription(models.Model):
    """A sentence translation belongs to one example sentence"""

    text = models.TextField()
    nmevideo = models.ForeignKey('GlossVideoNME', on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)

    def __str__(self):
        return self.text


class GlossVideoNME(GlossVideo):
    offset = models.IntegerField(default=1)

    class Meta:
        verbose_name = gettext("NME Gloss Video")
        ordering = ['offset', ]

    def __str__(self):
        translations = []
        gloss = self.gloss
        lemma = gloss.lemma
        count_dataset_languages = lemma.dataset.translation_languages.all().count() if lemma else 0
        glossvideodescriptions = GlossVideoDescription.objects.filter(nmevideo=self)
        for description in glossvideodescriptions:
            if count_dataset_languages > 1:
                translations.append("{}: {}".format(description.language, description.text))
            else:
                translations.append("{}".format(description.text))
        return ", ".join(translations)

    def add_descriptions(self, descriptions):
        """Add descriptions to the nme video"""
        for language in self.gloss.lemma.dataset.translation_languages.all():
            if language.language_code_2char in descriptions.keys():
                text = descriptions[language.language_code_2char]
                if text:
                    GlossVideoDescription.objects.create(text=text, nmevideo=self, language=language)

    def get_video_path(self):
        if settings.DEBUG_VIDEOS:
            print('get_video_path GlossVideoNME: ', str(self.videofile))
        return self.videofile.name

    def ensure_mp4(self):
        """Ensure that the video file is an h264 format
        video, convert it if necessary"""

        # convert video to use the right size and iphone/net friendly bitrate
        # create a temporary copy in the new format
        # then move it into place

        (basename, ext) = os.path.splitext(self.videofile.path)
        if ext == '.mov' or ext == '.webm':
            oldloc = self.videofile.path
            newloc = basename + ".mp4"
            err = convert_video(oldloc, newloc, force=False)
            self.videofile.name = get_video_file_path(self, os.path.basename(newloc),
                                                      nmevideo=True, perspective='', offset=self.offset)
            os.remove(oldloc)

    def save(self, *args, **kwargs):
        super(GlossVideoNME, self).save(*args, **kwargs)

    def move_video(self, move_files_on_disk=True):
        """
        Calculates the new path, moves the video file to the new path and updates the videofile field
        :return:
        """
        old_path = str(self.videofile)
        new_path = get_video_file_path(self, old_path, nmevideo=True, perspective='', offset=self.offset, version=0)
        if old_path != new_path:
            if move_files_on_disk:
                source = os.path.join(settings.WRITABLE_FOLDER, old_path)
                destination = os.path.join(settings.WRITABLE_FOLDER, new_path)
                if os.path.exists(source):
                    destination_dir = os.path.dirname(destination)
                    if not os.path.exists(destination_dir):
                        os.makedirs(destination_dir)
                    if os.path.isdir(destination_dir):
                        shutil.move(source, destination)

                    self.videofile.name = new_path
                    self.save()

    def delete_files(self):
        """Delete the files associated with this object"""
        if settings.DEBUG_VIDEOS:
            print('delete_files GlossVideoNME: ', str(self.videofile))
        try:
            os.unlink(self.videofile.path)
        except (OSError, PermissionError):
            if settings.DEBUG_VIDEOS:
                print('delete_files exception GlossVideo OSError, PermissionError: ', str(self.videofile))
            pass

    def reversion(self, revert=False):
        """Delete the video file of this object"""
        print("DELETE NME VIDEO", self.videofile.name)
        self.delete_files()
        self.delete()


PERSPECTIVE_CHOICES = (('left', 'Left'),
                       ('right', 'Right')
                       )


class GlossVideoPerspective(GlossVideo):
    perspective = models.CharField(max_length=20, choices=PERSPECTIVE_CHOICES)

    class Meta:
        verbose_name = gettext("Gloss Video Perspective")
        ordering = ['perspective', ]

    def get_video_path(self):
        return self.videofile.name

    def save(self, *args, **kwargs):
        super(GlossVideoPerspective, self).save(*args, **kwargs)

    def move_video(self, move_files_on_disk=True):
        """
        Calculates the new path, moves the video file to the new path and updates the videofile field
        :return:
        """
        if not move_files_on_disk:
            return
        # other code does this too. It's a dubious way to obtain the path
        old_path = str(self.videofile)
        new_path = get_video_file_path(self, old_path, nmevideo=False, perspective=str(self.perspective))
        if old_path == new_path:
            return

        source = os.path.join(settings.WRITABLE_FOLDER, old_path)
        destination = os.path.join(settings.WRITABLE_FOLDER, new_path)
        if os.path.exists(source):
            destination_dir = os.path.dirname(destination)
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
            if os.path.isdir(destination_dir):
                shutil.move(source, destination)

            self.videofile.name = new_path
            self.save()
        else:
            # on the production server this is a problem
            msg = "Perspective video file not found: " + source
            print(msg)

    def delete_files(self):
        """Delete the files associated with this object"""
        old_path = str(self.videofile)
        file_system_path = os.path.join(settings.WRITABLE_FOLDER, old_path)
        if settings.DEBUG_VIDEOS:
            print('perspective video delete files: ', file_system_path)
        if not os.path.exists(file_system_path):
            # Video file not found on server
            # on the production server this is a problem
            msg = "Perspective video file not found: " + file_system_path
            print(msg)
            return
        try:
            os.unlink(file_system_path)
        except OSError:
            msg = "Perspective video file could not be deleted: " + file_system_path
            print(msg)

    def reversion(self, revert=False):
        """Delete the video file of this object"""
        print("DELETE Perspective VIDEO", self.videofile.name)
        self.delete_files()
        self.delete()


@receiver(models.signals.post_save, sender=Dataset)
def process_dataset_changes(sender, instance, **kwargs):
    """
    Makes changes to GlossVideos if a Dataset has been changed.
    :param sender: 
    :param instance: 
    :param kwargs: 
    :return: 
    """
    # If the acronym has been changed, change all GlossVideos
    # and rename directories.
    dataset = instance
    if dataset._initial['acronym'] and dataset.acronym != dataset._initial['acronym']:
        # Move all media
        glossvideos = GlossVideo.objects.filter(gloss__lemma__dataset=dataset)
        for glossvideo in glossvideos:
            glossvideo.move_video(move_files_on_disk=False)

        # Rename dirs
        glossvideo_path_original = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, dataset._initial['acronym'])
        glossvideo_path_new = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, dataset.acronym)
        if os.path.exists(glossvideo_path_original):
            os.rename(glossvideo_path_original, glossvideo_path_new)

        glossimage_path_original = os.path.join(WRITABLE_FOLDER, GLOSS_IMAGE_DIRECTORY, dataset._initial['acronym'])
        glossimage_path_new = os.path.join(WRITABLE_FOLDER, GLOSS_IMAGE_DIRECTORY, dataset.acronym)
        if os.path.exists(glossimage_path_original):
            os.rename(glossimage_path_original, glossimage_path_new)

        # Make sure that _initial reflect the database for the dataset object
        dataset._initial['acronym'] = dataset.acronym

    # If the default language has been changed, change all GlossVideos
    # and move all video/poster files accordingly.
    if dataset._initial['default_language'] and dataset.default_language != dataset._initial['default_language']:
        # Move all media
        glossvideos = GlossVideo.objects.filter(gloss__lemma__dataset=dataset)
        for glossvideo in glossvideos:
            glossvideo.move_video(move_files_on_disk=True)

        # Make sure that _initial reflect the database for the dataset object
        dataset._initial['default_language'] = dataset.default_language


@receiver(models.signals.post_save, sender=LemmaIdglossTranslation)
def process_lemmaidglosstranslation_changes(sender, instance, **kwargs):
    """
    Makes changes to GlossVideos if a LemmaIdglossTranslation has been changed.
    :param sender: 
    :param instance: 
    :param kwargs: 
    :return: 
    """
    lemmaidglosstranslation = instance
    glossvideos = GlossVideo.objects.filter(gloss__lemma__lemmaidglosstranslation=lemmaidglosstranslation)
    for glossvideo in glossvideos:
        glossvideo.move_video(move_files_on_disk=True)


@receiver(models.signals.post_save, sender=LemmaIdgloss)
def process_lemmaidgloss_changes(sender, instance, **kwargs):
    """
    Makes changes to GlossVideos if a LemmaIdgloss has been changed.
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    lemmaidgloss = instance
    glossvideos = GlossVideo.objects.filter(gloss__lemma=lemmaidgloss)
    for glossvideo in glossvideos:
        glossvideo.move_video(move_files_on_disk=True)


@receiver(models.signals.post_save, sender=Gloss)
@receiver(models.signals.post_save, sender=Morpheme)
def process_gloss_changes(sender, instance, update_fields=[], **kwargs):
    """
    Makes changes to GlossVideos if a Gloss.lemma has changed
    :param sender: 
    :param instance:
    :param update_fields: indicate whether the video path has changed
    :param kwargs: 
    :return: 
    """
    if not update_fields:
        return
    gloss = instance
    glossvideos = GlossVideo.objects.filter(gloss=gloss, glossvideonme=None, glossvideoperspective=None)
    for glossvideo in glossvideos:
        if hasattr(instance, 'glossvideonme'):
            continue
        if hasattr(instance, 'glossvideoperspective'):
            continue
        glossvideo.move_video(move_files_on_disk=True)
    glossvideos = GlossVideoNME.objects.filter(gloss=gloss)
    for glossvideo in glossvideos:
        glossvideo.move_video(move_files_on_disk=True)
    glossvideos = GlossVideoPerspective.objects.filter(gloss=gloss)
    for glossvideo in glossvideos:
        glossvideo.move_video(move_files_on_disk=True)


@receiver(models.signals.post_save, sender=GlossVideoNME)
def process_nmevideo_changes(sender, instance, update_fields=[], **kwargs):
    """
    Makes changes to GlossVideoNME if an offset has changed
    :param sender:
    :param instance:
    :param update_fields: indicate whether the video path has changed
    :param kwargs:
    :return:
    """
    if settings.DEBUG_VIDEOS:
        move_videos = not update_fields or 'offset' not in update_fields
        print('process_nmevideo_changes move videos: ', str(instance), move_videos)
    if not update_fields or 'offset' not in update_fields:
        return
    glossvideo = instance
    glossvideo.move_video(move_files_on_disk=True)


@receiver(models.signals.post_save, sender=GlossVideoPerspective)
def process_perspectivevideo_changes(sender, instance, update_fields=[], **kwargs):
    """
    Makes changes to GlossVideoPerspective if an offset has changed
    :param sender:
    :param instance:
    :param update_fields: indicate whether the video path has changed
    :param kwargs:
    :return:
    """
    if settings.DEBUG_VIDEOS:
        move_videos = not update_fields
        print('process_perspectivevideo_changes move videos: ', str(instance), move_videos)
    if not update_fields:
        return
    glossvideo = instance
    glossvideo.move_video(move_files_on_disk=True)


@receiver(models.signals.pre_delete, sender=GlossVideo)
@receiver(models.signals.pre_delete, sender=GlossVideoNME)
@receiver(models.signals.pre_delete, sender=GlossVideoPerspective)
def delete_files(sender, instance, **kwargs):
    """
    Deletes all associated files when the GlossVideo instance is deleted.
    :param sender: 
    :param instance: 
    :param kwargs: 
    :return: 
    """
    if settings.DEBUG_VIDEOS:
        print('delete_files pre_delete: ', str(instance))
        print('delete_files settings.DELETE_FILES_ON_GLOSSVIDEO_DELETE: ', settings.DELETE_FILES_ON_GLOSSVIDEO_DELETE)
    if hasattr(instance, 'glossvideonme'):
        # before deleting a GlossVideoNME object, delete the files
        instance.delete_files()
    elif hasattr(instance, 'glossvideoperspective'):
        # before deleting a GlossVideoPerspective object, delete the files
        instance.delete_files()
    elif settings.DELETE_FILES_ON_GLOSSVIDEO_DELETE:
        # before a GlossVideo object, only delete the files if the setting is True
        # default.py has this set to false so primary gloss video files are (never) deleted
        # check whether this conflicts with reversion. If the file is not deleted, the object cannot be deleted
        instance.delete_files()
