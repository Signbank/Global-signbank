from django.conf import settings

def url(request):    
    return {'URL': settings.URL, 'PREFIX_URL': settings.PREFIX_URL, 'SEPARATE_ENGLISH_IDGLOSS_FIELD':settings.SEPARATE_ENGLISH_IDGLOSS_FIELD,
            'CROP_GLOSS_IMAGES': settings.CROP_GLOSS_IMAGES}
