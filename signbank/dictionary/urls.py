from django.conf.urls import *
from django.contrib.auth.decorators import login_required, permission_required

from signbank.dictionary.models import *
from signbank.dictionary.forms import *

from signbank.dictionary.adminviews import GlossListView, GlossDetailView, GlossRelationsDetailView, MorphemeDetailView, \
    MorphemeListView, HandshapeDetailView, HandshapeListView, LemmaListView, LemmaCreateView, LemmaDeleteView

#These are needed for the urls below
import signbank.dictionary.views
import signbank.dictionary.tagviews
import signbank.dictionary.adminviews

urlpatterns = [

    # index page is just the search page
    url(r'^$', signbank.dictionary.views.search),

    # we use the same view for a definition and for the feedback form on that
    # definition, the first component of the path is word or feedback in each case
    url(r'^words/(?P<keyword>.+)-(?P<n>\d+).html$',
            signbank.dictionary.views.word),

    url(r'^tag/(?P<tag>[^/]*)/?$', signbank.dictionary.tagviews.taglist),

    # and and alternate view for direct display of a gloss
    url(r'gloss/(?P<glossid>\d+).html$', signbank.dictionary.views.gloss, name='public_gloss'),

    url(r'^search/$', signbank.dictionary.views.search, name="search"),
    url(r'^search_morpheme/$', signbank.dictionary.views.search_morpheme, name="search_morpheme"),
    url(r'^update/gloss/(?P<glossid>\d+)$', signbank.dictionary.update.update_gloss, name='update_gloss'),
    url(r'^update/handshape/(?P<handshapeid>\d+)$', signbank.dictionary.update.update_handshape, name='update_handshape'),
    url(r'^update/morpheme/(?P<morphemeid>\d+)$', signbank.dictionary.update.update_morpheme, name='update_morpheme'),
    url(r'^update/tag/(?P<glossid>\d+)$', signbank.dictionary.update.add_tag, name='add_tag'),
    url(r'^update/morphemetag/(?P<morphemeid>\d+)$', signbank.dictionary.update.add_morphemetag, name='add_morphemetag'),
    url(r'^update/definition/(?P<glossid>\d+)$', signbank.dictionary.update.add_definition, name='add_definition'),
    url(r'^update/relation/$', signbank.dictionary.update.add_relation, name='add_relation'),
    url(r'^update/relationtoforeignsign/$', signbank.dictionary.update.add_relationtoforeignsign, name='add_relationtoforeignsign'),
    url(r'^update/morphologydefinition/$', signbank.dictionary.update.add_morphology_definition, name='add_morphologydefinition'),
    url(r'^update/morphemedefinition/(?P<glossid>\d+)$', signbank.dictionary.update.add_morpheme_definition, name='add_morphemedefinition'),
    url(r'^update/morphemeappearance/$', signbank.dictionary.update.add_morphemeappearance, name='add_morphemeappearance'),
    url(r'^update/othermedia/', signbank.dictionary.update.add_othermedia, name='add_othermedia'),
    url(r'^update/gloss/', signbank.dictionary.update.add_gloss, name='add_gloss'),
    url(r'^update/morpheme/', signbank.dictionary.update.add_morpheme, name='add_morpheme'),
    url(r'^update/blenddefinition/(?P<glossid>\d+)$', signbank.dictionary.update.add_blend_definition, name='add_blenddefinition'),

    # The next one does not have a permission check because it should be accessible from a cronjob 
    url(r'^update_ecv/', GlossListView.as_view(only_export_ecv=True)),
    url(r'^update/variants_of_gloss/$', signbank.dictionary.update.variants_of_gloss, name='variants_of_gloss'),
    url(r'^switch_to_language/(?P<language>[\-a-z]{2,20})$', signbank.dictionary.views.switch_to_language,name='switch_to_language'),
    url(r'^recently_added_glosses/$', signbank.dictionary.views.recently_added_glosses,name='recently_added_glosses'),

    # Ajax urls
    url(r'^ajax/keyword/(?P<prefix>.*)$', signbank.dictionary.views.keyword_value_list),
    url(r'^ajax/tags/$', signbank.dictionary.tagviews.taglist_json),
    url(r'^ajax/gloss/(?P<prefix>.*)$', signbank.dictionary.adminviews.gloss_ajax_complete, name='gloss_complete'),
    url(r'^ajax/handshape/(?P<prefix>.*)$', signbank.dictionary.adminviews.handshape_ajax_complete, name='handshape_complete'),
    url(r'^ajax/morph/(?P<prefix>.*)$', signbank.dictionary.adminviews.morph_ajax_complete, name='morph_complete'),
    url(r'^ajax/user/(?P<prefix>.*)$', permission_required('dictionary.change_gloss')(signbank.dictionary.adminviews.user_ajax_complete), name='user_complete'),
    url(r'^ajax/searchresults/$',signbank.dictionary.adminviews.gloss_ajax_search_results, name='ajax_search_results'),
    url(r'^ajax/handshapesearchresults/$', signbank.dictionary.adminviews.handshape_ajax_search_results, name='handshape_ajax_search_results'),

    url(r'^missingvideo.html$', signbank.dictionary.views.missing_video_view),

    url(r'^import_images/$', permission_required('dictionary.change_gloss')(signbank.dictionary.views.import_media),{'video':False}),
    url(r'^import_videos/$', permission_required('dictionary.change_gloss')(signbank.dictionary.views.import_media),{'video':True}),
    url(r'^import_other_media/$', permission_required('dictionary.change_gloss')(signbank.dictionary.views.import_other_media)),

    url(r'find_and_save_variants/$',permission_required('dictionary.change_gloss')(signbank.dictionary.views.find_and_save_variants)),

    url(r'update_cngt_counts/$', permission_required('dictionary.change_gloss')(signbank.dictionary.views.update_cngt_counts)),
    url(r'update_cngt_counts/(?P<folder_index>\d+)$', permission_required('dictionary.change_gloss')(signbank.dictionary.views.update_cngt_counts)),
    url(r'configure_handshapes/$',
        permission_required('dictionary.change_gloss')(signbank.dictionary.views.configure_handshapes)),

    url(r'get_unused_videos/$',permission_required('dictionary.change_gloss')(signbank.dictionary.views.get_unused_videos)),
    url(r'all_field_choices.tsv/$',signbank.dictionary.views.list_all_fieldchoice_names),
    url(r'package/$', signbank.dictionary.views.package),
    url(r'info/$', signbank.dictionary.views.info),
    url(r'protected_media/(?P<filename>.*)$', signbank.dictionary.views.protected_media, name='protected_media'),

    # Admin views
    url(r'^try/$', signbank.dictionary.views.try_code), #A view for the developer to try out some things
    url(r'^import_authors/$', permission_required('dictionary.change_gloss')(signbank.dictionary.views.import_authors)),

    url(r'^list/$', permission_required('dictionary.search_gloss')(GlossListView.as_view()), name='admin_gloss_list'),
    url(r'^morphemes/$', permission_required('dictionary.search_gloss')(MorphemeListView.as_view()), name='admin_morpheme_list'),
    url(r'^handshapes/$', permission_required('dictionary.search_gloss')(HandshapeListView.as_view()), name='admin_handshape_list'),
    url(r'^gloss/(?P<pk>\d+)', GlossDetailView.as_view(), name='admin_gloss_view'),
    url(r'^gloss_relations/(?P<pk>\d+)', GlossRelationsDetailView.as_view(), name='admin_gloss_relations_view'),
    url(r'^morpheme/(?P<pk>\d+)', MorphemeDetailView.as_view(), name='admin_morpheme_view'),
    url(r'^handshape/(?P<pk>\d+)', HandshapeDetailView.as_view(), name='admin_handshape_view'),

    # Lemma Idgloss views
    url(r'^lemma/$', permission_required('dictionary.change_lemmaidgloss')(LemmaListView.as_view()), name='admin_lemma_list'),
    url(r'^lemma/add/$', permission_required('dictionary.add_lemmaidgloss')(LemmaCreateView.as_view()), name='create_lemma'),
    url(r'^lemma/delete/(?P<pk>\d+)', permission_required('dictionary.delete_lemmaidgloss')(LemmaDeleteView.as_view()), name='delete_lemma'),
]
