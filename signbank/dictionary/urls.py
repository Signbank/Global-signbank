from django.conf.urls import *
from django.contrib.auth.decorators import login_required, permission_required

from signbank.dictionary.models import *
from signbank.dictionary.forms import *

from signbank.dictionary.adminviews import GlossListView, GlossDetailView, GlossFrequencyView, GlossRelationsDetailView, MorphemeDetailView, \
    MorphemeListView, HandshapeDetailView, HandshapeListView, LemmaListView, LemmaCreateView, LemmaDeleteView, LemmaFrequencyView, \
    create_lemma_for_gloss, LemmaUpdateView, SemanticFieldDetailView, SemanticFieldListView, DerivationHistoryDetailView, \
    DerivationHistoryListView, GlossVideosView

from signbank.dictionary.views import create_citation_image

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
    url(r'morpheme/(?P<glossid>\d+).html$', signbank.dictionary.views.morpheme, name='public_morpheme'),

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
    url(r'^update/othermedia/', signbank.dictionary.update.add_othermedia, name='add_othermedia'),
    url(r'^update/gloss/', signbank.dictionary.update.add_gloss, name='add_gloss'),
    url(r'^update/morpheme/', signbank.dictionary.update.add_morpheme, name='add_morpheme'),
    url(r'^update/blenddefinition/(?P<glossid>\d+)$', signbank.dictionary.update.add_blend_definition, name='add_blenddefinition'),

    url(r'^update/field_choice_color/(?P<category>.*)/(?P<fieldchoiceid>\d+)$', login_required(signbank.dictionary.update.update_field_choice_color),
        name='update_field_choice_color'),

    # The next one does not have a permission check because it should be accessible from a cronjob 
    url(r'^update_ecv/', GlossListView.as_view(only_export_ecv=True)),
    url(r'^update/variants_of_gloss/$', signbank.dictionary.update.variants_of_gloss, name='variants_of_gloss'),
    url(r'^switch_to_language/(?P<language>[\-a-z]{2,20})$', signbank.dictionary.views.switch_to_language,name='switch_to_language'),
    url(r'^recently_added_glosses/$', login_required(signbank.dictionary.views.recently_added_glosses),name='recently_added_glosses'),

    # Ajax urls
    url(r'^ajax/keyword/(?P<prefix>.*)$', signbank.dictionary.views.keyword_value_list),
    url(r'^ajax/tags/$', signbank.dictionary.tagviews.taglist_json),
    url(r'^ajax/gloss/(?P<prefix>.*)$', signbank.dictionary.adminviews.gloss_ajax_complete, name='gloss_complete'),
    url(r'^ajax/handshape/(?P<prefix>.*)$', signbank.dictionary.adminviews.handshape_ajax_complete, name='handshape_complete'),
    url(r'^ajax/morph/(?P<prefix>.*)$', signbank.dictionary.adminviews.morph_ajax_complete, name='morph_complete'),
    url(r'^ajax/user/(?P<prefix>.*)$', permission_required('dictionary.change_gloss')(signbank.dictionary.adminviews.user_ajax_complete), name='user_complete'),
    url(r'^ajax/searchresults/$',signbank.dictionary.adminviews.gloss_ajax_search_results, name='ajax_search_results'),
    url(r'^ajax/handshapesearchresults/$', signbank.dictionary.adminviews.handshape_ajax_search_results, name='handshape_ajax_search_results'),
    url(r'^ajax/lemmasearchresults/$', signbank.dictionary.adminviews.lemma_ajax_search_results, name='lemma_ajax_search_results'),
    url(r'^ajax/lemma/(?P<dataset_id>.*)/(?P<language_code>.*)/(?P<q>.*)$', permission_required('dictionary.change_gloss')(signbank.dictionary.adminviews.lemma_ajax_complete), name='lemma_complete'),
    url(r'^ajax/homonyms/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.homonyms_ajax_complete, name='homonyms_ajax_complete'),
    url(r'^ajax/minimalpairs/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.minimalpairs_ajax_complete, name='minimalpairs_ajax_complete'),
    url(r'^ajax/glossrow/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.glosslist_ajax_complete, name='glosslist_ajax_complete'),
    url(r'^ajax/glosslistheader/$', signbank.dictionary.adminviews.glosslistheader_ajax, name='glosslistheader_ajax'),
    url(r'^ajax/lemmaglossrow/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.lemmaglosslist_ajax_complete, name='lemmaglosslist_ajax_complete'),
    url(r'^ajax/choice_lists/$', signbank.dictionary.views.choice_lists,name='choice_lists'),

    url(r'^missingvideo.html$', signbank.dictionary.views.missing_video_view),

    url(r'^import_images/$', permission_required('dictionary.change_gloss')(signbank.dictionary.views.import_media),{'video':False}),
    url(r'^import_videos/$', permission_required('dictionary.change_gloss')(signbank.dictionary.views.import_media),{'video':True}),
    url(r'update_corpus_document_counts/(?P<dataset_id>.*)/(?P<document_id>.*)/$',
        permission_required('dictionary.change_gloss')(signbank.frequency.update_document_counts)),
    url(r'update_corpora/$',
        permission_required('dictionary.change_gloss')(signbank.frequency.update_corpora)),

    url(r'find_and_save_variants/$',permission_required('dictionary.change_gloss')(signbank.dictionary.views.find_and_save_variants)),

    url(r'get_unused_videos/$',permission_required('dictionary.change_gloss')(signbank.dictionary.views.get_unused_videos)),
    url(r'package/$', signbank.dictionary.views.package),
    url(r'info/$', signbank.dictionary.views.info),
    url(r'protected_media/(?P<filename>.*)$', signbank.dictionary.views.protected_media, name='protected_media'),

    # Admin views
    url(r'^try/$', signbank.dictionary.views.try_code), #A view for the developer to try out some things
    url(r'^gif_prototype/$', signbank.dictionary.views.gif_prototype),
    url(r'^import_authors/$', permission_required('dictionary.change_gloss')(signbank.dictionary.views.import_authors)),

    url(r'^list/$', permission_required('dictionary.search_gloss')(GlossListView.as_view()), name='admin_gloss_list'),
    url(r'^morphemes/$', permission_required('dictionary.search_gloss')(MorphemeListView.as_view()), name='admin_morpheme_list'),
    url(r'^handshapes/$', permission_required('dictionary.search_gloss')(HandshapeListView.as_view()), name='admin_handshape_list'),
    url(r'^gloss/(?P<gloss_pk>\d+)/history', signbank.dictionary.views.gloss_revision_history, name='gloss_revision_history'),
    url(r'^gloss/(?P<pk>\d+)/glossvideos', GlossVideosView.as_view(), name='gloss_videos'),
    url(r'^gloss/(?P<pk>\d+)', GlossDetailView.as_view(), name='admin_gloss_view'),
    url(r'^gloss_preview/(?P<pk>\d+)', GlossDetailView.as_view(), name='admin_gloss_view_colors'),
    url(r'^gloss_frequency/(?P<gloss_id>.*)/$', GlossFrequencyView.as_view(), name='admin_frequency_gloss'),
    url(r'^lemma_frequency/(?P<gloss_id>.*)/$', LemmaFrequencyView.as_view(), name='admin_frequency_lemma'),
    url(r'^gloss_relations/(?P<pk>\d+)', GlossRelationsDetailView.as_view(), name='admin_gloss_relations_view'),
    url(r'^morpheme/(?P<pk>\d+)', MorphemeDetailView.as_view(), name='admin_morpheme_view'),
    url(r'^handshape/(?P<pk>\d+)', HandshapeDetailView.as_view(), name='admin_handshape_view'),
    url(r'^semanticfield/(?P<pk>\d+)', SemanticFieldDetailView.as_view(), name='admin_semanticfield_view'),
    url(r'^semanticfields/$', permission_required('dictionary.search_gloss')(SemanticFieldListView.as_view()), name='admin_semanticfield_list'),
    url(r'^derivationhistory/(?P<pk>\d+)', DerivationHistoryDetailView.as_view(), name='admin_derivationhistory_view'),
    url(r'^derivationhistory_list/$', permission_required('dictionary.search_gloss')(DerivationHistoryListView.as_view()),
        name='admin_derivationhistory_list'),
    # Lemma Idgloss views
    url(r'^lemma/$', login_required(LemmaListView.as_view()), name='admin_lemma_list'),
    url(r'^lemma/add/$', permission_required('dictionary.add_lemmaidgloss')(LemmaCreateView.as_view()), name='create_lemma'),
    url(r'^lemma/delete/(?P<pk>\d+)', permission_required('dictionary.delete_lemmaidgloss')(LemmaDeleteView.as_view()), name='delete_lemma'),
    url(r'lemma/add/(?P<glossid>\d+)$', signbank.dictionary.adminviews.create_lemma_for_gloss, name='create_lemma_gloss'),
    url(r'lemma/update/(?P<pk>\d+)$', permission_required('dictionary.change_lemmaidgloss')(LemmaUpdateView.as_view()), name='change_lemma'),

    url(r'find_interesting_frequency_examples',signbank.dictionary.views.find_interesting_frequency_examples),

    url(r'createcitationimage/(?P<pk>\d+)', permission_required('dictionary.change_gloss')(create_citation_image), name='create_citation_image')
]
