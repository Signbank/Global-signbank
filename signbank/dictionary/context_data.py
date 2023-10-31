from signbank.dictionary.models import *
from signbank.dictionary.forms import GlossSearchForm, SentenceForm, GlossCreateForm, LemmaCreateForm
from signbank.tools import get_selected_datasets_for_user, get_dataset_languages, searchform_panels
from django.http import QueryDict
from django.utils.html import escape
from signbank.dictionary.field_choices import fields_to_fieldcategory_dict
from signbank.dictionary.translate_choice_list import choicelist_queryset_to_field_colors


def get_web_search(request):
    """
    Get the inWeb value
    """
    if 'inWeb' in request.GET:
        return request.GET['inWeb'] == '2'
    elif not request.user.is_authenticated:
        return True
    else:
        return False


def get_selected_datasets(request):
    """
    Get the selected datasets
    """
    if 'selected_datasets' in request.session.keys():
        return Dataset.objects.filter(acronym__in=request.session['selected_datasets'])
    return get_selected_datasets_for_user(request.user)


def get_context_data_for_list_view(request, listview, kwargs, context={}):
    """
    Creates basic context data for several ListViews (e.g. GlossListView, SenseListView)
    """
    context['show_all'] = kwargs.get('show_all', False)
    context['view_type'] = request.GET.get('view_type', listview.view_type)
    context['menu_bar_search'] = request.GET['search'] if 'search' in request.GET else ''
    context['web_search'] = get_web_search(request)

    search_type = request.GET.get('search_type')
    context['search_type'] = search_type if search_type else listview.search_type
    if 'search_type' not in request.session.keys():
        request.session['search_type'] = search_type

    selected_datasets = get_selected_datasets(request)
    context['selected_datasets'] = selected_datasets
    dataset_languages = get_dataset_languages(selected_datasets)
    context['dataset_languages'] = dataset_languages

    # the following is needed by javascript in the case only one dataset is available
    # in order not to compute dynamically in the template
    dataset_languages_abbreviations = [language.language_code_2char for language in dataset_languages]
    context['js_dataset_languages'] = ','.join(dataset_languages_abbreviations)

    if not dataset_languages_abbreviations:
        default_dataset = Dataset.objects.get(acronym=settings.DEFAULT_DATASET_ACRONYM)
        dataset_languages_abbreviations = [default_dataset.default_language.language_code_2char]
    context['queryset_language_codes'] = dataset_languages_abbreviations

    last_used_dataset = request.session.get('last_used_dataset', None)
    if not last_used_dataset and len(selected_datasets) == 1:
        last_used_dataset = selected_datasets.first().acronym
    context['last_used_dataset'] = last_used_dataset

    context['sign_languages'] = [(sign_language.id, sign_language.name) for sign_language
                                 in SignLanguage.objects.filter(dataset__in=selected_datasets).distinct()]

    context['dialects'] = [(str(dialect.id), dialect.signlanguage.name + "/" + dialect.name) for dialect in
                           Dialect.objects.filter(signlanguage__dataset__in=selected_datasets)
                           .prefetch_related('signlanguage').distinct()]

    prefixes = [GlossSearchForm.gloss_search_field_prefix, GlossSearchForm.lemma_search_field_prefix,
                GlossSearchForm.keyword_search_field_prefix]
    context['language_query_keys'] = json.dumps([prefix + language.language_code_2char
                                                 for language in dataset_languages for prefix in prefixes])

    return context


def get_other_parameter_keys():
    # other parameters are in the GlossSearchForm in the template that are not initialised
    # via multiselect or language fields, plus semantics and phonology fields with text types
    other_parameters = ['sortOrder'] + settings.SEARCH_BY['publication'] + settings.FIELDS['phonology'] + \
                       settings.FIELDS['semantics']
    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew']
    fields_with_choices = fields_to_fieldcategory_dict()
    multiple_select_gloss_fields = [fieldname for fieldname in fieldnames if fieldname in fields_with_choices.keys()]
    other_parameters_keys = [key for key in other_parameters if key not in multiple_select_gloss_fields]
    return other_parameters_keys, multiple_select_gloss_fields, fields_with_choices


def get_gloss_fields_to_populate(request):
    # If the menu bar search form was used, populate the search form with the query string
    from signbank.tools import strip_control_characters  # TODO Why is this import here?

    return {field: escape(strip_control_characters(request.GET[field]))
            for field in ['search', 'translation']
            if field in request.GET and request.GET[field] != ''}


def get_choices_colors(fields_with_choices):
    fields_with_choices['definitionRole'] = 'NoteType'
    fields_with_choices['hasComponentOfType'] = 'MorphologyType'
    choices_colors = {}
    for (fieldname, field_category) in fields_with_choices.items():
        if field_category in CATEGORY_MODELS_MAPPING.keys():
            field_choices = CATEGORY_MODELS_MAPPING[field_category].objects.all()
        else:
            field_choices = FieldChoice.objects.filter(field__iexact=field_category)
        choices_colors[fieldname] = json.dumps(choicelist_queryset_to_field_colors(field_choices))
    return choices_colors


