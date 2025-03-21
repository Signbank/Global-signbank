from django.conf import settings
from guardian.shortcuts import get_objects_for_user, get_user_perms
from signbank.dictionary.context_data import get_selected_datasets
from signbank.tools import get_datasets_with_public_glosses
from signbank.dictionary.models import Dataset


def url(request):

    # get the datasets with public glosses to display in the site banner
    viewable_datasets = list(get_datasets_with_public_glosses())
    # get the selected datasets to highlight in the banner
    selected_datasets = get_selected_datasets(request)
    # assumes the selected datasets are included in the viewable datasets for anonymous users
    if request.user.is_authenticated:
        # add more datasets to the banner for logged in users
        # display selected plus viewable datasets in site banner
        for dataset in Dataset.objects.all():
            if dataset in viewable_datasets:
                continue
            # dataset is not in the banner
            if dataset in selected_datasets:
                # dataset is selected but not in banner
                # make sure dataset in in banner
                viewable_datasets.append(dataset)
                continue
            # see if the user has permission to view the dataset
            permissions_for_dataset = get_user_perms(request.user, dataset)
            if 'view_dataset' in permissions_for_dataset:
                # add the dataset to the banner
                viewable_datasets.append(dataset)

    if 'dark_mode' not in request.session.keys():
        # initialise
        request.session['dark_mode'] = "False"
        request.session.modified = True

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
