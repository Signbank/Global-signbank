
from signbank.dictionary.context_data import get_selected_datasets
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.core.paginator import Paginator
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from signbank.video.models import GlossVideo
from signbank.dictionary.models import Dataset, Gloss, AnnotationIdglossTranslation
from signbank.dictionary.forms import GlossVideoSearchForm
from signbank.dataset_operations import (find_unlinked_video_files_for_dataset, gloss_annotations_check, gloss_videos_check, gloss_video_filename_check, gloss_subclass_videos_check)
from signbank.tools import get_dataset_languages
from signbank.settings.server_specific import *
from guardian.shortcuts import get_objects_for_user
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from signbank.dictionary.adminviews import show_warning
from django.contrib import messages
from django.shortcuts import *
from django.conf import settings
from django.utils.translation import override, gettext, gettext_lazy as _, activate
from signbank.query_parameters import set_up_language_fields


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


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context

        if 'pk' in kwargs:
            self.dataset = get_object_or_404(Dataset, pk=kwargs['pk'])
        context = super(GlossVideoListView, self).get_context_data(**kwargs)

        context['dataset'] = self.dataset
        selected_datasets = get_selected_datasets(self.request)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages
        context['default_language'] = self.dataset.default_language if self.dataset else ''

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        glosses = Gloss.objects.filter(lemma__dataset=self.dataset, morpheme=None)
        nr_of_glosses = glosses.count()
        context['nr_of_glosses'] = nr_of_glosses

        context['gloss_videos'] = self.get_query_set()
        context['searchform'] = self.search_form

        return context

    def get_query_set(self):
        get = self.request.GET

        selected_datasets = get_selected_datasets(self.request)
        if not self.dataset:
            self.dataset = selected_datasets.first()
        default_language = self.dataset.default_language

        if not self.search_form.is_bound:
            # if the search_form is not bound, then
            # this is the first time the get_queryset function is called for this view
            # it has already been initialised with the __init__ method, but
            # the language fields are dynamic and are not inside the form yet
            # they depend on the selected datasets which are inside the request, which
            # is not available to the __init__ method
            set_up_language_fields(GlossVideo, self, self.search_form)

        gloss_videos = []

        all_glosses = Gloss.objects.filter(lemma__dataset=self.dataset,
                                           lemma__lemmaidglosstranslation__language=default_language).order_by(
            'lemma__lemmaidglosstranslation__text').distinct()

        for gloss in all_glosses:

            glossvideos = GlossVideo.objects.filter(gloss=gloss,
                gloss__lemma__dataset__in=selected_datasets).order_by('gloss__annotationidglosstranslation__text', 'version')

            num_videos = glossvideos.count()

            if num_videos > 0:
                list_videos = ', '.join([str(gv.version)+': '+str(gv.videofile) for gv in glossvideos])
                gloss_videos.append((gloss, num_videos, list_videos))

        return gloss_videos
