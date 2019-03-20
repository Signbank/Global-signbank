from django.conf.urls import *
from signbank.attachments.views import *

urlpatterns = [
    
    url(r'^$', permission_required('attachments.add_attachment') (AttachmentListView.as_view()), name="attachments"),
    url(r'^upload/', upload_file),
]

