import os
from itertools import chain
import logging

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.conf import settings
from django.db.models.query import QuerySet
from django.utils.encoding import escape_uri_path

from signbank.dictionary.models import Gloss
from signbank.video.models import GlossVideo


logger = logging.getLogger(__name__)


def parse_range(range_to_parse):
    parts = range_to_parse.split('-')
    if not 1 <= len(parts) <= 2:
        raise ValueError("Bad range: '%s'" % (range_to_parse,))
    parts = [int(i) for i in parts]
    start = parts[0]
    end = start if len(parts) == 1 else parts[1]
    if start > end:
        end, start = start, end
    return range(start, end + 1)


def parse_range_list(ranges):
    return sorted(set(chain(*[parse_range(range) for range in ranges.split(',') if range])))


class Command(BaseCommand):
    help = 'Makes GlossVideos when appropriate and moves videos to correct destination'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('--dry-run', action='store_true', dest='dry-run', default=False,
                            help='Make a dry run, i.e. do not make changes to the database or move files.',)
        parser.add_argument('--gloss-ids', dest='gloss-ids', default='',
                            help='Specify the gloss IDs [,]',)

    def handle(self, *args, **options):
        gloss_ids = parse_range_list(options['gloss-ids'])
        make_gloss_videos(options['dry-run'], gloss_ids)


def get_contructed_video(gloss):
    """Get the video path from idgloss"""
    foldername = gloss.idgloss[:2]
    if len(foldername) == 1:
        foldername += '-'

    constructed_video_path = os.path.join('glossvideo', foldername, gloss.idgloss + '-' + str(gloss.pk) + '.mp4')
    if hasattr(settings, 'ESCAPE_UPLOADED_VIDEO_FILE_PATH') and settings.ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        constructed_video_path = escape_uri_path(constructed_video_path)

    logger.info(f"Gloss {gloss} (id: {gloss.id}): Constructed video path: {constructed_video_path}")
    constructed_video_exists = os.path.exists(os.path.join(settings.WRITABLE_FOLDER, constructed_video_path))
    if constructed_video_exists:
        logger.info(f"Gloss {gloss} (id: {gloss.id}): Constructed video exists")

    return constructed_video_path, constructed_video_exists


def get_glossvideo_path(gloss, dry_run):
    """Get the video path from GlossVideo"""
    try:
        glossvideo = gloss.glossvideo_set.get(version=0)
        glossvideo_video_path = glossvideo.videofile.name
        glossvideo_video_exists = os.path.exists(os.path.join(settings.WRITABLE_FOLDER, glossvideo_video_path))
        return glossvideo, glossvideo_video_path, glossvideo_video_exists
    except ObjectDoesNotExist:
        return None, None, None
    except MultipleObjectsReturned:
        return get_path_for_multiple_glossvideos(gloss, dry_run)


def get_path_for_multiple_glossvideos(gloss, dry_run, glossvideo=None, glossvideo_video_path=None,
                                      glossvideo_video_exists=None):
    glossvideo_set = GlossVideo.objects.filter(gloss=gloss, version=0).order_by('-id')
    glossvideofile_set = {gloss_video.videofile.name for gloss_video in glossvideo_set}
    if len(glossvideofile_set) != 1:
        logger.info(f"Gloss {gloss} (id: {gloss.pk}): multiple GlossVideo objects with version 0")
        glossvideo = glossvideo_set
        return glossvideo, glossvideo_video_path, glossvideo_video_exists
    if dry_run:
        logger.info(f"Gloss {gloss} (id: {gloss.pk}): multiple GlossVideo objects with version 0, all the same")
        return glossvideo, glossvideo_video_path, glossvideo_video_exists
    glossvideo = glossvideo_set[0]
    glossvideo_video_path = glossvideo.videofile.name
    glossvideo_video_exists = os.path.exists(os.path.join(settings.WRITABLE_FOLDER, glossvideo_video_path))
    glossvideo_set.exclude(id=glossvideo.id).delete()
    return glossvideo, glossvideo_video_path, glossvideo_video_exists


def create_new_glossvideo(gloss, video_path, dry_run):
    # Backup the existing video objects stored in the database
    if not dry_run:
        for video_object in GlossVideo.objects.filter(gloss=gloss):
            video_object.reversion(revert=False)

    logger.info(f"Gloss {gloss} (id: {gloss.id}): creating a new glossvideo.")
    new_glossvideo = GlossVideo(gloss=gloss, videofile=video_path)
    if not dry_run:
        new_glossvideo.save()
        new_glossvideo.move_video()


def make_gloss_videos(dry_run=False, gloss_ids=None):
    for gloss in Gloss.objects.filter(id__in=gloss_ids or []) if gloss_ids else Gloss.objects.all():
        constructed_video_path, constructed_video_exists = get_contructed_video(gloss)
        glossvideo, glossvideo_video_path, glossvideo_video_exists = get_glossvideo_path(gloss, dry_run)

        if not constructed_video_exists:
            if isinstance(glossvideo, QuerySet):
                pass  # TODO handle multiple different glossvideos
            elif glossvideo and not glossvideo_video_exists:
                glossvideo.delete() if not dry_run else None
            elif glossvideo:
                logger.info(f"Gloss {gloss} (id: {gloss.id}): the video file is moved")
                glossvideo.move_video() if not dry_run else None

        elif not isinstance(glossvideo, GlossVideo):
            if isinstance(glossvideo, QuerySet):
                pass  # TODO handle multiple different glossvideos
            else:
                create_new_glossvideo(gloss, constructed_video_path, dry_run=dry_run)

        elif glossvideo_video_path == constructed_video_path:
            logger.info(f"Gloss {gloss} (id: {gloss.id}): the glossvideo path and constructed path are the same")
            logger.info("Gloss {gloss} (id: {gloss.id}): the video file is moved")
            glossvideo.move_video() if not dry_run else None

        elif glossvideo_video_exists:
            logger.info(f"Gloss {gloss} (id: {gloss.id}): the constructed path ({constructed_video_path}) "
                        f"and the glossvideo path ({glossvideo_video_path}) are not equal and both refer "
                        f"to an existing file")

        else:
            logger.info(f"Gloss {gloss} (id: {gloss.id}): the existing glossvideo gets the constructed path")
            glossvideo.videofile.name = constructed_video_path
            logger.info(f"Gloss {gloss} (id: {gloss.id}): the video file is moved")
            glossvideo.save() if not dry_run else None
            glossvideo.move_video() if not dry_run else None
