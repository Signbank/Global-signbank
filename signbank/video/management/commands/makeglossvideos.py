from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.conf import settings
from django.db.models.query import QuerySet
from signbank.dictionary.models import Gloss
from signbank.video.models import GlossVideo

import os

from itertools import chain


def parse_range(rng):
    parts = rng.split('-')
    if 1 > len(parts) > 2:
        raise ValueError("Bad range: '%s'" % (rng,))
    parts = [int(i) for i in parts]
    start = parts[0]
    end = start if len(parts) == 1 else parts[1]
    if start > end:
        end, start = start, end
    return range(start, end + 1)


def parse_range_list(rngs):
    return sorted(set(chain(*[parse_range(rng) for rng in rngs.split(',') if rng])))


class Command(BaseCommand):
    help = 'Makes GlossVideos when appropriate and moves videos to correct destination'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry-run',
            default=False,
            help='Make a dry run, i.e. do not make changes to the database or move files.',
        )
        parser.add_argument(
            '--gloss-ids',
            dest='gloss-ids',
            default='',
            help='Specify the gloss IDs [,]',
        )

    def handle(self, *args, **options):
        gloss_ids = parse_range_list(options['gloss-ids'])
        make_gloss_videos(options['dry-run'], gloss_ids)


def get_contructed_video(gloss):
    """Get the video path from idgloss"""

    foldername = gloss.idgloss[:2]
    if len(foldername) == 1:
        foldername += '-'

    constructed_video_path = os.path.join('glossvideo', foldername,
                                          gloss.idgloss + '-' + str(gloss.pk) + '.mp4')
    if hasattr(settings, 'ESCAPE_UPLOADED_VIDEO_FILE_PATH') and settings.ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        from django.utils.encoding import escape_uri_path
        constructed_video_path = escape_uri_path(constructed_video_path)

    constructed_video_exists = os.path.exists(os.path.join(settings.WRITABLE_FOLDER,
                                                           constructed_video_path))
    print("Gloss {} (id: {}): Constructed video path: {}".format(gloss, gloss.id, constructed_video_path))
    if constructed_video_exists:
        print("Gloss {} (id: {}): Constructed video exists".format(gloss, gloss.id, constructed_video_path))

    return constructed_video_path, constructed_video_exists


def get_fields_that_differ(model, obj1, obj2):
    """Returns the fields that differ when comparing two instances of the same model."""
    if type(obj1) == type(obj2):
        field_names = [f.name for f in model._meta.get_fields() if not f.unique]
        fields_that_differ = [f for f in
                              filter(lambda field: getattr(obj1, field, None) != getattr(obj2, field, None), field_names)]
        return fields_that_differ
    else:
        pass  # TODO throw an exception?


def get_glossvideo_path(gloss, dry_run):
    """Get the video path from GlossVideo"""
    glossvideo = None
    glossvideo_video_path = None
    glossvideo_video_exists = None
    try:
        glossvideo = gloss.glossvideo_set.get(version=0)
        glossvideo_video_path = glossvideo.videofile.name
        glossvideo_video_exists = os.path.exists(os.path.join(settings.WRITABLE_FOLDER, glossvideo_video_path))
    except ObjectDoesNotExist:
        pass
    except MultipleObjectsReturned:
        glossvideo_set = GlossVideo.objects.filter(gloss=gloss, version=0).order_by('-id')
        glossvideofile_set = set([gv.videofile.name for gv in glossvideo_set])
        if len(glossvideofile_set) == 1:
            if dry_run:
                print("Gloss {} (id: {}): multiple GlossVideo objects with version 0, all the same"
                      .format(gloss, gloss.pk))
            else:
                glossvideo = glossvideo_set[0]
                glossvideo_video_path = glossvideo.videofile.name
                glossvideo_video_exists = os.path.exists(os.path.join(settings.WRITABLE_FOLDER, glossvideo_video_path))
                glossvideo_set.exclude(id=glossvideo.id).delete()
        else:
            print("Gloss {} (id: {}): multiple GlossVideo objects with version 0"
                  .format(gloss, gloss.pk))
            glossvideo = glossvideo_set

    return glossvideo, glossvideo_video_path, glossvideo_video_exists


def create_new_glossvideo(gloss, video_path, dry_run):
    # Backup the existing video objects stored in the database
    if not dry_run:
        existing_videos = GlossVideo.objects.filter(gloss=gloss)
        for video_object in existing_videos:
            video_object.reversion(revert=False)

    print("Gloss {} (id: {}): creating a new glossvideo.".format(gloss, gloss.id))
    new_glossvideo = GlossVideo(gloss=gloss, videofile=video_path)
    if not dry_run:
        new_glossvideo.save()
        new_glossvideo.move_video()


def make_gloss_videos(dry_run=False, gloss_ids=[]):
    if gloss_ids:
        glosses = Gloss.objects.filter(id__in=gloss_ids)
    else:
        glosses = Gloss.objects.all()
    for gloss in glosses:
        constructed_video_path, constructed_video_exists = get_contructed_video(gloss)
        glossvideo, glossvideo_video_path, glossvideo_video_exists = get_glossvideo_path(gloss, dry_run)

        # Go through all possibilities
        if constructed_video_exists:
            if isinstance(glossvideo, GlossVideo):
                if glossvideo_video_path == constructed_video_path:
                    print("Gloss {} (id: {}): the glossvideo path and constructed path are the same".format(gloss, gloss.id))
                    print("Gloss {} (id: {}): the video file is moved".format(gloss, gloss.id))
                    if not dry_run:
                        glossvideo.move_video()
                else:
                    if glossvideo_video_exists:
                        print("Gloss {} (id: {}): the constructed path ({}) and the glossvideo path ({}) are not "
                              "equal and both refer to an existing file"
                              .format(gloss, gloss.id, constructed_video_path, glossvideo_video_path))
                    else:
                        print("Gloss {} (id: {}): the existing glossvideo gets the constructed path"
                              .format(gloss, gloss.id))
                        glossvideo.videofile.name = constructed_video_path
                        print("Gloss {} (id: {}): the video file is moved".format(gloss, gloss.id))
                        if not dry_run:
                            glossvideo.save()
                            glossvideo.move_video()
            elif isinstance(glossvideo, QuerySet):
                pass  # TODO handle multiple different glossvideos
            else:
                create_new_glossvideo(gloss, constructed_video_path, dry_run=dry_run)
        else:
            if glossvideo:
                if glossvideo_video_exists:
                    print("Gloss {} (id: {}): the video file is moved".format(gloss, gloss.id))
                    if not dry_run:
                        glossvideo.move_video()
                else:
                    if not dry_run:
                        glossvideo.delete()
            elif isinstance(glossvideo, QuerySet):
                pass  # TODO handle multiple different glossvideos
