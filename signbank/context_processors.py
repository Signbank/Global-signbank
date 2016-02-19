from django.conf import settings

def url(request):    
    return {'URL': settings.URL}
