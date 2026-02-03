"""
Models for the video application keep track of uploaded videos and converted versions
"""

import sys
import os
import glob
import re
import stat
import shutil
import logging
from urllib.parse import urlparse
from pathlib import Path

import ffmpeg
from CNGT_scripts.python.resizeVideos import VideoResizer
from pympi.Elan import Eaf

from django.db import models
from django.dispatch import receiver
from django.forms.utils import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User
from django.utils.encoding import escape_uri_path
from django.utils.translation import gettext

from signbank.settings.server_specific import (WRITABLE_FOLDER, DEBUG_VIDEOS, DELETE_FILES_ON_GLOSSVIDEO_DELETE,
                                               ESCAPE_UPLOADED_VIDEO_FILE_PATH, EXAMPLESENTENCE_VIDEO_DIRECTORY,
                                               ANNOTATEDSENTENCE_VIDEO_DIRECTORY, DELETED_FILES_FOLDER,
                                               GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY, FFMPEG_PROGRAM)
from signbank.settings.base import MEDIA_ROOT, MEDIA_URL
from signbank.video.convertvideo import (extract_frame, convert_video, generate_image_sequence,
                                         remove_stills, detect_video_file_extension, ACCEPTABLE_VIDEO_EXTENSIONS)
from signbank.dictionary.models import (Gloss, Morpheme, Dataset, Language, LemmaIdgloss, LemmaIdglossTranslation,
                                        ExampleSentence, AnnotatedSentence, AnnotatedSentenceSource)
from signbank.tools import get_two_letter_dir, generate_still_image


logger = logging.getLogger(__name__)


def filename_matches_nme(filename):
    filename_without_extension, _ = os.path.splitext(os.path.basename(filename))
    return re.search(r".+-(\d+)_(nme_\d+|nme_\d+_left|nme_\d+_right|nme_\d+_center)$", filename_without_extension)


def filename_matches_perspective(filename):
    filename_without_extension, _ = os.path.splitext(os.path.basename(filename))
    return re.search(r".+-(\d+)_(left|right|nme_\d+_left|nme_\d+_right)$", filename_without_extension)


def filename_matches_video(filename):
    filename_without_extension, _ = os.path.splitext(os.path.basename(filename))
    return re.search(r".+-(\d+)$", filename_without_extension)


def filename_matches_backup_video(filename):
    filename_with_extension = os.path.basename(filename)
    extension_pattern = "|".join(ACCEPTABLE_VIDEO_EXTENSIONS)
    return re.search(rf".+-(\d+)({extension_pattern})\.(bak\d+)$", filename_with_extension)


def flattened_video_path(relative_path):
    """
    This constructs the filename to be used in the DELETED_FILES_FOLDER
    Take apart the gloss video relative path
    If this succeeds, prefix the filename with the dataset-specific components
    Otherwise just return the filename
    """
    relative_path_folders, filename = os.path.split(relative_path)
    m = re.search(r"^glossvideo/(.+)/(..)$", relative_path_folders)
    if m:
        dataset_folder = m.group(1)
        two_char_folder = m.group(2)
        return f"{dataset_folder}_{two_char_folder}_{filename}"
    return filename


def move_file_to_trash(filepath, relative_path):
    destination_dir = os.path.join(WRITABLE_FOLDER, DELETED_FILES_FOLDER)
    deleted_file_name = flattened_video_path(relative_path)
    deleted_destination = os.path.join(destination_dir, deleted_file_name)
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    try:
        shutil.move(str(filepath), str(deleted_destination))
        if DEBUG_VIDEOS:
            logger.info(f'video:models:move_file_to_trash:shutil.move: {filepath} {deleted_destination}')
    except (OSError, PermissionError) as e:
        if DEBUG_VIDEOS:
            logger.info(f'video:models:move_file_to_trash:shutil.move: {filepath} {deleted_destination}')
            logger.info(f'video:models:move_file_to_trash:shutil.move: {e}')
        os.remove(str(filepath))


