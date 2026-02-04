from django.core.exceptions import ObjectDoesNotExist
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.conf import settings
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect

from signbank.pages.models import Page
from signbank.tools import get_dataset_languages
from signbank.dictionary.context_data import get_selected_datasets
from signbank.settings.server_specific import USE_REGULAR_EXPRESSIONS

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
        return HttpResponseRedirect(f'{request.path}/')
    if not url.startswith('/'):
        url = "/" + url

    try:
        page = Page.objects.get(url__exact=url)
    except ObjectDoesNotExist:
        if url == '/':
            page = Page(title='No Pages', content='<p>No pages defined. Login to <a href="/admin"> to create some.</p>')
        else:
            template = loader.get_template("404.html")
            return HttpResponseNotFound(template.render(request=request))

    template = loader.select_template((page.template_name, DEFAULT_TEMPLATE)) \
                if page.template_name else loader.get_template(DEFAULT_TEMPLATE)

    page.title = mark_safe(page.title)
    page.content = mark_safe(page.content)

    selected_datasets = get_selected_datasets(request)
    dataset_languages = get_dataset_languages(selected_datasets)

    context = {
        'page': page,
        'dataset_languages': dataset_languages,
        'selected_datasets': selected_datasets,
        'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
        'USE_REGULAR_EXPRESSIONS': USE_REGULAR_EXPRESSIONS,
    }
    return HttpResponse(template.render(context, request))
