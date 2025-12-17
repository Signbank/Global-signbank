import logging
import os
import stat
import shutil
import datetime as DT
from pathlib import Path

from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from signbank.video.models import (GlossVideo, GlossVideoHistory, AnnotatedVideo, ExampleVideoHistory,
                                   filename_matches_nme, filename_matches_perspective, filename_matches_video,
                                   filename_matches_backup_video, flattened_video_path, build_glossvideo_filename)
from signbank.dictionary.models import Dataset, AnnotatedGloss, Gloss
from signbank.settings.base import GLOSS_VIDEO_DIRECTORY
from signbank.settings.server_specific import WRITABLE_FOLDER, FILESYSTEM_SIGNBANK_GROUPS, DELETED_FILES_FOLDER
from signbank.tools import get_two_letter_dir
from signbank.video.convertvideo import video_file_type_extension, convert_video


logger = logging.getLogger(__name__)


class GlossVideoDatasetFilter(admin.SimpleListFilter):
    """Filter the GlossVideo objects on the Dataset of the gloss"""
    title = _('Dataset')
    parameter_name = 'videos_per_dataset'

    def lookups(self, request, model_admin):
        return Dataset.objects.values_list('id', 'acronym')

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        return queryset.filter(gloss__lemma__dataset_id=self.value())


class GlossVideoFileSystemGroupFilter(admin.SimpleListFilter):
    """Filter the GlossVideo objects on the file system group of the video file"""
    title = _('File System Group')
    parameter_name = 'filesystem_group'

    def lookups(self, request, model_admin):
        return ((group, group) for group in FILESYSTEM_SIGNBANK_GROUPS)

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()

        glossvideo_list = queryset.values('id', 'videofile')
        results = [glossvideo['id'] for glossvideo in glossvideo_list
                   if self.matching_file_group(glossvideo['videofile'], self.value())]
        return queryset.filter(id__in=results)

    @staticmethod
    def matching_file_group(videofile, key):
        if not key:
            return False
        video_file_full_path = Path(WRITABLE_FOLDER, videofile)
        if not video_file_full_path.exists():
            return False
        return video_file_full_path.group() == key


class TrueFalseFilterMixin:
    true_str = 'Yes'
    false_str = 'No'

    def lookups(self, request, model_admin):
        return ((boolean, boolean) for boolean in (self.true_str, self.false_str))


class GlossVideoExistenceFilter(TrueFalseFilterMixin, admin.SimpleListFilter):
    """Filter the GlossVideo objects on whether the video file exists"""
    title = _('File Exists')
    parameter_name = 'file_exists'

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()

        glossvideo_list = queryset.values('id', 'videofile')
        results = [glossvideo['id'] for glossvideo in glossvideo_list
                   if self.matching_file_exists(glossvideo['videofile'], self.value())]
        return queryset.filter(id__in=results)

    def matching_file_exists(self, videofile, key):
        if not key:
            return False
        if "glossvideo" not in videofile:
            return False
        if Path(WRITABLE_FOLDER, videofile).exists():
            return key == self.true_str
        return key == self.false_str


class GlossVideoFilenameFilter(TrueFalseFilterMixin, admin.SimpleListFilter):
    """Filter the GlossVideo objects on whether the filename is correct for the type of video"""
    title = _('Filename Correct')
    parameter_name = 'filename_correct'

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        glossvideo_list = queryset.values('id', 'videofile', 'glossvideonme', 'glossvideoperspective', 'version')
        results = [glossvideo['id'] for glossvideo in glossvideo_list
                   if self.matching_filename(glossvideo, self.value())]
        return queryset.filter(id__in=results)

    def matching_filename(self, glossvideo, key):
        if not key:
            return False
        video_file_full_path = Path(WRITABLE_FOLDER, glossvideo['videofile'])
        if glossvideo['glossvideonme']:
            filename_is_correct = filename_matches_nme(video_file_full_path) is not None
        elif glossvideo['glossvideoperspective']:
            filename_is_correct = filename_matches_perspective(video_file_full_path) is not None
        elif glossvideo['version'] > 0:
            filename_is_correct = filename_matches_backup_video(video_file_full_path) is not None
        else:
            filename_is_correct = filename_matches_video(video_file_full_path) is not None
        return key == (self.true_str if filename_is_correct else self.false_str)