def get_input_names_fields_and_labels(search_form):
    input_names_fields_and_labels = {}
    for topic in ['main', 'phonology', 'semantics']:
        input_names_fields_and_labels[topic] = []
        for fieldname in settings.FIELDS[topic]:
            if fieldname == 'derivHist' and not settings.USE_DERIVATIONHISTORY:
                continue
            # exclude the dependent fields for Handedness, Strong Hand, and Weak Hand
            # for purposes of nested dependencies in Search form
            if fieldname not in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
                field = search_form[fieldname]
                input_names_fields_and_labels[topic].append((fieldname, field, field.label))
    return input_names_fields_and_labels


def get_context_data_for_gloss_search_form(request, listview, kwargs, context={}):
    # This is called by GlossListView, SenseListView
    query_parameters_in_session = request.session.get('query_parameters', '')
    query_parameters = json.loads(query_parameters_in_session) \
        if not context['show_all'] and query_parameters_in_session not in ['', '{}'] \
        else listview.query_parameters
    context['query_parameters'] = json.dumps(query_parameters)
    context['query_parameters_keys'] = json.dumps(list(query_parameters.keys()))

    search_form = GlossSearchForm(request.GET, languages=context['dataset_languages'],
                                  sign_languages=context['sign_languages'], dialects=context['dialects'])
    context['searchform'] = search_form
    context['sentenceform'] = SentenceForm(request.GET)

    other_parameter_keys, multiple_select_gloss_fields, fields_with_choices = get_other_parameter_keys()
    context['other_parameters_keys'] = json.dumps(other_parameter_keys)
    multiple_select_gloss_fields.extend(['definitionRole', 'hasComponentOfType'])
    context['MULTIPLE_SELECT_GLOSS_FIELDS'] = multiple_select_gloss_fields
    context['field_colors'] = get_choices_colors(fields_with_choices)

    gloss_fields_to_populate = get_gloss_fields_to_populate(request)
    context['gloss_fields_to_populate'] = json.dumps(gloss_fields_to_populate)
    context['gloss_fields_to_populate_keys'] = list(gloss_fields_to_populate.keys())

    context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)

    if hasattr(settings, 'SEARCH_BY') and 'publication' in settings.SEARCH_BY.keys() and request.user.is_authenticated:
        context['search_by_publication_fields'] = searchform_panels(search_form, settings.SEARCH_BY['publication'])
    else:
        context['search_by_publication_fields'] = []

    context['DISABLE_MOVING_THUMBNAILS_ABOVE_NR_OF_GLOSSES'] = \
        getattr(settings, 'DISABLE_MOVING_THUMBNAILS_ABOVE_NR_OF_GLOSSES', 0)

    context['input_names_fields_and_labels'] = get_input_names_fields_and_labels(search_form)

    context['input_names_fields_labels_handedness'] = [
        ('weakdrop', search_form['weakdrop'], search_form['weakdrop'].label),
        ('weakprop', search_form['weakprop'], search_form['weakprop'].label)
    ]
    context['input_names_fields_labels_domhndsh'] = [
        ('domhndsh_letter', search_form['domhndsh_letter'], search_form['domhndsh_letter'].label),
        ('domhndsh_number', search_form['domhndsh_number'], search_form['domhndsh_number'].label)
    ]
    context['input_names_fields_labels_subhndsh'] = [
        ('subhndsh_letter', search_form['subhndsh_letter'], search_form['subhndsh_letter'].label),
        ('subhndsh_number', search_form['subhndsh_number'], search_form['subhndsh_number'].label)
    ]

    if listview.model == Gloss:
        context['SHOW_MORPHEME_SEARCH'] = getattr(settings, 'SHOW_MORPHEME_SEARCH', False) \
            if request.user.is_authenticated else False
        context['GLOSS_LIST_DISPLAY_HEADER'] = getattr(settings, 'GLOSS_LIST_DISPLAY_HEADER', []) \
            if request.user.is_authenticated else []

        if hasattr(settings, 'SEARCH_BY') and 'relations' in settings.SEARCH_BY.keys() and request.user.is_authenticated:
            context['search_by_relation_fields'] = searchform_panels(search_form, settings.SEARCH_BY['relations'])
        else:
            context['search_by_relation_fields'] = []

        context['morpheme_idgloss'] = get_morpheme_idgloss(query_parameters)
        context['default_dataset_lang'] = context['dataset_languages'].first().language_code_2char \
            if context['dataset_languages'] else LANGUAGE_CODE
        context['add_gloss_form'] = GlossCreateForm(request.GET, languages=context['dataset_languages'],
                                                    user=request.user, last_used_dataset=context['last_used_dataset'])
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

    return context


def get_morpheme_idgloss(query_parameters):
    # This is needed to display the idgloss of the morpheme in
    # Search by Morphology: Search for gloss with this as morpheme
    # The id of the morpheme selected in the GlossSearchForm is kept in a hidden input field
    # after selection from the lookahead list
    if 'morpheme' in query_parameters.keys():
        try:
            return Morpheme.objects.get(pk=query_parameters['morpheme']).idgloss
        except ObjectDoesNotExist:
            return ''
    return ''
