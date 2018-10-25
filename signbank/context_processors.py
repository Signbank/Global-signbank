from django.conf import settings
from signbank.tools import get_selected_datasets_for_user

def url(request):
    selected_datasets = get_selected_datasets_for_user(request.user)
    return {'URL': settings.URL,
            'PREFIX_URL': settings.PREFIX_URL,
            'selected_datasets': selected_datasets,
            'SEPARATE_ENGLISH_IDGLOSS_FIELD':settings.SEPARATE_ENGLISH_IDGLOSS_FIELD,
            'CROP_GLOSS_IMAGES': settings.CROP_GLOSS_IMAGES}
