""" Models for the video application
keep track of uploaded videos and converted versions
"""

import sys
import os
import re
import stat
import shutil
import ffmpeg
import subprocess

from django.db import models
from django.db.models.fields.files import FieldFile
from django.dispatch import receiver
from django.forms.utils import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User
from django.utils.encoding import escape_uri_path
from django.utils.translation import gettext

from signbank.settings.server_specific import (WRITABLE_FOLDER, DEBUG_VIDEOS, DELETE_FILES_ON_GLOSSVIDEO_DELETE,
                                               ESCAPE_UPLOADED_VIDEO_FILE_PATH, EXAMPLESENTENCE_VIDEO_DIRECTORY,
                                               ANNOTATEDSENTENCE_VIDEO_DIRECTORY,
                                               GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY, FFMPEG_PROGRAM)
from signbank.settings.base import MEDIA_ROOT, MEDIA_URL
from signbank.video.convertvideo import (extract_frame, convert_video, make_thumbnail_video, generate_image_sequence,
                                         remove_stills, detect_video_file_extension)
from signbank.video.operations import (filename_matches_nme, filename_matches_nme_backup, filename_matches_perspective,
                                       filename_matches_perspective_backup, filename_matches_video,
                                       filename_matches_backup_video, move_file_to_prullenmand)
from signbank.dictionary.models import (Gloss, Morpheme, Dataset, Language, LemmaIdgloss, LemmaIdglossTranslation,
                                        ExampleSentence, AnnotatedSentence, AnnotatedSentenceSource)
from signbank.tools import get_two_letter_dir, generate_still_image, get_checksum_for_path

from CNGT_scripts.python.resizeVideos import VideoResizer
from urllib.parse import urlparse
from pathlib import Path
from pympi.Elan import Eaf


def filename_matches_non_backup(gloss, filename):
    # used to make sure a backup video object does not point to a non-backup file
    primary_video_filename = f'{gloss.idgloss}-{gloss.id}'
    filename_with_extension = os.path.basename(filename)
    filename_matches_primary = re.search(rf"^{primary_video_filename}\.(mp4|m4v|mov|webm|mkv|m2v)$", filename_with_extension)
    filename_matches_perspective_video = re.search(rf"^{primary_video_filename}_(left|right|nme_\d+_left|nme_\d+_right)\.(mp4|m4v|mov|webm|mkv|m2v)$", filename_with_extension)
    filename_matches_nme_video = re.search(rf"^{primary_video_filename}_(nme_\d+|nme_\d+_left|nme_\d+_right|nme_\d+_center)\.(mp4|m4v|mov|webm|mkv|m2v)$", filename_with_extension)
    return filename_matches_primary or filename_matches_perspective_video or filename_matches_nme_video


def find_dangling_video_files(gloss):
    dataset_dir = gloss.lemma.dataset.acronym
    two_letter_dir = get_two_letter_dir(gloss.idgloss)
    filename_prefix = f'{gloss.idgloss}-{gloss.id}'
    chosen_path = str(os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, dataset_dir, two_letter_dir))
    file_names = []
    for gloss_video in GlossVideo.objects.filter(gloss=gloss).iterator():
        file_names.append(gloss_video.videofile.name.split("/")[-1])
    files_without_glossvideo_object = []
    for subdir, dirs, files in os.walk(chosen_path):
        for file in files:
            if file.startswith(filename_prefix) and file not in file_names:
                # Each entry is a (relative_path, filename) tuple for use in templates and views.
                files_without_glossvideo_object.append((f'{GLOSS_VIDEO_DIRECTORY}/{dataset_dir}/{two_letter_dir}/{file}', file))
    return files_without_glossvideo_object


def has_correct_filename(videofile, nmevideo, perspective, version):
    if not videofile:
        return False
    video_file_full_path = Path(WRITABLE_FOLDER, videofile)
    if nmevideo is not None:
        if version > 0:
            filename_is_correct = filename_matches_nme_backup(video_file_full_path) is not None
        else:
            filename_is_correct = filename_matches_nme(video_file_full_path) is not None
        return filename_is_correct
    elif perspective is not None:
        if version > 0:
            filename_is_correct = filename_matches_perspective_backup(video_file_full_path) is not None
        else:
            filename_is_correct = filename_matches_perspective(video_file_full_path) is not None
        return filename_is_correct
    elif version > 0:
        filename_is_correct = filename_matches_backup_video(video_file_full_path) is not None
        return filename_is_correct
    else:
        filename_is_correct = filename_matches_video(video_file_full_path) is not None
        return filename_is_correct


