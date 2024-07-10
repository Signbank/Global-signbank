from django.conf.urls import *
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import re_path, path, include

from signbank.dictionary.models import *
from signbank.dictionary.forms import *

from signbank.dictionary.adminviews import GlossListView, GlossDetailView, GlossFrequencyView, GlossRelationsDetailView, MorphemeDetailView, \
    MorphemeListView, HandshapeDetailView, HandshapeListView, LemmaListView, LemmaCreateView, LemmaDeleteView, LemmaFrequencyView, \
    create_lemma_for_gloss, LemmaUpdateView, SemanticFieldDetailView, SemanticFieldListView, DerivationHistoryDetailView, \
    DerivationHistoryListView, GlossVideosView, KeywordListView

from signbank.dictionary.views import create_citation_image

# These are needed for the urls below
import signbank.dictionary.views
import signbank.dictionary.tagviews
import signbank.dictionary.adminviews
import signbank.api_interface
import signbank.manage_videos
import signbank.abstract_machine
import signbank.gloss_update
import signbank.dictionary.batch_edit
import signbank.gloss_morphology_update

app_name = 'dictionary'
urlpatterns = [

    re_path(r'^tag/(?P<tag>[^/]*)/?$', signbank.dictionary.tagviews.taglist),

    # an alternate view for direct display of a gloss
    re_path(r'gloss/(?P<glossid>\d+).html$', signbank.dictionary.views.gloss, name='public_gloss'),
    re_path(r'morpheme/(?P<glossid>\d+).html$', signbank.dictionary.views.morpheme, name='public_morpheme'),

    re_path(r'^update/gloss/(?P<glossid>\d+)$', signbank.dictionary.update.update_gloss, name='update_gloss'),
    re_path(r'^update/handshape/(?P<handshapeid>\d+)$', signbank.dictionary.update.update_handshape, name='update_handshape'),
    re_path(r'^update/morpheme/(?P<morphemeid>\d+)$', signbank.dictionary.update.update_morpheme, name='update_morpheme'),
    re_path(r'^update/tag/(?P<glossid>\d+)$', signbank.dictionary.update.add_tag, name='add_tag'),
    re_path(r'^update/affiliation/(?P<glossid>\d+)$', signbank.dictionary.update.add_affiliation, name='add_affiliation'),
    re_path(r'^update/morphemetag/(?P<morphemeid>\d+)$', signbank.dictionary.update.add_morphemetag, name='add_morphemetag'),
    re_path(r'^update/definition/(?P<glossid>\d+)$', signbank.dictionary.update.add_definition, name='add_definition'),
    re_path(r'^update/relation/$', signbank.dictionary.update.add_relation, name='add_relation'),
    re_path(r'^update/relationtoforeignsign/$', signbank.dictionary.update.add_relationtoforeignsign, name='add_relationtoforeignsign'),
    re_path(r'^update/morphologydefinition/$', signbank.dictionary.update.add_morphology_definition, name='add_morphologydefinition'),
    re_path(r'^update/morphemedefinition/(?P<glossid>\d+)$', signbank.dictionary.update.add_morpheme_definition, name='add_morphemedefinition'),
    re_path(r'^update/othermedia/', signbank.dictionary.update.add_othermedia, name='add_othermedia'),
    re_path(r'^update/gloss/', signbank.dictionary.update.add_gloss, name='add_gloss'),
    re_path(r'^update/assign_lemma_dataset_to_gloss/(?P<glossid>\d+)$', signbank.dictionary.update.assign_lemma_dataset_to_gloss,
            name='assign_lemma_dataset_to_gloss'),
    re_path(r'^update/sense/(?P<senseid>\d+)$', signbank.dictionary.update.update_sense, name='update_sense'),
    re_path(r'^update/linksense/(?P<senseid>\d+)$', signbank.dictionary.update.link_sense, name='link_sense'),
    re_path(r'^update/addsense/(?P<glossid>\d+)$', signbank.dictionary.update.create_sense, name='create_sense'),
    re_path(r'^update/sortsense/(?P<glossid>\d+)/(?P<order>\d+)/(?P<direction>\w+)$', signbank.dictionary.update.sort_sense, name='sort_sense'),
    re_path(r'^update/sortexamplesentence/(?P<senseid>\d+)/(?P<glossid>\d+)/(?P<order>\d+)/(?P<direction>\w+)$', signbank.dictionary.update.sort_examplesentence, name='sort_examplesentence'),
    re_path(r'^update/deletesense/(?P<glossid>\d+)$', signbank.dictionary.update.delete_sense, name='delete_sense'),
    re_path(r'^update/examplesentence/(?P<examplesentenceid>\d+)$', signbank.dictionary.update.update_examplesentence, name='update_examplesentence'),
    re_path(r'^update/addexamplesentence/(?P<senseid>\d+)$', signbank.dictionary.update.create_examplesentence, name='create_examplesentence'),
    re_path(r'^update/deleteexamplesentence/(?P<senseid>\d+)$', signbank.dictionary.update.delete_examplesentence, name='delete_examplesentence'),
    re_path(r'^update/addsentencevideo/(?P<glossid>\d+)/(?P<examplesentenceid>\d+)$', signbank.dictionary.update.add_sentence_video, name='add_sentence_video'),
    re_path(r'^update/addannotatedmedia/(?P<glossid>\d+)$', signbank.dictionary.update.add_annotated_media, name='add_annotated_media'),
    re_path(r'^update/updateannotatedsentence/(?P<glossid>\d+)/(?P<annotatedsentenceid>\d+)$', signbank.dictionary.update.edit_annotated_sentence, name='edit_annotated_sentence'),
    re_path(r'^update/saveeditannotatedsentence/', signbank.dictionary.update.save_edit_annotated_sentence, name='save_edit_annotated_sentence'),
    re_path(r'^update/deleteannotatedsentence/(?P<glossid>\d+)$', signbank.dictionary.update.delete_annotated_sentence, name='delete_annotated_sentence'),
    re_path(r'^update/morpheme/', signbank.dictionary.update.add_morpheme, name='add_morpheme'),
    re_path(r'^update/blenddefinition/(?P<glossid>\d+)$', signbank.dictionary.update.add_blend_definition, name='add_blenddefinition'),

    re_path(r'^update/field_choice_color/(?P<category>.*)/(?P<fieldchoiceid>\d+)$', login_required(signbank.dictionary.update.update_field_choice_color),
        name='update_field_choice_color'),

    re_path(r'^update/query/(?P<queryid>\d+)$', signbank.dictionary.update.update_query, name='update_query'),
    re_path(r'^update/semanticfield/(?P<semfieldid>\d+)$', signbank.dictionary.update.update_semfield, name='update_semfield'),
    re_path(r'^update/group_keywords/(?P<glossid>\d+)$', signbank.dictionary.update.group_keywords,
            name='group_keywords'),
    re_path(r'^update/edit_keywords/(?P<glossid>\d+)$', signbank.dictionary.update.edit_keywords,
            name='edit_keywords'),
    re_path(r'^update/add_keyword/(?P<glossid>\d+)$', signbank.dictionary.update.add_keyword,
            name='add_keyword'),
    re_path(r'^update/edit_senses_matrix/(?P<glossid>\d+)$', signbank.dictionary.update.edit_senses_matrix,
            name='edit_senses_matrix'),
    re_path(r'^update/toggle_sense_tag/(?P<glossid>\d+)$', signbank.dictionary.update.toggle_sense_tag,
            name='toggle_sense_tag'),

    re_path(r'^update/toggle_tag/(?P<glossid>\d+)/(?P<tagid>.*)$', signbank.dictionary.update.toggle_tag,
            name='toggle_tag'),
    re_path(r'^update/toggle_semantics/(?P<glossid>\d+)/(?P<semanticfield>.*)$', signbank.dictionary.update.toggle_semantic_field,
            name='toggle_semantic_field'),
    re_path(r'^update/toggle_wordclass/(?P<glossid>\d+)/(?P<wordclass>.*)$',
            signbank.dictionary.update.toggle_wordclass,
            name='toggle_wordclass'),
    re_path(r'^update/toggle_namedentity/(?P<glossid>\d+)/(?P<namedentity>.*)$',
            signbank.dictionary.update.toggle_namedentity,
            name='toggle_namedentity'),
    re_path(r'^update/toggle_handedness/(?P<glossid>\d+)/(?P<handedness>.*)$',
            signbank.dictionary.update.toggle_handedness,
            name='toggle_handedness'),
    re_path(r'^update/toggle_domhndsh/(?P<glossid>\d+)/(?P<domhndsh>.*)$',
            signbank.dictionary.update.toggle_domhndsh,
            name='toggle_domhndsh'),
    re_path(r'^update/toggle_subhndsh/(?P<glossid>\d+)/(?P<subhndsh>.*)$',
            signbank.dictionary.update.toggle_subhndsh,
            name='toggle_subhndsh'),
    re_path(r'^update/toggle_locprim/(?P<glossid>\d+)/(?P<locprim>.*)$',
            signbank.dictionary.update.toggle_locprim,
            name='toggle_locprim'),
    re_path(r'^update/toggle_movSh/(?P<glossid>\d+)/(?P<movSh>.*)$',
            signbank.dictionary.update.toggle_movSh,
            name='toggle_movSh'),
    re_path(r'^update/toggle_repeat/(?P<glossid>\d+)/(?P<repeat>.*)$',
            signbank.dictionary.update.toggle_repeat,
            name='toggle_repeat'),
    re_path(r'^update/toggle_altern/(?P<glossid>\d+)/(?P<altern>.*)$',
            signbank.dictionary.update.toggle_altern,
            name='toggle_altern'),

    re_path(r'^update/quick_create_sense/(?P<glossid>\d+)$',
            signbank.dictionary.update.quick_create_sense,
            name='quick_create_sense'),

    re_path(r'^update/toggle_language_fields/(?P<glossid>\d+)$',
            signbank.dictionary.update.toggle_language_fields,
            name='toggle_language_fields'),

    # The next one does not have a permission check because it should be accessible from a cronjob
    re_path(r'^update_ecv/', GlossListView.as_view(only_export_ecv=True)),
    re_path(r'^update/variants_of_gloss/$', signbank.dictionary.update.variants_of_gloss, name='variants_of_gloss'),
    re_path(r'^switch_to_language/(?P<language>[\-a-z]{2,20})$', signbank.dictionary.views.switch_to_language,name='switch_to_language'),

    # Ajax urls
    re_path(r'^ajax/tags/$', signbank.dictionary.tagviews.taglist_json),
    re_path(r'^ajax/gloss/(?P<prefix>.*)$', signbank.dictionary.adminviews.gloss_ajax_complete, name='gloss_complete'),
    re_path(r'^ajax/similarglosses/(?P<gloss_id>.*)$', signbank.dictionary.batch_edit.similarglosses, name='similarglosses'),
    re_path(r'^ajax/handshape/(?P<prefix>.*)$', signbank.dictionary.adminviews.handshape_ajax_complete, name='handshape_complete'),
    re_path(r'^ajax/morph/(?P<prefix>.*)$', signbank.dictionary.adminviews.morph_ajax_complete, name='morph_complete'),
    re_path(r'^ajax/user/(?P<prefix>.*)$', permission_required('dictionary.change_gloss')(signbank.dictionary.adminviews.user_ajax_complete), name='user_complete'),
    re_path(r'^ajax/searchresults/$',signbank.dictionary.adminviews.gloss_ajax_search_results, name='ajax_search_results'),
    re_path(r'^ajax/handshapesearchresults/$', signbank.dictionary.adminviews.handshape_ajax_search_results, name='handshape_ajax_search_results'),
    re_path(r'^ajax/lemmasearchresults/$', signbank.dictionary.adminviews.lemma_ajax_search_results, name='lemma_ajax_search_results'),
    re_path(r'^ajax/lemma/(?P<dataset_id>.*)/(?P<language_code>.*)/(?P<q>.*)$', permission_required('dictionary.change_gloss')(signbank.dictionary.adminviews.lemma_ajax_complete), name='lemma_complete'),
    re_path(r'^ajax/sensetranslation/(?P<dataset_id>.*)/(?P<language_code>.*)/(?P<q>.*)$', permission_required('dictionary.change_gloss')(signbank.dictionary.adminviews.sensetranslation_ajax_complete), name='sensetranslation_complete'),
    re_path(r'^ajax/homonyms/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.homonyms_ajax_complete, name='homonyms_ajax_complete'),
    re_path(r'^ajax/minimalpairs/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.minimalpairs_ajax_complete, name='minimalpairs_ajax_complete'),
    re_path(r'^ajax/glossrow/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.glosslist_ajax_complete, name='glosslist_ajax_complete'),
    re_path(r'^ajax/glosslistheader/$', signbank.dictionary.adminviews.glosslistheader_ajax, name='glosslistheader_ajax'),
    re_path(r'^ajax/senserow/(?P<sense_id>.*)/$', signbank.dictionary.adminviews.senselist_ajax_complete, name='senselist_ajax_complete'),
    re_path(r'^ajax/senselistheader/$', signbank.dictionary.adminviews.senselistheader_ajax, name='senselistheader_ajax'),
    re_path(r'^ajax/lemmaglossrow/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.lemmaglosslist_ajax_complete, name='lemmaglosslist_ajax_complete'),
    re_path(r'^ajax/choice_lists/$', signbank.dictionary.views.choice_lists,name='choice_lists'),

    re_path(r'^missingvideo.html$', signbank.dictionary.views.missing_video_view),

    re_path(r'update_corpus_document_counts/(?P<dataset_id>.*)/(?P<document_id>.*)/$',
            permission_required('dictionary.change_gloss')(signbank.frequency.update_document_counts)),
    re_path(r'update_corpora/$',
            permission_required('dictionary.change_gloss')(signbank.frequency.update_corpora)),

    re_path(r'find_and_save_variants/$',login_required(signbank.dictionary.views.find_and_save_variants), name='find_and_save_variants'),
    re_path(r'export_csv_template/$', signbank.csv_interface.export_csv_template,
            name='export_csv_template'),

    re_path(r'get_unused_videos/$',permission_required('dictionary.change_gloss')(signbank.dictionary.views.get_unused_videos)),
    re_path(r'package/$', signbank.dictionary.views.package),
    re_path(r'get_gloss_data/(?P<datasetid>\d+)/(?P<glossid>\d+)/$',
            signbank.api_interface.get_gloss_data_json, name='get_gloss_data_json'),
    re_path(r'get_fields_data/(?P<datasetid>\d+)/$',
            signbank.api_interface.get_fields_data_json, name='get_fields_data_json'),
    re_path(r'get_unzipped_video_files_json/(?P<datasetid>\d+)/$',
            signbank.api_interface.get_unzipped_video_files_json, name='get_unzipped_video_files_json'),
    re_path(r'upload_zipped_videos_folder_json/(?P<datasetid>\d+)/$',
            signbank.api_interface.upload_zipped_videos_folder_json, name='upload_zipped_videos_folder_json'),

    re_path(r'upload_videos_to_glosses/(?P<datasetid>\d+)/$',
            signbank.api_interface.upload_videos_to_glosses, name='upload_videos_to_glosses'),

    re_path(r'upload_zipped_videos_folder/$',
            signbank.manage_videos.upload_zipped_videos_folder, name='upload_zipped_videos_folder'),
    re_path(r'import_video_to_gloss_json/$',
            signbank.manage_videos.import_video_to_gloss_json, name='import_video_to_gloss_json'),

    re_path(r'api_create_gloss/(?P<datasetid>\d+)/$',
            signbank.abstract_machine.api_create_gloss, name='api_create_gloss'),
    re_path(r'test_abstract_machine/(?P<datasetid>\d+)/$',
            signbank.dictionary.views.test_abstract_machine, name='test_abstract_machine'),
    re_path(r'api_update_gloss/(?P<datasetid>\d+)/(?P<glossid>\d+)/$',
            signbank.gloss_update.api_update_gloss, name='api_update_gloss'),
    re_path(r'test_am_update_gloss/(?P<datasetid>\d+)/(?P<glossid>\d+)/$',
            signbank.dictionary.views.test_am_update_gloss, name='test_am_update_gloss'),
    re_path(r'api_update_gloss_morphology/(?P<datasetid>\d+)/(?P<glossid>\d+)/$',
            signbank.gloss_morphology_update.api_update_gloss_morphology, name='api_update_gloss'),

    re_path(r'info/$', signbank.dictionary.views.info),
    re_path(r'protected_media/(?P<filename>.*)$', signbank.dictionary.views.protected_media, name='protected_media'),

    # Admin views
    re_path(r'^try/(?P<pk>\d+)$', signbank.dictionary.views.try_code),  # View for the developer to view senses for a gloss
    re_path(r'^gif_prototype/$', signbank.dictionary.views.gif_prototype),

    re_path(r'^list/$', permission_required('dictionary.search_gloss')(GlossListView.as_view()), name='admin_gloss_list'),
    re_path(r'^morphemes/$', permission_required('dictionary.search_gloss')(MorphemeListView.as_view()), name='admin_morpheme_list'),
    re_path(r'^handshapes/$', permission_required('dictionary.search_gloss')(HandshapeListView.as_view()), name='admin_handshape_list'),
    re_path(r'^gloss/(?P<gloss_pk>\d+)/history', signbank.dictionary.views.gloss_revision_history, name='gloss_revision_history'),
    re_path(r'^gloss/(?P<pk>\d+)/glossvideos', GlossVideosView.as_view(), name='gloss_videos'),
    re_path(r'^gloss/(?P<pk>\d+)', GlossDetailView.as_view(), name='admin_gloss_view'),
    re_path(r'^gloss_preview/(?P<pk>\d+)', GlossDetailView.as_view(), name='admin_gloss_view_colors'),
    re_path(r'^gloss_frequency/(?P<gloss_id>.*)/$', GlossFrequencyView.as_view(), name='admin_frequency_gloss'),
    re_path(r'^lemma_frequency/(?P<gloss_id>.*)/$', LemmaFrequencyView.as_view(), name='admin_frequency_lemma'),
    re_path(r'^gloss_relations/(?P<pk>\d+)', GlossRelationsDetailView.as_view(), name='admin_gloss_relations_view'),
    re_path(r'^morpheme/(?P<pk>\d+)', MorphemeDetailView.as_view(), name='admin_morpheme_view'),
    re_path(r'^handshape/(?P<pk>\d+)', HandshapeDetailView.as_view(), name='admin_handshape_view'),
    re_path(r'^semanticfield/(?P<pk>\d+)', SemanticFieldDetailView.as_view(), name='admin_semanticfield_view'),
    re_path(r'^semanticfields/$', permission_required('dictionary.search_gloss')(SemanticFieldListView.as_view()), name='admin_semanticfield_list'),
    re_path(r'^derivationhistory/(?P<pk>\d+)', DerivationHistoryDetailView.as_view(), name='admin_derivationhistory_view'),
    re_path(r'^derivationhistory_list/$', permission_required('dictionary.search_gloss')(DerivationHistoryListView.as_view()),
        name='admin_derivationhistory_list'),
    # Lemma Idgloss views
    re_path(r'^lemma/$', login_required(LemmaListView.as_view()), name='admin_lemma_list'),
    re_path(r'^lemma/add/$', permission_required('dictionary.add_lemmaidgloss')(LemmaCreateView.as_view()), name='create_lemma'),
    re_path(r'^lemma/delete/(?P<pk>\d+)', permission_required('dictionary.delete_lemmaidgloss')(LemmaDeleteView.as_view()), name='delete_lemma'),
    re_path(r'lemma/add/(?P<glossid>\d+)$', signbank.dictionary.adminviews.create_lemma_for_gloss, name='create_lemma_gloss'),
    re_path(r'lemma/update/(?P<pk>\d+)$', permission_required('dictionary.change_lemmaidgloss')(LemmaUpdateView.as_view()), name='change_lemma'),

    re_path(r'^keywords/$', KeywordListView.as_view(), name='admin_keyword_list'),

    re_path(r'find_interesting_frequency_examples',signbank.dictionary.views.find_interesting_frequency_examples),

    re_path(r'createcitationimage/(?P<pk>\d+)',
            permission_required('dictionary.change_gloss')(signbank.dictionary.views.create_citation_image),
            name='create_citation_image'),

    re_path(r'gloss/api/', signbank.dictionary.views.gloss_api_get_sign_name_and_media_info, name='gloss_api_get_info')
]
