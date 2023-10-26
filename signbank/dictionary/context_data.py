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
    # This is called by GlossListView, SenseListView
    last_used_dataset = None

    context['show_all'] = kwargs.get('show_all', False)

    search_type = request.GET.get('search_type')
    context['search_type'] = search_type if search_type else listview.search_type
    if 'search_type' not in request.session.keys():
        request.session['search_type'] = search_type

    if 'search' in request.GET:
        context['menu_bar_search'] = request.GET['search']

    context['view_type'] = request.GET.get('view_type', listview.view_type)

    context['web_search'] = get_web_search(request)

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

    if len(selected_datasets) == 1:
        last_used_dataset = selected_datasets.first().acronym
    elif 'last_used_dataset' in request.session.keys():
        last_used_dataset = request.session['last_used_dataset']

    context['last_used_dataset'] = last_used_dataset

    selected_datasets_signlanguage = list(SignLanguage.objects.filter(dataset__in=selected_datasets))
    sign_languages = []
    for sl in selected_datasets_signlanguage:
        if (str(sl.id), sl.name) not in sign_languages:
            sign_languages.append((str(sl.id), sl.name))
    context['sign_languages'] = sign_languages

    selected_datasets_dialects = Dialect.objects.filter(signlanguage__in=selected_datasets_signlanguage) \
        .prefetch_related('signlanguage').distinct()
    dialects = []
    for dl in selected_datasets_dialects:
        dialect_name = dl.signlanguage.name + "/" + dl.name
        dialects.append((str(dl.id), dialect_name))
    context['dialects'] = dialects

    language_query_keys = []
    for language in dataset_languages:
        glosssearch_field_name = GlossSearchForm.gloss_search_field_prefix + language.language_code_2char
        language_query_keys.append(glosssearch_field_name)
        lemma_field_name = GlossSearchForm.lemma_search_field_prefix + language.language_code_2char
        language_query_keys.append(lemma_field_name)
        keyword_field_name = GlossSearchForm.keyword_search_field_prefix + language.language_code_2char
        language_query_keys.append(keyword_field_name)
    context['language_query_keys'] = json.dumps(language_query_keys)

    return context