def wrong_filename_filter(glossvideos):
    filenames = []
    queryset_tuples = glossvideos.values('id', 'videofile', 'glossvideonme', 'glossvideoperspective', 'version')
    for qv in queryset_tuples:
       if not has_correct_filename(qv['videofile'],
                                   qv['glossvideonme'],
                                   qv['glossvideoperspective'], qv['version']):
           filenames.append(qv['id'])
    return filenames


def delete_glossvideo_objects_and_files(gloss):
    """
    This method removes wrongly named video files that do not match the correct naming
    If the file points to a primary video, its name is erased prior to deleting the object
    This prevents deleting a primary video file that was wrongly linked to a backup video object
    """
    all_gloss_video_objects = GlossVideo.objects.filter(gloss=gloss).distinct()
    gloss_video_ids = wrong_filename_filter(all_gloss_video_objects)
    gloss_video_objects = GlossVideo.objects.filter(id__in=gloss_video_ids)
    for glossvideo in gloss_video_objects:
        relative_path = str(glossvideo.videofile)
        if not relative_path:
            glossvideo.delete()
            continue

        video_file_full_path = os.path.join(WRITABLE_FOLDER, relative_path)
        if os.path.exists(video_file_full_path):
            if filename_matches_non_backup(gloss, video_file_full_path):
                # this gloss video object points to a non-backup video file, just erase the link
                glossvideo.videofile.name = ""
                glossvideo.save()
            else:
                os.remove(video_file_full_path)
        glossvideo.delete()


def renumber_backup_videos(gloss):
    lookup_backup_files = GlossVideo.objects.filter(gloss=gloss,
                                                    glossvideonme=None,
                                                    glossvideoperspective=None,
                                                    version__gt=0).order_by('version', 'id')
    # enumerate over the backup videos and give them new version numbers
    for inx, video in enumerate(lookup_backup_files, 1):
        if inx == video.version:
            continue
        video.version = inx
        video.save()


def remove_backup_videos(gloss):
    backup_files = GlossVideo.objects.filter(gloss=gloss,
                                             version__gt=0).order_by('version', 'id')
    for glossvideo in backup_files:
        relative_path = str(glossvideo.videofile)
        if not relative_path:
            glossvideo.delete()
            continue

        video_file_full_path = os.path.join(WRITABLE_FOLDER, relative_path)
        if os.path.exists(video_file_full_path):
            if filename_matches_non_backup(gloss, video_file_full_path):
                # this gloss video object points to a non-backup video file, just erase the link
                glossvideo.videofile.name = ""
                glossvideo.save()
            else:
                os.remove(video_file_full_path)
        glossvideo.delete()


def remove_duplicate_videos(gloss):
    primary_video = GlossVideo.objects.filter(gloss=gloss,
                                              version=0,
                                              glossvideonme=None,
                                              glossvideoperspective=None).first()
    if not primary_video or not primary_video.videofile:
        return
    fullpath = os.path.join(WRITABLE_FOLDER, primary_video.videofile.path)
    if not os.path.exists(fullpath):
        return
    checksum_primary_video = get_checksum_for_path(fullpath)
    backup_files = GlossVideo.objects.filter(gloss=gloss,
                                             glossvideonme=None,
                                             glossvideoperspective=None,
                                             version__gt=0)
    for glossvideo in backup_files:
        if not glossvideo.videofile:
            glossvideo.delete()
            continue
        video_file_full_path = os.path.join(WRITABLE_FOLDER, glossvideo.videofile.path)
        if not os.path.exists(video_file_full_path):
            glossvideo.delete()
            continue
        checksum_this_backup_video = get_checksum_for_path(video_file_full_path)
        if checksum_primary_video != checksum_this_backup_video:
            continue
        # construct the primary video filename and make sure the object does not point to it
        _, extension = os.path.splitext(video_file_full_path)
        basename = os.path.basename(video_file_full_path)
        primary_video_filename = f'{gloss.idgloss}-{gloss.id}{extension}'
        if basename == primary_video_filename:
            # this gloss video object points to the primary video, just erase the link
            glossvideo.videofile.name = ""
            glossvideo.save()
        else:
            os.remove(video_file_full_path)
        glossvideo.delete()


