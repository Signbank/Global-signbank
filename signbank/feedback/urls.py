from django.conf.urls import *
from django.urls import re_path, path, include
from signbank.dictionary.models import *
from django.contrib.auth.decorators import login_required, permission_required

import signbank.feedback.views

app_name = 'feedback'
urlpatterns = [
    re_path(r'^$', signbank.feedback.views.index),

    re_path(r'^show.html', signbank.feedback.views.showfeedback),
    re_path(r'^missingsign.html', signbank.feedback.views.missingsign),
    re_path(r'^generalfeedback.html', signbank.feedback.views.generalfeedback,name='general_feedback'),

    re_path(r'^missing/$', login_required(signbank.feedback.views.missingsign)),
    re_path(r'^site/$', signbank.feedback.views.generalfeedback),

    re_path(r'^sign/(?P<keyword>.+)-(?P<n>\d+).html$',  signbank.feedback.views.signfeedback),

    re_path(r'^gloss/(?P<glossid>\d+)/$',  signbank.feedback.views.glossfeedback),
    re_path(r'^morpheme/(?P<glossid>\d+)/$', signbank.feedback.views.glossfeedback),

    re_path(r'^interpreter/(?P<glossid>\d+)', signbank.feedback.views.interpreterfeedback, name='intnote'),
    re_path(r'^interpreter.html', signbank.feedback.views.interpreterfeedback, name='intnotelist'),

    re_path(r'^(?P<kind>general|sign|missingsign)/delete/(?P<id>\d+)$', signbank.feedback.views.delete),
]