def find_dangling_video_files(gloss):
    """Find files on disk that do not have a GlossVideo object in the database."""
    file_names_in_db = [gloss_video.videofile.name for gloss_video in GlossVideo.objects.filter(gloss=gloss)]
    path_in_writable = os.path.join(GLOSS_VIDEO_DIRECTORY, gloss.lemma.dataset.acronym,
                                    get_two_letter_dir(gloss.idgloss))
    return [
        f"{path_in_writable}/{file}"
        for file in glob.glob(f"{path_in_writable}/**/*", root_dir=WRITABLE_FOLDER, recursive=True)
        if file.startswith(f'{path_in_writable}/{gloss.idgloss}-{gloss.id}') and file not in file_names_in_db
    ]


def has_correct_filename(videofile, nmevideo, perspective, version):
    if not videofile:
        return False
    video_file_full_path = Path(WRITABLE_FOLDER, videofile)
    if nmevideo is not None:
        return filename_matches_nme(video_file_full_path) is not None
    if perspective is not None:
        return filename_matches_perspective(video_file_full_path) is not None
    if version > 0:
        return filename_matches_backup_video(video_file_full_path) is not None
    return filename_matches_video(video_file_full_path) is not None


def wrong_filename_filter(glossvideos):
    """Return IDs of GlossVideo objects where the videofile is not correct."""
    return [
        gloss_video.id
        for gloss_video in glossvideos.values('id', 'videofile', 'glossvideonme', 'glossvideoperspective', 'version')
        if not has_correct_filename(gloss_video['videofile'], gloss_video['glossvideonme'],
                                    gloss_video['glossvideoperspective'], gloss_video['version'])
    ]


def delete_glossvideo_objects_and_files(gloss):
    wrong_gloss_video_ids = wrong_filename_filter(GlossVideo.objects.filter(gloss=gloss).distinct())
    delete_gloss_videos(GlossVideo.objects.filter(id__in=wrong_gloss_video_ids), gloss)


def renumber_backup_videos(gloss):
    backup_gloss_videos = GlossVideo.objects.filter(gloss=gloss, glossvideonme=None, glossvideoperspective=None,
                                                    version__gt=0).order_by('version', 'id')
    # enumerate over the backup videos and give them new version numbers
    for index, gloss_video in enumerate(backup_gloss_videos, 1):
        if index == gloss_video.version:
            continue
        gloss_video.version = index
        gloss_video.save()


def remove_backup_videos(gloss):
    backup_gloss_videos = GlossVideo.objects.filter(gloss=gloss, glossvideonme=None, glossvideoperspective=None,
                                                    version__gt=0).order_by('version', 'id')
    delete_gloss_videos(backup_gloss_videos, gloss)


def delete_gloss_videos(gloss_videos, gloss):
    """
    This method removes video files that do not match the correct naming.
    If the file points to the primary video, its name is erased prior to deleting the object.
    This prevents deleting the primary video file that was wrongly linked to an object during the delete class method.
    """
    for glossvideo in gloss_videos:
        if not glossvideo.videofile:
            glossvideo.delete()
            continue

        video_file_full_path = os.path.join(WRITABLE_FOLDER, glossvideo.videofile.name)
        if os.path.exists(video_file_full_path):
            # construct the primary video filename and make sure the object does not point to it
            _, extension = os.path.splitext(video_file_full_path)
            if os.path.basename(video_file_full_path) == f'{gloss.idgloss}-{gloss.id}{extension}':
                # this gloss video object points to the primary video, just erase the link
                glossvideo.videofile.name = ""
                glossvideo.save()
            else:
                os.remove(video_file_full_path)
        glossvideo.delete()


def flipped_backup_filename(gloss, glossvideo, extension):
    desired_extension = f'.bak{glossvideo.pk}{extension}' if glossvideo.version > 0 else extension
    return f'{gloss.idgloss}-{gloss.id}' + desired_extension


def build_glossvideo_filename(glossvideo, extension, flipped=False):
    """Builds file name for a GlossVideo video file"""
    gloss = glossvideo.gloss
    if flipped:
        return f'{gloss.idgloss}-{gloss.id}.bak{glossvideo.pk}{extension}'
    if glossvideo.version > 0:
        return f'{gloss.idgloss}-{gloss.id}{extension}.bak{glossvideo.pk}'
    return f'{gloss.idgloss}-{gloss.id}{extension}'