def weedout_duplicate_backup_videos(gloss):
    backup_files = GlossVideo.objects.filter(gloss=gloss,
                                             glossvideonme=None,
                                             glossvideoperspective=None,
                                             version__gt=0).distinct()
    checksum_X_glossvideo = []
    for glossvideo in backup_files:
        if not glossvideo.videofile:
            glossvideo.delete()
            continue
        video_file_full_path = os.path.join(WRITABLE_FOLDER, glossvideo.videofile.path)
        if not os.path.exists(video_file_full_path):
            glossvideo.delete()
            continue
        checksum_this_backup_video = get_checksum_for_path(video_file_full_path)
        checksum_X_glossvideo.append((checksum_this_backup_video, glossvideo))
    sorted_by_checksum = sorted(checksum_X_glossvideo, key=lambda x: x[0])
    visited = set()
    duplicates = []
    for (checksum, glossvideo) in sorted_by_checksum:
        if checksum not in visited:
            visited.add(checksum)
        else:
            duplicates.append(glossvideo)
    for glossvideo in duplicates:
        video_file_full_path = os.path.join(WRITABLE_FOLDER, glossvideo.videofile.path)
        # construct the primary video filename and make sure the object does not point to it
        _, extension = os.path.splitext(video_file_full_path)
        basename = os.path.basename(video_file_full_path)
        primary_video_filename = f'{gloss.idgloss}-{gloss.id}{extension}'
        if basename == primary_video_filename:
            # this gloss video object points to the primary video, just erase the link
            glossvideo.videofile.name = ""
            glossvideo.save()
        else:
            os.remove(video_file_full_path)
        glossvideo.delete()


def flipped_backup_filename(gloss, glossvideo, extension):
    idgloss = gloss.idgloss
    desired_filename_without_extension = f'{idgloss}-{gloss.pk}'
    if glossvideo.version > 0:
        desired_extension = f'.bak{glossvideo.pk}{extension}'
    else:
        desired_extension = extension
    desired_filename = desired_filename_without_extension + desired_extension
    return desired_filename


def build_filename(gloss, glossvideo, extension, include_dirs=False, flipped=False):
    if flipped:
        name = f'{gloss.idgloss}-{gloss.pk}.bak{glossvideo.pk}{extension}'
    elif glossvideo.version > 0:
        name = f'{gloss.idgloss}-{gloss.pk}{extension}.bak{glossvideo.pk}'
    else:
        name = f'{gloss.idgloss}-{gloss.pk}{extension}'
    if include_dirs:
        return get_two_letter_dir(gloss.idgloss), gloss.lemma.dataset.acronym, name
    else:
        return name


PERSPECTIVE_CHOICES = (('left', 'Left'),
                       ('right', 'Right')
                       )

NME_PERSPECTIVE_CHOICES = (('left','Left'),('right','Right'),('center', 'Center'))

