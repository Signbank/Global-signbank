from django.db import models
from django.contrib.auth import models as authmodels
from django.conf import settings
from django.utils.translation import gettext_noop, gettext_lazy as _, gettext, activate

import os.path

# Models for file attachments uploaded to the site
# basically just a simple container for files
# but allowing for replacement of previously uploaded files

class Attachment(models.Model):

    file = models.FileField(upload_to=settings.ATTACHMENT_LOCATION)
    description = models.TextField(blank=True)
    date = models.DateField(auto_now=True)
    uploader = models.ForeignKey(authmodels.User, on_delete=models.CASCADE)

    def get_absolute_url(self):

        return self.file.url

    def get_filename(self):

        return self.file.name

    def __str__(self):
        return self.file.name


class Communication(models.Model):
    label = models.CharField(_("Description of type of communication"), max_length=50, help_text="""Label without spaces""")
    subject = models.TextField(_("Site communication subject"), help_text="""The communication text.""")
    text = models.TextField(_("Site communication text"), help_text="""The communication text.""")

    class Meta:
        app_label = 'attachments'

