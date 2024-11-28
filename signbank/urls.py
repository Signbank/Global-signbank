from django.conf.urls import *
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import LoginView, LogoutView
#import signbank.registration.forms # I think this is unused?
from django.conf.urls.static import static
from django.urls import re_path, path, include
from django.views.generic import TemplateView

#These are needed for the urls below
import signbank.pages.views
import signbank.dictionary.urls
import signbank.feedback.urls
import signbank.feedback.views
import signbank.attachments.urls
import signbank.video.urls
import signbank.video.views
import signbank.animation.urls

import signbank.registration.urls
import django.contrib.auth.views
import django.contrib.admindocs.urls
import django_summernote.urls

from signbank.dictionary.adminviews import (GlossListView, MorphemeListView, DatasetListView, HandshapeListView,
                                            HomonymListView, MinimalPairsListView, DatasetManagerView,
                                            DatasetDetailView, FrequencyListView, DatasetFieldChoiceView,
                                            dataset_detail_view_by_acronym, FieldChoiceView, DatasetFrequencyView,
                                            QueryListView, SemanticFieldListView, DerivationHistoryListView,
                                            SearchHistoryView, SenseListView, LemmaListView, ToggleListView,
                                            DatasetMediaView, BatchEditView, AnnotatedGlossListView,
                                            AnnotatedSentenceListView)
from signbank.dictionary.dataset_views import DatasetConstraintsView
from signbank.dictionary.views import add_image, delete_image, add_new_morpheme, add_handshape_image

from django.contrib import admin
admin.autodiscover()

from signbank.adminsite import publisher_admin

if settings.SHOW_NUMBERSIGNS:
    numbersigns_view = TemplateView.as_view(template_name='numbersigns/numbersigns.html')
else:
    numbersigns_view = TemplateView.as_view(template_name='numbersigns/underconstruction.html')

import debug_toolbar

