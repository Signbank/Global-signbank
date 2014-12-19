from django.conf.urls import *

urlpatterns = patterns('signbank.pages.views',
    (r'^(?P<url>.*)$', 'page'),
)