class GlossVideoStorage(FileSystemStorage):
    """Implement our shadowing video storage system"""

    def __init__(self, location=MEDIA_ROOT, base_url=MEDIA_URL):
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
    actor = models.ForeignKey(User, on_delete=models.CASCADE)

    # One-to-many link: to the Gloss in dictionary.models.Gloss
    examplesentence = models.ForeignKey(ExampleSentence, on_delete=models.CASCADE)

    def __str__(self):
        self.examplesentence: ExampleSentence
        # Basic feedback from one History item: gloss-action-date
        name = f"{self.examplesentence.pk}: {self.action}, ({self.datestamp})"
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
    actor = models.ForeignKey(User, on_delete=models.CASCADE)

    # One-to-many link: to the Gloss in dictionary.models.Gloss
    gloss = models.ForeignKey(Gloss, on_delete=models.CASCADE)

    def __str__(self):
        self.gloss: Gloss
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
    :param nmevideo: boolean whether this is a nme video
    :param perspective: optional string for either 'left' or 'right'
    :param offset: order in sequence of NME video
    :param version: the version to determine the number of .bak extensions
    :return: 
    """
    (base, ext) = os.path.splitext(filename)

    idgloss = instance.gloss.idgloss
    two_letter_dir = get_two_letter_dir(idgloss)

    video_dir = GLOSS_VIDEO_DIRECTORY
    try:
        dataset_dir = instance.gloss.lemma.dataset.acronym
    except KeyError:
        dataset_dir = ""
        if DEBUG_VIDEOS:
            print('get_video_file_path: dataset_dir is empty for gloss ', str(instance.gloss.pk))
    if nmevideo and perspective:
        filename = f'{idgloss}-{instance.gloss.id}_nme_{offset}_{perspective}{ext}'
    elif nmevideo:
        filename = f'{idgloss}-{instance.gloss.id}_nme_{offset}{ext}'
    elif perspective:
        filename = f'{idgloss}-{instance.gloss.id}_{perspective}{ext}'
    elif version > 0:
        filename = f'{idgloss}-{instance.gloss.id}{ext}.bak{instance.id}'
    else:
        filename = f'{idgloss}-{instance.gloss.id}{ext}' 

    path = os.path.join(video_dir, dataset_dir, two_letter_dir, filename)
    if ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        path = escape_uri_path(path)
    if DEBUG_VIDEOS:
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
    video_dir = EXAMPLESENTENCE_VIDEO_DIRECTORY
    try:
        dataset_dir = os.path.join(instance.examplesentence.get_dataset().acronym, str(instance.examplesentence.id))
    except ObjectDoesNotExist:
        dataset_dir = ""

    if version > 0:
        filename = str(instance.examplesentence.id) + ext + '.bak' + str(instance.id)
    else:
        filename = str(instance.examplesentence.id) + ext

    path = os.path.join(video_dir, dataset_dir, filename)
    if ESCAPE_UPLOADED_VIDEO_FILE_PATH:
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
    video_dir = ANNOTATEDSENTENCE_VIDEO_DIRECTORY
    dataset = instance.annotatedsentence.get_dataset().acronym
    dataset_dir = os.path.join(dataset, str(instance.annotatedsentence.id))
    if version > 0:
        filename = str(instance.annotatedsentence.id) + ext + '.bak' + str(instance.id)
    else:
        filename = str(instance.annotatedsentence.id) + ext

    path = os.path.join(video_dir, dataset_dir, filename)
    if ESCAPE_UPLOADED_VIDEO_FILE_PATH:
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

        self.make_poster_image()
        self.ensure_mp4()

    def get_absolute_url(self):
        self.videofile: FieldFile
        return self.videofile.url

    def ensure_mp4(self):
        """Ensure that the video file is a h264 format
        video, convert it if necessary"""
        self.videofile: FieldFile
        if not self.videofile or not self.videofile.path or not os.path.exists(self.videofile.path):
            return
        if int(self.version or 0) > 0:
            return

        video_format_extension = detect_video_file_extension(self.videofile.path)
        if not video_format_extension:
            # this is not a video file
            os.remove(self.videofile.path)
            self.videofile.name = ''
            return
        (basename, ext) = os.path.splitext(self.videofile.path)
        if ext != '.mp4' or video_format_extension != '.mp4':
            old_relative_path = str(self.videofile)
            oldloc = self.videofile.path
            newloc = basename + ".mp4"
            okay = convert_video(oldloc, newloc)
            if not okay or not os.path.exists(newloc):
                return
            self.videofile.name = get_sentence_video_file_path(self, os.path.basename(newloc))
            move_file_to_prullenmand(oldloc, old_relative_path)

    def ch_own_mod_video(self):
        """Change owner and permissions"""
        self.videofile: FieldFile
        location = self.videofile.path
        # make sure they're readable by everyone
        # os.chown(location, 1000, 1002)
        os.chmod(location, stat.S_IRWXU | stat.S_IRWXG)

    def small_video(self, use_name=False):
        """Return the URL of the small version for this video
        :param use_name: whether videofile.name should be used instead of videofile.path
        """
        self.videofile: FieldFile
        small_video_path = add_small_appendix(self.videofile.path)
        if os.path.exists(small_video_path):
            if use_name:
                return add_small_appendix(self.videofile.name)
            return small_video_path
        else:
            return None

    def make_small_video(self):
        # this method is not called (bugs)

        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(self.videofile))
        try:
            resizer = VideoResizer([video_file_full_path], FFMPEG_PROGRAM, 180, 0, 0)
            resizer.run()
        except Exception as e:
            print("Error resizing video: ", video_file_full_path)
            print(e)

    def make_poster_image(self):
        try:
            generate_still_image(self)
        except (OSError, PermissionError):
            print('Error generating still image', sys.exc_info())

    def convert_to_mp4(self):
        # this method is not called (bugs)
        self.videofile: FieldFile
        print('Convert to mp4: ', self.videofile.path)
        name, _ = os.path.splitext(self.videofile.path)
        out_name = name + "_copy.mp4"
        stream = ffmpeg.input(self.videofile.path)
        stream = ffmpeg.output(stream, out_name, vcodec='h264')
        ffmpeg.run(stream, quiet=True)
        os.rename(out_name, self.videofile.path)
        print("Finished converting {}".format(self.videofile.path))

    def delete_files(self):
        """Delete the files associated with this object"""
        self.videofile: FieldFile
        small_video_path = self.small_video()
        try:
            os.unlink(self.videofile.path)
        except (OSError, PermissionError):
            pass

    def reversion(self):
        if self.version == 0:
            # find a name for the backup, a filename that isn't used already
            newname = self.videofile.name + ".bak" + str(self.pk)
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
        new_path = str(get_sentence_video_file_path(self, old_path, int(self.version or 0)))
        if old_path != new_path:
            if move_files_on_disk:
                source = os.path.join(WRITABLE_FOLDER, old_path)
                destination = os.path.join(WRITABLE_FOLDER, new_path)
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
        parsed_url = urlparse(str(self.url))
        if not parsed_url.scheme:
            return f'http://{self.url}'
        return self.url

    def ensure_mp4(self):
        """Ensure that the video file is a h264 format
        video, convert it if necessary"""
        self.videofile: FieldFile
        if not self.videofile or not self.videofile.path or not os.path.exists(self.videofile.path):
            return
        if int(self.version or 0) > 0:
            return

        video_format_extension = detect_video_file_extension(self.videofile.path)
        if not video_format_extension:
            # this is not a video file
            os.remove(self.videofile.path)
            self.videofile.name = ''
            return
        (basename, ext) = os.path.splitext(self.videofile.path)
        if ext != '.mp4' or video_format_extension != '.mp4':
            old_relative_path = str(self.videofile)
            oldloc = self.videofile.path
            newloc = basename + ".mp4"
            okay = convert_video(oldloc, newloc)
            if not okay or not os.path.exists(newloc):
                return
            self.videofile.name = get_annotated_video_file_path(self, os.path.basename(newloc))
            move_file_to_prullenmand(oldloc, old_relative_path)

    def ch_own_mod_video(self):
        """Change owner and permissions"""
        self.videofile: FieldFile
        location = self.videofile.path
        # make sure they're readable by everyone
        # os.chown(location, 1000, 1002)
        os.chmod(location, stat.S_IRWXU | stat.S_IRWXG)

    def delete_files(self, only_eaf=False):
        """Delete the files associated with this object"""
        self.eaffile: FieldFile
        self.annotatedsentence: AnnotatedSentence
        try:
            os.remove(self.eaffile.path)
            if not only_eaf:
                video_path = os.path.join(WRITABLE_FOLDER, ANNOTATEDSENTENCE_VIDEO_DIRECTORY, self.annotatedsentence.get_dataset().acronym, str(self.annotatedsentence.pk))
                shutil.rmtree(video_path)
        except (OSError, PermissionError):
            pass

    def get_eaffile_name(self):
        return os.path.basename(self.eaffile.name) if self.eaffile else ""

    def get_end_ms(self):
        """Get the duration of a video in ms using ffprobe."""
        self.videofile: FieldFile
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
        
        if tier_name not in eaf.tiers:
            return
        
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
        self.videofile: FieldFile
        self.eaffile: FieldFile
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
        self.select_annotations(eaf, 'Nederlands', start_ms, end_ms)
        self.select_annotations(eaf, 'Signbank ID glossen', start_ms, end_ms)
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
        self.ensure_mp4()
        super(GlossVideo, self).save(*args, **kwargs)

    def process(self):
        """The clean method will try to validate the video
        file format, optimise for streaming and generate
        the poster image"""

        self.poster_path()
        self.ensure_mp4()

    def poster_path(self, create=True):
        """Return the path of the poster image for this
        video, if create=True, create the image if needed
        Return None if create=False and the file doesn't exist"""
        self.videofile: FieldFile
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
        """Ensure that the video file is a h264 format
        video, convert it if necessary"""
        self.videofile: FieldFile
        if not self.videofile or not self.videofile.path or not os.path.exists(self.videofile.path):
            return
        if int(self.version or 0) > 0:
            return

        video_format_extension = detect_video_file_extension(self.videofile.path)
        if not video_format_extension:
            # this is not a video file
            os.remove(self.videofile.path)
            self.videofile.name = ''
            return
        (basename, ext) = os.path.splitext(self.videofile.path)
        if ext != '.mp4' or video_format_extension != '.mp4':
            old_relative_path = str(self.videofile)
            oldloc = self.videofile.path
            newloc = basename + ".mp4"
            okay = convert_video(oldloc, newloc)
            if not okay or not os.path.exists(newloc):
                return
            self.videofile.name = get_video_file_path(self, os.path.basename(newloc))
            move_file_to_prullenmand(oldloc, old_relative_path)

    def ch_own_mod_video(self):
        """Change owner and permissions"""
        self.videofile: FieldFile
        location = self.videofile.path

        # make sure they're readable by everyone
        # os.chown(location, 1000, 1002)
        os.chmod(location, stat.S_IRWXU | stat.S_IRWXG)

    def small_video(self, use_name=False):
        """Return the URL of the small version for this video
        :param use_name: whether videofile.name should be used instead of videofile.path
        """
        self.videofile: FieldFile
        if not self.videofile:
            return None
        small_video_path = add_small_appendix(self.videofile.path)
        if os.path.exists(small_video_path):
            if use_name:
                return add_small_appendix(self.videofile.name)
            return small_video_path
        else:
            return None

    def make_image_sequence(self):

        generate_image_sequence(self.gloss, self.videofile)

    def delete_image_sequence(self):

        remove_stills(self.gloss)

    def make_small_video(self):
        # this method is not called (bugs)
        self.videofile: FieldFile
        name, _ = os.path.splitext(self.videofile.path)
        small_name = name + "_small.mp4"
        make_thumbnail_video(self.videofile, small_name)

        # ffmpeg_small = FFMPEG_OPTIONS + ["-vf", "scale=180:-2"]
        # video_file_full_path = os.path.join(WRITABLE_FOLDER, str(self.videofile))
        # try:
        #     resizer = VideoResizer([video_file_full_path], FFMPEG_PROGRAM, 180, 0, 0)
        #     resizer.run()
        # except Exception as e:
        #     print("Error resizing video: ", video_file_full_path)
        #     print(e)

    def make_poster_image(self):
        try:
            generate_still_image(self)
        except (OSError, PermissionError):
            print('Error generating still image', sys.exc_info())

    def convert_to_mp4(self):
        # this method is not called (bugs)
        self.videofile: FieldFile
        print('Convert to mp4: ', self.videofile.path)
        name, _ = os.path.splitext(self.videofile.path)
        out_name = name + "_copy.mp4"
        stream = ffmpeg.input(self.videofile.path)
        stream = ffmpeg.output(stream, out_name, vcodec='h264')
        ffmpeg.run(stream, quiet=True)
        os.rename(out_name, self.videofile.path)
        print("Finished converting {}".format(self.videofile.path))

    def delete_files(self):
        """Delete the files associated with this object"""
        self.videofile: FieldFile
        if DEBUG_VIDEOS:
            print('delete_files GlossVideo: ', str(self.videofile))

        if not self.videofile or not self.videofile.name:
            return

        small_video_path = self.small_video()
        try:
            os.unlink(self.videofile.path)
            poster_path = self.poster_path(create=False)
            if small_video_path:
                os.unlink(small_video_path)
            if poster_path:
                os.unlink(poster_path)
        except (OSError, PermissionError):
            if DEBUG_VIDEOS:
                print('delete_files exception GlossVideo OSError, PermissionError: ', str(self.videofile))
            pass

    def reversion(self):
        """We have a new version of this video so increase
        the version count here and rename the video
        to video.mp4.bakNNN where NNN is the object ID"""

        if hasattr(self, 'glossvideonme') or hasattr(self, 'glossvideoperspective'):
            # make sure this is not applied to subclass objects
            return
        if self.version == 0:
            # find a name for the backup, a filename that isn't used already
            newname = self.videofile.name + ".bak" + str(self.pk)
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
        new_path = str(get_video_file_path(self, old_path, version=int(self.version or 0)))
        if old_path != new_path:
            if move_files_on_disk:
                source = os.path.join(WRITABLE_FOLDER, old_path)
                destination = os.path.join(WRITABLE_FOLDER, new_path)
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
                source_image = source_no_extension.replace(GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY)\
                               + '.png'
                destination_image = destination_no_extension.replace(GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY)\
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
    perspective = models.CharField(max_length=20, choices=NME_PERSPECTIVE_CHOICES, default='center')       

    class Meta:
        verbose_name = gettext("NME Gloss Video")
        ordering = ['offset', ]

    def __str__(self):
        self.gloss: Gloss
        translations = []
        lemma = self.gloss.lemma
        count_dataset_languages = lemma.dataset.translation_languages.all().count() if lemma else 0
        glossvideodescriptions = GlossVideoDescription.objects.filter(nmevideo=self)
        display_preface = str(self.offset) + "_" + str(self.perspective) if self.perspective else str(self.offset)
        for description in glossvideodescriptions:
            if count_dataset_languages > 1:
                translations.append("{}: {}".format(description.language, description.text))
            else:
                translations.append("{}".format(description.text))
        return display_preface + ": " + ", ".join(translations)

    def has_perspective_videos(self):
        perspectivevideos = GlossVideoNME.objects.filter(gloss=self.gloss, offset=self.offset, perspective__in=['left', 'right'])
        return perspectivevideos.count() > 0

    def has_left_perspective(self):
        nmevideos = GlossVideoNME.objects.filter(gloss=self.gloss, offset=self.offset, perspective='left')
        return nmevideos.count() > 0

    def has_right_perspective(self):
        nmevideos = GlossVideoNME.objects.filter(gloss=self.gloss, offset=self.offset, perspective='right')
        return nmevideos.count() > 0

    def add_descriptions(self, descriptions):
        """Add descriptions to the nme video"""
        self.gloss: Gloss
        if self.perspective not in ['', 'center']:
            return
        for language in self.gloss.lemma.dataset.translation_languages.all():
            if language.language_code_2char in descriptions.keys():
                text = descriptions[language.language_code_2char]
                if text:
                    GlossVideoDescription.objects.create(text=text, nmevideo=self, language=language)

    def get_video_path(self):
        if DEBUG_VIDEOS:
            print('get_video_path GlossVideoNME: ', str(self.videofile))
        return escape_uri_path(self.videofile.name) if self.videofile else ''

    def ensure_mp4(self):
        """Ensure that the video file is a h264 format
        video, convert it if necessary"""

        # convert video to use the right size and iphone/net friendly bitrate
        # create a temporary copy in the new format
        # then move it into place
        self.videofile: FieldFile
        if not self.videofile or not self.videofile.path or not os.path.exists(self.videofile.path):
            return
        if int(self.version or 0) > 0:
            return

        video_format_extension = detect_video_file_extension(self.videofile.path)
        if not video_format_extension:
            # this is not a video file
            os.remove(self.videofile.path)
            self.videofile.name = ''
            return
        (basename, ext) = os.path.splitext(self.videofile.path)
        if ext != '.mp4' or video_format_extension != '.mp4':
            old_relative_path = str(self.videofile)
            oldloc = self.videofile.path
            newloc = basename + ".mp4"
            okay = convert_video(oldloc, newloc)
            if not okay or not os.path.exists(newloc):
                return
            self.videofile.name = get_video_file_path(self, os.path.basename(newloc),
                                                      nmevideo=True, perspective='', offset=int(self.offset or 0))
            move_file_to_prullenmand(oldloc, old_relative_path)

    def save(self, *args, **kwargs):
        super(GlossVideoNME, self).save(*args, **kwargs)

    def move_video(self, move_files_on_disk=True):
        """
        Calculates the new path, moves the video file to the new path and updates the videofile field
        :return:
        """
        old_path = str(self.videofile)
        if not move_files_on_disk or not old_path:
            return
        new_path = str(get_video_file_path(self, old_path, nmevideo=True, perspective=self.perspective, offset=int(self.offset or 0), version=self.version))
        if old_path == new_path:
            return
        source = os.path.join(WRITABLE_FOLDER, old_path)
        destination = os.path.join(WRITABLE_FOLDER, new_path)
        if not os.path.exists(source):
            return
        destination_dir = os.path.dirname(destination)
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        if os.path.isdir(destination_dir):
            shutil.move(source, destination)

        self.videofile.name = new_path
        self.save()

    def delete_files(self):
        """Delete the files associated with this object"""
        old_path = str(self.videofile)
        if not old_path:
            return True
        file_system_path = os.path.join(WRITABLE_FOLDER, old_path)
        if filename_matches_nme(file_system_path) is None:
            # this points to the normal video file, just erase the name rather than delete file
            self.videofile.name = ""
            self.save()
            return True
        if not os.path.exists(file_system_path):
            return True
        try:
            os.unlink(file_system_path)
            return True
        except (OSError, PermissionError) as e:
            print(e)
            return False

    def reversion(self):
        if self.version == 0:
            # find a name for the backup, a filename that isn't used already
            newname = self.videofile.name + ".bak" + str(self.pk)
            if os.path.isfile(os.path.join(storage.location, self.videofile.name)):
                os.rename(os.path.join(storage.location, self.videofile.name),
                          os.path.join(storage.location, newname))
            self.videofile.name = newname
        self.version += 1
        self.save()


