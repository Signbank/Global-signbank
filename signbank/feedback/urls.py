from django.conf.urls import *
from signbank.dictionary.models import *
from django.contrib.auth.decorators import login_required, permission_required

import signbank.feedback.views

urlpatterns = [
    url(r'^$', signbank.feedback.views.index),

    url(r'^missing/$', login_required(signbank.feedback.views.missingsign)),
    url(r'^site/$', signbank.feedback.views.generalfeedback),

    url(r'^overview/$', signbank.feedback.views.showfeedback),
    url(r'^showfeedback_signs/$', signbank.feedback.views.showfeedback_signs),
    url(r'^showfeedback_morphemes/$', signbank.feedback.views.showfeedback_morphemes),
    url(r'^showfeedback_missing/$', signbank.feedback.views.showfeedback_missing),

    url(r'^gloss/(?P<glossid>\d+)/$',  signbank.feedback.views.glossfeedback),
    url(r'^morpheme/(?P<glossid>\d+)/$', signbank.feedback.views.morphemefeedback),

    url(r'^(?P<kind>general|sign|morpheme|missingsign)/delete/(?P<id>\d+)$', signbank.feedback.views.delete),
]