class GlossVideoNMEFilter(TrueFalseFilterMixin, admin.SimpleListFilter):
    """ Filter the GlossVideo objects on whether the video is an NME Video"""
    title = _('NME Video')
    parameter_name = 'nme_videos'

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        if self.value() == self.true_str:
            return queryset.filter(glossvideonme__isnull=False)
        return queryset.filter(glossvideonme__isnull=True)


class GlossVideoPerspectiveFilter(TrueFalseFilterMixin, admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on whether the video is a Perspective Video
    The values of lookups show in the right-hand column of the admin under a heading "Perspective Video"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('Perspective Video')
    parameter_name = 'perspective_videos'

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        if self.value() == self.true_str:
            return queryset.filter(glossvideoperspective__isnull=False)
        return queryset.filter(glossvideoperspective__isnull=True)


class GlossVideoFileTypeFilter(TrueFalseFilterMixin, admin.SimpleListFilter):
    """Filter the GlossVideo objects on whether the video is an MP4 video"""
    title = _('MP4 File')
    parameter_name = 'file_type'

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        glossvideo_list = queryset.values('id', 'videofile')
        results = [glossvideo['id'] for glossvideo in glossvideo_list
                   if self.matching_file_type(glossvideo['videofile'], self.value())]
        return queryset.filter(id__in=results)

    def matching_file_type(self, videofile, key):
        if not key:
            return False
        video_file_full_path = Path(WRITABLE_FOLDER, videofile)
        file_extension = video_file_type_extension(video_file_full_path)
        has_mp4_type = file_extension == ".mp4"
        return key == (self.true_str if has_mp4_type else self.false_str)


class GlossVideoWebmTypeFilter(TrueFalseFilterMixin, admin.SimpleListFilter):
    """Filter the GlossVideo objects on whether the video is a Webm video"""
    title = _('Webm File')
    parameter_name = 'webm_file_type'

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        glossvideo_list = queryset.values('id', 'videofile')
        results = [glossvideo['id'] for glossvideo in glossvideo_list
                   if self.matching_file_type(glossvideo['videofile'], self.value())]

        return queryset.filter(id__in=results)

    def matching_file_type(self, videofile, key):
        if not key:
            return False
        video_file_full_path = Path(WRITABLE_FOLDER, videofile)
        file_extension = video_file_type_extension(video_file_full_path)
        has_webm_type = file_extension == '.webm'
        return key == self.true_str if has_webm_type else key == self.false_str


class GlossVideoBackupFilter(TrueFalseFilterMixin, admin.SimpleListFilter):
    """Filter the GlossVideo objects on whether the video is a backup video"""
    title = _('Backup Video')
    parameter_name = 'backup_videos'

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        if self.value() == self.true_str:
            return queryset.filter(version__gt=0)
        return queryset.filter(version=0)


@admin.action(description="Rename normal video files to match type")
def rename_extension_videos(modeladmin, request, queryset):
    """
    This command determines which glosses are selected, then retrieves the normal video objects for those glosses.
    This allows the user to merely select one of the objects and then change them all.
    For those gloss video objects, it renames the file if the filename is not correct.
    This also applies to wrong video types in filenames, e.g., a webm video that has mp4 in its filename.
    This applies to backup videos as well as normal videos.
    """
    glosses = Gloss.objects.filter(glossvideo__in=queryset)
    glossvideos = (GlossVideo.objects.filter(gloss__in=glosses, glossvideonme=None, glossvideoperspective=None)
                                     .exclude(videofile='').order_by('version', 'id'))

    for glossvideo in glossvideos:
        video_file_full_path = os.path.join(WRITABLE_FOLDER, glossvideo.videofile.name)
        desired_video_extension = video_file_type_extension(video_file_full_path)
        if not desired_video_extension:
            continue

        desired_filename = build_glossvideo_filename(glossvideo, desired_video_extension)
        if glossvideo.version > 0:
            desired_filename = f'{desired_filename}.bak{glossvideo.id}'
        if desired_filename == os.path.basename(video_file_full_path):
            continue

        rename_videofile(desired_filename, glossvideo, video_file_full_path)


def rename_videofile(desired_filename: str, glossvideo: GlossVideo, video_file_full_path: str):
    """Renames the file of the given GlossVideo.videofile"""
    dataset_acronym = glossvideo.gloss.lemma.dataset.acronym
    two_letter_dir = get_two_letter_dir(glossvideo.gloss.idgloss)
    desired_relative_path = os.path.join(GLOSS_VIDEO_DIRECTORY, dataset_acronym, two_letter_dir, desired_filename)
    destination = os.path.join(WRITABLE_FOLDER, desired_relative_path)

    logger.info(f'video:admin:rename_extension_videos:os.rename: {video_file_full_path, destination}')

    if os.path.exists(video_file_full_path):
        os.rename(video_file_full_path, destination)

    logger.info(f'video:admin:rename_extension_videos:videofile.name := {desired_relative_path}')

    glossvideo.videofile.name = desired_relative_path
    glossvideo.save()


@admin.action(description="Move selected backup files to trash")
def remove_backups(modeladmin, request, queryset):
    """
    This command moves the selected backup files to the DELETED_FILES_FOLDER location.
    To prevent the GlossVideo object from pointing to the deleted files folder location,
    the name stored in the object is set to empty before deleting the object.
    Other selected objects are ignored.
    This allows the user to keep a number of the backup files by not selecting everything.
    """
    for glossvideo in queryset.filter(glossvideonme=None, glossvideoperspective=None, version__gt=0):
        relative_path = glossvideo.videofile.name
        if not relative_path:
            continue
        video_file_full_path = os.path.join(WRITABLE_FOLDER, relative_path)
        if not os.path.exists(video_file_full_path):
            logger.info(f'video:admin:remove_backups:delete object: {relative_path}')
            glossvideo.delete()
            continue

        # move the video file to DELETED_FILES_FOLDER and erase the name to avoid the signals on GlossVideo delete
        deleted_file_name = flattened_video_path(relative_path)
        destination = os.path.join(WRITABLE_FOLDER, DELETED_FILES_FOLDER, deleted_file_name)
        destination_dir = os.path.dirname(destination)
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)

        # TODO rethink code below
        if os.path.isdir(destination_dir):
            try:
                shutil.move(video_file_full_path, destination)
                glossvideo.videofile.name = ""
                glossvideo.save()
                logger.info(f'video:admin:remove_backups:shutil.move: {video_file_full_path, destination}')
            except (OSError, PermissionError) as e:
                print(e)
                continue
        # the object does not point to anything anymore, so it can be deleted
        logger.info(f'video:admin:remove_backups:delete object: {relative_path}')
        glossvideo.delete()