urlpatterns = [

    re_path(r'^$', signbank.pages.views.page, name='root_page'),

    re_path(r'^dictionary/', include(signbank.dictionary.urls)),
    re_path(r'^feedback/', include(signbank.feedback.urls)),
    re_path(r'^attachments/', include(signbank.attachments.urls)),
    re_path(r'^video/', include(signbank.video.urls)),
    re_path(r'^animation/', include(signbank.animation.urls)),
    re_path(r'^image/upload/', add_image),
    re_path(r'^handshapeimage/upload/', add_handshape_image),
    re_path(r'^image/delete/(?P<pk>[0-9]+)$', delete_image),

    # re_path(r'^register.html', 'signbank.views.index'),
    re_path(r'^logout/', django.contrib.auth.views.LogoutView.as_view(), name="logout"),

    re_path(r'^spell/twohanded.html$', TemplateView.as_view(template_name='fingerspell/fingerspellingtwohanded.html')),
    re_path(r'^spell/practice.html$', TemplateView.as_view(template_name='fingerspell/fingerspellingpractice.html')),
    re_path(r'^spell/onehanded.html$', TemplateView.as_view(template_name='fingerspell/fingerspellingonehanded.html')),
    re_path(r'^numbersigns.html$', numbersigns_view),

    # Hardcoding a number of special urls:
    re_path(r'^signs/search/$', GlossListView.as_view(), {'show_all': False}, name='signs_search'),
    re_path(r'^annotatedsentences/show_all/$', login_required(AnnotatedSentenceListView.as_view()),{'show_all': True}),
    re_path(r'^signs/show_all/$', GlossListView.as_view(),{'show_all': True}),
    re_path(r'^signs/add/$', signbank.dictionary.views.add_new_sign),
    re_path(r'^signs/import_csv_create/$', signbank.dictionary.views.import_csv_create, name='import_csv_create'),
    re_path(r'^signs/import_csv_create_sentences/$', signbank.dictionary.views.import_csv_create_sentences,
            name='import_csv_create_sentences'),
    re_path(r'^signs/import_csv_update/$', signbank.dictionary.views.import_csv_update, name='import_csv_update'),
    re_path(r'^signs/import_csv_lemmas/$', signbank.dictionary.views.import_csv_lemmas, name='import_csv_lemmas'),
    re_path(r'^signs/senses/search/$', SenseListView.as_view(), name='senses_search'),
    re_path(r'^signs/annotatedgloss/search/$', AnnotatedGlossListView.as_view(), name='annotatedgloss_search'),
    re_path(r'^analysis/homonyms/$', HomonymListView.as_view(), name='admin_homonyms_list'),
    re_path(r'^ajax/homonyms/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.homonyms_ajax_complete,
                      name='homonyms_complete'),
    re_path(r'^ajax/minimalpairs/(?P<gloss_id>.*)/$', signbank.dictionary.adminviews.minimalpairs_ajax_complete,
                      name='minimalpairs_complete'),
    re_path(r'^analysis/minimalpairs/$', MinimalPairsListView.as_view(), name='admin_minimalpairs_list'),
    re_path(r'^analysis/frequencies/$', FrequencyListView.as_view(), name='admin_frequency_list'),
    re_path(r'^analysis/queries/$', QueryListView.as_view(), name='admin_query_list'),
    re_path(r'^analysis/search_history/$', SearchHistoryView.as_view(), name='admin_search_history'),
    re_path(r'^analysis/toggle_view/$', ToggleListView.as_view(), name='admin_toggle_list'),
    re_path(r'^analysis/batch_edit_view/$', BatchEditView.as_view(), name='admin_batch_edit_view'),

    re_path(r'^signs/recently_added/$', login_required(signbank.dictionary.views.recently_added_glosses),
            name='recently_added_glosses'),
    re_path(r'^signs/proposed_new/$', signbank.dictionary.views.proposed_new_signs),
    re_path(r'^handshapes/show_all/$', HandshapeListView.as_view(), {'show_all': True}),
    re_path(r'^signs/search_handshape/$', permission_required('dictionary.search_gloss')(HandshapeListView.as_view()),
                name='admin_handshape_list'),
    re_path(r'^lemmas/show_all/$', LemmaListView.as_view(), {'show_all': True}),
    re_path(r'^morphemes/search/$', permission_required('dictionary.search_gloss')(MorphemeListView.as_view()),
            name='morphemes_search'),
    re_path(r'^morphemes/show_all/$', login_required(MorphemeListView.as_view()), {'show_all': True}),
    re_path(r'^morphemes/add/$', login_required(signbank.dictionary.views.add_new_morpheme)),
    re_path(r'^feedback/overview/$', signbank.feedback.views.showfeedback),

    # A standard view for setting the language
    re_path(r'^i18n/', include('django.conf.urls.i18n')),

    # compatibility with old links - intercept and return 401
    re_path(r'^index.cfm', TemplateView.as_view(template_name='compat.html')),

    re_path(r'^accounts/', include(signbank.registration.urls)),
    re_path(r'^'+settings.ADMIN_URL+r'/doc/', include(django.contrib.admindocs.urls)),
    re_path(r'^'+settings.ADMIN_URL+r'/', admin.site.urls),

    re_path(r'^settings/field_colors/$', login_required(FieldChoiceView.as_view()), {'color': True},
        name='admin_dataset_field_choice_colors'),
    re_path(r'^settings/semanticfields/$',
                  permission_required('dictionary.search_gloss')(SemanticFieldListView.as_view()),
                  name='admin_semanticfield_list'),
    re_path(r'^settings/derivationhistory_list/$',
                  permission_required('dictionary.search_gloss')(DerivationHistoryListView.as_view()),
                  name='admin_derivationhistory_list'),

    re_path(r'^set_dark_mode/', signbank.tools.set_dark_mode, name='set_dark_mode'),

    # special admin sub site
    re_path(r'^publisher/', publisher_admin.urls),

    re_path(r'^summernote/', include(django_summernote.urls)),

    re_path(r'reload_signbank/$',signbank.tools.reload_signbank),

    re_path(r'^datasets/available', DatasetListView.as_view(), name='admin_dataset_view'),
    re_path(r'^datasets/recent_feedback$', signbank.feedback.views.recent_feedback),
    re_path(r'^datasets/select', DatasetListView.as_view(), {'select': True}, name='admin_dataset_select'),
    re_path(r'^datasets/change_selection', signbank.dictionary.update.change_dataset_selection, name='change_dataset_selection'),
    re_path(r'^datasets/unassigned_glosses', signbank.dictionary.views.show_unassigned_glosses, name="show_unassigned_glosses"),
    re_path(r'^datasets/show_glosses_with_no_lemma', signbank.dictionary.views.show_glosses_with_no_lemma, name="show_glosses_with_no_lemma"),
    re_path(r'^datasets/manage_media/(?P<pk>\d+)$', login_required(DatasetMediaView.as_view()), name='admin_dataset_media'),
    re_path(r'^datasets/checks/(?P<pk>\d+)$', login_required(DatasetConstraintsView.as_view()), name='admin_dataset_checks'),
    re_path(r'^datasets/manager', login_required(DatasetManagerView.as_view()), name='admin_dataset_manager'),
    re_path(r'^datasets/detail/(?P<pk>\d+)$', DatasetDetailView.as_view(), name='admin_dataset_detail'),
    re_path(r'^datasets/frequency/(?P<pk>\d+)$', DatasetFrequencyView.as_view(), name='admin_dataset_frequency'),
    re_path(r'^datasets/change_details/(?P<datasetid>\d+)$', signbank.dictionary.update.update_dataset, name='update_dataset'),
    re_path(r'^datasets/field_choices/$', login_required(DatasetFieldChoiceView.as_view()),
        name='admin_dataset_field_choices'),
    re_path(r'^datasets/update_excluded_choices/$', login_required(signbank.dictionary.update.update_excluded_choices),
        name='update_excluded_choices'),
    re_path(r'^datasets/(?P<acronym>.*)$', dataset_detail_view_by_acronym, name='dataset_detail_view_by_acronym'),
    re_path(r'^update/metadata/', signbank.dictionary.update.upload_metadata, name='upload_metadata'),
    re_path(r'^update/dataset_eafs/', signbank.dictionary.update.upload_eaf_files, name='upload_eaf_files'),
    re_path(r'^update/remove_eaf_files/', signbank.dictionary.update.remove_eaf_files, name='remove_eaf_files'),
                re_path(r'^__debug__/', include(debug_toolbar.urls)),
    re_path(r'^update/expiry/', signbank.dictionary.update.update_expiry, name='update_expiry'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
