from django.conf.urls import *
from django.contrib.auth.decorators import permission_required
from django.urls import re_path, path, include

import signbank.video.views

urlpatterns = [
    re_path(r'^video/(?P<videoid>\d+)$', signbank.video.views.video),
    re_path(r'^upload/', signbank.video.views.addvideo),
    re_path(r'^uploadsentencevideo/', signbank.video.views.addsentencevideo),
    re_path(r'^delete/(?P<videoid>\d+)$', signbank.video.views.deletevideo),
    re_path(r'^create_still_images/', permission_required('dictionary.change_gloss')(signbank.video.views.create_still_images))
    ]