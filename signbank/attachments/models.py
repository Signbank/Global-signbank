from django.db import models
from django.contrib.auth import models as authmodels
from django.conf import settings
from django.utils.translation import gettext_noop, gettext_lazy as _, gettext, activate

import os.path

# Models for file attachments uploaded to the site
# basically just a simple container for files
# but allowing for replacement of previously uploaded files



