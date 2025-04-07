import json

from signbank.dictionary.context_data import get_selected_datasets
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.core.paginator import Paginator
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from signbank.video.models import GlossVideo, GlossVideoNME, GlossVideoPerspective
from signbank.dictionary.models import Dataset, Gloss, AnnotationIdglossTranslation
from signbank.dictionary.forms import GlossVideoSearchForm
from signbank.dataset_operations import (find_unlinked_video_files_for_dataset, gloss_annotations_check, gloss_videos_check, gloss_video_filename_check, gloss_subclass_videos_check)
from signbank.tools import get_dataset_languages
from signbank.settings.server_specific import *
from guardian.shortcuts import get_objects_for_user
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from signbank.dictionary.adminviews import show_warning, error_message_regular_expression
from django.contrib import messages
from django.shortcuts import *
from django.conf import settings
from django.utils.translation import override, gettext, gettext_lazy as _, activate
from signbank.query_parameters import (set_up_language_fields, check_language_fields, query_parameters_from_get,
                                       apply_language_filters_to_results, apply_video_filters_to_results,
                                       apply_nmevideo_filters_to_results)


class DatasetConstraintsView(DetailView):
    model = Dataset
    context_object_name = 'dataset'
    template_name = 'dictionary/dataset_video_storage.html'

    # set the default dataset, this should not be empty
    dataset_acronym = DEFAULT_DATASET_ACRONYM

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets(self.request)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested dataset does not exist.')
            return show_warning(request, translated_message, selected_datasets)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        context = super(DatasetConstraintsView, self).get_context_data(**kwargs)

        dataset = context['dataset']

        selected_datasets = get_selected_datasets(self.request)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages
        context['default_language'] = dataset.default_language

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        glosses = Gloss.objects.filter(lemma__dataset=dataset, morpheme=None)
        nr_of_glosses = glosses.count()

        summary_glosses = gloss_annotations_check(dataset)
        context['glosses_with_too_many_annotations'] = summary_glosses['glosses_with_too_many_annotations']
        context['glosses_missing_annotations'] = summary_glosses['glosses_missing_annotations']

        summary_videos = gloss_videos_check(dataset)
        context['glosses_with_too_many_videos'] = summary_videos['glosses_with_too_many_videos']
        context['gloss_videos'] = summary_videos['gloss_videos']

        summary_subclass_videos = gloss_subclass_videos_check(dataset)
        context['gloss_nme_videos'] = summary_subclass_videos['gloss_nme_videos']
        context['gloss_perspective_videos'] = summary_subclass_videos['gloss_perspective_videos']

        summary_filenames = gloss_video_filename_check(dataset)
        context['glosses_with_weird_filenames'] = summary_filenames['glosses_with_weird_filenames']
        context['non_mp4_videos'] = summary_filenames['non_mp4_videos']
        context['wrong_folder'] = summary_filenames['wrong_folder']

        unlinked_video_files_for_dataset = find_unlinked_video_files_for_dataset(dataset)
        context['unlinked_video_files_for_dataset'] = unlinked_video_files_for_dataset

        context['nr_of_glosses'] = nr_of_glosses

        context['messages'] = messages.get_messages(self.request)

        return context