PERSPECTIVE_CHOICES = (('left', 'Left'), ('right', 'Right'))
NME_PERSPECTIVE_CHOICES = (('left', 'Left'), ('right', 'Right'), ('center', 'Center'))


class GlossVideoStorage(FileSystemStorage):
    """Implement our shadowing video storage system"""
    def __init__(self, location=MEDIA_ROOT, base_url=MEDIA_URL):
        super().__init__(location, base_url)

    def get_valid_name(self, name):
        return name


storage = GlossVideoStorage()


# The 'action' choices are used in the GlossVideoHistory class
ACTION_CHOICES = (
    ('delete', 'delete'),
    ('upload', 'upload'),
    ('rename', 'rename'),
    ('watch', 'watch'),
    ('import', 'import'),
)


class VideoHistory(models.Model):
    """History of video uploading and deletion"""
    action = models.CharField("Video History Action", max_length=6, choices=ACTION_CHOICES, default='watch')
    datestamp = models.DateTimeField("Date and time of action", auto_now_add=True)
    uploadfile = models.TextField("User upload path", default='(not specified)')
    goal_location = models.TextField("Full target path", default='(not specified)')
    actor = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True
        ordering = ['datestamp']


class ExampleVideoHistory(VideoHistory):
    examplesentence = models.ForeignKey(ExampleSentence, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.examplesentence.id}: {self.action}, ({self.datestamp})"


class GlossVideoHistory(VideoHistory):
    gloss = models.ForeignKey(Gloss, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.gloss.idgloss}: {self.action}, ({self.datestamp})"


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
    relative_path = os.path.join(GLOSS_VIDEO_DIRECTORY, gloss.lemma.dataset.acronym,
                                 get_two_letter_dir(gloss.idgloss), f'{gloss.idgloss}-{gloss.id}.mp4')
    if os.path.exists(os.path.join(WRITABLE_FOLDER, relative_path)):
        return relative_path
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
    gloss = instance.gloss
    try:
        dataset_dir = gloss.lemma.dataset.acronym
    except KeyError:
        dataset_dir = ""
        if DEBUG_VIDEOS:
            print(f'get_video_file_path: dataset_dir is empty for gloss {gloss.pk}')

    _, ext = os.path.splitext(filename)
    if nmevideo:
        filename = f'{gloss.idgloss}-{gloss.id}_nme_{offset}_{perspective}{ext}'
    elif perspective:
        filename = f'{gloss.idgloss}-{gloss.id}_{perspective}{ext}'
    elif version > 0:
        filename = f'{gloss.idgloss}-{gloss.id}{ext}.bak{instance.id}'
    else:
        filename = f'{gloss.idgloss}-{gloss.id}{ext}'

    path = os.path.join(GLOSS_VIDEO_DIRECTORY, dataset_dir, get_two_letter_dir(gloss.idgloss), filename)
    if ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        path = escape_uri_path(path)
    if DEBUG_VIDEOS:
        logger.info(f'get_video_file_path: {path}')
    return path


SMALL_APPENDIX = '_small'


def add_small_appendix(path, reverse=False):
    path_without_extension, extension = os.path.splitext(path)
    ends_with_small = path_without_extension.endswith(SMALL_APPENDIX)
    if reverse and ends_with_small:
        return path_without_extension[:-len(SMALL_APPENDIX)] + extension
    if not reverse and not ends_with_small:
        return path_without_extension + SMALL_APPENDIX + extension
    return path


def validate_file_extension(value):
    if value.file.content_type not in ['video/mp4', 'video/quicktime']:
        raise ValidationError('Error message')


# VIDEO PATH FOR AN EXAMPLESENTENCE AND ANNOTATEDSENTENCE #
#
# The path of a video is constructed by
# 1. the acronym of the corresponding dataset
# 2. the id of the examplesentence/annotatedsentence
#
# That means that if the dataset acronym, the dataset default language or the lemmaidgloss for the
# dataset default language is changed, the video path should also be changed.