@admin.action(description="Renumber selected backups")
def renumber_backups(modeladmin, request, queryset):
    """
    This command renumbers the backup video objects for the GlossVideo queryset.
    The command determines which glosses are selected, then retrieves the backup video objects for those glosses.
    This allows the user to merely select one of the objects and then renumber them all.
    Because the backup objects are numbered by version, all of the objects must be renumbered.
    """
    for gloss in Gloss.objects.filter(glossvideo__in=queryset).distinct():
        glossvideos = GlossVideo.objects.filter(gloss=gloss, glossvideonme=None, glossvideoperspective=None,
                                                version__gt=0).order_by('version', 'id')
        for index, glossvideo in enumerate(glossvideos, 1):
            if index == glossvideo.version:
                continue
            glossvideo.version = index
            glossvideo.save()


@admin.action(description="Set incorrect NME/Perspective filenames to empty string")
def unlink_files(modeladmin, request, queryset):
    """
    This command only applies to Perspective and NME videos, other selected videos are ignored.
    Allow to erase the filename from an object if it has the wrong format.
    This is for the purpose of repairing doubly linked files where the subclass object points to the normal video.
    Once the filename has been cleared, the user can delete the object as normal with the Admin delete command.
    This prevents a normal video linked to by a subclass video from being deleted.
    """
    for glossvideo in queryset:
        if not hasattr(glossvideo, 'glossvideonme') and not hasattr(glossvideo, 'glossvideoperspective'):
            continue
        relative_path = glossvideo.videofile.name
        if not relative_path:
            continue
        video_file_full_path = Path(WRITABLE_FOLDER, relative_path)
        # ignore the files that have the correct filename
        if hasattr(glossvideo, 'glossvideonme') and filename_matches_nme(video_file_full_path):
            continue
        if hasattr(glossvideo, 'glossvideoperspective') and filename_matches_perspective(video_file_full_path):
            continue

        logger.info(f'unlink_files: erase incorrect path from NME or Perspective object: '
                    f'{glossvideo} {video_file_full_path}')

        glossvideo.videofile.name = ""
        glossvideo.save()