class GlossVideoPerspective(GlossVideo):
    perspective = models.CharField(max_length=20, choices=PERSPECTIVE_CHOICES)

    class Meta:
        verbose_name = gettext("Gloss Video Perspective")
        ordering = ['perspective', ]

    def get_video_path(self):
        return escape_uri_path(self.videofile.name) if self.videofile else ''

    def save(self, *args, **kwargs):
        super(GlossVideoPerspective, self).save(*args, **kwargs)

    def ensure_mp4(self):
        """Ensure that the video file is a h264 format
        video, convert it if necessary"""

        # convert video to use the right size and iphone/net friendly bitrate
        # create a temporary copy in the new format
        # then move it into place
        self.videofile: FieldFile
        if not self.videofile or not self.videofile.path or not os.path.exists(self.videofile.path):
            return
        if int(self.version or 0) > 0:
            return

        video_format_extension = detect_video_file_extension(self.videofile.path)
        if not video_format_extension:
            # this is not a video file
            os.remove(self.videofile.path)
            self.videofile.name = ''
            return
        (basename, ext) = os.path.splitext(self.videofile.path)
        if ext != '.mp4' or video_format_extension != '.mp4':
            old_relative_path = str(self.videofile)
            oldloc = self.videofile.path
            newloc = basename + ".mp4"
            okay = convert_video(oldloc, newloc)
            if not okay or not os.path.exists(newloc):
                return
            self.videofile.name = get_video_file_path(self, os.path.basename(newloc),
                                                      nmevideo=False, perspective=self.perspective, offset=0, version=self.version)
            move_file_to_prullenmand(oldloc, old_relative_path)

    def move_video(self, move_files_on_disk=True):
        """
        Calculates the new path, moves the video file to the new path and updates the videofile field
        :return:
        """
        if not move_files_on_disk:
            return
        # other code does this too. It's a dubious way to obtain the path
        old_path = str(self.videofile)
        if not old_path:
            return
        new_path = str(get_video_file_path(self, old_path, nmevideo=False, perspective=str(self.perspective), version=self.version))
        if old_path == new_path:
            return

        source = os.path.join(WRITABLE_FOLDER, old_path)
        destination = os.path.join(WRITABLE_FOLDER, new_path)
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
        old_path = str(self.videofile)
        if not old_path:
            return True
        file_system_path = os.path.join(WRITABLE_FOLDER, old_path)
        if filename_matches_perspective(file_system_path) is None:
            # this points to the normal video file, just erase the name rather than delete file
            self.videofile.name = ""
            self.save()
            return True
        if not os.path.exists(file_system_path):
            return True
        try:
            os.unlink(file_system_path)
            return True
        except (PermissionError, OSError) as e:
            print(e)
            return False

    def reversion(self):
        if self.version == 0:
            # find a name for the backup, a filename that isn't used already
            newname = self.videofile.name + ".bak" + str(self.pk)
            if os.path.isfile(os.path.join(storage.location, self.videofile.name)):
                os.rename(os.path.join(storage.location, self.videofile.name),
                          os.path.join(storage.location, newname))
            self.videofile.name = newname
        self.version += 1
        self.save()