def get_sentence_video_file_path(instance, filename, version=0):
    return get_x_video_file_path(instance, filename, 'examplesentence', version)


def get_annotated_video_file_path(instance, filename, version=0):
    return get_x_video_file_path(instance, filename, 'annotatedsentence', version)


def get_x_video_file_path(instance, filename, field_name, version: int) -> str:
    field = getattr(instance, field_name)
    try:
        dataset_dir = os.path.join(field.get_dataset().acronym, str(field.id))
    except ObjectDoesNotExist:
        dataset_dir = ""

    _, extension = os.path.splitext(filename)
    filename = f'{instance.examplesentence.id}{extension}'
    if version > 0:
        filename = f'{filename}.bak{instance.id}'

    path = os.path.join(EXAMPLESENTENCE_VIDEO_DIRECTORY, dataset_dir, filename)
    if ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        path = escape_uri_path(path)
    return path


class EnsureMp4Mixin:
    def ensure_mp4(self):
        """Ensure that the video file is an h264 format video, convert it if necessary"""
        if (
            not self.videofile
            or not self.videofile.path
            or not os.path.exists(self.videofile.path)
            or self.version > 0
        ):
            return

        video_format_extension = detect_video_file_extension(self.videofile.path)
        basename, extension = os.path.splitext(self.videofile.path)
        if extension == '.mp4' and video_format_extension == '.mp4':
            return

        old_location = self.videofile.path
        new_location = basename + ".mp4"
        success = convert_video(old_location, new_location)
        if not success or not os.path.exists(new_location):
            return
        self.videofile.name = self.get_videofile_name_function(os.path.basename(new_location))
        move_file_to_trash(old_location, self.videofile.name)


class ReversionMixin:
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
        if not revert:
            if self.version == 0:
                newname = f"{self.videofile.name}.bak{self.id}"
                if os.path.isfile(self.videofile.path):
                    os.rename(self.videofile.path, self.videofile.storage.path(newname))
                self.videofile.name = newname
            self.version += 1
            self.save()
            return

        logger.info(f"REVERT VIDEO {self.videofile.name} {self.version}")

        if self.version == 0:
            logger.info(f"DELETE VIDEO VIA REVERSION {self.videofile.name}")
            self.delete_files()
            self.delete()
            return

        # also remove the post image if present, it will be regenerated
        poster_path_func = getattr(self, 'poster_path')
        if callable(poster_path_func):
            poster = self.poster_path(create=False)
            if poster is not None:
                os.unlink(poster)

        if self.version == 1:
            # remove .bak from filename and decrement the version
            newname, bak = os.path.splitext(self.videofile.name)
            expected_extension = f".bak{self.id}"
            if bak != expected_extension:
                raise Exception(f"Unknown suffix on stored video file. Expected {expected_extension}")
            if os.path.isfile(self.videofile.path):
                os.rename(self.videofile.path, self.videofile.storage.path(newname))
            self.videofile.name = newname
            if callable(poster_path_func):
                self.poster_path(create=True)

        self.version -= 1
        self.save()


