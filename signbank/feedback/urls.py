from django.conf.urls import *
from django.urls import re_path, path, include
from signbank.dictionary.models import *
from django.contrib.auth.decorators import login_required, permission_required

import signbank.feedback.views

app_name = 'feedback'
urlpatterns = [
    re_path(r'^$', signbank.feedback.views.index),

    re_path(r'^missing/$', login_required(signbank.feedback.views.missingsign)),
    re_path(r'^site/$', signbank.feedback.views.generalfeedback),

    re_path(r'^overview/$', signbank.feedback.views.showfeedback),
    re_path(r'^showfeedback_signs/$', signbank.feedback.views.showfeedback_signs),
    re_path(r'^showfeedback_morphemes/$', signbank.feedback.views.showfeedback_morphemes),
    re_path(r'^showfeedback_missing/$', signbank.feedback.views.showfeedback_missing),

    re_path(r'^gloss/(?P<glossid>\d+)/$',  signbank.feedback.views.glossfeedback),
    re_path(r'^morpheme/(?P<glossid>\d+)/$', signbank.feedback.views.morphemefeedback),

    re_path(r'^(?P<kind>general|sign|morpheme|missingsign)/delete/(?P<id>\d+)$', signbank.feedback.views.delete),
]