def move_videos_for_filter(filter, move_files_on_disk: bool=False) -> None:
    """
    Changes GlossVideo.videofile values for a filter dict
    and moves files on disk if move_file_on_disk is True (default is False).
    A filter dict is used in the QuerySet.filter method as **filter
    """
    for glossvideo in GlossVideo.objects.filter(**filter, glossvideonme=None, glossvideoperspective=None):
        glossvideo.move_video(move_files_on_disk=move_files_on_disk)
    for glossvideo_nme in GlossVideoNME.objects.filter(**filter):
        glossvideo_nme.move_video(move_files_on_disk=move_files_on_disk)
    for glossvideos_perspective in GlossVideoPerspective.objects.filter(**filter):
        glossvideos_perspective.move_video(move_files_on_disk=move_files_on_disk)


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
        move_videos_for_filter({'gloss__lemma_dataset': dataset}, move_files_on_disk=False)

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
    if dataset._initial['default_language'] and dataset.default_language_id != dataset._initial['default_language']:
        move_videos_for_filter({'gloss__lemma_dataset': dataset}, move_files_on_disk=True)

        # Make sure that _initial reflect the database for the dataset object
        dataset._initial['default_language'] = dataset.default_language_id


@receiver(models.signals.post_save, sender=LemmaIdglossTranslation)
def process_lemmaidglosstranslation_changes(sender, instance, **kwargs):
    """
    Makes changes to GlossVideos if a LemmaIdglossTranslation has been changed.
    :param sender: 
    :param instance: 
    :param kwargs: 
    :return: 
    """
    move_videos_for_filter({'gloss__lemma__lemmaidglosstranslation': instance}, move_files_on_disk=True)


@receiver(models.signals.post_save, sender=LemmaIdgloss)
def process_lemmaidgloss_changes(sender, instance, **kwargs):
    """
    Makes changes to GlossVideos if a LemmaIdgloss has been changed.
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    move_videos_for_filter({'gloss__lemma': instance}, move_files_on_disk=True)


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
    if DEBUG_VIDEOS:
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
    if DEBUG_VIDEOS:
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
    if DEBUG_VIDEOS:
        print('delete_files pre_delete: ', str(instance))
        print('delete_files settings.DELETE_FILES_ON_GLOSSVIDEO_DELETE: ', DELETE_FILES_ON_GLOSSVIDEO_DELETE)
    if hasattr(instance, 'glossvideonme'):
        status = instance.delete_files()
    elif hasattr(instance, 'glossvideoperspective'):
        status = instance.delete_files()
    elif DELETE_FILES_ON_GLOSSVIDEO_DELETE:
        instance.delete_files()
