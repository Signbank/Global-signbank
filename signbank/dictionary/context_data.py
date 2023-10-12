from signbank.dictionary.models import *
from signbank.dictionary.forms import GlossSearchForm
from signbank.tools import get_selected_datasets_for_user, get_dataset_languages


def get_context_data_for_list_view(request, listview, kwargs, extra_context=None):
    # This is called by GlossListView, SenseListView
    search_type = listview.search_type
    view_type = listview.view_type
    web_search = False
    queryset_language_codes = []
    last_used_dataset = None

    if extra_context is None:
        extra_context = dict()

    local_context = extra_context

    if 'show_all' in kwargs.keys():
        local_context['show_all'] = kwargs['show_all']
    else:
        local_context['show_all'] = False

    if 'search_type' in request.GET:
        search_type = request.GET['search_type']

    if 'search' in request.GET:
        local_context['menu_bar_search'] = request.GET['search']

    if 'search_type' not in request.session.keys():
        request.session['search_type'] = search_type

    local_context['search_type'] = search_type

    if 'view_type' in request.GET:
        view_type = request.GET['view_type']
    local_context['view_type'] = view_type

    if 'inWeb' in request.GET:
        web_search = request.GET['inWeb'] == '2'
    elif not request.user.is_authenticated:
        web_search = True
    local_context['web_search'] = web_search

    if request.user.is_authenticated:
        selected_datasets = get_selected_datasets_for_user(request.user)
    elif 'selected_datasets' in request.session.keys():
        selected_datasets = Dataset.objects.filter(acronym__in=request.session['selected_datasets'])
    else:
        selected_datasets = Dataset.objects.filter(acronym=settings.DEFAULT_DATASET_ACRONYM)
    local_context['selected_datasets'] = selected_datasets
    dataset_languages = get_dataset_languages(selected_datasets)
    local_context['dataset_languages'] = dataset_languages

    # the following is needed by javascript in the case only one dataset is available
    # in order not to compute dynamically in the template
    dataset_languages_abbreviations = []
    for ds in selected_datasets:
        for sdl in ds.translation_languages.all():
            if sdl.language_code_2char not in dataset_languages_abbreviations:
                dataset_languages_abbreviations.append(sdl.language_code_2char)
    js_dataset_languages = ','.join(dataset_languages_abbreviations)
    local_context['js_dataset_languages'] = js_dataset_languages

    default_dataset_acronym = settings.DEFAULT_DATASET_ACRONYM
    default_dataset = Dataset.objects.get(acronym=default_dataset_acronym)

    for lang in dataset_languages:
        if lang.language_code_2char not in queryset_language_codes:
            queryset_language_codes.append(lang.language_code_2char)
    if not queryset_language_codes:
        queryset_language_codes = [default_dataset.default_language.language_code_2char]
    if len(selected_datasets) == 1:
        last_used_dataset = selected_datasets.first().acronym
    elif 'last_used_dataset' in request.session.keys():
        last_used_dataset = request.session['last_used_dataset']

    local_context['last_used_dataset'] = last_used_dataset

    selected_datasets_signlanguage = list(SignLanguage.objects.filter(dataset__in=selected_datasets))
    sign_languages = []
    for sl in selected_datasets_signlanguage:
        if (str(sl.id), sl.name) not in sign_languages:
            sign_languages.append((str(sl.id), sl.name))
    local_context['sign_languages'] = sign_languages

    selected_datasets_dialects = Dialect.objects.filter(signlanguage__in=selected_datasets_signlanguage) \
        .prefetch_related('signlanguage').distinct()
    dialects = []
    for dl in selected_datasets_dialects:
        dialect_name = dl.signlanguage.name + "/" + dl.name
        dialects.append((str(dl.id), dialect_name))
    local_context['dialects'] = dialects

    language_query_keys = []
    for language in dataset_languages:
        glosssearch_field_name = GlossSearchForm.gloss_search_field_prefix + language.language_code_2char
        language_query_keys.append(glosssearch_field_name)
        lemma_field_name = GlossSearchForm.lemma_search_field_prefix + language.language_code_2char
        language_query_keys.append(lemma_field_name)
        keyword_field_name = GlossSearchForm.keyword_search_field_prefix + language.language_code_2char
        language_query_keys.append(keyword_field_name)
    local_context['language_query_keys'] = json.dumps(language_query_keys)

    return local_context
