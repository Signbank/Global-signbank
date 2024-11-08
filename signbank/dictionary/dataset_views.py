
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.core.paginator import Paginator
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from signbank.dictionary.models import Dataset, Gloss, AnnotationIdglossTranslation
from signbank.dataset_checks import (gloss_annotations_check, gloss_backup_videos, rename_backup_videos,
                                     gloss_videos_check, gloss_video_filename_check, gloss_subclass_videos_check)
from signbank.tools import get_selected_datasets_for_user, get_dataset_languages
from signbank.settings.server_specific import *
from guardian.shortcuts import get_objects_for_user
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from signbank.dictionary.adminviews import show_warning
from django.contrib import messages
from django.shortcuts import *
from django.conf import settings
from django.utils.translation import override, gettext, gettext_lazy as _, activate


class DatasetConstraintsView(DetailView):
    model = Dataset
    context_object_name = 'dataset'
    template_name = 'dictionary/dataset_consistency_checks.html'

    # set the default dataset, this should not be empty
    dataset_acronym = DEFAULT_DATASET_ACRONYM

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

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

        selected_datasets = get_selected_datasets_for_user(self.request.user)
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

        bak_videos = gloss_backup_videos(dataset)
        print(bak_videos)
        rename_backup_videos(bak_videos)

        summary_subclass_videos = gloss_subclass_videos_check(dataset)
        context['gloss_nme_videos'] = summary_subclass_videos['gloss_nme_videos']
        context['gloss_perspective_videos'] = summary_subclass_videos['gloss_perspective_videos']

        summary_filenames = gloss_video_filename_check(dataset)
        context['glosses_with_weird_filenames'] = summary_filenames['glosses_with_weird_filenames']
        context['non_mp4_videos'] = summary_filenames['non_mp4_videos']
        context['wrong_folder'] = summary_filenames['wrong_folder']

        context['nr_of_glosses'] = nr_of_glosses

        context['messages'] = messages.get_messages(self.request)

        return context

