from django.conf.urls import *
from signbank.dictionary.models import *
from django.contrib.auth.decorators import login_required, permission_required

import signbank.feedback.views

urlpatterns = [
    url(r'^$', signbank.feedback.views.index),

    url(r'^missing/$', login_required(signbank.feedback.views.missingsign)),
    url(r'^site/$', signbank.feedback.views.generalfeedback),

    url(r'^gloss/(?P<glossid>\d+)/$',  signbank.feedback.views.glossfeedback),
    url(r'^morpheme/(?P<glossid>\d+)/$', signbank.feedback.views.morphemefeedback),

    url(r'^(?P<kind>general|sign|morpheme|missingsign)/delete/(?P<id>\d+)$', signbank.feedback.views.delete),
]


