from django.conf import settings
from guardian.shortcuts import get_objects_for_user
from signbank.tools import get_selected_datasets_for_user
from signbank.dictionary.models import Dataset

def url(request):

    viewable_datasets = get_objects_for_user(request.user, 'view_dataset', Dataset)
    selected_datasets = get_selected_datasets_for_user(request.user)

    return {'URL': settings.URL,
            'PREFIX_URL': settings.PREFIX_URL,
            'viewable_datasets': [(dataset,dataset in selected_datasets) for dataset in viewable_datasets],
            'selected_datasets': selected_datasets,
            'SEPARATE_ENGLISH_IDGLOSS_FIELD':settings.SEPARATE_ENGLISH_IDGLOSS_FIELD,
            'CROP_GLOSS_IMAGES': settings.CROP_GLOSS_IMAGES}