class ExampleVideo(EnsureMp4Mixin, ReversionMixin, models.Model):
    """A video that shows an example of the use of a particular sense"""
    videofile = models.FileField("video file", upload_to=get_sentence_video_file_path, storage=storage,
                                 validators=[validate_file_extension])
    examplesentence = models.ForeignKey(ExampleSentence, on_delete=models.CASCADE)
    version = models.IntegerField("Version", default=0)
    get_videofile_name_function = get_sentence_video_file_path

    def save(self, *args, **kwargs):
        self.ensure_mp4()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return self.videofile.url

    def change_file_permissions(self):
        """Change permissions"""
        os.chmod(self.videofile.path, stat.S_IRWXU | stat.S_IRWXG)

    def make_small_video(self):
        video_file_full_path = os.path.join(WRITABLE_FOLDER, self.videofile.name)
        try:
            resizer = VideoResizer([video_file_full_path], FFMPEG_PROGRAM, 180, 0, 0)
            resizer.run()
        except Exception as e:
            logger.info(f"Error resizing video: {video_file_full_path}")
            logger.info(e)

    def make_poster_image(self):
        try:
            generate_still_image(self)
        except (OSError, PermissionError):
            logger.info(f'Error generating still image {sys.exc_info()}')

    def delete_files(self):
        """Delete the files associated with this object"""
        try:
            os.unlink(self.videofile.path)
        except (OSError, PermissionError):
            pass

    def __str__(self):
        return self.videofile.name

    def move_video(self, move_files_on_disk=True):
        """
        Calculates the new path, moves the video file to the new path and updates the videofile field
        :return:
        """
        old_path = self.videofile.name
        new_path = get_sentence_video_file_path(self, old_path, self.version)
        if old_path == new_path:
            return

        self.videofile.name = new_path
        self.save()

        if not move_files_on_disk:
            return

        source = os.path.join(WRITABLE_FOLDER, old_path)
        destination = os.path.join(WRITABLE_FOLDER, new_path)

        # Small video
        source_small = add_small_appendix(source)
        destination_small = add_small_appendix(destination)
        if os.path.exists(source_small):
            shutil.move(source_small, destination_small)

        if not os.path.exists(source):
            return

        destination_dir = os.path.dirname(destination)
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        if os.path.isdir(destination_dir):
            shutil.move(source, destination)


