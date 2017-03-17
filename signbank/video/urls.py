from django.conf.urls import *

import signbank.video.views

urlpatterns = [
    url(r'^video/(?P<videoid>\d+)$', signbank.video.views.video),
    url(r'^upload/', signbank.video.views.addvideo),
    url(r'^delete/(?P<videoid>\d+)$', signbank.video.views.deletevideo),
    url(r'^poster/(?P<videoid>\d+)$', signbank.video.views.poster),
    url(r'^iframe/(?P<videoid>\d+)$', signbank.video.views.iframe),
    url(r'^create_still_images/', signbank.video.views.create_still_images)
    ]