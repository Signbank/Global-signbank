import json

from django.contrib import messages
from django.utils.translation import gettext, gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.http import Http404

from signbank.settings.server_specific import (DEFAULT_DATASET_ACRONYM, SHOW_DATASET_INTERFACE_OPTIONS,
                                               USE_REGULAR_EXPRESSIONS)

from signbank.video.models import GlossVideo, GlossVideoNME, GlossVideoPerspective
from signbank.dictionary.models import Dataset, Gloss
from signbank.dictionary.forms import GlossVideoSearchForm, check_language_fields
from signbank.dataset_operations import (find_unlinked_video_files_for_dataset, gloss_annotations_check,
                                         gloss_videos_check, gloss_video_filename_check, gloss_subclass_videos_check,
                                         wrong_filename_filter, get_primary_videos_for_gloss, get_backup_videos_for_gloss,
                                         get_perspective_videos_for_gloss, get_nme_videos_for_gloss, get_wrong_videos_for_gloss)
from signbank.tools import get_dataset_languages
from signbank.dictionary.adminviews import show_warning, error_message_regular_expression
from signbank.dictionary.context_data import get_selected_datasets
from signbank.query_parameters import (set_up_language_fields, query_parameters_from_get,
                                       apply_language_filters_to_results)


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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = SHOW_DATASET_INTERFACE_OPTIONS
        context['USE_REGULAR_EXPRESSIONS'] = USE_REGULAR_EXPRESSIONS

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

        # this is a ListView, but the url takes the dataset ID
        # the dataset is stored in the class self to allow sharing
        # Depending on control flow, it should be retrieved either here or in get_queryset
        if 'pk' in self.kwargs:
            self.dataset = get_object_or_404(Dataset, pk=self.kwargs['pk'])
        context = super(GlossVideoListView, self).get_context_data(**kwargs)

        context['datasetid'] = self.dataset.id
        context['dataset'] = self.dataset
        selected_datasets = get_selected_datasets(self.request)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages
        context['default_language'] = self.dataset.default_language if self.dataset else ''

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = SHOW_DATASET_INTERFACE_OPTIONS
        context['USE_REGULAR_EXPRESSIONS'] = USE_REGULAR_EXPRESSIONS

        glosses = Gloss.objects.filter(lemma__dataset=self.dataset, archived=False, morpheme=None).distinct()
        nr_of_glosses = glosses.count()
        context['nr_of_glosses'] = nr_of_glosses

        if not self.search_form.is_bound:
            # if the search_form is not bound, then initialise the dynamic language fields for the dataset
            set_up_language_fields(GlossVideo, self, self.search_form)

        context['searchform'] = self.search_form

        (gloss_videos, count_video_objects,
         count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos, count_wrong_filename) = self.get_query_set()
        context['gloss_videos'] = gloss_videos
        context['count_video_objects'] = count_video_objects
        context['count_glossvideos'] = count_glossvideos
        context['count_glossbackupvideos'] = count_glossbackupvideos
        context['count_glossperspvideos'] = count_glossperspvideos
        context['count_glossnmevideos'] = count_glossnmevideos
        context['count_wrong_filename'] = count_wrong_filename

        # data structures to store the query parameters in order to keep them in the form
        prefixes = [GlossVideoSearchForm.gloss_search_field_prefix, GlossVideoSearchForm.lemma_search_field_prefix,
                    GlossVideoSearchForm.keyword_search_field_prefix]
        context['language_query_keys'] = json.dumps([prefix + language.language_code_2char
                                                     for language in dataset_languages for prefix in prefixes])
        context['select_query_keys'] = json.dumps(['isPrimaryVideo', 'isNMEVideo', 'isPerspectiveVideo', 'isBackup', 'wrongFilename'])
        context['query_parameters'] = json.dumps(self.query_parameters)
        query_parameters_keys = list(self.query_parameters.keys())
        context['query_parameters_keys'] = json.dumps(query_parameters_keys)

        return context

    def get_query_set(self):
        selected_datasets = get_selected_datasets(self.request)
        if not selected_datasets or selected_datasets.count() > 1:
            feedback_message = _('Please select a single dataset to view video storage.')
            return show_warning(self.request, feedback_message, selected_datasets)

        if not self.dataset:
            # this depends on the evaluation order of get_context_data and get_queryset
            # sometimes this seems arbitrary
            self.dataset = selected_datasets.first()
        dataset_languages = get_dataset_languages(selected_datasets)

        if not self.search_form.is_bound:
            # if the search_form is not bound, then initialise the dynamic language fields for the dataset
            set_up_language_fields(GlossVideo, self, self.search_form)

        # initialise all template summaries to empty
        gloss_videos, count_video_objects, count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos, count_wrong_filename = [], 0, 0, 0, 0, 0, 0

        if not self.request.user.is_authenticated or not self.request.user.has_perm('dictionary.change_gloss'):
            translated_message = _('You do not have permission to manage the dataset videos.')
            return show_warning(self.request, translated_message, selected_datasets)

        get = self.request.GET
        if not get:
            # don't show anything on initial visit
            self.request.session['search_results'] = []
            self.request.session.modified = True
            return (gloss_videos, count_video_objects,
                    count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos, count_wrong_filename)

        valid_regex, search_fields, field_values = check_language_fields(self.search_form, GlossVideoSearchForm, get, dataset_languages)

        if USE_REGULAR_EXPRESSIONS and not valid_regex:
            error_message_regular_expression(self.request, search_fields, field_values)
            self.request.session['search_results'] = []
            self.request.session.modified = True
            return (gloss_videos, count_video_objects,
                    count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos, count_wrong_filename)

        qs = Gloss.objects.filter(lemma__dataset=self.dataset, archived=False, morpheme=None).distinct()

        # this is a temporary query_parameters variable
        # it is saved to self.query_parameters after the parameters are processed
        query_parameters = dict()

        query_parameters = query_parameters_from_get(self.search_form, get, query_parameters)
        qs = apply_language_filters_to_results('Gloss', qs, query_parameters)
        qs = qs.distinct()

        # the active query parameters are passed to the context via self
        self.query_parameters = query_parameters

        if 'isPrimaryVideo' in query_parameters.keys() and query_parameters['isPrimaryVideo'] == '2':
            count_glossvideos = GlossVideo.objects.filter(gloss__in=qs, version=0,
                                                          glossvideonme=None, glossvideoperspective=None).distinct().count()
        if 'isBackup' in query_parameters.keys() and query_parameters['isBackup'] == '2':
            count_glossbackupvideos = GlossVideo.objects.filter(gloss__in=qs, version__gt=0).distinct().count()
        if 'isPerspectiveVideo' in query_parameters.keys() and query_parameters['isPerspectiveVideo'] == '2':
            count_glossperspvideos = GlossVideoPerspective.objects.filter(gloss__in=qs).distinct().count()
        if 'isNMEVideo' in query_parameters.keys() and query_parameters['isNMEVideo'] == '2':
            count_glossnmevideos = GlossVideoNME.objects.filter(gloss__in=qs).distinct().count()
        if 'wrongFilename' in query_parameters.keys() and query_parameters['wrongFilename'] == '2':
            all_gloss_video_objects = GlossVideo.objects.filter(gloss__in=qs).distinct()
            gloss_video_ids = wrong_filename_filter(all_gloss_video_objects)
            count_wrong_filename = len(gloss_video_ids)
        count_video_objects = count_glossvideos + count_glossbackupvideos + count_glossperspvideos + count_glossnmevideos + count_wrong_filename

        # This is to prevent the interface from choking on backup videos
        # For NGT there are over 100,000 backup video objects
        if count_video_objects > 1000:
            translated_message = gettext("{count_video_objects} results. Please refine your query to retrieve fewer results.").format(count_video_objects=str(count_video_objects))
            messages.add_message(self.request, messages.ERROR, translated_message)
            # reset the counts of the individual objects for the template, since the query has not been done yet
            count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos, count_wrong_filename = 0, 0, 0, 0, 0
            return (gloss_videos, count_video_objects,
                    count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos, count_wrong_filename)

        # a single data structure is created that includes the various kinds of videos in a way suited to the display
        for gloss in qs:
            display_glossvideos, num_backup_videos, display_glossbackupvideos, display_perspvideos, display_nmevideos, display_wrong_videos = '', 0, '', '', '', ''
            if 'isPrimaryVideo' in query_parameters.keys() and query_parameters['isPrimaryVideo'] == '2':
                display_glossvideos = get_primary_videos_for_gloss(gloss)
            if 'isBackup' in query_parameters.keys() and query_parameters['isBackup'] == '2':
                # the number of backups for the gloss is displayed in the template
                num_backup_videos, display_glossbackupvideos = get_backup_videos_for_gloss(gloss)
            if 'isPerspectiveVideo' in query_parameters.keys() and query_parameters['isPerspectiveVideo'] == '2':
                display_perspvideos = get_perspective_videos_for_gloss(gloss)
            if 'isNMEVideo' in query_parameters.keys() and query_parameters['isNMEVideo'] == '2':
                display_nmevideos = get_nme_videos_for_gloss(gloss)
            if 'wrongFilename' in query_parameters.keys() and query_parameters['wrongFilename'] == '2':
                display_wrong_videos = get_wrong_videos_for_gloss(gloss)
            if display_glossvideos or display_glossbackupvideos or display_perspvideos or display_nmevideos or display_wrong_videos:
                gloss_videos.append((gloss, num_backup_videos, display_glossvideos,
                                     display_glossbackupvideos, display_perspvideos, display_nmevideos, display_wrong_videos))
        return (gloss_videos, count_video_objects,
                count_glossvideos, count_glossbackupvideos, count_glossperspvideos, count_glossnmevideos, count_wrong_filename)