@admin.action(description="Convert non-mp4 video files to mp4")
def convert_non_mp4_videos(modeladmin, request, queryset):
    """
    This command determines which glosses are selected, then retrieves the normal video objects for those glosses.
    This allows the user to merely select one of the objects and hereby change them all instead of numerous selections.
    For those gloss video objects, it converts the file if the format is not mp4.
    """
    glosses = Gloss.objects.filter(glossvideo__in=queryset)
    glossvideos = (GlossVideo.objects.filter(gloss__in=glosses, glossvideonme=None, glossvideoperspective=None)
                                     .exclude(videofile='').order_by('version', 'id'))

    for glossvideo in glossvideos:
        video_file_full_path = os.path.join(WRITABLE_FOLDER, glossvideo.videofile.name)
        desired_video_extension = video_file_type_extension(video_file_full_path)
        if not desired_video_extension:
            continue

        desired_filename = build_glossvideo_filename(glossvideo, desired_video_extension)
        if desired_filename != os.path.basename(video_file_full_path):
            rename_videofile(desired_filename, glossvideo, video_file_full_path)

        if desired_video_extension == '.mp4':
            continue

        dataset_acronym = glossvideo.gloss.lemma.dataset.acronym
        two_letter_dir_relative = os.path.join(GLOSS_VIDEO_DIRECTORY, dataset_acronym,
                                               get_two_letter_dir(glossvideo.gloss.idgloss))

        if glossvideo.version > 0:
            # the video is not converted by ensure_mp4 if it is a backup, refetch the path after possible renaming
            goto_next_glossvideo = convert_non_mp4_backup_videos(desired_video_extension, glossvideo,
                                                                 two_letter_dir_relative, video_file_full_path)
            if goto_next_glossvideo:
                continue

        # move the original video file to DELETED_FILES_FOLDER, it is not referenced anymore by the GlossVideo object
        deleted_file_name = flattened_video_path(os.path.join(two_letter_dir_relative, desired_filename))
        deleted_destination = os.path.join(WRITABLE_FOLDER, DELETED_FILES_FOLDER, deleted_file_name)

        destination_dir = os.path.join(WRITABLE_FOLDER, two_letter_dir_relative)
        original_with_correct_extension = os.path.join(destination_dir, desired_filename)

        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        try:
            shutil.move(str(original_with_correct_extension), str(deleted_destination))
            logger.info(f'video:admin:convert_non_mp4_videos:shutil.move: '
                        f'{original_with_correct_extension} {deleted_destination}')
        except (OSError, PermissionError) as e:
            logger.info(e)


def convert_non_mp4_backup_videos(desired_video_extension, glossvideo, two_letter_dir_relative, video_file_full_path):
    flipped_source = os.path.join(WRITABLE_FOLDER, two_letter_dir_relative,
                                  build_glossvideo_filename(glossvideo, desired_video_extension, flipped=True))

    flipped_destination = os.path.join(WRITABLE_FOLDER, two_letter_dir_relative,
                                       build_glossvideo_filename(glossvideo, '.mp4', flipped=True))

    desired_filename = build_glossvideo_filename(glossvideo, '.mp4')
    destination = os.path.join(WRITABLE_FOLDER, two_letter_dir_relative, desired_filename)
    desired_relative_path = os.path.join(two_letter_dir_relative, desired_filename)

    if not os.path.exists(video_file_full_path):
        return True

    logger.info(f'video:admin:convert_non_mp4_videos:os.rename: {video_file_full_path} {flipped_source}')

    os.rename(video_file_full_path, flipped_source)
    succes = convert_video(flipped_source, flipped_destination)

    logger.info(f'video:admin:convert_non_mp4_videos:convert_video: {flipped_source} {flipped_destination}')

    if not succes or not os.path.exists(flipped_destination):
        return True

    logger.info(f'video:admin:convert_non_mp4_videos:os.rename: {flipped_destination} {desired_relative_path}')
    logger.info(f'video:admin:convert_non_mp4_videos:videofile.name := {desired_relative_path}')

    os.rename(flipped_destination, destination)
    glossvideo.videofile.name = desired_relative_path
    glossvideo.save()
    os.rename(flipped_source, video_file_full_path)
    return False