class GlossVideoListView(ListView):
    model = GlossVideo
    template_name = 'dictionary/admin_dataset_videos_list.html'
    dataset = None
    search_form = GlossVideoSearchForm()
    query_parameters = dict()

    def get_context_data(self, **kwargs):

        if 'pk' in self.kwargs:
            self.dataset = get_object_or_404(Dataset, pk=self.kwargs['pk'])
        context = super(GlossVideoListView, self).get_context_data(**kwargs)

        context['datasetid'] = self.dataset.id
        context['dataset'] = self.dataset
        selected_datasets = get_selected_datasets(self.request)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages
        context['default_language'] = self.dataset.default_language if self.dataset else ''

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        glosses = Gloss.objects.filter(lemma__dataset=self.dataset, archived=False, morpheme=None)
        nr_of_glosses = glosses.count()
        context['nr_of_glosses'] = nr_of_glosses

        # context['gloss_videos'] = self.get_query_set()
        if not self.search_form.is_bound:
            # if the search_form is not bound, then
            # this is the first time the get_queryset function is called for this view
            # it has already been initialised with the __init__ method, but
            # the language fields are dynamic and are not inside the form yet
            # they depend on the selected datasets which are inside the request, which
            # is not available to the __init__ method
            set_up_language_fields(GlossVideo, self, self.search_form)

        context['searchform'] = self.search_form

        (gloss_videos, count_glosses, count_glossvideos,
         count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos) = self.get_query_set()
        context['gloss_videos'] = gloss_videos
        context['count_glosses'] = count_glosses
        context['count_glossvideos'] = count_glossvideos
        context['count_glossbackupvideos'] = count_glossbackupvideos
        context['count_glossperspvideos'] = count_glossperspvideos
        context['count_glossnmevideos'] = count_glossnmevideos

        # data structures to store the query parameters in order to keep them in the form
        prefixes = [GlossVideoSearchForm.gloss_search_field_prefix, GlossVideoSearchForm.lemma_search_field_prefix,
                    GlossVideoSearchForm.keyword_search_field_prefix]
        context['language_query_keys'] = json.dumps([prefix + language.language_code_2char
                                                     for language in dataset_languages for prefix in prefixes])
        context['select_query_keys'] = json.dumps(['isNormalVideo', 'isNMEVideo', 'isPerspectiveVideo', 'isBackup'])
        context['query_parameters'] = json.dumps(self.query_parameters)
        query_parameters_keys = list(self.query_parameters.keys())
        context['query_parameters_keys'] = json.dumps(query_parameters_keys)

        return context

    def get_query_set(self):
        selected_datasets = get_selected_datasets(self.request)
        if not selected_datasets or selected_datasets.count() > 1:
            feedback_message = _('Please select a single dataset to view minimal pairs.')
            return show_warning(self.request, feedback_message, selected_datasets)

        if not self.dataset:
            # this depends on the evaluation order of get_context_data and get_queryset
            # sometimes this seems arbitrary
            self.dataset = selected_datasets.first()
        default_language = self.dataset.default_language
        dataset_languages = get_dataset_languages(selected_datasets)

        if not self.search_form.is_bound:
            # if the search_form is not bound, then
            # this is the first time the get_queryset function is called for this view
            # it has already been initialised with the __init__ method, but
            # the language fields are dynamic and are not inside the form yet
            # they depend on the selected datasets which are inside the request, which
            # is not available to the __init__ method
            set_up_language_fields(GlossVideo, self, self.search_form)

        (gloss_videos, count_glosses, count_glossvideos,
         count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos) = [], 0, 0, 0, 0, 0

        if not self.request.user.is_authenticated or not self.request.user.has_perm('dictionary.change_gloss'):
            translated_message = _('You do not have permission to manage the dataset videos.')
            return show_warning(self.request, translated_message, selected_datasets)

        get = self.request.GET
        if not get:
            # don't show anything on initial visit
            self.request.session['search_results'] = []
            self.request.session.modified = True
            return gloss_videos, count_glosses, count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos

        valid_regex, search_fields, field_values = check_language_fields(self.search_form, GlossVideoSearchForm, get, dataset_languages)

        if USE_REGULAR_EXPRESSIONS and not valid_regex:
            error_message_regular_expression(self.request, search_fields, field_values)
            self.request.session['search_results'] = []
            self.request.session.modified = True
            return gloss_videos, count_glosses, count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos

        # this is a temporary query_parameters variable
        # it is saved to self.query_parameters after the parameters are processed
        query_parameters = dict()

        qs = Gloss.objects.filter(lemma__dataset=self.dataset, archived=False, morpheme=None).distinct().order_by(
            'lemma__lemmaidglosstranslation__text').distinct()

        query_parameters = query_parameters_from_get(self.search_form, get, query_parameters)
        qs = apply_language_filters_to_results('Gloss', qs, query_parameters)
        qs = qs.distinct()

        count_glosses = qs.count()
        if 'isNormalVideo' in query_parameters.keys() and query_parameters['isNormalVideo'] == '2':
            count_glossvideos = GlossVideo.objects.filter(gloss__in=qs, version=0,
                                                          glossvideonme=None, glossvideoperspective=None).count()
        if 'isBackup' in query_parameters.keys() and query_parameters['isBackup'] == '2':
            count_glossbackupvideos = GlossVideo.objects.filter(gloss__in=qs, version__gt=0).count()
        if 'isNMEVideo' in query_parameters.keys() and query_parameters['isNMEVideo'] == '2':
            count_glossnmevideos = GlossVideoNME.objects.filter(gloss__in=qs).count()
        if 'isPerspectiveVideo' in query_parameters.keys() and query_parameters['isPerspectiveVideo'] == '2':
            count_glossperspvideos = GlossVideoPerspective.objects.filter(gloss__in=qs).count()
        count_glosses = count_glossvideos + count_glossbackupvideos + count_glossnmevideos + count_glossperspvideos

        # a single data structure is created that includes the various kinds of videos in a way suited to the display
        for gloss in qs:

            if 'isNormalVideo' in query_parameters.keys() and query_parameters['isNormalVideo'] == '2':
                glossvideos = GlossVideo.objects.filter(gloss=gloss,
                                                        version=0,
                                                        glossvideonme=None,
                                                        glossvideoperspective=None).order_by('version')
                num_normal_videos = glossvideos.count()
                if num_normal_videos:
                    list_glossvideos = ', '.join([str(gv.version)+': '+str(gv.videofile) for gv in glossvideos])
                else:
                    list_glossvideos = ''
            else:
                list_glossvideos = ''
            if 'isBackup' in query_parameters.keys() and query_parameters['isBackup'] == '2':
                backupglossvideos = GlossVideo.objects.filter(gloss=gloss, version__gt=0).order_by('version')
                num_backup_videos = backupglossvideos.count()
                if num_backup_videos:
                    list_glossbackupvideos = ', '.join([str(gv.version) + ': ' + str(gv.videofile) for gv in backupglossvideos])
                else:
                    list_glossbackupvideos = ''
            else:
                num_backup_videos = 0
                list_glossbackupvideos = ''
            if 'isNMEVideo' in query_parameters.keys() and query_parameters['isNMEVideo'] == '2':
                glossnmevideos = GlossVideoNME.objects.filter(gloss=gloss).order_by('offset')
                num_nme_videos = glossnmevideos.count()
                if num_nme_videos > 0:
                    list_nmevideos = ', '.join([str(gv.offset) + ': ' + str(gv.videofile) for gv in glossnmevideos])
                else:
                    list_nmevideos = ''
            else:
                list_nmevideos = ''
            if 'isPerspectiveVideo' in query_parameters.keys() and query_parameters['isPerspectiveVideo'] == '2':
                glossperspvideos = GlossVideoPerspective.objects.filter(gloss=gloss)
                num_persp = glossperspvideos.count()
                if num_persp > 0:
                    list_perspvideos = ', '.join([str(gv.perspective) + ': ' + str(gv.videofile) for gv in glossperspvideos])
                else:
                    list_perspvideos = ''
            else:
                list_perspvideos = ''
            if list_glossvideos or list_glossbackupvideos or list_perspvideos or list_nmevideos:
                gloss_videos.append((gloss, num_backup_videos, list_glossvideos, list_glossbackupvideos, list_perspvideos, list_nmevideos))

        # the active query parameters are passed to the context via self
        self.query_parameters = query_parameters

        return gloss_videos, count_glosses, count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos
