
from django.contrib import admin
from signbank.video.models import (GlossVideo, GlossVideoHistory, AnnotatedVideo, ExampleVideoHistory,
                                   build_filename)
from signbank.dictionary.models import Dataset, AnnotatedGloss, Gloss
from django.contrib.auth.models import User
from signbank.settings.base import *
from signbank.settings.server_specific import WRITABLE_FOLDER, FILESYSTEM_SIGNBANK_GROUPS, DEBUG_VIDEOS, DELETED_FILES_FOLDER
from django.utils.translation import gettext_lazy as _
from signbank.tools import get_two_letter_dir
from signbank.video.convertvideo import video_file_type_extension, convert_video
from signbank.video.operations import (filename_matches_nme, filename_matches_perspective,
                                       filename_matches_video, filename_matches_backup_video, flattened_video_path)
from pathlib import Path
import os
import stat
import shutil
import datetime as DT


class GlossVideoDatasetFilter(admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on the Dataset of the gloss
    The values of lookups show in the right-hand column of the admin under a heading "Dataset"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('Dataset')
    parameter_name = 'videos_per_dataset'

    def lookups(self, request, model_admin):
        datasets = Dataset.objects.all()
        return (tuple(
            (dataset.pk, dataset.acronym) for dataset in datasets
        ))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gloss__lemma__dataset_id=self.value())
        return queryset.all()


class GlossVideoFileSystemGroupFilter(admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on the file system group of the video file
    The values of lookups show in the right-hand column of the admin under a heading "File System Group"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('File System Group')
    parameter_name = 'filesystem_group'

    def lookups(self, request, model_admin):
        filesystem_groups = tuple((g, g) for g in FILESYSTEM_SIGNBANK_GROUPS)
        return filesystem_groups

    def queryset(self, request, queryset):

        def matching_file_group(videofile, key):
            if not key:
                return False
            video_file_full_path = Path(WRITABLE_FOLDER, videofile)
            if not video_file_full_path.exists():
                return False
            return video_file_full_path.group() == key

        queryset_res = queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file_group(qv['videofile'], self.value())]

        if self.value():
            return queryset.filter(id__in=results)
        else:
            return queryset.all()


class GlossVideoExistenceFilter(admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on whether the video file exists
    The values of lookups show in the right-hand column of the admin under a heading "File Exists"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('File Exists')
    parameter_name = 'file_exists'

    def lookups(self, request, model_admin):
        file_exists = tuple((b, b) for b in ('True', 'False'))
        return file_exists

    def queryset(self, request, queryset):

        def matching_file_exists(videofile, key):
            if not key:
                return False
            if 'glossvideo' not in videofile:
                return False
            video_file_full_path = Path(WRITABLE_FOLDER, videofile)
            if video_file_full_path.exists():
                return key == 'True'
            else:
                return key == 'False'

        queryset_res = queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file_exists(qv['videofile'], self.value())]
        if self.value():
            return queryset.filter(id__in=results)
        else:
            return queryset.all()


class GlossVideoFilenameFilter(admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on whether the filename is correct for the type of video
    The values of lookups show in the right-hand column of the admin under a heading "Filename Correct"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('Filename Correct')
    parameter_name = 'filename_correct'

    def lookups(self, request, model_admin):
        file_exists = tuple((b, b) for b in ('True', 'False'))
        return file_exists

    def queryset(self, request, queryset):

        def matching_filename(videofile, nmevideo, perspective, version, key):
            if not key:
                return False
            video_file_full_path = Path(WRITABLE_FOLDER, videofile)
            if nmevideo:
                filename_is_correct = filename_matches_nme(video_file_full_path) is not None
                return key == str(filename_is_correct)
            elif perspective:
                filename_is_correct = filename_matches_perspective(video_file_full_path) is not None
                return key == str(filename_is_correct)
            elif version > 0:
                filename_is_correct = filename_matches_backup_video(video_file_full_path) is not None
                return key == str(filename_is_correct)
            else:
                filename_is_correct = filename_matches_video(video_file_full_path) is not None
                return key == str(filename_is_correct)

        queryset_res = queryset.values('id', 'videofile', 'glossvideonme', 'glossvideoperspective', 'version')
        results = [qv['id'] for qv in queryset_res
                   if matching_filename(qv['videofile'],
                                        qv['glossvideonme'],
                                        qv['glossvideoperspective'], qv['version'], self.value())]

        if self.value():
            return queryset.filter(id__in=results)
        else:
            return queryset.all()


class GlossVideoNMEFilter(admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on whether the video is an NME Video
    The values of lookups show in the right-hand column of the admin under a heading "NME Video"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('NME Video')
    parameter_name = 'nme_videos'

    def lookups(self, request, model_admin):
        nme_video = tuple((b, b) for b in ('True', 'False'))
        return nme_video

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == 'True':
                return queryset.filter(glossvideonme__isnull=False)
            else:
                return queryset.filter(glossvideonme__isnull=True)
        return queryset.all()


class GlossVideoPerspectiveFilter(admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on whether the video is a Perspective Video
    The values of lookups show in the right-hand column of the admin under a heading "Perspective Video"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('Perspective Video')
    parameter_name = 'perspective_videos'

    def lookups(self, request, model_admin):
        perspective_video = tuple((b, b) for b in ('True', 'False'))
        return perspective_video

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == 'True':
                return queryset.filter(glossvideoperspective__isnull=False)
            else:
                return queryset.filter(glossvideoperspective__isnull=True)
        return queryset.all()


class GlossVideoFileTypeFilter(admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on whether the video is an MP4 video
    The values of lookups show in the right-hand column of the admin under a heading "MP4 File"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('MP4 File')
    parameter_name = 'file_type'

    def lookups(self, request, model_admin):
        file_type = tuple((b, b) for b in ('True', 'False'))
        return file_type

    def queryset(self, request, queryset):

        def matching_file_type(videofile, key):
            if not key:
                return False
            video_file_full_path = Path(WRITABLE_FOLDER, videofile)
            file_extension = video_file_type_extension(video_file_full_path)
            has_mp4_type = file_extension == '.mp4'
            return key == str(has_mp4_type)

        queryset_res = queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file_type(qv['videofile'], self.value())]

        if self.value():
            return queryset.filter(id__in=results)
        else:
            return queryset.all()


class GlossVideoWebmTypeFilter(admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on whether the video is a Webm video
    The values of lookups show in the right-hand column of the admin under a heading "Webm File"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('Webm File')
    parameter_name = 'webm_file_type'

    def lookups(self, request, model_admin):
        file_type = tuple((b, b) for b in ('True', 'False'))
        return file_type

    def queryset(self, request, queryset):

        def matching_file_type(videofile, key):
            if not key:
                return False
            video_file_full_path = Path(WRITABLE_FOLDER, videofile)
            file_extension = video_file_type_extension(video_file_full_path)
            has_webm_type = file_extension == '.webm'
            return key == str(has_webm_type)

        queryset_res = queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file_type(qv['videofile'], self.value())]

        if self.value():
            return queryset.filter(id__in=results)
        else:
            return queryset.all()


class GlossVideoBackupFilter(admin.SimpleListFilter):
    """
    Filter the GlossVideo objects on whether the video is a backup video
    The values of lookups show in the right-hand column of the admin under a heading "Backup Video"
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    title = _('Backup Video')
    parameter_name = 'backup_videos'

    def lookups(self, request, model_admin):
        is_backup = tuple((b, b) for b in ('True', 'False'))
        return is_backup

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == 'True':
                return queryset.filter(version__gt=0)
            else:
                return queryset.filter(version=0)
        return queryset.all()


@admin.action(description="Rename normal video files to match type")
def rename_extension_videos(modeladmin, request, queryset):
    """
    Command for the GlossVideo objects selected in queryset
    The command appears in the admin pull-down list of commands for the selected gloss videos
    The command determines which glosses are selected, then retrieves the normal video objects for those glosses
    This allows the user to merely select one of the objects and hereby change them all instead of numerous selections
    For those gloss video objects, it renames the file if the filename is not correct
    This also applies to wrong video types in filenames, e.g., a webm video that has mp4 in its filename
    This applies to back-up videos as well as normal videos
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    # retrieve glosses of selected GlossVideo objects
    distinct_glosses = Gloss.objects.filter(glossvideo__in=queryset).distinct()

    for gloss in distinct_glosses:
        for glossvideo in GlossVideo.objects.filter(gloss=gloss, glossvideonme=None, glossvideoperspective=None).order_by('version', 'id'):
            current_relative_path = str(glossvideo.videofile)
            if not current_relative_path:
                # make sure the path is not empty
                continue

            video_file_full_path = os.path.join(WRITABLE_FOLDER, current_relative_path)

            # use the file system command 'file' to determine the extension for the type of video file
            desired_video_extension = video_file_type_extension(video_file_full_path)
            if not desired_video_extension:
                continue

            # compare the stored filename to the name it should have
            base_filename = os.path.basename(video_file_full_path)

            idgloss = gloss.idgloss
            two_letter_dir = get_two_letter_dir(idgloss)
            dataset_dir = gloss.lemma.dataset.acronym
            desired_filename_without_extension = f'{idgloss}-{gloss.id}'

            if glossvideo.version > 0:
                desired_extension = f'{desired_video_extension}.bak{glossvideo.id}'
            else:
                desired_extension = desired_video_extension

            desired_filename = desired_filename_without_extension + desired_extension
            if base_filename == desired_filename:
                continue

            # if we get to here, the file has the wrong filename
            source = os.path.join(WRITABLE_FOLDER, current_relative_path)
            destination = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY,
                                       dataset_dir, two_letter_dir, desired_filename)
            desired_relative_path = os.path.join(GLOSS_VIDEO_DIRECTORY,
                                                 dataset_dir, two_letter_dir, desired_filename)
            if DEBUG_VIDEOS:
                print('video:admin:rename_extension_videos:os.rename: ', source, destination)
            if os.path.exists(video_file_full_path):
                os.rename(source, destination)
            if DEBUG_VIDEOS:
                print('video:admin:rename_extension_videos:videofile.name := ', desired_relative_path)
            glossvideo.videofile.name = desired_relative_path
            glossvideo.save()


@admin.action(description="Move selected backup files to trash")
def remove_backups(modeladmin, request, queryset):
    """
    Command for the GlossVideo objects selected in queryset
    The command appears in the admin pull-down list of commands for the selected gloss videos
    The command moves the selected backup files to the DELETED_FILES_FOLDER location
    To prevent the gloss video object from pointing to the deleted files folder location
    the name stored in the object is set to empty before deleting the object
    Other selected objects are ignored
    This allows the user to keep a number of the backup files by not selecting everything
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    # make sure the queryset only applies to backups for normal videos
    for obj in queryset.filter(glossvideonme=None, glossvideoperspective=None, version__gt=0):
        relative_path = str(obj.videofile)
        if not relative_path:
            continue
        video_file_full_path = os.path.join(WRITABLE_FOLDER, relative_path)
        if not os.path.exists(video_file_full_path):
            if DEBUG_VIDEOS:
                print('video:admin:remove_backups:delete object: ', relative_path)
            obj.delete()
            continue

        # move the video file to DELETED_FILES_FOLDER and erase the name to avoid the signals on GlossVideo delete
        deleted_file_name = flattened_video_path(relative_path)
        destination = os.path.join(WRITABLE_FOLDER, DELETED_FILES_FOLDER, deleted_file_name)
        destination_dir = os.path.dirname(destination)
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        if os.path.isdir(destination_dir):
            try:
                obj.videofile.name = ""
                obj.save()
                shutil.move(video_file_full_path, destination)
                if DEBUG_VIDEOS:
                    print('video:admin:remove_backups:shutil.move: ', video_file_full_path, destination)
            except (OSError, PermissionError) as e:
                print(e)
                continue
        # the object does not point to anything anymore, so it can be deleted
        if DEBUG_VIDEOS:
            print('video:admin:remove_backups:delete object: ', relative_path)
        obj.delete()


@admin.action(description="Renumber selected backups")
def renumber_backups(modeladmin, request, queryset):
    """
    Command for the GlossVideo objects selected in queryset
    The command appears in the admin pull-down list of commands for the selected gloss videos
    The command renumbers the backup video objects for the GlossVideo queryset
    The command determines which glosses are selected, then retrieves the backup video objects for those glosses
    This allows the user to merely select one of the objects and hereby renumber them all
    Because the backup objects are numbered by version, all of the objects must be renumbered
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    # retrieve glosses of selected GlossVideo objects
    distinct_glosses = Gloss.objects.filter(glossvideo__in=queryset).distinct()
    # construct data structure for glosses and backup videos including those that are not selected
    lookup_backup_files = dict()
    for gloss in distinct_glosses:
        lookup_backup_files[gloss] = GlossVideo.objects.filter(gloss=gloss,
                                                               glossvideonme=None,
                                                               glossvideoperspective=None,
                                                               version__gt=0).order_by('version', 'id')
    for gloss, videos in lookup_backup_files.items():
        # enumerate over the backup videos and give them new version numbers
        for inx, video in enumerate(videos, 1):
            if inx == video.version:
                continue
            video.version = inx
            video.save()


@admin.action(description="Set incorrect NME/Perspective filenames to empty string")
def unlink_files(modeladmin, request, queryset):
    """
    Command for the GlossVideo objects selected in queryset
    The command appears in the admin pull-down list of commands for the selected gloss videos
    The command only applies to Perspective and NME videos, other selected videos are ignored.
    Allow to erase the filename from an object if it has the wrong format
    This is for the purpose of repairing doubly linked files where the subclass object points to the normal video
    Once the filename has been cleared, the user can delete the object as normal with the Admin delete command
    This prevents a normal video linked to by a subclass video from being deleted
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    for obj in queryset:
        if not hasattr(obj, 'glossvideonme') and not hasattr(obj, 'glossvideoperspective'):
            # the selected gloss video is not a subclass video
            continue
        relative_path = str(obj.videofile)
        if not relative_path:
            continue
        video_file_full_path = Path(WRITABLE_FOLDER, relative_path)
        # ignore the files that have the correct filename
        if hasattr(obj, 'glossvideonme') and filename_matches_nme(video_file_full_path):
            continue
        if hasattr(obj, 'glossvideoperspective') and filename_matches_perspective(video_file_full_path):
            continue

        if DEBUG_VIDEOS:
            print('unlink_files: erase incorrect path from NME or Perspective object: ', obj, video_file_full_path)
        obj.videofile.name = ""
        obj.save()


@admin.action(description="Convert non-mp4 video files to mp4")
def convert_non_mp4_videos(modeladmin, request, queryset):
    """
    Command for the GlossVideo objects selected in queryset
    The command appears in the admin pull-down list of commands for the selected gloss videos
    The command determines which glosses are selected, then retrieves the normal video objects for those glosses
    This allows the user to merely select one of the objects and hereby change them all instead of numerous selections
    For those gloss video objects, it converts the file if the format is not mp4.
    Called from GlossVideoAdmin
    :model: GlossVideoAdmin
    """
    # retrieve glosses of selected GlossVideo objects
    distinct_glosses = Gloss.objects.filter(glossvideo__in=queryset).distinct()

    for gloss in distinct_glosses:
        for glossvideo in GlossVideo.objects.filter(gloss=gloss, glossvideonme=None, glossvideoperspective=None).order_by('version', 'id'):
            current_relative_path = str(glossvideo.videofile)
            if not current_relative_path:
                # make sure the path is not empty
                continue

            video_file_full_path = os.path.join(WRITABLE_FOLDER, current_relative_path)

            # use the file system command 'file' to determine the extension for the type of video file
            desired_video_extension = video_file_type_extension(video_file_full_path)
            if not desired_video_extension:
                continue

            (two_letter_dir, dataset_dir,
             desired_filename_including_extension) = build_filename(gloss, glossvideo, desired_video_extension, include_dirs=True)

            # compare the stored filename to the name it should have
            base_filename_including_extension = os.path.basename(video_file_full_path)

            if base_filename_including_extension != desired_filename_including_extension:
                # the file has the wrong filename, the file may be a backup file that includes a video extension
                source = os.path.join(WRITABLE_FOLDER, current_relative_path)
                destination = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY,
                                           dataset_dir, two_letter_dir, desired_filename_including_extension)
                desired_relative_path = os.path.join(GLOSS_VIDEO_DIRECTORY,
                                                     dataset_dir, two_letter_dir, desired_filename_including_extension)
                if DEBUG_VIDEOS:
                    print('video:admin:convert_non_mp4_videos:os.rename: ', source, destination)
                if os.path.exists(video_file_full_path):
                    os.rename(source, destination)
                if DEBUG_VIDEOS:
                    print('video:admin:convert_non_mp4_videos:videofile.name := ', desired_relative_path)
                glossvideo.videofile.name = desired_relative_path
                glossvideo.save()

            if desired_video_extension == '.mp4':
                # this is tested after a possible renaming of a backup video file in the above step
                continue

            if glossvideo.version > 0:
                # the video is not converted by ensure_mp4 if it is a backup, refetch the path after possible renaming
                current_relative_path = str(glossvideo.videofile)
                flipped_source_filename = build_filename(gloss, glossvideo, desired_video_extension, flipped=True)
                flipped_source = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY,
                                              dataset_dir, two_letter_dir, flipped_source_filename)
                source = os.path.join(WRITABLE_FOLDER, current_relative_path)
                desired_filename = build_filename(gloss, glossvideo, '.mp4')
                flipped_destination_filename = build_filename(gloss, glossvideo, '.mp4', flipped=True)
                flipped_destination = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY,
                                           dataset_dir, two_letter_dir, flipped_destination_filename)
                destination = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY,
                                           dataset_dir, two_letter_dir, desired_filename)
                desired_relative_path = os.path.join(GLOSS_VIDEO_DIRECTORY,
                                                     dataset_dir, two_letter_dir, desired_filename)
                if not os.path.exists(source):
                    continue
                if DEBUG_VIDEOS:
                    print('video:admin:convert_non_mp4_videos:os.rename: ', source, flipped_source)
                os.rename(source, flipped_source)
                okay = convert_video(flipped_source, flipped_destination)
                if DEBUG_VIDEOS:
                    print('video:admin:convert_non_mp4_videos:convert_video: ', flipped_source, flipped_destination)
                if not okay or not os.path.exists(flipped_destination):
                    continue
                if DEBUG_VIDEOS:
                    print('video:admin:convert_non_mp4_videos:os.rename: ', flipped_destination, desired_relative_path)
                    print('video:admin:convert_non_mp4_videos:videofile.name := ', desired_relative_path)
                os.rename(flipped_destination, destination)
                glossvideo.videofile.name = desired_relative_path
                glossvideo.save()
                os.rename(flipped_source, source)

            # move the original video file to DELETED_FILES_FOLDER, it is not referenced anymore by the GlossVideo object
            original_with_correct_extension = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY,
                                       dataset_dir, two_letter_dir, desired_filename_including_extension)
            original_relative_path = os.path.join(GLOSS_VIDEO_DIRECTORY,
                                                 dataset_dir, two_letter_dir, desired_filename_including_extension)
            deleted_file_name = flattened_video_path(original_relative_path)
            deleted_destination = os.path.join(WRITABLE_FOLDER, DELETED_FILES_FOLDER, deleted_file_name)
            destination_dir = os.path.dirname(original_with_correct_extension)
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
            try:
                shutil.move(str(original_with_correct_extension), str(deleted_destination))
                if DEBUG_VIDEOS:
                    print('video:admin:convert_non_mp4_videos:shutil.move: ', original_with_correct_extension, deleted_destination)
            except (OSError, PermissionError) as e:
                print(e)


class GlossVideoAdmin(admin.ModelAdmin):

    list_display = ['id', 'gloss', 'video_file', 'perspective', 'NME', 'file_timestamp', 'file_group', 'permissions', 'file_size', 'video_type',  'version']
    list_filter = (GlossVideoDatasetFilter, GlossVideoFileSystemGroupFilter, GlossVideoExistenceFilter,
                   GlossVideoFileTypeFilter, GlossVideoWebmTypeFilter, GlossVideoNMEFilter, GlossVideoPerspectiveFilter,
                   GlossVideoFilenameFilter, GlossVideoBackupFilter)

    search_fields = ['^gloss__annotationidglosstranslation__text', '^gloss__lemma__lemmaidglosstranslation__text']
    actions = [rename_extension_videos, remove_backups, renumber_backups, unlink_files, convert_non_mp4_videos]

    def video_file(self, obj=None):
        """
        column VIDEO FILE
        this will display the full path in the list view, also for non-existent files
        this allows to browse the file paths also on the development servers
        """
        if obj is None or not str(obj.videofile):
            return ""
        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.videofile))

        return video_file_full_path

    def perspective(self, obj=None):
        """
        column PERSPECTIVE
        This will be True if the object is of subclass GlossVideoPerspective
        """
        if obj is None:
            return ""
        return obj.is_glossvideoperspective() is True

    def NME(self, obj=None):
        """
        column NME
        This will be True if the object is of subclass GlossVideoNME
        """
        if obj is None:
            return ""
        return obj.is_glossvideonme() is True

    def file_timestamp(self, obj=None):
        """
        column FILE TIMESTAMP
        if the file exists, this will display its timestamp in the list view
        """
        if obj is None or not str(obj.videofile):
            return ""
        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.videofile))
        if not os.path.exists(video_file_full_path):
            return ""
        return DT.datetime.fromtimestamp(os.path.getctime(video_file_full_path))

    def file_group(self, obj=None):
        """
        column FILE GROUP
        if the file exists, this will display the file system group in the list view
        """
        if obj is None or not str(obj.videofile):
            return ""
        video_file_full_path = Path(WRITABLE_FOLDER, str(obj.videofile))
        if not video_file_full_path.exists():
            return ""
        group = video_file_full_path.group()
        return group

    def file_size(self, obj=None):
        """
        column FILE SIZE
        if the file exists, this will display the file size in the list view
        """
        if obj is None or not str(obj.videofile):
            return ""
        video_file_full_path = Path(WRITABLE_FOLDER, str(obj.videofile))
        if not video_file_full_path.exists():
            return ""
        size = str(video_file_full_path.stat().st_size)
        return size

    def permissions(self, obj=None):
        """
        column PERMISSIONS
        if the file exists, this will display the file system permissions in the list view
        """
        if obj is None or not str(obj.videofile):
            return ""
        video_file_full_path = Path(WRITABLE_FOLDER, str(obj.videofile))
        if not video_file_full_path.exists():
            return ""
        stats = stat.filemode(video_file_full_path.stat().st_mode)
        return stats

    def video_type(self, obj=None):
        """
        column VIDEO TYPE
        if the file exists, this will display the video type in file extension format
        """
        if obj is None or not str(obj.videofile):
            return ""
        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.videofile))
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
        datasets = Dataset.objects.all()
        return (tuple(
            (dataset.id, dataset.acronym) for dataset in datasets
        ))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gloss__lemma__dataset_id=self.value())
        return queryset.all()


class GlossVideoHistoryActorFilter(admin.SimpleListFilter):

    title = _('Actor')
    parameter_name = 'videos_per_actor'

    def lookups(self, request, model_admin):
        users = User.objects.all().distinct().order_by('first_name')
        return (tuple(
            (user.id, user.username) for user in users
        ))

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
        datasets = Dataset.objects.all()
        return (tuple(
            (dataset.id, dataset.acronym) for dataset in datasets
        ))

    def queryset(self, request, queryset):
        if self.value():
            annotated_glosses = AnnotatedGloss.objects.filter(gloss__lemma__dataset_id=self.value())
            annotated_sentences_ids = [ag.annotatedsentence.id for ag in annotated_glosses]
            if not annotated_sentences_ids:
                return None
            return queryset.filter(annotatedsentence_id__in=annotated_sentences_ids)
        return queryset.all()


class AnnotatedVideoAdmin(admin.ModelAdmin):
    actions = None
    list_display = ('dataset', 'annotated_sentence', 'video_file', 'timestamp', 'eaf_file', 'eaf_timestamp', 'url', 'source')
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
        dataset = annotated_glosses.first().gloss.lemma.dataset
        return dataset.acronym

    def annotated_sentence(self, obj=None):
        if obj is None:
            return ""
        translations = obj.annotatedsentence.get_annotatedstc_translations()
        return " | ".join(translations)

    def video_file(self, obj=None):
        if obj is None:
            return ""

        return str(obj.videofile.name)

    def timestamp(self, obj=None):
        # if the file exists, this will display its timestamp in the list view
        if obj is None:
            return ""
        video_file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.videofile))
        if os.path.exists(video_file_full_path):
            return DT.datetime.fromtimestamp(os.path.getctime(video_file_full_path))
        else:
            return ""

    def eaf_file(self, obj=None):
        if obj is None:
            return ""
        return str(obj.eaffile.name)

    def eaf_timestamp(self, obj=None):
        # if the file exists, this will display its timestamp in the list view
        if obj is None:
            return ""
        eaf_file_full_path = os.path.join(WRITABLE_FOLDER, str(obj.eaffile))
        if os.path.exists(eaf_file_full_path):
            return DT.datetime.fromtimestamp(os.path.getctime(eaf_file_full_path))
        else:
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