class GlossVideoAdmin(admin.ModelAdmin):
    list_display = ['id', 'gloss', 'video_file', 'perspective', 'NME', 'file_timestamp', 'file_group', 'permissions',
                    'file_size', 'video_type',  'version']
    list_filter = (GlossVideoDatasetFilter, GlossVideoFileSystemGroupFilter, GlossVideoExistenceFilter,
                   GlossVideoFileTypeFilter, GlossVideoWebmTypeFilter, GlossVideoNMEFilter, GlossVideoPerspectiveFilter,
                   GlossVideoFilenameFilter, GlossVideoBackupFilter)
    search_fields = ['^gloss__annotationidglosstranslation__text', '^gloss__lemma__lemmaidglosstranslation__text']
    actions = [rename_extension_videos, remove_backups, renumber_backups, unlink_files, convert_non_mp4_videos]

    def video_file(self, obj=None):
        """
        column VIDEO FILE
        this will display the full path in the list view, also for non-existent files
        """
        if obj is None or not obj.videofile.name:
            return ""
        return os.path.join(WRITABLE_FOLDER, obj.videofile.name)

    def perspective(self, obj=None):
        """
        column PERSPECTIVE
        This will be True if the object is of subclass GlossVideoPerspective
        """
        if obj is None:
            return ""
        return obj.is_glossvideoperspective()

    def NME(self, obj=None):
        """
        column NME
        This will be True if the object is of subclass GlossVideoNME
        """
        if obj is None:
            return ""
        return obj.is_glossvideonme()

    def file_timestamp(self, obj=None):
        """
        column FILE TIMESTAMP
        if the file exists, this will display its timestamp in the list view
        """
        if obj is None or not obj.videofile.name:
            return ""
        video_file_full_path = os.path.join(WRITABLE_FOLDER, obj.videofile.name)
        if not os.path.exists(video_file_full_path):
            return ""
        return DT.datetime.fromtimestamp(os.path.getctime(video_file_full_path))

    def file_group(self, obj=None):
        """
        column FILE GROUP
        if the file exists, this will display the file system group in the list view
        """
        if obj is None or not obj.videofile.name:
            return ""
        video_file_full_path = Path(WRITABLE_FOLDER, obj.videofile.name)
        if not video_file_full_path.exists():
            return ""
        return video_file_full_path.group()

    def file_size(self, obj=None):
        """
        column FILE SIZE
        if the file exists, this will display the file size in the list view
        """
        if obj is None or not obj.videofile.name:
            return ""
        video_file_full_path = Path(WRITABLE_FOLDER, obj.videofile.name)
        if not video_file_full_path.exists():
            return ""
        return str(video_file_full_path.stat().st_size)

    def permissions(self, obj=None):
        """
        column PERMISSIONS
        if the file exists, this will display the file system permissions in the list view
        """
        if obj is None or not obj.videofile.name:
            return ""
        video_file_full_path = Path(WRITABLE_FOLDER, obj.videofile.name)
        if not video_file_full_path.exists():
            return ""
        return stat.filemode(video_file_full_path.stat().st_mode)

    def video_type(self, obj=None):
        """
        column VIDEO TYPE
        if the file exists, this will display the video type in file extension format
        """
        if obj is None or not obj.videofile.name:
            return ""
        video_file_full_path = os.path.join(WRITABLE_FOLDER, obj.videofile.name)
        if not os.path.exists(video_file_full_path):
            return ""
        return video_file_type_extension(video_file_full_path)

    def get_list_display_links(self, request, list_display):
        # do not allow the user to click on data of individual elements in the list display
        self.list_display_links = (None, )
        return self.list_display_links

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Only allow to delete objects without any file
        if not self.file_timestamp(obj):
            return True
        return False


