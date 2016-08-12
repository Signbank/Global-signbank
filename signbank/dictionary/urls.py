from django.conf.urls import *
from django.contrib.auth.decorators import login_required, permission_required

from signbank.dictionary.models import *
from signbank.dictionary.forms import *

from signbank.dictionary.adminviews import GlossListView, GlossDetailView, MorphemeDetailView


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
    url(r'^search_morpheme/$', 'signbank.dictionary.views.search_morpheme', name="search_morpheme"),
    url(r'^update/gloss/(?P<glossid>\d+)$', 'signbank.dictionary.update.update_gloss', name='update_gloss'),
    url(r'^update/morpheme/(?P<morphemeid>\d+)$', 'signbank.dictionary.update.update_morpheme', name='update_morpheme'),
    url(r'^update/tag/(?P<glossid>\d+)$', 'signbank.dictionary.update.add_tag', name='add_tag'),
    url(r'^update/morphemetag/(?P<morphemeid>\d+)$', 'signbank.dictionary.update.add_morphemetag', name='add_morphemetag'),
    url(r'^update/definition/(?P<glossid>\d+)$', 'signbank.dictionary.update.add_definition', name='add_definition'),
    url(r'^update/relation/$', 'signbank.dictionary.update.add_relation', name='add_relation'),
    url(r'^update/relationtoforeignsign/$', 'signbank.dictionary.update.add_relationtoforeignsign', name='add_relationtoforeignsign'),
    url(r'^update/morphologydefinition/$', 'signbank.dictionary.update.add_morphology_definition', name='add_morphologydefinition'),
    url(r'^update/morphemedefinition/(?P<glossid>\d+)$', 'signbank.dictionary.update.add_morpheme_definition', name='add_morphemedefinition'),
    url(r'^update/morphemeappearance/$', 'signbank.dictionary.update.add_morphemeappearance', name='add_morphemeappearance'),
    url(r'^update/othermedia/', 'signbank.dictionary.update.add_othermedia', name='add_othermedia'),
    url(r'^update/gloss/', 'signbank.dictionary.update.add_gloss', name='add_gloss'),
    url(r'^update/morpheme/', 'signbank.dictionary.update.add_morpheme', name='add_morpheme'),
    url(r'^update_ecv/', GlossListView.as_view(only_export_ecv=True)),

    url(r'^switch_to_language/(?P<language>..)$', 'signbank.dictionary.views.switch_to_language',name='switch_to_language'),
    url(r'^recently_added_glosses/$', 'signbank.dictionary.views.recently_added_glosses',name='recently_added_glosses'),

    # Ajax urls
    url(r'^ajax/keyword/(?P<prefix>.*)$', 'signbank.dictionary.views.keyword_value_list'),
    url(r'^ajax/tags/$', 'signbank.dictionary.tagviews.taglist_json'),
    url(r'^ajax/gloss/(?P<prefix>.*)$', 'signbank.dictionary.adminviews.gloss_ajax_complete', name='gloss_complete'),
    url(r'^ajax/morph/(?P<prefix>.*)$', 'signbank.dictionary.adminviews.morph_ajax_complete', name='morph_complete'),
    url(r'^ajax/searchresults/$','signbank.dictionary.adminviews.gloss_ajax_search_results', name='ajax_search_results'),

    url(r'^missingvideo.html$', 'signbank.dictionary.views.missing_video_view'),

    url(r'^import_images/$', 'signbank.dictionary.views.import_media',{'video':False}),
    url(r'^import_videos/$', 'signbank.dictionary.views.import_media',{'video':True}),
    url(r'^import_other_media/$', 'signbank.dictionary.views.import_other_media'),

    url(r'update_cngt_counts/$', 'signbank.dictionary.views.update_cngt_counts'),
    url(r'update_cngt_counts/(?P<folder_index>\d+)$', 'signbank.dictionary.views.update_cngt_counts'),

   url(r'package/$', 'signbank.dictionary.views.package'),
    #url(r'package/$','signbank.dictionary.views.package'),

    # Admin views
    url(r'^try/$', 'signbank.dictionary.views.try_code'), #A view for the developer to try out some things
    url(r'^import_authors/$', 'signbank.dictionary.views.import_authors'),

    url(r'^list/$', permission_required('dictionary.search_gloss')(GlossListView.as_view()), name='admin_gloss_list'),
    url(r'^gloss/(?P<pk>\d+)', permission_required('dictionary.search_gloss')(GlossDetailView.as_view()), name='admin_gloss_view'),
    url(r'^morpheme/(?P<pk>\d+)', permission_required('dictionary.search_gloss')(MorphemeDetailView.as_view()), name='admin_morpheme_view'),
)


