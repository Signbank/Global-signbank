""" Models for the animation application
keep track of uploaded animation files and converted versions
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
from pyfbx import Fbx


if sys.argv[0] == 'mod_wsgi':
    from signbank.dictionary.models import *
else:
    from signbank.dictionary.models import Gloss, Language


def get_two_letter_dir(idgloss):
    foldername = idgloss[:2]

    if len(foldername) == 1:
        foldername += '-'

    return foldername

class AnimationStorage(FileSystemStorage):
    """Implement our shadowing animation storage system"""

    def __init__(self, location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL):
        super(AnimationStorage, self).__init__(location, base_url)

    def get_valid_name(self, name):
        return name


storage = AnimationStorage()

# The 'action' choices are used in the GlossVideoHistory class
ACTION_CHOICES = (('delete', 'delete'),
                  ('upload', 'upload'),
                  ('rename', 'rename'),
                  ('watch', 'watch'),
                  ('import', 'import'),
                  )


def validate_file_extension(value):
    if value.file.content_type not in ['application/octet-stream']:
        raise ValidationError(u'Error message')


def get_animation_file_path(instance, filename):
    """
    Return the full path for storing an uploaded animation
    :param instance: A GlossAnimation instance
    :param filename: the original file name
    :return:
    """
    (base, ext) = os.path.splitext(filename)

    idgloss = instance.gloss.idgloss

    animation_dir = settings.ANIMATION_DIRECTORY
    try:
        dataset_dir = instance.gloss.lemma.dataset.acronym
    except KeyError:
        dataset_dir = ""

    two_letter_dir = get_two_letter_dir(idgloss)
    filename = idgloss + '-' + str(instance.gloss.id) + ext
    path = os.path.join(animation_dir, dataset_dir, two_letter_dir, filename)
    if hasattr(settings, 'ESCAPE_UPLOADED_VIDEO_FILE_PATH') and settings.ESCAPE_UPLOADED_VIDEO_FILE_PATH:
        from django.utils.encoding import escape_uri_path
        path = escape_uri_path(path)
    return path


class GlossAnimation(models.Model):
    """A video that represents a particular idgloss"""

    fbxfile = models.FileField("FBX file", storage=storage,
                                 validators=[validate_file_extension])

    gloss = models.ForeignKey(Gloss, on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        if 'upload_to' in kwargs:
            self.upload_to = kwargs.pop('upload_to')
        else:
            self.upload_to = get_animation_file_path
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):

        super(GlossAnimation, self).save(*args, **kwargs)

    def get_absolute_url(self):

        return self.fbxfile.name


class GlossAnimationHistory(models.Model):
    """History of video uploading and deletion"""

    action = models.CharField("Animation History Action", max_length=6, choices=ACTION_CHOICES, default='watch')
    # When was this action done?
    datestamp = models.DateTimeField("Date and time of action", auto_now_add=True)
    # See 'fbxfile' in animation.views.addanimation
    uploadfile = models.TextField("User upload path", default='(not specified)')
    # See 'goal_location' in addanimation
    goal_location = models.TextField("Full target path", default='(not specified)')

    # WAS: Many-to-many link: to the user that has uploaded or deleted this video
    # WAS: actor = models.ManyToManyField("", User)
    # The user that has uploaded or deleted this video
    actor = models.ForeignKey(authmodels.User, on_delete=models.CASCADE)

    # One-to-many link: to the Gloss in dictionary.models.Gloss
    gloss = models.ForeignKey(Gloss, on_delete=models.CASCADE)

    def __str__(self):

        # Basic feedback from one History item: gloss-action-date
        name = self.gloss.idgloss + ': ' + self.action + ', (' + str(self.datestamp) + ')'
        return str(name.encode('ascii', errors='replace'))

    class Meta:
        ordering = ['datestamp']
