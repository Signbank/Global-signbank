from django.conf import settings
from guardian.shortcuts import get_objects_for_user
from signbank.tools import get_selected_datasets_for_user, get_datasets_with_public_glosses
from signbank.dictionary.models import Dataset

def url(request):

    if not request.user.is_authenticated():
        # for anonymous users, show datasets with public glosses in header
        viewable_datasets = get_datasets_with_public_glosses()

        if 'selected_datasets' in request.session.keys():
            selected_datasets = Dataset.objects.filter(acronym__in=request.session['selected_datasets'])
        else:
            # this happens at the start of a session
            selected_datasets = Dataset.objects.filter(acronym=settings.DEFAULT_DATASET_ACRONYM)
    else:
        # display all datasets in header
        viewable_datasets = Dataset.objects.all()
        selected_datasets = get_selected_datasets_for_user(request.user)

    return {'URL': settings.URL,
            'PREFIX_URL': settings.PREFIX_URL,
            'viewable_datasets': [(dataset, dataset in selected_datasets) for dataset in viewable_datasets],
            'selected_datasets': selected_datasets,
            'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
            'SEPARATE_ENGLISH_IDGLOSS_FIELD':settings.SEPARATE_ENGLISH_IDGLOSS_FIELD,
            'CROP_GLOSS_IMAGES': settings.CROP_GLOSS_IMAGES,
			'INTERFACE_LANGUAGE_CODES': [language_code for language_code, full_name in settings.LANGUAGES],
			'INTERFACE_LANGUAGE_SHORT_NAMES': settings.INTERFACE_LANGUAGE_SHORT_NAMES
			}
