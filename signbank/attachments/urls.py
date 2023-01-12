from django.conf.urls import *
from django.urls import re_path, path, include
from signbank.attachments.views import *

urlpatterns = [
    re_path(r'^$', permission_required('attachments.add_attachment') (AttachmentListView.as_view()), name="attachments"),
    re_path(r'^upload/', upload_file),
]