class GlossVideoHistoryDatasetFilter(admin.SimpleListFilter):
    title = _('Dataset')
    parameter_name = 'videos_per_dataset'

    def lookups(self, request, model_admin):
        return Dataset.objects.values_list('id', 'acronym')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gloss__lemma__dataset_id=self.value())
        return queryset.all()


class GlossVideoHistoryActorFilter(admin.SimpleListFilter):
    title = _('Actor')
    parameter_name = 'videos_per_actor'

    def lookups(self, request, model_admin):
        return User.objects.values_list('id', 'username').order_by('username')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(actor__id=self.value())
        return queryset.all()


class GlossVideoHistoryAdmin(admin.ModelAdmin):
    list_display = ['action', 'datestamp', 'uploadfile', 'goal_location', 'actor', 'gloss']
    list_filter = (GlossVideoHistoryDatasetFilter, GlossVideoHistoryActorFilter)
    search_fields = ['^gloss__annotationidglosstranslation__text']


class AnnotatedVideoDatasetFilter(admin.SimpleListFilter):
    title = _('Dataset')
    parameter_name = 'dataset'

    def lookups(self, request, model_admin):
        return Dataset.objects.values_list('id', 'acronym')

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.all()
        annotated_glosses = AnnotatedGloss.objects.filter(gloss__lemma__dataset_id=self.value())
        annotated_sentences_ids = [ag.annotatedsentence_id for ag in annotated_glosses]
        if not annotated_sentences_ids:
            return None
        return queryset.filter(annotatedsentence_id__in=annotated_sentences_ids)


class AnnotatedVideoAdmin(admin.ModelAdmin):
    actions = None
    list_display = ('dataset', 'annotated_sentence', 'video_file', 'timestamp', 'eaf_file', 'eaf_timestamp', 'url',
                    'source')
    list_filter = [AnnotatedVideoDatasetFilter]
    search_fields = ['annotatedsentence__annotated_sentence_translations__text']

    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }

    def dataset(self, obj=None):
        if obj is None:
            return ""
        annotated_glosses = AnnotatedGloss.objects.filter(annotatedsentence=obj.annotatedsentence)
        if not annotated_glosses:
            return ""
        return annotated_glosses.first().gloss.lemma.dataset

    def annotated_sentence(self, obj=None):
        if obj is None:
            return ""
        translations = obj.annotatedsentence.get_annotatedstc_translations()
        return " | ".join(translations)

    def video_file(self, obj=None):
        if obj is None:
            return ""
        return obj.videofile.name

    def timestamp(self, obj=None):
        # if the file exists, this will display its timestamp in the list view
        if obj is None:
            return ""
        video_file_full_path = os.path.join(WRITABLE_FOLDER, obj.videofile.name)
        if os.path.exists(video_file_full_path):
            return DT.datetime.fromtimestamp(os.path.getctime(video_file_full_path))
        return ""

    def eaf_file(self, obj=None):
        if obj is None:
            return ""
        return obj.eaffile.name

    def eaf_timestamp(self, obj=None):
        # if the file exists, this will display its timestamp in the list view
        if obj is None:
            return ""
        eaf_file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.eaffile))
        if os.path.exists(eaf_file_full_path):
            return DT.datetime.fromtimestamp(os.path.getctime(eaf_file_full_path))
        return ""

    def get_list_display_links(self, request, list_display):
        self.list_display_links = (None, )
        return self.list_display_links


class ExampleVideoHistoryAdmin(admin.ModelAdmin):
    list_display = ['action', 'datestamp', 'uploadfile', 'goal_location', 'actor', 'examplesentence']
    search_fields = ['^examplesentence__examplesentencetranslation__text']


admin.site.register(GlossVideo, GlossVideoAdmin)
admin.site.register(GlossVideoHistory, GlossVideoHistoryAdmin)
admin.site.register(AnnotatedVideo, AnnotatedVideoAdmin)
admin.site.register(ExampleVideoHistory, ExampleVideoHistoryAdmin)
