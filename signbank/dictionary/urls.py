from django.conf.urls import *
from django.contrib.auth.decorators import login_required, permission_required

from signbank.dictionary.models import *
from signbank.dictionary.forms import *

from signbank.dictionary.adminviews import GlossListView, GlossDetailView


urlpatterns = patterns('',

    # index page is just the search page
    url(r'^$', 'signbank.dictionary.views.search'),

    # we use the same view for a definition and for the feedback form on that
    # definition, the first component of the path is word or feedback in each case
    url(r'^words/(?P<keyword>.+)-(?P<n>\d+).html$',
            'signbank.dictionary.views.word'),

    url(r'^tag/(?P<tag>[^/]*)/?$', 'signbank.dictionary.tagviews.taglist'),

    # and and alternate view for direct display of a gloss
    url(r'gloss/(?P<idgloss>.+).html$', 'signbank.dictionary.views.gloss', name='public_gloss'),

    url(r'^search/$', 'signbank.dictionary.views.search', name="search"),
    url(r'^update/gloss/(?P<glossid>\d+)$', 'signbank.dictionary.update.update_gloss', name='update_gloss'),
    url(r'^update/tag/(?P<glossid>\d+)$', 'signbank.dictionary.update.add_tag', name='add_tag'),
    url(r'^update/definition/(?P<glossid>\d+)$', 'signbank.dictionary.update.add_definition', name='add_definition'),
    url(r'^update/relation/$', 'signbank.dictionary.update.add_relation', name='add_relation'),
    url(r'^update/relationtoforeignsign/$', 'signbank.dictionary.update.add_relationtoforeignsign', name='add_relationtoforeignsign'),
    url(r'^update/morphologydefinition/$', 'signbank.dictionary.update.add_morphology_definition', name='add_morphologydefinition'),
    url(r'^update/gloss/', 'signbank.dictionary.update.add_gloss', name='add_gloss'),

    url(r'^ajax/keyword/(?P<prefix>.*)$', 'signbank.dictionary.views.keyword_value_list'),
    url(r'^ajax/tags/$', 'signbank.dictionary.tagviews.taglist_json'),
    url(r'^ajax/gloss/(?P<prefix>.*)$', 'signbank.dictionary.adminviews.gloss_ajax_complete', name='gloss_complete'),
    
    url(r'^missingvideo.html$', 'signbank.dictionary.views.missing_video_view'),

    url(r'^import_videos/$', 'signbank.dictionary.views.import_videos'),

    # Admin views
    url(r'^try/$', 'signbank.dictionary.views.try_code'), #A view for the developer to try out some things

    url(r'^list/$', permission_required('dictionary.search_gloss')(GlossListView.as_view()), name='admin_gloss_list'),
    url(r'^gloss/(?P<pk>\d+)', permission_required('dictionary.search_gloss')(GlossDetailView.as_view()), name='admin_gloss_view'),

)


