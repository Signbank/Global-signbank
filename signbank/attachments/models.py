from django.db import models
from django.contrib.auth import models as authmodels
from django.conf import settings
import os.path

# Models for file attachments uploaded to the site
# basically just a simple container for files
# but allowing for replacement of previously uploaded files

class Attachment(models.Model):

    file = models.FileField(upload_to=settings.ATTACHMENT_LOCATION)
    description = models.TextField(blank=True)
    date = models.DateField(auto_now=True)
    uploader = models.ForeignKey(authmodels.User)

