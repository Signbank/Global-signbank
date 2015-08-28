from django.conf.urls import *
from signbank.dictionary.models import *

urlpatterns = patterns('',
    
    (r'^$', 'signbank.feedback.views.index'),
    
    (r'^show.html', 'signbank.feedback.views.showfeedback'),
    (r'^missingsign.html', 'signbank.feedback.views.missingsign'), 
    (r'^generalfeedback.html', 'signbank.feedback.views.generalfeedback'),
    
    (r'^sign/(?P<keyword>.+)-(?P<n>\d+).html$',  'signbank.feedback.views.signfeedback'),
   
    (r'^gloss/(?P<glossid>.+).html$',  'signbank.feedback.views.glossfeedback'),
   
    url(r'^interpreter/(?P<glossid>\d+)', 'signbank.feedback.views.interpreterfeedback', name='intnote'),
    url(r'^interpreter.html', 'signbank.feedback.views.interpreterfeedback', name='intnotelist'),
   
    (r'^(?P<kind>general|sign|missingsign)/delete/(?P<id>\d+)$', 'signbank.feedback.views.delete'),
)


