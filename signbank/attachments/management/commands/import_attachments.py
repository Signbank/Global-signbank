"""Import files as attachment objects"""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from signbank.attachments.models import Attachment
from django.conf import settings
from django.contrib.auth.models import User
import os

class Command(BaseCommand):

    help = 'import any files in the attachments folder that we don\'t already have'
    args = '<username>'

    def handle(self, *args, **options):

        if len(args) != 1:
            print "Usage: import_attachments", self.args
            return
        try:
            user = args[0]
            user = User.objects.get(username=user)
        except:
            print "unknown user", user
            return

        dirname = os.path.join(settings.MEDIA_ROOT, settings.ATTACHMENT_LOCATION)
        for f in os.listdir(dirname):
            if not os.path.isdir(f):
                path = os.path.join(settings.ATTACHMENT_LOCATION, f)
                existing = Attachment.objects.filter(file=path)
                if len(existing) == 0:
                    a = Attachment(file=path, uploader=user, description=f)
                    a.save()
                    print "storing ", path
                else:
                    print "not storing ", path
