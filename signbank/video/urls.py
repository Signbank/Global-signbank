from django.conf.urls import *

urlpatterns = patterns('',
    
    (r'^video/(?P<videoid>\d+)$', 'signbank.video.views.video'),
    (r'^upload/', 'signbank.video.views.addvideo'),
    (r'^delete/(?P<videoid>\d+)$', 'signbank.video.views.deletevideo'),
    (r'^poster/(?P<videoid>\d+)$', 'signbank.video.views.poster'),
    (r'^iframe/(?P<videoid>\d+)$', 'signbank.video.views.iframe'),
)


