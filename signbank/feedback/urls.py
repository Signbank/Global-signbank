from django.conf.urls import *
from signbank.dictionary.models import *

import signbank.feedback.views

urlpatterns = [
    url(r'^$', signbank.feedback.views.index),

    url(r'^show.html', signbank.feedback.views.showfeedback),
    url(r'^missingsign.html', signbank.feedback.views.missingsign),
    url(r'^generalfeedback.html', signbank.feedback.views.generalfeedback,name='general_feedback'),

    url(r'^missing/$', signbank.feedback.views.missingsign),
    url(r'^site/$', signbank.feedback.views.generalfeedback),

    url(r'^sign/(?P<keyword>.+)-(?P<n>\d+).html$',  signbank.feedback.views.signfeedback),

    url(r'^gloss/(?P<glossid>.+).html$',  signbank.feedback.views.glossfeedback),
   
    url(r'^interpreter/(?P<glossid>\d+)', signbank.feedback.views.interpreterfeedback, name='intnote'),
    url(r'^interpreter.html', signbank.feedback.views.interpreterfeedback, name='intnotelist'),

    url(r'^(?P<kind>general|sign|missingsign)/delete/(?P<id>\d+)$', signbank.feedback.views.delete),
]