class AnnotatedVideo(EnsureMp4Mixin, models.Model):
    """A video that shows an example of the use of a particular sense"""
    annotatedsentence = models.OneToOneField(AnnotatedSentence, on_delete=models.CASCADE)
    videofile = models.FileField("video file", upload_to=get_annotated_video_file_path, storage=storage,
                                 validators=[validate_file_extension])
    eaffile = models.FileField("eaf file", upload_to=get_annotated_video_file_path, storage=storage)
    source = models.ForeignKey(AnnotatedSentenceSource, null=True, on_delete=models.SET_NULL)
    url = models.URLField("URL", null=True, blank=True)
    get_videofile_name_function = get_annotated_video_file_path

    # video version, version = 0 is always the one that will be displayed
    # we will increment the version (via reversion) if a new video is added for this gloss
    # TODO: HIS IS NOT IMPLEMENTED YET
    version = models.IntegerField("Version", default=0)

    def save(self, *args, **kwargs):
        self.ensure_mp4()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        parsed_url = urlparse(self.url)
        if not parsed_url.scheme:
            return 'http://' + self.url
        return self.url

    def delete_files(self, only_eaf=False):
        """Delete the files associated with this object"""
        try:
            os.remove(self.eaffile.path)
            if not only_eaf:
                video_path = os.path.join(WRITABLE_FOLDER, ANNOTATEDSENTENCE_VIDEO_DIRECTORY,
                                          self.annotatedsentence.get_dataset().acronym, str(self.annotatedsentence.id))
                shutil.rmtree(video_path)
        except (OSError, PermissionError):
            pass

    def get_end_ms(self):
        """Get the duration of a video in ms using ffprobe."""
        ffprobe = ffmpeg.probe(self.videofile.path)
        stream = next((stream for stream in ffprobe['streams'] if stream['codec_type'] == 'video'), None)
        if not stream:
            return -1
        return float(stream['duration']) * 1000

    def __str__(self):
        return self.videofile.name

    def convert_milliseconds_to_time_format(self, ms):
        """Convert milliseconds to a time format HH:MM:SS.mmm"""
        milliseconds = ms % 1000
        seconds = (ms // 1000) % 60
        minutes = (ms // (1000 * 60)) % 60
        hours = (ms // (1000 * 60 * 60)) % 24
        return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

    def select_annotations(self, eaf, tier_name, start_ms, end_ms):
        """Select annotations that are within the selected range"""
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
        start_time = self.convert_milliseconds_to_time_format(int(start_ms))
        end_time = self.convert_milliseconds_to_time_format(int(end_ms))

        # Cut the video
        input_file = Path(self.videofile.path)
        temp_output_file = Path(os.path.join(os.path.split(input_file)[0], 'temp.mp4'))
        try:
            (ffmpeg
             .input(input_file)
             .output(temp_output_file, ss=start_time, to=end_time)
             .run(overwrite_output=True, quiet=True))
        except ffmpeg.Error as e:
            raise RuntimeError(f"ffmpeg error: {e}")

        # Overwrite the original file with the cut video
        try:
            shutil.move(temp_output_file, input_file)
        except (OSError, PermissionError) as e:
            raise RuntimeError(f"File overwrite error: {e}")

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


class GlossVideo(EnsureMp4Mixin, ReversionMixin, models.Model):
    """A video that represents a particular idgloss"""
    videofile = models.FileField("video file", storage=storage, validators=[validate_file_extension])
    gloss = models.ForeignKey(Gloss, on_delete=models.CASCADE)
    version = models.IntegerField("Version", default=0)
    get_videofile_name_function = get_video_file_path

    def __init__(self, *args, **kwargs):
        self.upload_to = kwargs.pop('upload_to', get_video_file_path)
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.ensure_mp4()
        super().save(*args, **kwargs)

    def poster_path(self, create=True):
        """Return the path of the poster image for this video, if create=True, create the image if needed
        Return None if create=False and the file doesn't exist"""
        video_path, _ = os.path.splitext(self.videofile.path)
        poster_path = f'{video_path}.png'
        poster_path = poster_path.replace(GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY, 1)

        if os.path.exists(poster_path):
            return poster_path

        if not create:
            return None

        extract_frame(self.videofile.path, poster_path)
        return poster_path

    def poster_file(self):
        video_file, _ = os.path.splitext(self.videofile.name)
        poster_file = f'{video_file}.png'
        poster_file = poster_file.replace(GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY, 1)
        return poster_file

    def small_video(self, use_name=False):
        """Return the URL of the small version for this video
        :param use_name: whether videofile.name should be used instead of videofile.path
        """
        if not self.videofile:
            return None
        small_video_path = add_small_appendix(self.videofile.path)
        if not os.path.exists(small_video_path):
            return None
        if use_name:
            return add_small_appendix(self.videofile.name)
        return small_video_path

    def make_image_sequence(self):
        generate_image_sequence(self.gloss, self.videofile)

    def delete_image_sequence(self):
        remove_stills(self.gloss)

    def make_small_video(self):
        name, _ = os.path.splitext(self.videofile.path)
        small_name = name + "_small.mp4"
        (ffmpeg.input(self.videofile.path)
               .filter("scale", -2, 180)
               .output(small_name)
               .run(quiet=True))

    def make_poster_image(self):
        try:
            generate_still_image(self)
        except (OSError, PermissionError):
            logger.info(f'Error generating still image {sys.exc_info()}')

    def convert_to_mp4(self):
        # this method is not called (bugs)
        logger.info(f'Convert to mp4: {self.videofile.path}')
        name, _ = os.path.splitext(self.videofile.path)
        out_name = f'{name}_copy.mp4'

        (ffmpeg.input(self.videofile.path)
               .output(out_name, vcodec='h264')
               .run(quiet=True))

        os.rename(out_name, self.videofile.path)
        logger.info(f"Finished converting {self.videofile.path}")

    def delete_files(self):
        """Delete the files associated with this object"""
        if DEBUG_VIDEOS:
            logger.info(f'delete_files GlossVideo: {self.videofile}')

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
                logger.info(f'delete_files exception GlossVideo OSError, PermissionError: {self.videofile}')

    def __str__(self):
        return self.videofile.name

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
        if old_path == new_path:
            return

        self.videofile.name = new_path
        self.save()

        if not move_files_on_disk:
            return

        source = os.path.join(WRITABLE_FOLDER, old_path)
        destination = os.path.join(WRITABLE_FOLDER, new_path)
        if os.path.exists(source):
            destination_dir = os.path.dirname(destination)
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
            if os.path.isdir(destination_dir):
                shutil.move(source, destination)

        # Small video
        source_small = add_small_appendix(source)
        destination_small = add_small_appendix(destination)
        if os.path.exists(source_small):
            shutil.move(source_small, destination_small)

        # Image
        source_no_extension, _ = os.path.splitext(source)
        source_image = source_no_extension.replace(GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY) + '.png'
        if not os.path.exists(source_image):
            return
        destination_no_extension, _ = os.path.splitext(destination)
        destination_image = destination_no_extension.replace(GLOSS_VIDEO_DIRECTORY, GLOSS_IMAGE_DIRECTORY) + '.png'

        destination_image_dir = os.path.dirname(destination_image)
        if not os.path.exists(destination_image_dir):
            os.makedirs(destination_image_dir)
        if os.path.isdir(destination_image_dir):
            shutil.move(source_image, destination_image)


class GlossVideoDescription(models.Model):
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
        lemma = self.gloss.lemma
        dataset_language_count = lemma.dataset.translation_languages.all().count() if lemma else 0
        translations = [
            f"{description.language}: {description.text}" if dataset_language_count > 1 else f"{description.text}"
            for description in GlossVideoDescription.objects.filter(nmevideo=self)
        ]
        display_preface = f'{self.offset}_{self.perspective}' if self.perspective else f'{self.offset}'
        return f'{display_preface}: {", ".join(translations)}'

    def has_perspective_videos(self):
        if self.perspective not in ['', 'center']:
            return False
        return (GlossVideoNME.objects.filter(gloss=self.gloss, offset=self.offset, perspective__in=['left', 'right'])
                .exists())

    def has_left_perspective(self):
        return GlossVideoNME.objects.filter(gloss=self.gloss, offset=self.offset, perspective='left').exists()

    def has_right_perspective(self):
        return GlossVideoNME.objects.filter(gloss=self.gloss, offset=self.offset, perspective='right').exists()

    def add_descriptions(self, descriptions):
        if self.perspective not in ['', 'center']:
            return
        for language in self.gloss.lemma.dataset.translation_languages.all():
            if language.language_code_2char in descriptions and (text := descriptions[language.language_code_2char]):
                GlossVideoDescription.objects.create(text=text, nmevideo=self, language=language)

    def get_video_path(self):
        if DEBUG_VIDEOS:
            logger.info(f'get_video_path GlossVideoNME: {self.videofile}')
        return escape_uri_path(self.videofile.name) if self.videofile else ''

    def ensure_mp4(self):
        """Ensure that the video file is an h264 format video, convert it if necessary"""
        if not self.videofile or not self.videofile.path or not os.path.exists(self.videofile.path):
            return

        video_format_extension = detect_video_file_extension(self.videofile.path)
        basename, extension = os.path.splitext(self.videofile.path)
        if extension == '.mp4' and video_format_extension == '.mp4':
            return

        old_relative_path = self.videofile.name
        old_location = self.videofile.path
        new_location = basename + ".mp4"
        succes = convert_video(old_location, new_location)
        if not succes or not os.path.exists(new_location):
            return
        self.videofile.name = get_video_file_path(self, os.path.basename(new_location),
                                                  nmevideo=True, perspective='', offset=self.offset)
        move_file_to_trash(old_location, old_relative_path)

    def move_video(self, move_files_on_disk=True):
        """
        Calculates the new path, moves the video file to the new path and updates the videofile field
        :return:
        """
        old_path = str(self.videofile)
        if not move_files_on_disk or not old_path:
            return
        new_path = get_video_file_path(self, old_path, nmevideo=True, perspective='', offset=self.offset, version=0)
        if old_path == new_path:
            return
        source = os.path.join(WRITABLE_FOLDER, old_path)
        if not os.path.exists(source):
            return
        destination = os.path.join(WRITABLE_FOLDER, new_path)
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
            logger.info(e)
            return False

    def reversion(self, revert=False):
        """Delete the video file of this object"""
        success = self.delete_files()
        if not success:
            logger.info(f"DELETE NME VIDEO FAILED: {self.videofile.name}")
        else:
            self.delete()


class GlossVideoPerspective(GlossVideo):
    perspective = models.CharField(max_length=20, choices=PERSPECTIVE_CHOICES)

    class Meta:
        verbose_name = gettext("Gloss Video Perspective")
        ordering = ['perspective', ]

    def get_video_path(self):
        return escape_uri_path(self.videofile.name) if self.videofile else ''

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
        new_path = get_video_file_path(self, old_path, nmevideo=False, perspective=str(self.perspective))
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
            logger.info(e)
            return False

    def reversion(self, revert=False):
        """Delete the video file of this object"""
        success = self.delete_files()
        if not success:
            logger.info(f"DELETE Perspective VIDEO FAILED: {self.videofile.name}")
        else:
            self.delete()


def move_videos_for_filter(filter_dict, move_files_on_disk: bool = False) -> None:
    """
    Changes GlossVideo.videofile values for a filter dict
    and moves files on disk if move_file_on_disk is True (default is False).
    A filter dict is used in the QuerySet.filter method as **filter
    """
    for glossvideo in GlossVideo.objects.filter(**filter_dict, glossvideonme=None, glossvideoperspective=None):
        glossvideo.move_video(move_files_on_disk=move_files_on_disk)
    for glossvideo_nme in GlossVideoNME.objects.filter(**filter_dict):
        glossvideo_nme.move_video(move_files_on_disk=move_files_on_disk)
    for glossvideos_perspective in GlossVideoPerspective.objects.filter(**filter_dict):
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
    dataset = instance
    if dataset._initial['acronym'] and dataset.acronym != dataset._initial['acronym']:
        process_dataset_acronym_change(dataset)
    if dataset._initial['default_language'] and dataset.default_language_id != dataset._initial['default_language']:
        process_dataset_default_language_change(dataset)


def process_dataset_acronym_change(dataset):
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


def process_dataset_default_language_change(dataset):
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
def process_gloss_changes(sender, instance, update_fields, **kwargs):
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
    for glossvideo in GlossVideo.objects.filter(gloss=gloss, glossvideonme=None, glossvideoperspective=None):
        glossvideo.move_video(move_files_on_disk=True)

    for glossvideonme in GlossVideoNME.objects.filter(gloss=gloss):
        glossvideonme.move_video(move_files_on_disk=True)

    for glossvideoperspective in GlossVideoPerspective.objects.filter(gloss=gloss):
        glossvideoperspective.move_video(move_files_on_disk=True)


@receiver(models.signals.post_save, sender=GlossVideoNME)
def process_nmevideo_changes(sender, instance, update_fields, **kwargs):
    """
    Makes changes to GlossVideoNME if an offset has changed
    :param sender:
    :param instance:
    :param update_fields: indicate whether the video path has changed
    :param kwargs:
    :return:
    """
    do_not_move_videos = not update_fields or 'offset' not in update_fields
    if DEBUG_VIDEOS:
        logger.info(f'process_nmevideo_changes move videos: {instance} {do_not_move_videos}')
    if do_not_move_videos:
        return
    glossvideonme = instance
    glossvideonme.move_video(move_files_on_disk=True)


@receiver(models.signals.post_save, sender=GlossVideoPerspective)
def process_perspectivevideo_changes(sender, instance, update_fields, **kwargs):
    """
    Makes changes to GlossVideoPerspective if an offset has changed
    :param sender:
    :param instance:
    :param update_fields: indicate whether the video path has changed
    :param kwargs:
    :return:
    """
    do_not_move_videos = not update_fields
    if DEBUG_VIDEOS:
        logger.info(f'process_perspectivevideo_changes move videos: {instance} {do_not_move_videos}')
    if do_not_move_videos:
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
        logger.info(f'delete_files pre_delete: {instance}')
        logger.info(f'delete_files settings.DELETE_FILES_ON_GLOSSVIDEO_DELETE: {DELETE_FILES_ON_GLOSSVIDEO_DELETE}')
    if hasattr(instance, 'glossvideonme'):
        instance.delete_files()
    elif hasattr(instance, 'glossvideoperspective'):
        instance.delete_files()
    elif DELETE_FILES_ON_GLOSSVIDEO_DELETE:
        instance.delete_files()
