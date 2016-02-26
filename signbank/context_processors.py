from django.conf import settings

def url(request):    
    return {'URL': settings.URL,'SEPARATE_ENGLISH_IDGLOSS_FIELD':settings.SEPARATE_ENGLISH_IDGLOSS_FIELD}