def get_context_data_for_gloss_search_form(request, listview, kwargs, context={}):
    # This is called by GlossListView, SenseListView
    query_parameters = listview.query_parameters

    if not context['show_all'] and ('query_parameters' in request.session.keys()
                                          and request.session['query_parameters'] not in ['', '{}']):
        # if the query parameters are available, convert them to a dictionary
        session_query_parameters = request.session['query_parameters']
        query_parameters = json.loads(session_query_parameters)

    search_form = GlossSearchForm(request.GET,
                                  languages=context['dataset_languages'],
                                  sign_languages=context['sign_languages'],
                                  dialects=context['dialects'])

    sentence_form = SentenceForm(request.GET)
    context['sentenceform'] = sentence_form

    context['query_parameters'] = json.dumps(query_parameters)
    query_parameters_keys = list(query_parameters.keys())
    context['query_parameters_keys'] = json.dumps(query_parameters_keys)

    # other parameters are in the GlossSearchForm in the template that are not initialised
    # via multiselect or language fields
    # plus semantics and phonology fields with text types
    other_parameters = ['sortOrder'] + \
                       settings.SEARCH_BY['publication'] + \
                       settings.FIELDS['phonology'] + \
                       settings.FIELDS['semantics']

    fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew']
    fields_with_choices = fields_to_fieldcategory_dict()
    multiple_select_gloss_fields = [fieldname for fieldname in fieldnames if fieldname in fields_with_choices.keys()]
    other_parameters_keys = [key for key in other_parameters if key not in multiple_select_gloss_fields]

    context['other_parameters_keys'] = json.dumps(other_parameters_keys)
    context['searchform'] = search_form

    # If the menu bar search form was used, populate the search form with the query string
    gloss_fields_to_populate = dict()
    if 'search' in request.GET and request.GET['search'] != '':
        val = request.GET['search']
        from signbank.tools import strip_control_characters
        val = strip_control_characters(val)
        gloss_fields_to_populate['search'] = escape(val)
    if 'translation' in request.GET and request.GET['translation'] != '':
        val = request.GET['translation']
        from signbank.tools import strip_control_characters
        val = strip_control_characters(val)
        gloss_fields_to_populate['translation'] = escape(val)
    gloss_fields_to_populate_keys = list(gloss_fields_to_populate.keys())
    context['gloss_fields_to_populate'] = json.dumps(gloss_fields_to_populate)
    context['gloss_fields_to_populate_keys'] = gloss_fields_to_populate_keys

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

    if hasattr(settings,
               'SEARCH_BY') and 'publication' in settings.SEARCH_BY.keys() and request.user.is_authenticated:
        context['search_by_publication_fields'] = searchform_panels(search_form, settings.SEARCH_BY['publication'])
    else:
        context['search_by_publication_fields'] = []

    multiple_select_gloss_fields.append('definitionRole')
    multiple_select_gloss_fields.append('hasComponentOfType')
    context['MULTIPLE_SELECT_GLOSS_FIELDS'] = multiple_select_gloss_fields

    fields_with_choices['definitionRole'] = 'NoteType'
    fields_with_choices['hasComponentOfType'] = 'MorphologyType'
    choices_colors = {}
    for (fieldname, field_category) in fields_with_choices.items():
        if field_category in CATEGORY_MODELS_MAPPING.keys():
            field_choices = CATEGORY_MODELS_MAPPING[field_category].objects.all()
        else:
            field_choices = FieldChoice.objects.filter(field__iexact=field_category)
        choices_colors[fieldname] = json.dumps(choicelist_queryset_to_field_colors(field_choices))

    context['field_colors'] = choices_colors

    if hasattr(settings, 'DISABLE_MOVING_THUMBNAILS_ABOVE_NR_OF_GLOSSES'):
        context[
            'DISABLE_MOVING_THUMBNAILS_ABOVE_NR_OF_GLOSSES'] = settings.DISABLE_MOVING_THUMBNAILS_ABOVE_NR_OF_GLOSSES
    else:
        context['DISABLE_MOVING_THUMBNAILS_ABOVE_NR_OF_GLOSSES'] = 0

    context['input_names_fields_and_labels'] = {}

    for topic in ['main', 'phonology', 'semantics']:

        context['input_names_fields_and_labels'][topic] = []

        for fieldname in settings.FIELDS[topic]:

            if fieldname == 'derivHist' and not settings.USE_DERIVATIONHISTORY:
                continue
            # exclude the dependent fields for Handedness, Strong Hand, and Weak Hand
            # for purposes of nested dependencies in Search form
            if fieldname not in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
                field = search_form[fieldname]
                label = field.label
                context['input_names_fields_and_labels'][topic].append((fieldname, field, label))

    context['input_names_fields_labels_handedness'] = []
    context['input_names_fields_labels_handedness'].append(('weakdrop',
                                                                  search_form['weakdrop'],
                                                                  search_form['weakdrop'].label))
    context['input_names_fields_labels_handedness'].append(('weakprop',
                                                                  search_form['weakprop'],
                                                                  search_form['weakprop'].label))

    context['input_names_fields_labels_domhndsh'] = []
    context['input_names_fields_labels_domhndsh'].append(('domhndsh_letter',
                                                                search_form['domhndsh_letter'],
                                                                search_form['domhndsh_letter'].label))
    context['input_names_fields_labels_domhndsh'].append(('domhndsh_number',
                                                                search_form['domhndsh_number'],
                                                                search_form['domhndsh_number'].label))

    context['input_names_fields_labels_subhndsh'] = []
    context['input_names_fields_labels_subhndsh'].append(('subhndsh_letter',
                                                                search_form['subhndsh_letter'],
                                                                search_form['subhndsh_letter'].label))

    context['input_names_fields_labels_subhndsh'].append(('subhndsh_number',
                                                                search_form['subhndsh_number'],
                                                                search_form['subhndsh_number'].label))

    if listview.model == Gloss:

        if hasattr(settings, 'SHOW_MORPHEME_SEARCH') and request.user.is_authenticated:
            context['SHOW_MORPHEME_SEARCH'] = settings.SHOW_MORPHEME_SEARCH
        else:
            context['SHOW_MORPHEME_SEARCH'] = False

        if hasattr(settings, 'GLOSS_LIST_DISPLAY_HEADER') and request.user.is_authenticated:
            context['GLOSS_LIST_DISPLAY_HEADER'] = settings.GLOSS_LIST_DISPLAY_HEADER
        else:
            context['GLOSS_LIST_DISPLAY_HEADER'] = []

        if hasattr(settings, 'SEARCH_BY') and 'relations' in settings.SEARCH_BY.keys() and request.user.is_authenticated:
            context['search_by_relation_fields'] = searchform_panels(search_form, settings.SEARCH_BY['relations'])
        else:
            context['search_by_relation_fields'] = []

        # This is needed to display the idgloss of the morpheme in
        # Search by Morphology: Search for gloss with this as morpheme
        # The id of the morpheme selected in the GlossSearchForm is kept in a hidden input field
        # after selection from the lookahead list
        if 'morpheme' in query_parameters.keys():
            try:
                morpheme_idgloss = Morpheme.objects.get(pk=query_parameters['morpheme']).idgloss
            except ObjectDoesNotExist:
                morpheme_idgloss = ''
        else:
            morpheme_idgloss = ''
        context['morpheme_idgloss'] = morpheme_idgloss

        context['default_dataset_lang'] = context['dataset_languages'].first().language_code_2char \
            if context['dataset_languages'] else LANGUAGE_CODE
        context['add_gloss_form'] = GlossCreateForm(request.GET,
                                                          languages=context['dataset_languages'],
                                                          user=request.user,
                                                          last_used_dataset=context['last_used_dataset'])

        context['default_dataset_lang'] = context['dataset_languages'].first().language_code_2char \
            if context['dataset_languages'] else LANGUAGE_CODE
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

    return context
