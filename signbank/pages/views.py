from signbank.pages.models import *
from signbank.tools import get_dataset_languages
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.conf import settings
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect

from signbank.dictionary.context_data import get_selected_datasets


DEFAULT_TEMPLATE = 'pages/default.html'

@csrf_protect
def page(request, url='/'):
    """
    Flat page view.

    Models: `pages.page`
    Templates: Uses the template defined by the ``template_name`` field,
        or `pages/default.html` if template_name is not defined.
    Context:
        page
            `pages.page` object
    """
    if not url.endswith('/') and settings.APPEND_SLASH:
        return HttpResponseRedirect("%s/" % request.path)
    if not url.startswith('/'):
        url = "/" + url
    # here I've removed the requirement that the page be for this site
    # - this won't work if we ever have more than one site here
    # which isn't planned
    # deal with the lack of a root page
    try:
        f = Page.objects.get(url__exact=url)
    except:
        # no page, if we're after the root page then serve a default page
        if url == '/':

            f = Page(title='No Pages', 
                     content='<p>No pages defined. Login to <a href="/admin"> to create some.</p>')  
        else:
            t = loader.get_template("404.html")
            return HttpResponseNotFound(t.render(request=request))

    
    # If registration is required for accessing this page, and the user isn't
    # logged in, redirect to the login page.

    # if len(f.group_required.all()) > 0:
    #
    #      if not request.user.is_authenticated :
    #          from django.contrib.auth.views import redirect_to_login
    #          return redirect_to_login(request.path)

    if f.template_name:
        t = loader.select_template((f.template_name, DEFAULT_TEMPLATE))
    else:
        t = loader.get_template(DEFAULT_TEMPLATE)

    # To avoid having to always use the "|safe" filter in flatpage templates,
    # mark the title and content as already safe (since they are raw HTML
    # content in the first place).
    f.title = mark_safe(f.title)
    f.content = mark_safe(f.content)

    selected_datasets = get_selected_datasets(request)
    dataset_languages = get_dataset_languages(selected_datasets)

    response = HttpResponse(t.render({'page': f,
                                      'dataset_languages': dataset_languages,
                                      'selected_datasets': selected_datasets,
                                      'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS
                                      },request))
    return response