import json

from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.db.models import Q, F, ExpressionWrapper, IntegerField, Count
from django.db.models import CharField, TextField, Value as V
from django.db.models import OuterRef, Subquery
from django.db.models.query import QuerySet
from django.db.models.functions import Concat
from django.db.models.fields import BooleanField, BooleanField
from django.db.models.sql.where import NothingNode, WhereNode
from django.http import HttpResponse, HttpResponseRedirect, QueryDict, JsonResponse
from django.template import RequestContext
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.paginator import Paginator
from django.utils.translation import override, gettext_lazy as _, activate
from django.utils.html import escape
from django.forms.fields import ChoiceField
from django.shortcuts import *
from django.contrib import messages
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from signbank.dictionary.templatetags.field_choice import get_field_choice
from django.contrib.auth.models import User, Group

import csv
import operator
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import datetime as DT
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_objects_for_user

from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from signbank.feedback.models import *
from signbank.video.forms import VideoUploadForGlossForm
from tagging.models import Tag, TaggedItem
from signbank.settings.base import ECV_FILE,EARLIEST_GLOSS_CREATION_DATE, FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD, \
    LANGUAGE_CODE, ECV_SETTINGS, URL, LANGUAGE_CODE_MAP, LANGUAGES, LANGUAGES_LANGUAGE_CODE_3CHAR
from signbank.settings import server_specific
from signbank.settings.server_specific import *

from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value, \
    choicelist_queryset_to_translated_dict, choicelist_queryset_to_machine_value_dict, choicelist_queryset_to_colors, \
    choicelist_queryset_to_field_colors
from signbank.dictionary.field_choices import get_static_choice_lists, get_frequencies_for_category, category_to_fields, \
    fields_to_categories, fields_to_fieldcategory_dict

from signbank.dictionary.forms import GlossSearchForm, MorphemeSearchForm
from django.forms import TypedMultipleChoiceField, ChoiceField
from signbank.dictionary.update import upload_metadata
from signbank.tools import get_selected_datasets_for_user, write_ecv_file_for_dataset, write_csv_for_handshapes, \
    construct_scrollbar, write_csv_for_minimalpairs, get_dataset_languages, get_datasets_with_public_glosses, \
    searchform_panels, map_search_results_to_gloss_list, \
    get_interface_language_and_default_language_codes
from signbank.query_parameters import convert_query_parameters_to_filter, pretty_print_query_fields, pretty_print_query_values, \
    query_parameters_this_gloss, apply_language_filters_to_results
from signbank.search_history import available_query_parameters_in_search_history, languages_in_query, display_parameters, \
    get_query_parameters, save_query_parameters, fieldnames_from_query_parameters
from signbank.frequency import import_corpus_speakers, configure_corpus_documents_for_dataset, update_corpus_counts, \
    speaker_identifiers_contain_dataset_acronym, get_names_of_updated_eaf_files, update_corpus_document_counts, \
    dictionary_speakers_to_documents, document_has_been_updated, document_to_number_of_glosses, \
    document_to_glosses, get_corpus_speakers, remove_document_from_corpus, document_identifiers_from_paths, \
    eaf_file_from_paths, documents_paths_dictionary
from signbank.dictionary.frequency_display import collect_speaker_age_data, collect_variants_data, collect_variants_age_range_data, \
                                                    collect_variants_age_sex_raw_percentage

def order_queryset_by_sort_order(get, qs, queryset_language_codes):
    """Change the sort-order of the query set, depending on the form field [sortOrder]

    This function is used both by GlossListView as well as by MorphemeListView.
    The value of [sortOrder] is 'lemma__lemmaidglosstranslation__text' by default.
    [sortOrder] is a hidden field inside the "adminsearch" html form in the template admin_gloss_list.html
    Its value is changed by clicking the up/down buttons in the second row of the search result table
    """

    # Helper: order a queryset on field [sOrder], which is a number from a list of tuples named [sListName]
    def order_queryset_by_tuple_list(qs, sOrder, sListName, bReversed):
        """Order a queryset on field [sOrder], which is a number from a list of tuples named [sListName]"""

        # Get a list of tuples for this sort-order
        tpList = list(FieldChoice.objects.filter(field=sListName).values_list('machine_value', 'name'))
        # Determine sort order: ascending is default
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrder = sOrder[1:]
        def lambda_sort_tuple(x, bReversed):
            # Order by the string-values in the tuple list
            getattr_sOrder = getattr(x, sOrder)
            if getattr_sOrder is None:
                # if the field is not set, use the machine value 0 choice
                return (True, dict(tpList)[0])
            elif getattr_sOrder.machine_value in [0,1]:
                return (True, dict(tpList)[getattr_sOrder.machine_value])
            else:
                return(bReversed, dict(tpList)[getattr(x, sOrder).machine_value])

        return sorted(qs, key=lambda x: lambda_sort_tuple(x, bReversed), reverse=bReversed)

    def order_queryset_by_annotationidglosstranslation(qs, sOrder):
        language_code_2char = sOrder[-2:]
        sOrderAsc = sOrder
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrderAsc = sOrder[1:]
        annotationidglosstranslation = AnnotationIdglossTranslation.objects.filter(gloss=OuterRef('pk')).filter(language__language_code_2char__iexact=language_code_2char).distinct()
        qs = qs.annotate(**{sOrderAsc: Subquery(annotationidglosstranslation.values('text')[:1])}).order_by(sOrder)
        return qs

    def order_queryset_by_lemmaidglosstranslation(qs, sOrder):
        language_code_2char = sOrder[-2:]
        sOrderAsc = sOrder
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrderAsc = sOrder[1:]
        lemmaidglosstranslation = LemmaIdglossTranslation.objects.filter(lemma=OuterRef('lemma'), language__language_code_2char__iexact=language_code_2char)
        qs = qs.annotate(**{sOrderAsc: Subquery(lemmaidglosstranslation.values('text')[:1])}).order_by(sOrder)
        return qs

    def order_queryset_by_translation(qs, sOrder):
        language_code_2char = sOrder[-2:]
        query_sort_parameter = 'translation__index'
        sOrderAsc = sOrder
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrderAsc = sOrder[1:]
        translations = Translation.objects.filter(gloss=OuterRef('pk')).filter(language__language_code_2char__iexact=language_code_2char).order_by(query_sort_parameter)
        qs = qs.annotate(**{sOrderAsc: Subquery(translations.values('translation__index')[:1])}).order_by(sOrder)
        return qs

    # Set the default sort order
    default_sort_order = True
    bReversed = False
    bText = True

    # See if the form contains any sort-order information
    if ('sortOrder' in get and get['sortOrder'] != ''):
        # Take the user-indicated sort order
        sOrder = get['sortOrder']
        default_sort_order = False
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            bReversed = True
    else:
        # this is important for the query
        # this is used by default_sort_order for the filtering out of annotations that start with symbols
        # so that they can be moved to the end of the results
        sOrder = 'annotationidglosstranslation__text'  # Default sort order if nothing is specified

    # The ordering method depends on the kind of field:
    # (1) text fields are ordered straightforwardly
    # (2) fields made from a choice_list need special treatment
    if (sOrder.endswith('handedness')):
        bText = False
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Handedness", bReversed)
    elif (sOrder.endswith('domhndsh') or sOrder.endswith('subhndsh')):
        bText = False
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Handshape", bReversed)
    elif (sOrder.endswith('locprim')):
        bText = False
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Location", bReversed)
    elif sOrder.startswith("annotationidglosstranslation_order_") or sOrder.startswith("-annotationidglosstranslation_order_"):
        ordered = order_queryset_by_annotationidglosstranslation(qs, sOrder)
    elif sOrder.startswith("lemmaidglosstranslation_order_") or sOrder.startswith("-lemmaidglosstranslation_order_"):
        ordered = order_queryset_by_lemmaidglosstranslation(qs, sOrder)
    elif sOrder.startswith("translation_") or sOrder.startswith("-translation_"):
        ordered = order_queryset_by_translation(qs, sOrder)
    else:
        # Use straightforward ordering on field [sOrder]
        if default_sort_order:
            lang_attr_name = settings.DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
            sort_language = 'annotationidglosstranslation__language__language_code_2char'
            if len(queryset_language_codes) == 0:
                ordered = qs
            else:
                if lang_attr_name not in queryset_language_codes:
                    lang_attr_name = queryset_language_codes[0]

                qs_empty = qs.filter(**{sOrder+'__isnull': True})
                qs_letters = qs.filter(**{sOrder+'__regex':r'^[a-zA-Z]', sort_language:lang_attr_name})
                qs_special = qs.filter(**{sOrder+'__regex':r'^[^a-zA-Z]', sort_language:lang_attr_name})

                # sort_key = sOrder
                # # Using the order_by here results in duplicating the objects!
                ordered = list(qs_letters) #.order_by(sort_key))
                ordered += list(qs_special) #.order_by(sort_key))
                ordered += list(qs_empty)
        else:
            ordered = qs
    if bReversed and bText:
        ordered.reverse()

    # return the ordered list
    return ordered


class GlossListView(ListView):

    model = Gloss
    paginate_by = 100
    only_export_ecv = False #Used to call the 'export ecv' functionality of this view without the need for an extra GET parameter
    search_type = 'sign'
    view_type = 'gloss_list'
    web_search = False
    show_all = False
    dataset_name = settings.DEFAULT_DATASET_ACRONYM
    last_used_dataset = None
    queryset_language_codes = []
    query_parameters = dict()
    search_form_data = QueryDict(mutable=True)

    def get_template_names(self):
        return ['dictionary/admin_gloss_list.html']

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(GlossListView, self).get_context_data(**kwargs)

        if 'show_all' in self.kwargs.keys():
            context['show_all'] = self.kwargs['show_all']
            self.show_all = self.kwargs['show_all']
        else:
            context['show_all'] = self.show_all

        # Retrieve the search_type,so that we know whether the search should be restricted to Gloss or not
        if 'search_type' in self.request.GET:
            self.search_type = self.request.GET['search_type']

        if 'search' in self.request.GET:
            context['menu_bar_search'] = self.request.GET['search']

        # self.request.session['search_type'] = self.search_type

        if 'view_type' in self.request.GET:
            # user is adjusting the view, leave the rest of the context alone
            self.view_type = self.request.GET['view_type']
            context['view_type'] = self.view_type


        if 'inWeb' in self.request.GET:
            # user is searching for signs / morphemes visible to anonymous uers
            self.web_search = self.request.GET['inWeb'] == '2'
        elif not self.request.user.is_authenticated:
            self.web_search = True
        context['web_search'] = self.web_search

        if self.request.user.is_authenticated:
            selected_datasets = get_selected_datasets_for_user(self.request.user)
        elif 'selected_datasets' in self.request.session.keys():
            selected_datasets = Dataset.objects.filter(acronym__in=self.request.session['selected_datasets'])
        else:
            selected_datasets = Dataset.objects.filter(acronym=settings.DEFAULT_DATASET_ACRONYM)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        # the following is needed by javascript in the case only one dataset is available
        # in order not to compute dynamically in the template
        dataset_languages_abbreviations = []
        for ds in selected_datasets:
            for sdl in ds.translation_languages.all():
                if sdl.language_code_2char not in dataset_languages_abbreviations:
                    dataset_languages_abbreviations.append(sdl.language_code_2char)
        js_dataset_languages = ','.join(dataset_languages_abbreviations)
        context['js_dataset_languages'] = js_dataset_languages


        default_dataset_acronym = settings.DEFAULT_DATASET_ACRONYM
        default_dataset = Dataset.objects.get(acronym=default_dataset_acronym)

        for lang in dataset_languages:
            if lang.language_code_2char not in self.queryset_language_codes:
                self.queryset_language_codes.append(lang.language_code_2char)
        if self.queryset_language_codes is None:
            self.queryset_language_codes = [ default_dataset.default_language.language_code_2char ]
        if len(selected_datasets) == 1:
            self.last_used_dataset = selected_datasets.first().acronym
        elif 'last_used_dataset' in self.request.session.keys():
            self.last_used_dataset = self.request.session['last_used_dataset']

        context['last_used_dataset'] = self.last_used_dataset

        selected_datasets_signlanguage = list(SignLanguage.objects.filter(dataset__in=selected_datasets))
        sign_languages = []
        for sl in selected_datasets_signlanguage:
            if (str(sl.id),sl.name) not in sign_languages:
                sign_languages.append((str(sl.id), sl.name))

        selected_datasets_dialects = Dialect.objects.filter(signlanguage__in=selected_datasets_signlanguage)\
            .prefetch_related('signlanguage').distinct()
        dialects = []
        for dl in selected_datasets_dialects:
            dialect_name = dl.signlanguage.name + "/" + dl.name
            dialects.append((str(dl.id),dialect_name))

        if not self.show_all and ('query_parameters' in self.request.session.keys() and self.request.session['query_parameters'] not in ['', '{}']):
            if 'query' in self.request.GET:
                # if the query parameters are available, convert them to a dictionary
                session_query_parameters = self.request.session['query_parameters']
                self.query_parameters = json.loads(session_query_parameters)
            elif 'search_results' not in self.request.session.keys() or not self.request.session['search_results']:
                self.query_parameters = {}
                # save the default query parameters to the sessin variable
                self.request.session['query_parameters'] = json.dumps(self.query_parameters)
                self.request.session.modified = True
                # self.request.session['query_parameters'] = ''
                # self.request.session.modified = True
            else:
                # if the query parameters are available, convert them to a dictionary
                session_query_parameters = self.request.session['query_parameters']
                self.query_parameters = json.loads(session_query_parameters)

        search_form = GlossSearchForm(self.request.GET, languages=dataset_languages, sign_languages=sign_languages,
                                          dialects=dialects)

        context['query_parameters'] = json.dumps(self.query_parameters)
        query_parameters_keys = list(self.query_parameters.keys())
        context['query_parameters_keys'] = json.dumps(query_parameters_keys)
        # other parameters are in the GlossSearchForm in the template that are not initialised via multiselect or language fields
        # plus semantics and phonology fields with text types
        other_parameters = ['sortOrder'] + \
                                settings.SEARCH_BY['publication'] + \
                                settings.SEARCH_BY['relations'] + \
                                settings.SEARCH_BY['morpheme'] + \
                                settings.FIELDS['phonology'] + \
                                settings.FIELDS['semantics']

        fieldnames = FIELDS['main']+FIELDS['phonology']+FIELDS['semantics']+['inWeb', 'isNew']
        fields_with_choices = fields_to_fieldcategory_dict()
        multiple_select_gloss_fields = [fieldname for fieldname in fieldnames if fieldname in fields_with_choices.keys()]
        other_parameters_keys = [ key for key in other_parameters if key not in multiple_select_gloss_fields ]

        context['other_parameters_keys'] = json.dumps(other_parameters_keys)

        # This is needed to display the idgloss of the morpheme in Search by Morphology: Search for gloss with this as morpheme
        # The id of the morpheme selected in the GlossSearchForm is kept in a hidden input field
        # after selection from the lookahead list
        if 'morpheme' in self.query_parameters.keys():
            try:
                morpheme_idgloss = Morpheme.objects.get(pk=self.query_parameters['morpheme']).idgloss
            except ObjectDoesNotExist:
                morpheme_idgloss = ''
        else:
            morpheme_idgloss = ''
        context['morpheme_idgloss'] = morpheme_idgloss

        gloss_search_field_prefix = "glosssearch_"
        keyword_search_field_prefix = "keyword_"
        lemma_search_field_prefix = "lemma_"
        language_query_keys = []
        for language in dataset_languages:
            glosssearch_field_name = gloss_search_field_prefix + language.language_code_2char
            language_query_keys.append(glosssearch_field_name)
            lemma_field_name = lemma_search_field_prefix + language.language_code_2char
            language_query_keys.append(lemma_field_name)
            keyword_field_name = keyword_search_field_prefix + language.language_code_2char
            language_query_keys.append(keyword_field_name)
        context['language_query_keys'] = json.dumps(language_query_keys)

        context['searchform'] = search_form
        context['search_type'] = self.search_type
        context['view_type'] = self.view_type
        context['web_search'] = self.web_search

        # If the menu bar search form was used, populate the search form with the query string
        gloss_fields_to_populate = dict()
        if 'search' in self.request.GET and self.request.GET['search'] != '':
            val = self.request.GET['search']
            from signbank.tools import strip_control_characters
            val = strip_control_characters(val)
            gloss_fields_to_populate['search'] = escape(val)
        if 'translation' in self.request.GET and self.request.GET['translation'] != '':
            val = self.request.GET['translation']
            from signbank.tools import strip_control_characters
            val = strip_control_characters(val)
            gloss_fields_to_populate['translation'] = escape(val)
        gloss_fields_to_populate_keys = list(gloss_fields_to_populate.keys())
        context['gloss_fields_to_populate'] = json.dumps(gloss_fields_to_populate)
        context['gloss_fields_to_populate_keys'] = gloss_fields_to_populate_keys

        context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE
        context['add_gloss_form'] = GlossCreateForm(self.request.GET, languages=dataset_languages, user=self.request.user, last_used_dataset=self.last_used_dataset)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'SHOW_MORPHEME_SEARCH') and self.request.user.is_authenticated:
            context['SHOW_MORPHEME_SEARCH'] = settings.SHOW_MORPHEME_SEARCH
        else:
            context['SHOW_MORPHEME_SEARCH'] = False

        if hasattr(settings, 'GLOSS_LIST_DISPLAY_HEADER') and self.request.user.is_authenticated:
            context['GLOSS_LIST_DISPLAY_HEADER'] = settings.GLOSS_LIST_DISPLAY_HEADER
        else:
            context['GLOSS_LIST_DISPLAY_HEADER'] = []

        if hasattr(settings, 'SEARCH_BY') and 'publication' in settings.SEARCH_BY.keys() and self.request.user.is_authenticated:
            context['search_by_publication_fields'] = searchform_panels(search_form, settings.SEARCH_BY['publication'])
        else:
            context['search_by_publication_fields'] = []

        if hasattr(settings, 'SEARCH_BY') and 'relations' in settings.SEARCH_BY.keys() and self.request.user.is_authenticated:
            context['search_by_relation_fields'] = searchform_panels(search_form, settings.SEARCH_BY['relations'])
        else:
            context['search_by_relation_fields'] = []

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
            context['DISABLE_MOVING_THUMBNAILS_ABOVE_NR_OF_GLOSSES'] = settings.DISABLE_MOVING_THUMBNAILS_ABOVE_NR_OF_GLOSSES
        else:
            context['DISABLE_MOVING_THUMBNAILS_ABOVE_NR_OF_GLOSSES'] = 0

        context['input_names_fields_and_labels'] = {}

        for topic in ['main','phonology','semantics']:

            context['input_names_fields_and_labels'][topic] = []

            for fieldname in settings.FIELDS[topic]:

                if fieldname == 'derivHist' and not settings.USE_DERIVATIONHISTORY:
                    continue
                # exclude the dependent fields for Handedness, Strong Hand, and Weak Hand for purposes of nested dependencies in Search form
                if fieldname not in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
                    field = search_form[fieldname]
                    label = field.label
                    context['input_names_fields_and_labels'][topic].append((fieldname,field,label))

        context['input_names_fields_labels_handedness'] = []
        field = search_form['weakdrop']
        label = field.label
        context['input_names_fields_labels_handedness'].append(('weakdrop', field, label))
        field = search_form['weakprop']
        label = field.label
        context['input_names_fields_labels_handedness'].append(('weakprop',field,label))


        context['input_names_fields_labels_domhndsh'] = []
        field = search_form['domhndsh_letter']
        label = field.label
        context['input_names_fields_labels_domhndsh'].append(('domhndsh_letter',field,label))
        field = search_form['domhndsh_number']
        label = field.label
        context['input_names_fields_labels_domhndsh'].append(('domhndsh_number',field,label))

        context['input_names_fields_labels_subhndsh'] = []
        field = search_form['subhndsh_letter']
        label = field.label
        context['input_names_fields_labels_subhndsh'].append(('subhndsh_letter',field,label))
        field = search_form['subhndsh_number']
        label = field.label
        context['input_names_fields_labels_subhndsh'].append(('subhndsh_number',field,label))

        context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

        # it is necessary to sort the object list by lemma_id in order for all glosses with the same lemma to be grouped
        # correctly in the template
        list_of_object_ids = [ g.id for g in self.object_list ]
        glosses_ordered_by_lemma_id = Gloss.objects.filter(id__in=list_of_object_ids).order_by('lemma_id')
        context['glosses_ordered_by_lemma_id'] = glosses_ordered_by_lemma_id

        if self.search_type == 'sign' or not self.request.user.is_authenticated:
            # Only count the none-morpheme glosses
            # this branch is slower than the other one
            context['glosscount'] = Gloss.none_morpheme_objects().select_related('lemma').select_related('dataset').filter(lemma__dataset__in=selected_datasets).count()
        else:
            context['glosscount'] = Gloss.objects.select_related('lemma').select_related('dataset').filter(lemma__dataset__in=selected_datasets).count()  # Count the glosses + morphemes


        context['page_number'] = context['page_obj'].number

        context['objects_on_page'] = [ g.id for g in context['page_obj'].object_list ]

        # this is needed to avoid crashing the browser if you go to the last page
        # of an extremely long list and then go to Details on the objects

        this_page_number = context['page_obj'].number
        this_paginator = context['page_obj'].paginator
        if len(self.object_list) > settings.MAX_SCROLL_BAR:
            this_page = this_paginator.page(this_page_number)
            if this_page.has_previous():
                previous_objects = this_paginator.page(this_page_number - 1).object_list
            else:
                previous_objects = []
            if this_page.has_next():
                next_objects = this_paginator.page(this_page_number + 1).object_list
            else:
                next_objects = []
            list_of_objects = previous_objects + list(context['page_obj'].object_list) + next_objects
        else:
            list_of_objects = self.object_list

        # construct scroll bar
        # the following retrieves language code for English (or DEFAULT LANGUAGE)
        # so the sorting of the scroll bar matches the default sorting of the results in Gloss List View

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        dataset_display_languages = []
        for lang in dataset_languages:
            dataset_display_languages.append(lang.language_code_2char)
        if interface_language_code in dataset_display_languages:
            lang_attr_name = interface_language_code
        else:
            lang_attr_name = default_language_code

        items = construct_scrollbar(list_of_objects, self.search_type, lang_attr_name)
        self.request.session['search_results'] = items

        if 'paginate_by' in self.request.GET:
            context['paginate_by'] = int(self.request.GET.get('paginate_by'))
            self.request.session['paginate_by'] = context['paginate_by']
        else:
            if 'paginate_by' in self.request.session.keys():
                # restore any previous paginate setting for toggling between Lemma View and Gloss List View
                # the session variable is needed when you return to the List View after looking at the Lemma View
                context['paginate_by'] = self.request.session['paginate_by']
            else:
                context['paginate_by'] = self.paginate_by

        column_headers = []
        for fieldname in settings.GLOSS_LIST_DISPLAY_FIELDS:
            field_label = Gloss._meta.get_field(fieldname).verbose_name
            column_headers.append((fieldname, field_label))
        context['column_headers'] = column_headers
        return context


    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        # Toelichting (Information about coding):
        # Django generates a new context when one toggles to Lemma View.
        # Lemma View uses a regroup on the object list and also uses the default paginate_by in self.
        # If the user resets the paginate_by in Gloss List, this setup (session variable
        # that's only retrieved for Gloss View) handles returning to the previous paginate_by.
        # Because the Lemma View is sparsely populated, if the default pagination isn't used,
        # there are pages without contents, since only Lemma's with more than one gloss are shown.
        # We're essentially remembering the previous paginate_by for when the user
        # toggles back to Gloss View after List View

        if 'paginate_by' in self.request.GET:
            paginate_by = int(self.request.GET.get('paginate_by'))
            self.request.session['paginate_by'] = paginate_by
        else:
            if self.view_type == 'lemma_groups':
                paginate_by = self.paginate_by
            elif 'paginate_by' in self.request.session.keys():
                # restore any previous paginate setting for toggling between Lemma View and Gloss List View
                # the session variable is needed when you return to the List View after looking at the Lemma View
                paginate_by = self.request.session['paginate_by']
            else:
                paginate_by = self.paginate_by

        return paginate_by


    def render_to_response(self, context):
        # Look for a 'format=json' GET argument
        if self.request.GET.get('format') == 'CSV':
            # show_all is passed by the calling template
            return self.render_to_csv_response({'show_all': self.request.GET.get('show_all')})
        elif self.request.GET.get('export_ecv') == 'ECV' or self.only_export_ecv:
            return self.render_to_ecv_export_response(context)
        else:
            return super(GlossListView, self).render_to_response(context)

    def render_to_ecv_export_response(self, context):

        # check that the user is logged in
        if self.request.user.is_authenticated:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/signs/search/')

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/signs/search/')

        try:
            dataset_object = Dataset.objects.get(name=self.dataset_name)
        except ObjectDoesNotExist:
            messages.add_message(self.request, messages.ERROR, _('No dataset with that name found.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/signs/search/')

        # make sure the user can write to this dataset
        import guardian
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = guardian.shortcuts.get_objects_for_user(self.request.user, 'change_dataset', Dataset)
        if user_change_datasets and dataset_object in user_change_datasets:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, _('No permission to export dataset.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/signs/search/')

        # if we get to here, the user is authenticated and has permission to export the dataset
        success, ecv_file = write_ecv_file_for_dataset(self.dataset_name)

        if success:
            messages.add_message(self.request, messages.INFO, _('ECV successfully updated.'))
        else:
            messages.add_message(self.request, messages.INFO, _('No ECV created for dataset.'))
        return HttpResponseRedirect(URL + settings.PREFIX_URL + '/signs/search/')

    # noinspection PyInterpreter,PyInterpreter
    def render_to_csv_response(self, context):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        if 'show_all' in context.keys():
            show_all = context['show_all']
        else:
            show_all = False

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dictionary-export.csv"'

        fieldnames = FIELDS['main']+FIELDS['phonology']+FIELDS['semantics']+FIELDS['frequency']+['inWeb', 'isNew']

        fields = [Gloss._meta.get_field(fieldname) for fieldname in fieldnames]

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        lang_attr_name = 'name_' + DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
        annotationidglosstranslation_fields = ["Annotation ID Gloss" + " (" + getattr(language, lang_attr_name) + ")"
                                               for language in dataset_languages]
        lemmaidglosstranslation_fields = ["Lemma ID Gloss" + " (" + getattr(language, lang_attr_name) + ")"
                                          for language in dataset_languages]

        keyword_fields = ["Keywords" + " (" + getattr(language, lang_attr_name) + ")"
                                               for language in dataset_languages]
        writer = csv.writer(response)

        # CSV should be the first language in the settings
        activate(LANGUAGES[0][0])
        header = ['Signbank ID', 'Dataset'] + lemmaidglosstranslation_fields + annotationidglosstranslation_fields \
                                                    + keyword_fields + [f.verbose_name.encode('ascii','ignore').decode() for f in fields]
        for extra_column in ['SignLanguages','Dialects', 'Sequential Morphology', 'Simultaneous Morphology', 'Blend Morphology',
                             'Relations to other signs','Relations to foreign signs', 'Tags', 'Notes']:
            header.append(extra_column)

        writer.writerow(header)

        if self.object_list:
            query_set = self.object_list
        else:
            query_set = self.get_queryset()

        # for some reason when show_all has been selected, the object list has become a list instead of a QuerySet
        # it was also missing elements
        # in order to simply debug print statements, it's converted to a list here to make sure it always has the same type
        if isinstance(query_set, QuerySet):
            query_set = list(query_set)
        for gloss in query_set:
            row = [str(gloss.pk), gloss.lemma.dataset.acronym]
            for language in dataset_languages:
                lemmaidglosstranslations = gloss.lemma.lemmaidglosstranslation_set.filter(language=language)
                if lemmaidglosstranslations and len(lemmaidglosstranslations) == 1:
                    # get rid of any invisible characters at the end such as \t
                    lemmatranslation = lemmaidglosstranslations.first().text.strip()
                    row.append(lemmatranslation)
                else:
                    row.append("")
            for language in dataset_languages:
                annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
                if annotationidglosstranslations and len(annotationidglosstranslations) == 1:
                    # get rid of any invisible characters at the end such as \t
                    annotation = annotationidglosstranslations.first().text.strip()
                    row.append(annotation)
                else:
                    row.append("")

            # Keywords per language
            for language in dataset_languages:
                keywords_in_language = gloss.translation_set.filter(language=language).order_by('translation__index')
                # get rid of any invisible characters at the end such as \t
                keyword_translations = [t.translation.text.strip() for t in keywords_in_language]
                if len(keyword_translations) == 1:
                    row.append(keyword_translations[0])
                elif not keyword_translations:
                    row.append("")
                else:
                    keywords_joined = ', '.join(keyword_translations)
                    row.append(keywords_joined)
            for f in fields:
                #Try the value of the choicelist
                if hasattr(f, 'field_choice_category'):
                    if hasattr(gloss, 'get_' + f.name + '_display'):
                        value = getattr(gloss, 'get_' + f.name + '_display')()
                    else:
                        field_value = getattr(gloss, f.name)
                        value = field_value.name if field_value else '-'
                elif isinstance(f, models.ForeignKey) and f.related_model == Handshape:
                    handshape_field_value = getattr(gloss, f.name)
                    value = handshape_field_value.name if handshape_field_value else '-'
                elif f.related_model == SemanticField:
                    value = ", ".join([str(sf.name) for sf in gloss.semField.all()])
                elif f.related_model == DerivationHistory:
                    value = ", ".join([str(sf.name) for sf in gloss.derivHist.all()])
                else:
                    value = getattr(gloss, f.name)

                # some legacy glosses have empty text fields of other formats
                if (f.__class__.__name__ == 'CharField' or f.__class__.__name__ == 'TextField') \
                        and value in ['-','------',' ']:
                    value = ''

                if value is None:
                    if f.name in settings.HANDEDNESS_ARTICULATION_FIELDS:
                        value = 'Neutral'
                    elif f.name in settings.HANDSHAPE_ETYMOLOGY_FIELDS:
                        value = 'False'
                    else:
                        if hasattr(f, 'field_choice_category'):
                            value = '-'
                        elif f.__class__.__name__ == 'CharField' or f.__class__.__name__ == 'TextField':
                            value = ''
                        elif f.__class__.__name__ == 'IntegerField':
                            value = 0
                        else:
                            # what to do here? leave it as None or use empty string (for export to csv)
                            value = ''

                # This was disabled with the move to Python 3... might not be needed anymore?
                # if isinstance(value,unicode):
                #     value = str(value.encode('ascii','xmlcharrefreplace'))

                if not isinstance(value,str):
                    # this is needed for csv
                    value = str(value)

                # A handshape name can begin with =. To avoid Office thinking this is a formula, preface with '
                # if value[:1] == '=':
                #     value = '\'' + value

                row.append(value)

            # get languages
            signlanguages = [signlanguage.name for signlanguage in gloss.signlanguage.all()]
            row.append(", ".join(signlanguages))

            # get dialects
            dialects = [dialect.name for dialect in gloss.dialect.all()]
            row.append(", ".join(dialects))

            # get morphology
            # Sequential Morphology
            morphemes = [morpheme.get_role()+':'+str(morpheme.morpheme.id) for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]
            row.append(", ".join(morphemes))

            # Simultaneous Morphology
            morphemes = [(str(m.morpheme.id), m.role) for m in gloss.simultaneous_morphology.all()]
            sim_morphs = []
            for m in morphemes:
                sim_morphs.append(':'.join(m))
            simultaneous_morphemes = ', '.join(sim_morphs)
            row.append(simultaneous_morphemes)

            # Blend Morphology
            ble_morphemes = [(str(m.glosses.id), m.role) for m in gloss.blend_morphology.all()]
            ble_morphs = []
            for m in ble_morphemes:
                ble_morphs.append(':'.join(m))
            blend_morphemes = ', '.join(ble_morphs)
            row.append(blend_morphemes)

            # get relations to other signs
            relations = [(relation.role, str(relation.target.id)) for relation in Relation.objects.filter(source=gloss)]
            relations_with_categories = []
            for rel_cat in relations:
                relations_with_categories.append(':'.join(rel_cat))

            relations_categories = ", ".join(relations_with_categories)
            row.append(relations_categories)

            # get relations to foreign signs
            relations = [(str(relation.loan), relation.other_lang, relation.other_lang_gloss) for relation in RelationToForeignSign.objects.filter(gloss=gloss)]
            relations_with_categories = []
            for rel_cat in relations:
                relations_with_categories.append(':'.join(rel_cat))

            relations_categories = ", ".join(relations_with_categories)
            row.append(relations_categories)

            # export tags
            tags_of_gloss = TaggedItem.objects.filter(object_id=gloss.id)
            tag_names_of_gloss = []
            for t_obj in tags_of_gloss:
                tag_id = t_obj.tag_id
                tag_name = Tag.objects.get(id=tag_id)
                tag_names_of_gloss += [str(tag_name).replace('_',' ')]

            tag_names = ", ".join(tag_names_of_gloss)
            row.append(tag_names)

            # export notes
            notes_of_gloss = gloss.definition_set.all()

            notes_list = []
            for note in notes_of_gloss:
                notes_list += [note.note_tuple()]
            sorted_notes_list = sorted(notes_list, key=lambda x: (x[0], x[1], x[2], x[3]))

            notes_list = []
            for (role, published, count, text) in sorted_notes_list:
                # does not use a comprehension because of nested parentheses in role and text fields
                tuple_reordered = role + ': (' + published + ',' + count + ',' + text + ')'
                notes_list.append(tuple_reordered)

            notes_display = ", ".join(notes_list)
            row.append(notes_display)

            #Make it safe for weird chars
            safe_row = []
            for column in row:
                try:
                    safe_row.append(column.encode('utf-8').decode())
                except AttributeError:
                    safe_row.append(None)

            writer.writerow(safe_row)

        return response


    def get_queryset(self):
        get = self.request.GET

        #First check whether we want to show everything or a subset
        if 'show_all' in self.kwargs.keys():
            show_all = self.kwargs['show_all']
        else:
            show_all = False

        #Then check what kind of stuff we want
        if 'search_type' in get:
            self.search_type = get['search_type']
        else:
            self.search_type = 'sign'

        setattr(self.request.session, 'search_type', self.search_type)

        if 'view_type' in get:
            self.view_type = get['view_type']
            # don't change query, just change display
        else:
            # set to default
            self.view_type = 'gloss_list'

        setattr(self.request, 'view_type', self.view_type)

        if 'inWeb' in self.request.GET:
            # user is searching for signs / morphemes visible to anonymous uers
            self.web_search = self.request.GET['inWeb'] == '2'
        elif not self.request.user.is_authenticated:
            self.web_search = True

        setattr(self.request, 'web_search', self.web_search)

        if self.show_all:
            self.query_parameters = dict()
            # erase the previous query
            self.request.session['query_parameters'] = json.dumps(self.query_parameters)
            self.request.session.modified = True
        elif 'query_parameters' in self.request.session.keys() \
                and self.request.session['query_parameters'] not in ['', '{}'] \
                and 'query' in self.request.GET:
            session_query_parameters = self.request.session['query_parameters']
            self.query_parameters = json.loads(session_query_parameters)
            if 'search_type' in self.query_parameters.keys() and self.query_parameters['search_type'] != 'sign':
                # Make sure on loading the query parameters that the right kind of search is done
                # this is important if the user searched on Sign or Morpheme
                self.search_type = self.query_parameters['search_type']
        else:
            self.query_parameters = dict()

        if self.request.user.is_authenticated:
            selected_datasets = get_selected_datasets_for_user(self.request.user)
        elif 'selected_datasets' in self.request.session.keys():
            selected_datasets = Dataset.objects.filter(acronym__in=self.request.session['selected_datasets'])
        else:
            selected_datasets = Dataset.objects.filter(acronym=settings.DEFAULT_DATASET_ACRONYM)
        dataset_languages = get_dataset_languages(selected_datasets)

        from signbank.dictionary.forms import check_language_fields
        valid_regex, search_fields = check_language_fields(GlossSearchForm, get, dataset_languages)

        if not valid_regex:
            error_message_1 = _('Error in search field ')
            error_message_2 = ', '.join(search_fields)
            error_message_3 = _(': Please use a backslash before special characters.')
            error_message = error_message_1 + error_message_2 + error_message_3
            messages.add_message(self.request, messages.ERROR, error_message)
            qs = Gloss.objects.none()
            return qs

        #Get the initial selection
        if show_all or (len(get) > 0 and 'query' not in self.request.GET):
            # anonymous users can search signs, make sure no morphemes are in the results
            if self.search_type == 'sign' or not self.request.user.is_authenticated:
                # Get all the GLOSS items that are not member of the sub-class Morpheme
                if SPEED_UP_RETRIEVING_ALL_SIGNS:
                    qs = Gloss.none_morpheme_objects().select_related('lemma').prefetch_related('parent_glosses').prefetch_related('simultaneous_morphology').prefetch_related('translation_set').filter(lemma__dataset__in=selected_datasets)
                else:
                    qs = Gloss.none_morpheme_objects().filter(lemma__dataset__in=selected_datasets)
            else:
                if SPEED_UP_RETRIEVING_ALL_SIGNS:
                    qs = Gloss.objects.all().prefetch_related('lemma').prefetch_related('parent_glosses').prefetch_related('simultaneous_morphology').prefetch_related('translation_set').filter(lemma__dataset__in=selected_datasets)
                else:
                    qs = Gloss.objects.all().filter(lemma__dataset__in=selected_datasets)
        elif self.query_parameters and 'query' in self.request.GET:
            if self.search_type == 'sign_or_morpheme':
                qs = Gloss.objects.all().prefetch_related('lemma').filter(lemma__dataset__in=selected_datasets)
            else:
                qs = Gloss.none_morpheme_objects().prefetch_related('lemma').filter(lemma__dataset__in=selected_datasets)

            qs = apply_language_filters_to_results(qs, self.query_parameters)
            qs = qs.distinct()

            query = convert_query_parameters_to_filter(self.query_parameters)
            if query:
                qs = qs.filter(query).distinct()

            sorted_qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)
            return sorted_qs

        #No filters or 'show_all' specified? show nothing
        else:
            qs = Gloss.objects.none()

        if self.request.user.is_authenticated and self.request.user.has_perm('dictionary.search_gloss'):
            pass
        else:
            qs = qs.filter(inWeb__exact=True)

        #If we wanted to get everything, we're done now
        if show_all:
            # sort the results
            sorted_qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)
            return sorted_qs

        # this is a temporary query_parameters variable
        # it is saved to self.query_parameters after the parameters are processed
        query_parameters = dict()

        #If not, we will go trhough a long list of filters
        if 'search' in get and get['search'] != '':
            val = get['search']
            query_parameters['search'] = val
            from signbank.tools import strip_control_characters
            val = strip_control_characters(val)
            query = Q(annotationidglosstranslation__text__iregex=val)

            if re.match('^\d+$', val):
                query = query | Q(sn__exact=val)

            qs = qs.filter(query)

        if self.search_type != 'sign':
            query_parameters['search_type'] = self.search_type

        # Evaluate all gloss/language search fields
        for get_key, get_value in get.items():
            if get_key == 'csrfmiddlewaretoken':
                continue
            if get_key.startswith(GlossSearchForm.gloss_search_field_prefix) and get_value != '':

                query_parameters[get_key] = get_value
                language_code_2char = get_key[len(GlossSearchForm.gloss_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                qs = qs.filter(annotationidglosstranslation__text__iregex=get_value,
                               annotationidglosstranslation__language=language)
            elif get_key.startswith(GlossSearchForm.lemma_search_field_prefix) and get_value != '':
                query_parameters[get_key] = get_value
                language_code_2char = get_key[len(GlossSearchForm.lemma_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                qs = qs.filter(lemma__lemmaidglosstranslation__text__iregex=get_value,
                               lemma__lemmaidglosstranslation__language=language)
            elif get_key.startswith(GlossSearchForm.keyword_search_field_prefix) and get_value != '':
                query_parameters[get_key] = get_value
                language_code_2char = get_key[len(GlossSearchForm.keyword_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                qs = qs.filter(translation__translation__text__iregex=get_value,
                               translation__language=language)
                               
        if 'translation' in get and get['translation'] != '':
            val = get['translation']
            query_parameters['translation'] = get['translation']
            qs = qs.filter(translation__translation__text__iregex=val)

        if 'inWeb' in get and get['inWeb'] != '0':
            # Don't apply 'inWeb' filter, if it is unspecified ('0' according to the NULLBOOLEANCHOICES)
            val = get['inWeb'] == '2'
            query_parameters['inWeb'] = get['inWeb']
            qs = qs.filter(inWeb__exact=val)

        if 'excludeFromEcv' in get and get['excludeFromEcv'] != '0':
            # Don't apply 'excludeFromEcv' filter, if it is unspecified ('0' according to the NULLBOOLEANCHOICES)
            val = get['excludeFromEcv'] == '2'
            query_parameters['excludeFromEcv'] = get['excludeFromEcv']
            qs = qs.filter(excludeFromEcv__exact=val)

        if 'hasvideo' in get and get['hasvideo'] not in ['unspecified', '0']:
            val = get['hasvideo'] != '2'
            query_parameters['hasvideo'] = get['hasvideo']
            qs = qs.filter(glossvideo__isnull=val)

        if 'hasothermedia' in get and get['hasothermedia'] not in ['unspecified', '0']:
            query_parameters['hasothermedia'] = get['hasothermedia']

            # Remember the pk of all glosses that have other media
            pks_for_glosses_with_othermedia = [ om.parent_gloss.pk for om in OtherMedia.objects.all() ]

            if get['hasothermedia'] == '2': #We only want glosses with other media
                qs = qs.filter(pk__in=pks_for_glosses_with_othermedia)
            elif get['hasothermedia'] == '3': #We only want glosses without other media
                qs = qs.exclude(pk__in=pks_for_glosses_with_othermedia)

        if 'defspublished' in get and get['defspublished'] != 'unspecified':
            val = get['defspublished'] == 'yes'
            query_parameters['defspublished'] = get['defspublished']
            qs = qs.filter(definition__published=val)

        fieldnames = FIELDS['main']+FIELDS['phonology']+FIELDS['semantics']+['inWeb', 'isNew']
        if not settings.USE_DERIVATIONHISTORY and 'derivHist' in fieldnames:
            fieldnames.remove('derivHist')

        # SignLanguage and basic property filters
        # allows for multiselect
        vals = get.getlist('dialect[]')
        if vals != []:
            query_parameters['dialect[]'] = vals
            qs = qs.filter(dialect__in=vals)

        vals = get.getlist('tags[]')
        if vals != []:
            query_parameters['tags[]'] = vals
            glosses_with_tag = list(
                TaggedItem.objects.filter(tag__name__in=vals).values_list('object_id', flat=True))
            qs = qs.filter(id__in=glosses_with_tag)

        # allows for multiselect
        vals = get.getlist('signlanguage[]')
        if vals != []:
            query_parameters['signlanguage[]'] = vals
            qs = qs.filter(signlanguage__in=vals)

        if 'useInstr' in get and get['useInstr'] != '':
            query_parameters['useInstr'] = get['useInstr']
            qs = qs.filter(useInstr__icontains=get['useInstr'])

        fields_with_choices = fields_to_fieldcategory_dict()
        for fieldnamemulti in fields_with_choices.keys():
            fieldnamemultiVarname = fieldnamemulti + '[]'
            fieldnameQuery = fieldnamemulti + '__machine_value__in'

            vals = get.getlist(fieldnamemultiVarname)
            if vals != []:
                query_parameters[fieldnamemultiVarname] = vals
                if fieldnamemulti == 'semField':
                    qs = qs.filter(semField__in=vals)
                elif fieldnamemulti == 'derivHist':
                    qs = qs.filter(derivHist__in=vals)
                else:
                    qs = qs.filter(**{ fieldnameQuery: vals })

        ## phonology and semantics field filters
        fieldnames = [ f for f in fieldnames if f not in fields_with_choices.keys() ]
        for fieldname in fieldnames:

            if fieldname in get and get[fieldname] != '':
                field_obj = Gloss._meta.get_field(fieldname)

                if type(field_obj) in [CharField,TextField] and not hasattr(field_obj, 'field_choice_category'):
                    key = fieldname + '__icontains'
                else:
                    key = fieldname + '__exact'

                val = get[fieldname]

                if isinstance(field_obj,BooleanField):
                    val = {'0':'','1': None, '2': True, '3': False}[val]

                if val != '':
                    query_parameters[fieldname] = get[fieldname]

                    kwargs = {key:val}
                    qs = qs.filter(**kwargs)

        qs = qs.distinct()

        if 'relationToForeignSign' in get and get['relationToForeignSign'] != '':
            query_parameters['relationToForeignSign'] = get['relationToForeignSign']

            relations = RelationToForeignSign.objects.filter(other_lang_gloss__icontains=get['relationToForeignSign'])
            potential_pks = [relation.gloss.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if 'hasRelationToForeignSign' in get and get['hasRelationToForeignSign'] != '0':
            query_parameters['hasRelationToForeignSign'] = get['hasRelationToForeignSign']

            pks_for_glosses_with_relations = [relation.gloss.pk for relation in RelationToForeignSign.objects.all()]

            if get['hasRelationToForeignSign'] == '1': #We only want glosses with a relation to a foreign sign
                qs = qs.filter(pk__in=pks_for_glosses_with_relations)
            elif get['hasRelationToForeignSign'] == '2': #We only want glosses without a relation to a foreign sign
                qs = qs.exclude(pk__in=pks_for_glosses_with_relations)

        if 'relation' in get and get['relation'] != '':
            query_parameters['relation'] = get['relation']

            potential_targets = Gloss.objects.filter(annotationidglosstranslation__text__iregex=get['relation'])
            relations = Relation.objects.filter(target__in=potential_targets)
            potential_pks = [relation.source.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if 'hasRelation' in get and get['hasRelation'] != '':
            query_parameters['hasRelation'] = get['hasRelation']

            #Find all relations with this role
            if get['hasRelation'] == 'all':
                relations_with_this_role = Relation.objects.all()
            else:
                relations_with_this_role = Relation.objects.filter(role__exact=get['hasRelation'])

            #Remember the pk of all glosses that take part in the collected relations
            pks_for_glosses_with_correct_relation = [relation.source.pk for relation in relations_with_this_role]
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_relation)

        if 'morpheme' in get and get['morpheme'] != '':
            query_parameters['morpheme'] = get['morpheme']

            # morpheme is an integer
            input_morpheme = get['morpheme']
            # Filter all glosses that contain this morpheme in their simultaneous morphology
            try:
                selected_morpheme = Morpheme.objects.get(pk=get['morpheme'])
                potential_pks = [appears.parent_gloss.pk for appears in SimultaneousMorphologyDefinition.objects.filter(morpheme=selected_morpheme)]
                qs = qs.filter(pk__in=potential_pks)
            except ObjectDoesNotExist:
                # This error should not occur, the input search form requires the selection of a morpheme from a list
                # If the user attempts to input a string, it is ignored by the gloss list search form
                print("Morpheme not found: ", str(input_morpheme))

        if 'hasComponentOfType[]' in get:
            vals = get.getlist('hasComponentOfType[]')
            if vals != []:
                query_parameters['hasComponentOfType[]'] = vals

                morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__machine_value__in=vals)
                pks_for_glosses_with_morphdefs_with_correct_role = [morphdef.parent_gloss.pk for morphdef in morphdefs_with_correct_role]
                qs = qs.filter(pk__in=pks_for_glosses_with_morphdefs_with_correct_role)

        if 'hasMorphemeOfType' in get and get['hasMorphemeOfType'] not in ['', '0']:
            query_parameters['hasMorphemeOfType'] = get['hasMorphemeOfType']

            morpheme_type = get['hasMorphemeOfType']
            # Get all Morphemes of the indicated mrpType
            target_morphemes = [ m.id for m in Morpheme.objects.filter(mrpType__machine_value=morpheme_type) ]
            qs = qs.filter(id__in=target_morphemes)

        if 'definitionRole[]' in get:

            vals = get.getlist('definitionRole[]')
            if vals != []:
                query_parameters['definitionRole[]'] = vals
                #Find all definitions with this role
                definitions_with_this_role = Definition.objects.filter(role__machine_value__in=vals)

                #Remember the pk of all glosses that are referenced in the collection definitions
                pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role]
                qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if 'definitionContains' in get and get['definitionContains'] not in ['', '0']:
            query_parameters['definitionContains'] = get['definitionContains']

            definitions_with_this_text = Definition.objects.filter(text__icontains=get['definitionContains'])

            #Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_text]
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if 'createdBefore' in get and get['createdBefore'] != '':
            query_parameters['createdBefore'] = get['createdBefore']

            created_before_date = DT.datetime.strptime(get['createdBefore'], settings.DATE_FORMAT).date()
            qs = qs.filter(creationDate__range=(EARLIEST_GLOSS_CREATION_DATE,created_before_date))

        if 'createdAfter' in get and get['createdAfter'] != '':
            query_parameters['createdAfter'] = get['createdAfter']

            created_after_date = DT.datetime.strptime(get['createdAfter'], settings.DATE_FORMAT).date()
            qs = qs.filter(creationDate__range=(created_after_date,DT.datetime.now()))

        if 'createdBy' in get and get['createdBy'] != '':
            query_parameters['createdBy'] = get['createdBy']

            created_by_search_string = ' '.join(get['createdBy'].strip().split()) # remove redundant spaces
            qs = qs.annotate(
                created_by=Concat('creator__first_name', V(' '), 'creator__last_name', output_field=CharField())) \
                .filter(created_by__icontains=created_by_search_string)

        # save the query parameters to a session variable
        self.request.session['query_parameters'] = json.dumps(query_parameters)
        self.request.session.modified = True
        self.query_parameters = query_parameters
        qs = qs.select_related('lemma')

        # Sort the queryset by the parameters given
        sorted_qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)

        self.request.session['search_type'] = self.search_type
        self.request.session['web_search'] = self.web_search

        if 'last_used_dataset' not in self.request.session.keys():
            self.request.session['last_used_dataset'] = self.last_used_dataset

        # Return the resulting filtered and sorted queryset
        return sorted_qs


class GlossDetailView(DetailView):

    model = Gloss
    context_object_name = 'gloss'
    last_used_dataset = None
    query_parameters = dict()

    def get_template_names(self):
        return ['dictionary/gloss_detail.html']

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested gloss does not exist.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})
        if self.object.lemma == None or self.object.lemma.dataset == None:
            translated_message = _('Requested gloss has no lemma or dataset.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        if not request.user.is_authenticated:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_gloss = self.object.lemma.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=False, any_perm=True)

        if dataset_of_requested_gloss not in selected_datasets:
            translated_message = _('The gloss you are trying to view is not in your selected datasets.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })
        if dataset_of_requested_gloss not in datasets_user_can_view:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss',kwargs={'glossid':self.object.pk}))
            else:
                translated_message = _('The gloss you are trying to view is not in a dataset you can view.')
                return render(request, 'dictionary/warning.html',
                              {'warning': translated_message,
                               'dataset_languages': dataset_languages,
                               'selected_datasets': selected_datasets,
                               'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []
        if search_results and len(search_results) > 0:
            if self.request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        # Call the base implementation first to get a context
        context = super(GlossDetailView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        phonology_matrix = context['gloss'].phonology_matrix_homonymns(use_machine_value=True)
        phonology_focus = [field for field in phonology_matrix.keys()
                           if phonology_matrix[field] != None
                                and phonology_matrix[field] not in ['Neutral',  '0', '1', 'False'] ]
        default_query_parameters = query_parameters_this_gloss(phonology_focus, phonology_matrix)
        default_query_parameters_mapping = pretty_print_query_fields(dataset_languages, default_query_parameters.keys())
        default_query_parameters_values_mapping = pretty_print_query_values(dataset_languages, default_query_parameters)
        context['default_query_parameters'] = default_query_parameters
        context['default_query_parameters_mapping'] = default_query_parameters_mapping
        context['default_query_parameters_values_mapping'] = default_query_parameters_values_mapping
        context['json_default_query_parameters'] = json.dumps(default_query_parameters)

        # gloss_default_parameters_query_name = "Gloss " + str(context['gloss'].id) + " Default Parameters"
        # save_query_parameters(self.request, gloss_default_parameters_query_name, default_query_parameters)

        if 'query_parameters' in self.request.session.keys() and self.request.session['query_parameters'] not in ['', '{}']:
            # if the query parameters are available, convert them to a dictionary
            session_query_parameters = self.request.session['query_parameters']
            self.query_parameters = json.loads(session_query_parameters)

        context['query_parameters'] = self.query_parameters
        query_parameters_mapping = pretty_print_query_fields(dataset_languages, self.query_parameters.keys())
        query_parameters_values_mapping = pretty_print_query_values(dataset_languages, self.query_parameters)
        context['query_parameters_mapping'] = query_parameters_mapping
        context['query_parameters_values_mapping'] = query_parameters_values_mapping

        # Add in a QuerySet of all the books
        context['tagform'] = TagUpdateForm()
        context['videoform'] = VideoUploadForGlossForm()
        context['imageform'] = ImageUploadForGlossForm()
        context['definitionform'] = DefinitionForm()
        context['relationform'] = RelationForm()
        context['morphologyform'] = GlossMorphologyForm()
        context['morphemeform'] = GlossMorphemeForm()
        context['blendform'] = GlossBlendForm()
        context['othermediaform'] = OtherMediaForm()
        context['navigation'] = context['gloss'].navigation(True)
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

        context['SIGN_NAVIGATION']  = settings.SIGN_NAVIGATION
        context['handedness'] = (int(self.object.handedness.machine_value) > 1) \
            if self.object.handedness and self.object.handedness.machine_value else 0  # minimal machine value is 2
        context['domhndsh'] = (int(self.object.domhndsh.machine_value) > 1) \
            if self.object.domhndsh and self.object.domhndsh.machine_value else 0        # minimal machine value -s 3
        context['tokNo'] = self.object.tokNo                 # Number of occurrences of Sign, used to display Stars

        # check for existence of strong hand and weak hand shapes
        try:
            strong_hand_obj = Handshape.objects.get(machine_value = self.object.domhndsh.machine_value)
        except (Handshape.DoesNotExist, AttributeError):
            strong_hand_obj = None
        context['StrongHand'] = self.object.domhndsh.machine_value if strong_hand_obj else 0
        context['WeakHand'] = self.object.subhndsh.machine_value if self.object.subhndsh else 0

        # context['NamedEntityDefined'] = (int(self.object.namEnt) > 1) if self.object.namEnt else 0        # minimal machine value is 2
        context['SemanticFieldDefined'] =  self.object.semField.all().count() > 0
        # context['ValenceDefined'] = (int(self.object.valence) > 1) if self.object.valence else 0          # minimal machine value is 2
        # context['IconicImageDefined'] = self.object.iconImage                                             # exists if not emtpy

        context['DerivationHistoryDefined'] = self.object.derivHist.all().count() > 0

        next_gloss = Gloss.objects.get(pk=context['gloss'].pk).admin_next_gloss()
        if next_gloss == None:
            context['nextglossid'] = context['gloss'].pk #context['gloss']
        else:
            context['nextglossid'] = next_gloss.pk

        if settings.SIGN_NAVIGATION:
            context['glosscount'] = Gloss.objects.count()
            context['glossposn'] =  Gloss.objects.filter(sn__lt=context['gloss'].sn).count()+1

        #Pass info about which fields we want to see
        gl = context['gloss']
        context['active_id'] = gl.id
        labels = gl.field_labels()

        # the lemma field is non-empty because it's caught in the get method
        dataset_of_requested_gloss = gl.lemma.dataset

        # set a session variable to be able to pass the gloss's id to the ajax_complete method
        # the last_used_dataset name is updated to that of this gloss
        # if a sequesce of glosses are being created by hand, this keeps the dataset setting the same
        if dataset_of_requested_gloss:
            self.request.session['datasetid'] = dataset_of_requested_gloss.pk
            self.last_used_dataset = dataset_of_requested_gloss.acronym
        else:
            # in this case the gloss does not have a dataset assigned
            print("Alert: The gloss does not have a dataset. The default dataset is assigned to session variable 'datasetid'")
            self.request.session['datasetid'] = settings.DEFAULT_DATASET_PK
            self.last_used_dataset = settings.DEFAULT_DATASET_ACRONYM

        self.request.session['last_used_dataset'] = self.last_used_dataset

        # set up weak drop weak prop fields

        context['handedness_fields'] = []
        weak_drop = getattr(gl, 'weakdrop')

        weak_prop = getattr(gl, 'weakprop')

        context['handedness_fields'].append([weak_drop,'weakdrop',labels['weakdrop'],'list'])
        context['handedness_fields'].append([weak_prop,'weakprop',labels['weakprop'],'list'])

        context['etymology_fields_dom'] = []
        domhndsh_letter = getattr(gl, 'domhndsh_letter')
        domhndsh_number = getattr(gl, 'domhndsh_number')

        context['etymology_fields_sub'] = []
        subhndsh_letter = getattr(gl, 'subhndsh_letter')
        subhndsh_number = getattr(gl, 'subhndsh_number')


        context['etymology_fields_dom'].append([domhndsh_letter,'domhndsh_letter',labels['domhndsh_letter'],'check'])
        context['etymology_fields_dom'].append([domhndsh_number,'domhndsh_number',labels['domhndsh_number'],'check'])
        context['etymology_fields_sub'].append([subhndsh_letter,'subhndsh_letter',labels['subhndsh_letter'],'check'])
        context['etymology_fields_sub'].append([subhndsh_number,'subhndsh_number',labels['subhndsh_number'],'check'])

        phonology_list_kinds = []
        gloss_phonology = []

        context['frequency_fields'] = []
        for f_field in FIELDS['frequency']:
            context['frequency_fields'].append([getattr(gl,f_field), f_field, labels[f_field], 'IntegerField'])

        context['publication_fields'] = []
        # field excludeFromEcv is added here in order to show it in Gloss Edit
        for p_field in FIELDS['publication'] + ['excludeFromEcv']:
            context['publication_fields'].append([getattr(gl,p_field), p_field, labels[p_field], 'check'])

        context['static_choice_lists'] = {}
        context['static_choice_list_colors'] = {}
        #Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['main','phonology','semantics']:
            context[topic+'_fields'] = []
            for field in FIELDS[topic]:
                # the following check will be used when querying is added, at the moment these don't appear in the phonology list
                if field not in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
                    kind = fieldname_to_kind(field)

                    if topic == 'phonology':
                        gloss_phonology.append(field)
                        # Add the kind of field
                        if kind == 'list':
                            phonology_list_kinds.append(field)

                    (static_choice_lists, static_choice_list_colors) = get_static_choice_lists(field)

                    context['static_choice_lists'][field] = static_choice_lists
                    context['static_choice_list_colors'][field] = static_choice_list_colors

                    if field in ['semField', 'derivHist']:
                        # these are many to many fields and not in the gloss table of the database
                        # they are not fields of Gloss
                        continue

                    #Take the human value in the language we are using
                    field_value = getattr(gl,field)
                    if isinstance(field_value, FieldChoice) or isinstance(field_value, Handshape):
                        if field_value:
                            # this is a FieldChoice object
                            human_value = field_value.name
                        else:
                            # if this is a field choice field, it is empty
                            human_value = field_value
                    else:
                        # otherwise, it's not a fieldchoice
                        # take care of different representations of empty text in database
                        if fieldname_to_kind(field) == 'text' and (field_value is None or field_value in ['-',' ','------','']):
                            human_value = ''
                        else:
                            human_value = field_value

                    context[topic+'_fields'].append([human_value,field,labels[field],kind])

        context['gloss_phonology'] = gloss_phonology
        context['phonology_list_kinds'] = phonology_list_kinds

        #Collect all morphology definitions for th sequential morphology section, and make some translations in advance
        morphdef_roles = FieldChoice.objects.filter(field__iexact='MorphologyType')
        morphdefs = []

        for morphdef in context['gloss'].parent_glosses.all():

            translated_role = morphdef.role.name

            sign_display = str(morphdef.morpheme.id)
            morph_texts = morphdef.morpheme.get_annotationidglosstranslation_texts()
            if morph_texts.keys():
                if interface_language_code in morph_texts.keys():
                    sign_display = morph_texts[interface_language_code]
                else:
                    sign_display = morph_texts[default_language_code]

            morphdefs.append((morphdef,translated_role,sign_display))

        morphdefs = sorted(morphdefs, key=lambda tup: tup[1])
        context['morphdefs'] = morphdefs

        (homonyms_of_this_gloss, homonyms_not_saved, saved_but_not_homonyms) = gl.homonyms()
        homonyms_different_phonology = []

        for saved_gl in saved_but_not_homonyms:
            homo_trans = {}
            if saved_gl.dataset:
                for language in saved_gl.dataset.translation_languages.all():
                    homo_trans[language.language_code_2char] = saved_gl.annotationidglosstranslation_set.filter(language=language)
            else:
                language = Language.objects.get(id=get_default_language_id())
                homo_trans[language.language_code_2char] = saved_gl.annotationidglosstranslation_set.filter(language=language)
            if interface_language_code in homo_trans:
                homo_display = homo_trans[interface_language_code][0].text
            else:
                # This should be set to the default language if the interface language hasn't been set for this gloss
                homo_display = homo_trans[default_language_code][0].text

            homonyms_different_phonology.append((saved_gl,homo_display))

        context['homonyms_different_phonology'] = homonyms_different_phonology

        homonyms_but_not_saved = []
        if homonyms_but_not_saved:
            for homonym in homonyms_not_saved:
                homo_trans = {}
                if homonym.dataset:
                    for language in homonym.dataset.translation_languages.all():
                        homo_trans[language.language_code_2char] = homonym.annotationidglosstranslation_set.filter(language=language)
                else:
                    language = Language.objects.get(id=get_default_language_id())
                    homo_trans[language.language_code_2char] = homonym.annotationidglosstranslation_set.filter(language=language)
                if interface_language_code in homo_trans.keys():
                    homo_display = homo_trans[interface_language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    homo_display = homo_trans[default_language_code][0].text

                homonyms_but_not_saved.append((homonym,homo_display))

        context['homonyms_but_not_saved'] = homonyms_but_not_saved

        # Regroup notes
        note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType')
        notes = context['gloss'].definition_set.all()
        notes_groupedby_role = {}
        for note in notes:
            if note.role is not None:
                translated_note_role = note.role.name
            else:
                translated_note_role = ''
            role_id = (note.role, translated_note_role)
            if role_id not in notes_groupedby_role:
                notes_groupedby_role[role_id] = []
            notes_groupedby_role[role_id].append(note)
        context['notes_groupedby_role'] = notes_groupedby_role

        #Gather the OtherMedia
        context['other_media'] = []
        context['other_media_field_choices'] = {}
        other_media_type_choice_list = FieldChoice.objects.filter(field__iexact='OthermediaType')

        for other_media in gl.othermedia_set.all():
            media_okay, path, other_media_filename = other_media.get_othermedia_path(gl.id, check_existence=True)

            human_value_media_type = other_media.type.name

            import mimetypes
            file_type = mimetypes.guess_type(path, strict=True)[0]

            context['other_media'].append([media_okay, other_media.pk, path, file_type, human_value_media_type, other_media.alternative_gloss, other_media_filename])

            # Save the other_media_type choices (same for every other_media, but necessary because they all have other ids)
            context['other_media_field_choices'][
                'other-media-type_' + str(other_media.pk)] = choicelist_queryset_to_translated_dict(other_media_type_choice_list)

        context['other_media_field_choices'] = json.dumps(context['other_media_field_choices'])

        context['separate_english_idgloss_field'] = SEPARATE_ENGLISH_IDGLOSS_FIELD

        try:
            lemma_group_count = gl.lemma.gloss_set.count()
            if lemma_group_count > 1:
                context['lemma_group'] = True
                lemma_group_url_params = {'search_type': 'sign', 'view_type': 'lemma_groups'}
                for lemmaidglosstranslation in gl.lemma.lemmaidglosstranslation_set.prefetch_related('language'):
                    lang_code_2char = lemmaidglosstranslation.language.language_code_2char
                    lemma_group_url_params['lemma_'+lang_code_2char] = '^' + lemmaidglosstranslation.text + '$'
                from urllib.parse import urlencode
                url_query = urlencode(lemma_group_url_params)
                url_query = ("?" + url_query) if url_query else ''
                context['lemma_group_url'] = reverse_lazy('signs_search') + url_query
            else:
                context['lemma_group'] = False
                context['lemma_group_url'] = ''
        except:
            print("lemma_group_count: except")
            context['lemma_group'] = False
            context['lemma_group_url'] = ''

        gloss_annotations = gl.annotationidglosstranslation_set.all()
        if gloss_annotations:
            gloss_default_annotationidglosstranslation = gl.annotationidglosstranslation_set.get(language=default_language).text
        else:
            gloss_default_annotationidglosstranslation = str(gl.id)
        # Put annotation_idgloss per language in the context
        context['annotation_idgloss'] = {}
        for language in gl.dataset.translation_languages.all():
            try:
                annotation_text = gl.annotationidglosstranslation_set.get(language=language).text
            except (ObjectDoesNotExist):
                annotation_text = gloss_default_annotationidglosstranslation
            context['annotation_idgloss'][language] = annotation_text

        # Put translations (keywords) per language in the context
        context['translations_per_language'] = {}
        if gl.dataset:
            for language in gl.dataset.translation_languages.all():
                context['translations_per_language'][language] = gl.translation_set.filter(language=language).order_by('translation__index')
        else:
            language = Language.objects.get(id=get_default_language_id())
            context['translations_per_language'][language] = gl.translation_set.filter(language=language).order_by('translation__index')

        bad_dialect = False
        gloss_dialects = []

        try:
            gloss_signlanguage = gl.lemma.dataset.signlanguage
        except:
            gloss_signlanguage = None
            # this is needed to catch legacy code
        initial_gloss_dialects = gl.dialect.all()
        if gloss_signlanguage:
            gloss_dialect_choices = Dialect.objects.filter(signlanguage=gloss_signlanguage)
        else:
            gloss_dialect_choices = []

        for gd in initial_gloss_dialects:
            if gd in gloss_dialect_choices:
                gloss_dialects.append(gd)
            else:
                bad_dialect = True
                print('Bad dialect found in gloss ', gl.pk, ': ', gd)

        context['gloss_dialects'] = gloss_dialects

        # This is a patch
        if bad_dialect:
            print('PATCH: Remove bad dialect from gloss ', gl.pk)
            # take care of bad dialects due to evolution of Lemma, Dataset, SignLanguage setup
            gl.dialect.clear()
            for d in gloss_dialects:
                gl.dialect.add(d)

        gloss_semanticfields = []
        for sf in gl.semField.all():
            gloss_semanticfields.append(sf)

        context['gloss_semanticfields'] = gloss_semanticfields


        gloss_derivationhistory = []
        for sf in gl.derivHist.all():
            gloss_derivationhistory.append(sf)

        context['gloss_derivationhistory'] = gloss_derivationhistory


        simultaneous_morphology = []
        sim_morph_typ_choices = FieldChoice.objects.filter(field__iexact='MorphemeType')

        if gl.simultaneous_morphology:
            for sim_morph in gl.simultaneous_morphology.all():
                translated_morph_type = sim_morph.morpheme.mrpType.name

                morpheme_annotation_idgloss = {}
                if sim_morph.morpheme.dataset:
                    for language in sim_morph.morpheme.dataset.translation_languages.all():
                        morpheme_annotation_idgloss[language.language_code_2char] = sim_morph.morpheme.annotationidglosstranslation_set.filter(language=language)
                else:
                    language = Language.objects.get(id=get_default_language_id())
                    morpheme_annotation_idgloss[language.language_code_2char] = sim_morph.morpheme.annotationidglosstranslation_set.filter(language=language)
                if interface_language_code in morpheme_annotation_idgloss.keys():
                    morpheme_display = morpheme_annotation_idgloss[interface_language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    morpheme_display = morpheme_annotation_idgloss[default_language_code][0].text

                simultaneous_morphology.append((sim_morph,morpheme_display,translated_morph_type))

        context['simultaneous_morphology'] = simultaneous_morphology

        # Obtain the number of morphemes in the dataset of this gloss
        # The template will not show the facility to add simultaneous morphology if there are no morphemes to choose from
        dataset_id_of_gloss = gl.dataset
        count_morphemes_in_dataset = Morpheme.objects.filter(lemma__dataset=dataset_id_of_gloss).count()
        context['count_morphemes_in_dataset'] = count_morphemes_in_dataset

        blend_morphology = []

        if gl.blend_morphology:
            for ble_morph in gl.blend_morphology.all():

                glosses_annotation_idgloss = {}
                if ble_morph.glosses.dataset:
                    for language in ble_morph.glosses.dataset.translation_languages.all():
                        glosses_annotation_idgloss[language.language_code_2char] = ble_morph.glosses.annotationidglosstranslation_set.filter(language=language)
                else:
                    language = Language.objects.get(id=get_default_language_id())
                    glosses_annotation_idgloss[language.language_code_2char] = ble_morph.glosses.annotationidglosstranslation_set.filter(language=language)
                if interface_language_code in glosses_annotation_idgloss.keys():
                    morpheme_display = glosses_annotation_idgloss[interface_language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    morpheme_display = glosses_annotation_idgloss[default_language_code][0].text

                blend_morphology.append((ble_morph,morpheme_display))

        context['blend_morphology'] = blend_morphology

        otherrelations = []

        if gl.relation_sources:
            for oth_rel in gl.relation_sources.all():

                other_relations_dict = {}
                if oth_rel.target.dataset:
                    for language in oth_rel.target.dataset.translation_languages.all():
                        other_relations_dict[language.language_code_2char] = oth_rel.target.annotationidglosstranslation_set.filter(language=language)
                else:
                    language = Language.objects.get(id=get_default_language_id())
                    other_relations_dict[language.language_code_2char] = oth_rel.target.annotationidglosstranslation_set.filter(language=language)
                if interface_language_code in other_relations_dict.keys():
                    target_display = other_relations_dict[interface_language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    target_display = other_relations_dict[default_language_code][0].text

                otherrelations.append((oth_rel,target_display))

        context['otherrelations'] = otherrelations

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['dataset_choices'] = {}
            user = self.request.user
            if user.is_authenticated:
                qs = get_objects_for_user(user, ['view_dataset', 'can_view_dataset'], Dataset, accept_global_perms=False, any_perm=True)
                dataset_choices = {}
                for dataset in qs:
                    dataset_choices[dataset.acronym] = dataset.acronym
                context['dataset_choices'] = json.dumps(dataset_choices)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'SHOW_LETTER_NUMBER_PHONOLOGY'):
            context['SHOW_LETTER_NUMBER_PHONOLOGY'] = settings.SHOW_LETTER_NUMBER_PHONOLOGY
        else:
            context['SHOW_LETTER_NUMBER_PHONOLOGY'] = False

        if hasattr(settings, 'USE_DERIVATIONHISTORY') and settings.USE_DERIVATIONHISTORY:
            context['USE_DERIVATIONHISTORY'] = settings.USE_DERIVATIONHISTORY
        else:
            context['USE_DERIVATIONHISTORY'] = False

        if hasattr(settings, 'SHOW_QUERY_PARAMETERS_AS_BUTTON') and settings.SHOW_QUERY_PARAMETERS_AS_BUTTON:
            context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = settings.SHOW_QUERY_PARAMETERS_AS_BUTTON
        else:
            context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = False

        gloss_is_duplicate = False
        annotationidglosstranslations = gl.annotationidglosstranslation_set.all()
        for annotation in annotationidglosstranslations:
            if "-duplicate" in annotation.text:
                gloss_is_duplicate = True
        context['gloss_is_duplicate'] = gloss_is_duplicate

        return context

    def post(self, request, *args, **kwargs):
        if request.method != "POST" or not request.POST or request.POST.get('use_default_query_parameters') != 'default_parameters':
            return redirect(reverse('admin_gloss_view'))
        # set up gloss details default parameters here
        default_parameters = request.POST.get('default_parameters')
        request.session['query_parameters'] = default_parameters
        request.session.modified = True
        return redirect(settings.PREFIX_URL + '/signs/search/?query')

    def render_to_response(self, context):
        if self.request.GET.get('format') == 'Copy':
            return self.copy_gloss(context)
        else:
            return super(GlossDetailView, self).render_to_response(context)

    def copy_gloss(self, context):
        gl = context['gloss']
        context['active_id'] = gl.id

        annotationidglosstranslations = gl.annotationidglosstranslation_set.all()
        for annotation in annotationidglosstranslations:
            if "-duplicate" in annotation.text:
                # go back to the same page, this is already a duplicate
                return HttpResponseRedirect('/dictionary/gloss/' + str(gl.id))

        new_gloss = Gloss()
        dataset_pk = self.request.GET.get('dataset')
        dataset = Dataset.objects.get(pk=dataset_pk)
        if gl.lemma.dataset == dataset:
            setattr(new_gloss, 'lemma', getattr(gl, 'lemma'))
        else:
            # need to create a lemma for this gloss in the other dataset
            new_lemma = LemmaIdgloss(dataset=dataset)
            new_lemma.save()
            existing_lemma_translations = gl.lemma.lemmaidglosstranslation_set.all()
            for lemma_translation in existing_lemma_translations:
                new_lemma_text = lemma_translation.text + '-duplicate'
                duplication_lemma_translation = LemmaIdglossTranslation(lemma=new_lemma, language=lemma_translation.language,
                                                                      text=new_lemma_text)
                duplication_lemma_translation.save()
            setattr(new_gloss, 'lemma', new_lemma)

        for field in settings.FIELDS['phonology']:
            setattr(new_gloss, field, getattr(gl, field))
        new_gloss.save()
        new_gloss.creator.add(self.request.user)
        new_gloss.creationDate = DT.datetime.now()
        new_gloss.save()
        annotationidglosstranslations = gl.annotationidglosstranslation_set.all()
        for annotation in annotationidglosstranslations:
            new_annotation_text = annotation.text+'-duplicate'
            duplication_annotation = AnnotationIdglossTranslation(gloss=new_gloss, language=annotation.language, text=new_annotation_text)
            duplication_annotation.save()

        self.request.session['last_used_dataset'] = dataset.acronym

        return HttpResponseRedirect('/dictionary/gloss/'+str(new_gloss.id) + '?edit')


class GlossVideosView(DetailView):

    model = Gloss
    context_object_name = 'gloss'
    last_used_dataset = None
    template_name = 'dictionary/gloss_videos.html'

    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested gloss does not exist.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})
        if self.object.lemma == None or self.object.lemma.dataset == None:
            translated_message = _('Requested gloss has no lemma or dataset.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        if not request.user.is_authenticated:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_gloss = self.object.lemma.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=False, any_perm=True)

        if dataset_of_requested_gloss not in selected_datasets:
            translated_message = _('The gloss you are trying to view is not in your selected datasets.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })
        if dataset_of_requested_gloss not in datasets_user_can_view:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss',kwargs={'glossid':self.object.pk}))
            else:
                translated_message = _('The gloss you are trying to view is not in a dataset you can view.')
                return render(request, 'dictionary/warning.html',
                              {'warning': translated_message,
                               'dataset_languages': dataset_languages,
                               'selected_datasets': selected_datasets,
                               'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []
        if search_results and len(search_results) > 0:
            if self.request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []

        # Call the base implementation first to get a context
        context = super(GlossVideosView, self).get_context_data(**kwargs)

        next_gloss = Gloss.objects.get(pk=context['gloss'].pk).admin_next_gloss()
        if next_gloss == None:
            context['nextglossid'] = context['gloss'].pk #context['gloss']
        else:
            context['nextglossid'] = next_gloss.pk

        if settings.SIGN_NAVIGATION:
            context['glosscount'] = Gloss.objects.count()
            context['glossposn'] =  Gloss.objects.filter(sn__lt=context['gloss'].sn).count()+1

        #Pass info about which fields we want to see
        gl = context['gloss']
        context['active_id'] = gl.id
        labels = gl.field_labels()

        # Gather the OtherMedia
        context['other_media'] = []
        context['other_media_field_choices'] = {}
        other_media_type_choice_list = FieldChoice.objects.filter(field__iexact='OthermediaType')

        for other_media in gl.othermedia_set.all():
            media_okay, path, other_media_filename = other_media.get_othermedia_path(gl.id, check_existence=True)
            other_media_type_machine_value = other_media.type.machine_value if other_media.type else 0
            human_value_media_type = machine_value_to_translated_human_value(other_media_type_machine_value,other_media_type_choice_list)

            import mimetypes
            file_type = mimetypes.guess_type(path, strict=True)[0]
            context['other_media'].append([media_okay, other_media.pk, path, file_type, human_value_media_type, other_media.alternative_gloss, other_media_filename])

            # Save the other_media_type choices (same for every other_media, but necessary because they all have other ids)
            context['other_media_field_choices'][
                'other-media-type_' + str(other_media.pk)] = choicelist_queryset_to_translated_dict(other_media_type_choice_list)

        # the lemma field is non-empty because it's caught in the get method
        dataset_of_requested_gloss = gl.lemma.dataset

        # set a session variable to be able to pass the gloss's id to the ajax_complete method
        # the last_used_dataset name is updated to that of this gloss
        # if a sequesce of glosses are being created by hand, this keeps the dataset setting the same
        if dataset_of_requested_gloss:
            self.request.session['datasetid'] = dataset_of_requested_gloss.pk
            self.last_used_dataset = dataset_of_requested_gloss.acronym
        else:
            # in this case the gloss does not have a dataset assigned
            print("Alert: The gloss does not have a dataset. The default dataset is assigned to session variable 'datasetid'")
            self.request.session['datasetid'] = settings.DEFAULT_DATASET_PK
            self.last_used_dataset = settings.DEFAULT_DATASET_ACRONYM

        self.request.session['last_used_dataset'] = self.last_used_dataset

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False
        return context


class GlossRelationsDetailView(DetailView):
    model = Gloss
    template_name = 'dictionary/related_signs_detail_view.html'
    context_object_name = 'gloss'

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested gloss does not exist.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})
        if self.object.lemma == None or self.object.lemma.dataset == None:
            translated_message = _('Requested gloss has no lemma or dataset.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        if not request.user.is_authenticated:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_gloss = self.object.lemma.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=False, any_perm=True)

        if dataset_of_requested_gloss not in selected_datasets:
            translated_message = _('The gloss you are trying to view is not in your selected datasets.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })
        if dataset_of_requested_gloss not in datasets_user_can_view:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss',kwargs={'glossid':self.object.pk}))
            else:
                translated_message = _('The gloss you are trying to view is not in a dataset you can view.')
                return render(request, 'dictionary/warning.html',
                              {'warning': translated_message,
                               'dataset_languages': dataset_languages,
                               'selected_datasets': selected_datasets,
                               'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        # Call the base implementation first to get a context
        context = super(GlossRelationsDetailView, self).get_context_data(**kwargs)

        context['language'] = interface_language

        context['navigation'] = context['gloss'].navigation(True)
        context['SIGN_NAVIGATION']  = settings.SIGN_NAVIGATION

        #Pass info about which fields we want to see
        gl = context['gloss']
        context['active_id'] = gl.id
        labels = gl.field_labels()

        context['choice_lists'] = {}

        #Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['main','phonology','semantics','frequency']:
            context[topic+'_fields'] = []

            for field in FIELDS[topic]:
                choice_list = []
                gloss_field = Gloss._meta.get_field(field)
                #Get and save the choice list for this field
                if hasattr(gloss_field, 'field_choice_category'):
                    fieldchoice_category = gloss_field.field_choice_category
                    choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)
                elif isinstance(gloss_field, models.ForeignKey) and gloss_field.related_model == Handshape:
                    choice_list = Handshape.objects.all()

                if len(choice_list) > 0:
                    context['choice_lists'][field] = choicelist_queryset_to_translated_dict(choice_list)

                #Take the human value in the language we are using
                machine_value = getattr(gl,field)
                human_value = machine_value.name if isinstance(machine_value, FieldChoice) or isinstance(machine_value, Handshape) \
                                                 else machine_value

                #And add the kind of field
                kind = fieldname_to_kind(field)
                context[topic+'_fields'].append([human_value,field,labels[field],kind])

        #Add morphology to choice lists
        context['choice_lists']['morphology_role'] = choicelist_queryset_to_translated_dict(FieldChoice.objects.filter(field__iexact='MorphologyType'))

        #Collect all morphology definitions for th sequential morphology section, and make some translations in advance
        morphdef_roles = FieldChoice.objects.filter(field__iexact='MorphologyType')
        morphdefs = []

        for morphdef in context['gloss'].parent_glosses.all():

            translated_role = morphdef.role.name

            sign_display = str(morphdef.morpheme.id)
            morph_texts = morphdef.morpheme.get_annotationidglosstranslation_texts()
            if morph_texts.keys():
                if interface_language_code in morph_texts.keys():
                    sign_display = morph_texts[interface_language_code]
                else:
                    sign_display = morph_texts[default_language_code]

            morphdefs.append((morphdef,translated_role,sign_display))

        context['morphdefs'] = morphdefs

        context['separate_english_idgloss_field'] = SEPARATE_ENGLISH_IDGLOSS_FIELD

        try:
            lemma_group_count = gl.lemma.gloss_set.count()
            if lemma_group_count > 1:
                context['lemma_group'] = True
                lemma_group_url_params = {'search_type': 'sign', 'view_type': 'lemma_groups'}
                for lemmaidglosstranslation in gl.lemma.lemmaidglosstranslation_set.prefetch_related('language'):
                    lang_code_2char = lemmaidglosstranslation.language.language_code_2char
                    lemma_group_url_params['lemma_'+lang_code_2char] = '^' + lemmaidglosstranslation.text + '$'
                from urllib.parse import urlencode
                url_query = urlencode(lemma_group_url_params)
                url_query = ("?" + url_query) if url_query else ''
                context['lemma_group_url'] = reverse_lazy('signs_search') + url_query
            else:
                context['lemma_group'] = False
                context['lemma_group_url'] = ''
        except:
            context['lemma_group'] = False
            context['lemma_group_url'] = ''

        lemma_group_glosses = gl.lemma.gloss_set.all()
        glosses_in_lemma_group = []

        if lemma_group_glosses:
            for gl_lem in lemma_group_glosses:

                lemma_dict = {}
                if gl_lem.dataset:
                    for language in gl_lem.dataset.translation_languages.all():
                        lemma_dict[language.language_code_2char] = gl_lem.annotationidglosstranslation_set.filter(language=language)
                else:
                    language = Language.objects.get(id=get_default_language_id())
                    lemma_dict[language.language_code_2char] = gl_lem.annotationidglosstranslation_set.filter(language=language)
                if interface_language_code in lemma_dict.keys():
                    gl_lem_display = lemma_dict[interface_language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    gl_lem_display = lemma_dict[default_language_code][0].text

                glosses_in_lemma_group.append((gl_lem,gl_lem_display))

        context['glosses_in_lemma_group'] = glosses_in_lemma_group

        otherrelations = []

        if gl.relation_sources:
            for oth_rel in gl.relation_sources.all().distinct():
                other_relations_dict = {}
                if oth_rel.target.dataset:
                    for language in oth_rel.target.dataset.translation_languages.all():
                        other_relations_dict[language.language_code_2char] = oth_rel.target.annotationidglosstranslation_set.filter(language=language)
                else:
                    language = Language.objects.get(id=get_default_language_id())
                    other_relations_dict[language.language_code_2char] = oth_rel.target.annotationidglosstranslation_set.filter(language=language)
                if interface_language_code in other_relations_dict.keys():
                    target_display = other_relations_dict[interface_language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    target_display = other_relations_dict[default_language_code][0].text

                otherrelations.append((oth_rel,target_display))

        context['otherrelations'] = otherrelations


        try:
            pattern_variants = gl.pattern_variants()
        except:
            pattern_variants = []
        pattern_variants = [ v for v in pattern_variants if not v.id == gl.id ]
        try:
            other_variants = gl.has_variants()
        except:
            other_variants = []

        all_variants = pattern_variants + [ ov for ov in other_variants if ov not in pattern_variants ]

        has_variants = all_variants
        variants = []

        if has_variants:
            for gl_var in has_variants:

                variants_dict = {}
                if gl_var.dataset:
                    for language in gl_var.dataset.translation_languages.all():
                        variants_dict[language.language_code_2char] = gl_var.annotationidglosstranslation_set.filter(language=language)
                else:
                    language = Language.objects.get(id=get_default_language_id())
                    variants_dict[language.language_code_2char] = gl_var.annotationidglosstranslation_set.filter(language=language)
                if interface_language_code in variants_dict.keys():
                    gl_var_display = variants_dict[interface_language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    gl_var_display = variants_dict[default_language_code][0].text

                variants.append((gl_var,gl_var_display))

        context['variants'] = variants

        minimal_pairs_dict = gl.minimal_pairs_dict()
        minimalpairs = []

        for mpg, dict in minimal_pairs_dict.items():
            minimal_pairs_trans = {}
            if mpg.dataset:
                for language in mpg.dataset.translation_languages.all():
                    minimal_pairs_trans[language.language_code_2char] = mpg.annotationidglosstranslation_set.filter(language=language)
            else:
                language = Language.objects.get(id=get_default_language_id())
                minimal_pairs_trans[language.language_code_2char] = mpg.annotationidglosstranslation_set.filter(language=language)
            if interface_language_code in minimal_pairs_trans.keys():
                minpar_display = minimal_pairs_trans[interface_language_code][0].text
            else:
                # This should be set to the default language if the interface language hasn't been set for this gloss
                minpar_display = minimal_pairs_trans[default_language_code][0].text

            minimalpairs.append((mpg,dict,minpar_display))

        context['minimalpairs'] = minimalpairs

        morphdef_roles = FieldChoice.objects.filter(field__iexact='MorphologyType')
        compounds = []
        reverse_morphdefs = MorphologyDefinition.objects.filter(morpheme=gl.id)
        if reverse_morphdefs:
            for rm in reverse_morphdefs:
                morphdef_role_machine_value = rm.role.machine_value if rm.role else 0
                translated_role = machine_value_to_translated_human_value(morphdef_role_machine_value,morphdef_roles)

                compounds.append((rm.parent_gloss, translated_role))
        context['compounds'] = compounds

        gloss_default_annotationidglosstranslation = gl.annotationidglosstranslation_set.get(language=default_language).text
        # Put annotation_idgloss per language in the context
        context['annotation_idgloss'] = {}
        for language in gl.dataset.translation_languages.all():
            try:
                annotation_text = gl.annotationidglosstranslation_set.get(language=language).text
            except (ObjectDoesNotExist):
                annotation_text = gloss_default_annotationidglosstranslation
            context['annotation_idgloss'][language] = annotation_text

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'SHOW_QUERY_PARAMETERS_AS_BUTTON') and settings.SHOW_QUERY_PARAMETERS_AS_BUTTON:
            context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = settings.SHOW_QUERY_PARAMETERS_AS_BUTTON
        else:
            context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = False

        return context


class MorphemeListView(ListView):
    """The morpheme list view basically copies the gloss list view"""

    model = Morpheme
    search_type = 'morpheme'
    show_all = False
    dataset_name = settings.DEFAULT_DATASET_ACRONYM
    last_used_dataset = None
    template_name = 'dictionary/admin_morpheme_list.html'
    paginate_by = 100
    queryset_language_codes = []

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(MorphemeListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        default_dataset_acronym = settings.DEFAULT_DATASET_ACRONYM
        default_dataset = Dataset.objects.get(acronym=default_dataset_acronym)

        for lang in dataset_languages:
            if lang.language_code_2char not in self.queryset_language_codes:
                self.queryset_language_codes.append(lang.language_code_2char)
        if self.queryset_language_codes is None:
            self.queryset_language_codes = [ default_dataset.default_language.language_code_2char ]

        if len(selected_datasets) == 1:
            self.last_used_dataset = selected_datasets[0].acronym
        elif 'last_used_dataset' in self.request.session.keys():
            self.last_used_dataset = self.request.session['last_used_dataset']

        context['last_used_dataset'] = self.last_used_dataset

        selected_datasets_signlanguage = [ ds.signlanguage for ds in selected_datasets ]
        sign_languages = []
        for sl in selected_datasets_signlanguage:
            if ((str(sl.id), sl.name) not in sign_languages):
                sign_languages.append((str(sl.id), sl.name))

        selected_datasets_dialects = Dialect.objects.filter(signlanguage__in=selected_datasets_signlanguage).distinct()
        dialects = []
        for dl in selected_datasets_dialects:
            dialect_name = dl.signlanguage.name + "/" + dl.name
            dialects.append((str(dl.id),dialect_name))

        if 'show_all' in self.kwargs.keys():
            context['show_all'] = self.kwargs['show_all']
        else:
            context['show_all'] = False

        search_form = MorphemeSearchForm(self.request.GET, languages=dataset_languages, sign_languages=sign_languages,
                                         dialects=dialects)

        context['searchform'] = search_form

        context['glosscount'] = Morpheme.objects.filter(lemma__dataset__in=selected_datasets).count()

        self.request.session['search_type'] = self.search_type

        context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE
        context['add_morpheme_form'] = MorphemeCreateForm(self.request.GET, languages=dataset_languages, user=self.request.user, last_used_dataset=self.last_used_dataset)

        context['input_names_fields_and_labels'] = {}

        for topic in ['main', 'phonology', 'semantics']:

            context['input_names_fields_and_labels'][topic] = []

            for fieldname in settings.FIELDS[topic]:

                if fieldname == 'derivHist' and not settings.USE_DERIVATIONHISTORY:
                    continue

                if fieldname not in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:

                    if topic == 'phonology':
                        if fieldname not in settings.MORPHEME_DISPLAY_FIELDS:
                            continue

                    field = search_form[fieldname]
                    label = field.label

                    context['input_names_fields_and_labels'][topic].append((fieldname, field, label))

        context['page_number'] = context['page_obj'].number

        # this is needed to avoid crashing the browser if you go to the last page
        # of an extremely long list and go to Details on the objects

        if len(self.object_list) > settings.MAX_SCROLL_BAR:
            list_of_objects = context['page_obj'].object_list
        else:
            list_of_objects = self.object_list

        # construct scroll bar
        # the following retrieves language code for English (or DEFAULT LANGUAGE)
        # so the sorting of the scroll bar matches the default sorting of the results in Gloss List View

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        dataset_display_languages = []
        for lang in dataset_languages:
            dataset_display_languages.append(lang.language_code_2char)
        if interface_language_code in dataset_display_languages:
            lang_attr_name = interface_language_code
        else:
            lang_attr_name = default_language_code

        items = construct_scrollbar(list_of_objects, self.search_type, lang_attr_name)
        self.request.session['search_results'] = items

        if 'paginate_by' in self.request.GET:
            context['paginate_by'] = int(self.request.GET.get('paginate_by'))
            self.request.session['paginate_by'] = context['paginate_by']
        else:
            context['paginate_by'] = self.paginate_by # default

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

        fieldnames = FIELDS['main']+settings.MORPHEME_DISPLAY_FIELDS+FIELDS['semantics']+['inWeb', 'isNew', 'mrpType']
        if not settings.USE_DERIVATIONHISTORY and 'derivHist' in fieldnames:
            fieldnames.remove('derivHist')

        multiple_select_morpheme_categories = fields_to_fieldcategory_dict(fieldnames)
        multiple_select_morpheme_categories['definitionRole'] = 'NoteType'
        # multiple_select_morpheme_categories['hasComponentOfType'] = 'MorphologyType'

        multiple_select_morpheme_fields = [ fieldname for (fieldname, category) in multiple_select_morpheme_categories.items() ]

        context['MULTIPLE_SELECT_MORPHEME_FIELDS'] = multiple_select_morpheme_fields

        choices_colors = {}
        for (fieldname, field_category) in multiple_select_morpheme_categories.items():
            if field_category in CATEGORY_MODELS_MAPPING.keys():
                field_choices = CATEGORY_MODELS_MAPPING[field_category].objects.all()
            else:
                field_choices = FieldChoice.objects.filter(field__iexact=field_category)
            choices_colors[fieldname] = json.dumps(choicelist_queryset_to_field_colors(field_choices))

        context['field_colors'] = choices_colors

        if hasattr(settings, 'SEARCH_BY') and 'publication' in settings.SEARCH_BY.keys() and self.request.user.is_authenticated:
            context['search_by_publication_fields'] = searchform_panels(search_form, settings.SEARCH_BY['publication'])
        else:
            context['search_by_publication_fields'] = []

        return context


    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)


    def get_queryset(self):
        # get query terms from self.request
        get = self.request.GET

        try:
            if self.kwargs['show_all']:
                show_all = True
        except (KeyError,TypeError):
            show_all = False

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        from signbank.dictionary.forms import check_language_fields
        valid_regex, search_fields = check_language_fields(MorphemeSearchForm, get, dataset_languages)

        if not valid_regex:
            error_message_1 = _('Error in search field ')
            error_message_2 = ', '.join(search_fields)
            error_message_3 = _(': Please use a backslash before special characters.')
            error_message = error_message_1 + error_message_2 + error_message_3
            messages.add_message(self.request, messages.ERROR, error_message)
            qs = Morpheme.objects.none()
            return qs

        if len(get) > 0 or show_all:
            qs = Morpheme.objects.filter(lemma__dataset__in=selected_datasets)

        #Don't show anything when we're not searching yet
        else:
            qs = Morpheme.objects.none()

        if not self.request.user.has_perm('dictionary.search_gloss'):
            qs = qs.filter(inWeb__exact=True)

        #If we wanted to get everything, we're done now
        if show_all:

            qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)

            return qs

        # Evaluate all morpheme/language search fields
        for get_key, get_value in get.items():
            if get_key.startswith(MorphemeSearchForm.gloss_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(MorphemeSearchForm.gloss_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                qs = qs.filter(annotationidglosstranslation__text__iregex=get_value,
                               annotationidglosstranslation__language=language)
            elif get_key.startswith(GlossSearchForm.lemma_search_field_prefix) and get_value != '':
                query_parameters[get_key] = get_value
                language_code_2char = get_key[len(GlossSearchForm.lemma_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                qs = qs.filter(lemma__lemmaidglosstranslation__text__iregex=get_value,
                               lemma__lemmaidglosstranslation__language=language)
            elif get_key.startswith(MorphemeSearchForm.keyword_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(MorphemeSearchForm.keyword_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                qs = qs.filter(translation__translation__text__iregex=get_value,
                               translation__language=language)

        if 'translation' in get and get['translation'] != '':
            val = get['translation']
            qs = qs.filter(translation__translation__text__iregex=val)

        if 'inWeb' in get and get['inWeb'] != '0':
            # Don't apply 'inWeb' filter, if it is unspecified ('0' according to the NULLBOOLEANCHOICES)
            val = get['inWeb'] == '2'
            qs = qs.filter(inWeb__exact=val)

        if 'hasvideo' in get and get['hasvideo'] not in ['unspecified', '0']:
            val = get['hasvideo'] != '2'
            qs = qs.filter(glossvideo__isnull=val)

        if 'definitionRole[]' in get:

            vals = get.getlist('definitionRole[]')
            if vals != []:
                #Find all definitions with this role
                definitions_with_this_role = Definition.objects.filter(role__machine_value__in=vals)

                #Remember the pk of all glosses that are referenced in the collection definitions
                pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role]
                qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if 'defspublished' in get and get['defspublished'] != 'unspecified':
            val = get['defspublished'] == 'yes'

            qs = qs.filter(definition__published=val)

        # SignLanguage and basic property filters
        # allows for multiselect
        vals = get.getlist('dialect[]')
        if vals != []:
            qs = qs.filter(dialect__in=vals)

        # allows for multiselect
        vals = get.getlist('signlanguage[]')
        if vals != []:
            qs = qs.filter(signlanguage__in=vals)

        if 'tags[]' in get:
            vals = get.getlist('tags[]')
            if vals != []:
                morphemes_with_tag = list(
                    TaggedItem.objects.filter(tag__name__in=vals).values_list('object_id', flat=True))
                qs = qs.filter(id__in=morphemes_with_tag)

        if 'useInstr' in get and get['useInstr'] != '':
            qs = qs.filter(useInstr__icontains=get['useInstr'])

        fieldnames = FIELDS['main']+settings.MORPHEME_DISPLAY_FIELDS+FIELDS['semantics']+['inWeb', 'isNew', 'mrpType']
        if not settings.USE_DERIVATIONHISTORY and 'derivHist' in fieldnames:
            fieldnames.remove('derivHist')

        multiple_select_morpheme_categories = fields_to_fieldcategory_dict(fieldnames)
        # multiple_select_morpheme_categories['definitionRole'] = 'NoteType'

        multiple_select_morpheme_fields = [ fieldname for (fieldname, category) in multiple_select_morpheme_categories.items() ]

        for fieldnamemulti in multiple_select_morpheme_fields:
            fieldnamemultiVarname = fieldnamemulti + '[]'
            fieldnameQuery = fieldnamemulti + '__machine_value__in'

            vals = get.getlist(fieldnamemultiVarname)
            if vals != []:
                if fieldnamemulti == 'semField':
                    qs = qs.filter(semField__in=vals)
                elif fieldnamemulti == 'derivHist':
                    qs = qs.filter(derivHist__in=vals)
                else:
                    qs = qs.filter(**{ fieldnameQuery: vals })

        ## phonology and semantics field filters
        fieldnames = [ f for f in fieldnames if f not in multiple_select_morpheme_fields ]
        for fieldname in fieldnames:

            if fieldname in get:
                key = fieldname + '__exact'
                val = get[fieldname]

                if isinstance(Gloss._meta.get_field(fieldname), BooleanField):
                    val = {'0': '', '1': None, '2': True, '3': False}[val]

                if val != '':
                    kwargs = {key: val}
                    qs = qs.filter(**kwargs)


        # these fields are for ASL searching
        if 'initial_relative_orientation' in get and get['initial_relative_orientation'] != '':
            val = get['initial_relative_orientation']
            qs = qs.filter(initial_relative_orientation__exact=val)

        if 'final_relative_orientation' in get and get['final_relative_orientation'] != '':
            val = get['final_relative_orientation']
            qs = qs.filter(final_relative_orientation__exact=val)

        if 'initial_palm_orientation' in get and get['initial_palm_orientation'] != '':
            val = get['initial_palm_orientation']
            qs = qs.filter(initial_palm_orientation__exact=val)

        if 'final_palm_orientation' in get and get['final_palm_orientation'] != '':
            val = get['final_palm_orientation']
            qs = qs.filter(final_palm_orientation__exact=val)

        if 'initial_secondary_loc' in get and get['initial_secondary_loc'] != '':
            val = get['initial_secondary_loc']
            qs = qs.filter(initial_secondary_loc__exact=val)

        if 'final_secondary_loc' in get and get['final_secondary_loc'] != '':
            val = get['final_secondary_loc']
            qs = qs.filter(final_secondary_loc__exact=val)

        if 'final_secondary_loc' in get and get['final_secondary_loc'] != '':
            val = get['final_secondary_loc']
            qs = qs.filter(final_secondary_loc__exact=val)

        qs = qs.distinct()

        if 'definitionRole' in get and get['definitionRole'] != '':

            # Find all definitions with this role
            if get['definitionRole'] == 'all':
                definitions_with_this_role = Definition.objects.all()
            else:
                definitions_with_this_role = Definition.objects.filter(role__exact=get['definitionRole'])

            # Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role]
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if 'definitionContains' in get and get['definitionContains'] != '':
            definitions_with_this_text = Definition.objects.filter(text__icontains=get['definitionContains'])

            # Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_text]
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if 'createdBefore' in get and get['createdBefore'] != '':
            created_before_date = DT.datetime.strptime(get['createdBefore'], settings.DATE_FORMAT).date()
            qs = qs.filter(creationDate__range=(EARLIEST_GLOSS_CREATION_DATE, created_before_date))

        if 'createdAfter' in get and get['createdAfter'] != '':
            created_after_date = DT.datetime.strptime(get['createdAfter'], settings.DATE_FORMAT).date()
            qs = qs.filter(creationDate__range=(created_after_date, DT.datetime.now()))

        if 'createdBy' in get and get['createdBy'] != '':
            created_by_search_string = ' '.join(get['createdBy'].strip().split())  # remove redundant spaces
            qs = qs.annotate(
                created_by=Concat('creator__first_name', V(' '), 'creator__last_name', output_field=CharField())) \
                .filter(created_by__icontains=created_by_search_string)



        # Sort the queryset by the parameters given
        qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)

        self.request.session['search_type'] = 'morpheme'

        if 'last_used_dataset' not in self.request.session.keys():
            self.request.session['last_used_dataset'] = self.last_used_dataset

        # Return the resulting filtered and sorted queryset
        return qs


    def render_to_response(self, context):
        # Look for a 'format=json' GET argument
        if self.request.GET.get('format') == 'CSV':
            return self.render_to_csv_response(context)
        else:
            return super(MorphemeListView, self).render_to_response(context)

    # noinspection PyInterpreter,PyInterpreter
    def render_to_csv_response(self, context):
        """Convert all Morphemes into a CSV

        This function is derived from and similar to the one used in class GlossListView
        Differences:
        1 - this one adds the field [mrpType]
        2 - the filename is different"""

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dictionary-morph-export.csv"'

        #        fields = [f.name for f in Gloss._meta.fields]
        # We want to manually set which fields to export here

        fieldnames = FIELDS['main']+settings.MORPHEME_DISPLAY_FIELDS+FIELDS['semantics']+FIELDS['frequency']+['inWeb', 'isNew']

        # Different from Gloss: we use Morpheme here
        fields = [Morpheme._meta.get_field(fieldname) for fieldname in fieldnames]

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        lang_attr_name = 'name_' + DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
        annotationidglosstranslation_fields = ["Annotation ID Gloss" + " (" + getattr(language, lang_attr_name) + ")" for language in
                                               dataset_languages]

        writer = csv.writer(response)

        with override(LANGUAGE_CODE):
            header = ['Signbank ID'] + annotationidglosstranslation_fields + [f.verbose_name.title().encode('ascii', 'ignore').decode() for f in fields]

        for extra_column in ['SignLanguages', 'Dialects', 'Keywords', 'Morphology', 'Relations to other signs',
                             'Relations to foreign signs', 'Appears in signs', ]:
            header.append(extra_column)

        writer.writerow(header)

        for gloss in self.get_queryset():
            row = [str(gloss.pk)]

            for language in dataset_languages:
                annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
                if annotationidglosstranslations and len(annotationidglosstranslations) == 1:
                    row.append(annotationidglosstranslations[0].text)
                else:
                    row.append("")

            for f in fields:
                #Try the value of the choicelist
                if hasattr(f, 'field_choice_category'):
                    if hasattr(gloss, 'get_' + f.name + '_display'):
                        value = getattr(gloss, 'get_' + f.name + '_display')()
                    else:
                        field_value = getattr(gloss, f.name)
                        value = field_value.name if field_value else '-'
                elif isinstance(f, models.ForeignKey) and f.related_model == Handshape:
                    handshape_field_value = getattr(gloss, f.name)
                    value = handshape_field_value.name if handshape_field_value else '-'
                elif f.related_model == SemanticField:
                    value = ", ".join([str(sf.name) for sf in gloss.semField.all()])
                elif f.related_model == DerivationHistory:
                    value = ", ".join([str(sf.name) for sf in gloss.derivHist.all()])
                else:
                    value = getattr(gloss, f.name)
                    value = str(value)

                row.append(value)

            # get languages
            signlanguages = [signlanguage.name for signlanguage in gloss.signlanguage.all()]
            row.append(", ".join(signlanguages))

            # get dialects
            dialects = [dialect.name for dialect in gloss.dialect.all()]
            row.append(", ".join(dialects))

            # get translations
            trans = [t.translation.text for t in gloss.translation_set.all().order_by('translation__index')]
            row.append(", ".join(trans))

            # get compound's component type
            morphemes = [morpheme.role for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]
            row.append(", ".join(morphemes))

            # get relations to other signs
            relations = [relation.target.idgloss for relation in Relation.objects.filter(source=gloss)]
            row.append(", ".join(relations))

            # get relations to foreign signs
            relations = [relation.other_lang_gloss for relation in RelationToForeignSign.objects.filter(gloss=gloss)]
            row.append(", ".join(relations))

            # Got all the glosses (=signs) this morpheme appears in
            appearsin = [appears.idgloss for appears in MorphologyDefinition.objects.filter(parent_gloss=gloss)]
            row.append(", ".join(appearsin))

            # Make it safe for weird chars
            safe_row = []
            for column in row:
                try:
                    safe_row.append(column.encode('utf-8').decode())
                except AttributeError:
                    safe_row.append(None)

            writer.writerow(safe_row)

        return response

class HandshapeDetailView(DetailView):
    model = Handshape
    template_name = 'dictionary/handshape_detail.html'
    context_object_name = 'handshape'
    search_type = 'handshape'

    class Meta:
        verbose_name_plural = "Handshapes"
        ordering = ['machine_value']

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        match_machine_value = int(kwargs['pk'])
        try:
            # GET A HANDSHAPE OBJECT WITH THE REQUESTED MACHINE VALUE
            # see if Handshape object exists for this machine_value
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            # The handshape machine value does not exist as a Handshape
            translated_message = _('Handshape not configured.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        try:
            context = super(HandshapeDetailView, self).get_context_data(**kwargs)
        except:
            # return custom template
            return HttpResponse('invalid', {'content-type': 'text/plain'})

        hs = context['handshape']
        context['active_id'] = hs.machine_value

        setattr(self.request.session, 'search_type', self.search_type)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        labels = hs.field_labels()
        context['imageform'] = ImageUploadForHandshapeForm()

        context['choice_lists'] = {}
        context['handshape_fields'] = []

        context['handshape_fields_FS1'] = []
        context['handshape_fields_FS2'] = []
        context['handshape_fields_FC1'] = []
        context['handshape_fields_FC2'] = []
        context['handshape_fields_UF'] = []

        FINGER_SELECTION_FIELDS = ['hsFingSel', 'fsT', 'fsI', 'fsM', 'fsR', 'fsP']
        FINGER_SELECTION_2_FIELDS = ['hsFingSel2', 'fs2T', 'fs2I', 'fs2M', 'fs2R', 'fs2P']
        UNSELECTED_FINGERS_FIELDS = ['hsFingUnsel', 'ufT', 'ufI', 'ufM', 'ufR', 'ufP']

        handshape_fields_lookup = {}
        for f in Handshape._meta.fields:
            if f.name in settings.FIELDS['handshape']:
                handshape_fields_lookup[f.name] = f

        choice_lists = dict()
        for field in handshape_fields_lookup.keys():
            handshape_field = handshape_fields_lookup[field]
            # Get and save the choice list for this field
            if hasattr(handshape_field, 'field_choice_category'):
                fieldchoice_category = handshape_field.field_choice_category
                choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category).order_by('machine_value')

            else:
                fieldchoice_category = field
                choice_list = []

            if len(choice_list) > 0:
                choice_lists[field] = choicelist_queryset_to_translated_dict(choice_list)

            #Take the human value in the language we are using
            machine_value = getattr(hs, field)
            human_value = machine_value.name if isinstance(machine_value, FieldChoice) else machine_value

            #And add the kind of field
            kind = fieldname_to_kind(field)

            field_label = labels[field]

            if field in FINGER_SELECTION_FIELDS and field != 'hsFingSel':
                context['handshape_fields_FS1'].append([human_value, field, field_label, kind])
            elif field in FINGER_SELECTION_2_FIELDS and field != 'hsFingSel2':
                context['handshape_fields_FS2'].append([human_value, field, field_label, kind])
            elif field in UNSELECTED_FINGERS_FIELDS and field != 'hsFingUnsel':
                context['handshape_fields_UF'].append([human_value, field, field_label, kind])
            elif field == 'hsFingConf':
                context['handshape_fields_FC1'].append([human_value, field, field_label, kind])
            elif field == 'hsFingConf2':
                context['handshape_fields_FC2'].append([human_value, field, field_label, kind])
            else:
                context['handshape_fields'].append([human_value, field, field_label, kind])

        context['choice_lists'] = json.dumps(choice_lists)

        if 'search_type' not in self.request.session.keys() or self.request.session['search_type'] != 'handshape':
            self.request.session['search_type'] = self.search_type

        # Check the type of the current search results
        if 'search_results' in self.request.session.keys():
            if self.request.session['search_results'] and len(self.request.session['search_results']) > 0:
                if self.request.session['search_results'][0]['href_type'] in ['gloss', 'morpheme']:
                    # if the previous search does not match the search type
                    self.request.session['search_results'] = []

        if 'search_results' not in self.request.session.keys() or not self.request.session['search_results']:
            # there are no handshapes in the scrollbar, put some there

            qs = Handshape.objects.filter(machine_value__gt=1).order_by('machine_value')

            (interface_language, interface_language_code,
             default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

            dataset_display_languages = []
            for lang in dataset_languages:
                dataset_display_languages.append(lang.language_code_2char)
            if interface_language_code in dataset_display_languages:
                lang_attr_name = interface_language_code
            else:
                lang_attr_name = default_language_code

            items = construct_scrollbar(qs, self.search_type, lang_attr_name)
            self.request.session['search_results'] = items

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False
        return context


class SemanticFieldDetailView(DetailView):
    model = SemanticField
    template_name = 'dictionary/semanticfield_detail.html'
    context_object_name = 'semanticfield'

    class Meta:
        ordering = ['name']

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        # Get the machine value in the URL
        match_machine_value = int(kwargs['pk'])
        try:
            self.object = SemanticField.objects.get(machine_value=match_machine_value)
        except ObjectDoesNotExist:
            # No SemanticField exists for this machine value
            translated_message = _('SemanticField not configured for this machine value.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        try:
            context = super(SemanticFieldDetailView, self).get_context_data(**kwargs)
        except:
            # return custom template
            return HttpResponse('invalid', {'content-type': 'text/plain'})

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets

        context['translations'] = [ (translation.language.name, translation.name)
                                    for translation in self.object.semanticfieldtranslation_set.all() ]
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        existing_translation_languages = [ translation.language for translation in self.object.semanticfieldtranslation_set.all() ]
        context['existing_translation_languages'] = existing_translation_languages

        semanticfieldtranslationform = SemanticFieldTranslationForm(semField=self.object,
                                                                    languages=dataset_languages)

        context['semanticfieldtranslationform'] = semanticfieldtranslationform

        translation_mapping = {}
        for translation in self.object.semanticfieldtranslation_set.filter(language__in=dataset_languages):
            translation_mapping[translation.language.language_code_2char] = translation.name
        with override(settings.LANGUAGE_CODE):
            default_initial = self.object.name
        for language in dataset_languages:
            if language.language_code_2char not in translation_mapping.keys():
                translation_mapping[language.language_code_2char] = ""

        context['translation_mapping'] = translation_mapping

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False
        return context


class SemanticFieldListView(ListView):

    model = SemanticField
    template_name = 'dictionary/admin_semanticfield_list.html'
    search_type = 'semanticfield'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SemanticFieldListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets

        # this is needed to avoid crashing the browser if you go to the last page
        # of an extremely long list and go to Details on the objects

        if len(self.object_list) > settings.MAX_SCROLL_BAR:
            list_of_objects = context['page_obj'].object_list
        else:
            list_of_objects = self.object_list

        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        return context

    def get_queryset(self):

        # get query terms from self.request
        get = self.request.GET

        qs = SemanticField.objects.filter(machine_value__gt=1).order_by('name')

        return qs


class DerivationHistoryDetailView(DetailView):
    model = DerivationHistory
    template_name = 'dictionary/derivationhistory_detail.html'
    context_object_name = 'derivationhistory'

    class Meta:
        ordering = ['name']

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        # Get the machine value in the URL
        match_machine_value = int(kwargs['pk'])
        try:
            self.object = DerivationHistory.objects.get(machine_value=match_machine_value)
        except ObjectDoesNotExist:
            # No DerivationHistory exists for this machine value
            translated_message = _('DerivationHistory not configured for this machine value.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        try:
            context = super(DerivationHistoryDetailView, self).get_context_data(**kwargs)
        except:
            # return custom template
            return HttpResponse('invalid', {'content-type': 'text/plain'})

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets

        context['translations'] = [ (translation.language.name, translation.name)
                                    for translation in self.object.derivationhistorytranslation_set.all() ]
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False
        return context


class DerivationHistoryListView(ListView):

    model = DerivationHistory
    template_name = 'dictionary/admin_derivationhistory_list.html'
    search_type = 'derivationhistory'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DerivationHistoryListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets

        # this is needed to avoid crashing the browser if you go to the last page
        # of an extremely long list and go to Details on the objects

        if len(self.object_list) > settings.MAX_SCROLL_BAR:
            list_of_objects = context['page_obj'].object_list
        else:
            list_of_objects = self.object_list

        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        return context

    def get_queryset(self):

        # get query terms from self.request
        get = self.request.GET

        qs = DerivationHistory.objects.filter(machine_value__gt=1).order_by('name')

        return qs


class HomonymListView(ListView):
    model = Gloss
    template_name = 'dictionary/admin_homonyms_list.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(HomonymListView, self).get_context_data(**kwargs)

        if self.request.LANGUAGE_CODE == 'zh-hans':
            languages = Language.objects.filter(language_code_2char='zh')
        else:
            languages = Language.objects.filter(language_code_2char=self.request.LANGUAGE_CODE)
        if languages:
            context['language'] = languages[0]
        else:
            context['language'] = Language.objects.get(id=get_default_language_id())

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        handedness_filter = 'handedness__name__in'
        strong_hand_filter = 'domhndsh__name__in'
        empty_value = ['-','N/A']

        # this is used to set up the ajax calls, one per each focus gloss in the table
        context['ids_of_all_glosses'] = [ g.id for g in Gloss.none_morpheme_objects().select_related('lemma').filter(
            lemma__dataset__in=selected_datasets).exclude(
            (Q(**{handedness_filter: empty_value}))).exclude((Q(**{strong_hand_filter: empty_value}))) ]

        return context

    def get_queryset(self):

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        handedness_filter = 'handedness__name__in'
        strong_hand_filter = 'domhndsh__name__in'
        empty_value = ['-','N/A']

        glosses_with_phonology = Gloss.none_morpheme_objects().select_related('lemma').filter(
            lemma__dataset__in=selected_datasets).exclude(
            (Q(**{handedness_filter: empty_value}))).exclude((Q(**{strong_hand_filter: empty_value})))

        return glosses_with_phonology

class MinimalPairsListView(ListView):
    model = Gloss
    template_name = 'dictionary/admin_minimalpairs_list.html'
    paginate_by = 10
    filter = False

    def get_context_data(self, **kwargs):
        context = super(MinimalPairsListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if not selected_datasets or selected_datasets.count() > 1:
            feedback_message = _('Please select a single dataset to view minimal pairs.')
            messages.add_message(self.request, messages.ERROR, feedback_message)

        dataset = selected_datasets.first()
        context['dataset'] = dataset
        context['dataset_name'] = dataset.acronym
        self.request.session['last_used_dataset'] = dataset.acronym
        self.request.session.modified = True

        fieldnames = settings.MINIMAL_PAIRS_SEARCH_FIELDS
        fields_with_choices = fields_to_fieldcategory_dict()
        multiple_select_gloss_fields = [fieldname for fieldname in fieldnames
                                                  if fieldname in fields_with_choices.keys()]
        context['MULTIPLE_SELECT_GLOSS_FIELDS'] = multiple_select_gloss_fields

        field_names = []
        for field in FIELDS['phonology']:
            field_object = Gloss._meta.get_field(field)
            # don't consider text fields that are not choice lists
            if isinstance(field_object, models.CharField) or isinstance(field_object, models.TextField):
                continue
            field_names.append(field)

        field_labels = dict()
        for field in field_names:
            field_label = Gloss._meta.get_field(field).verbose_name
            field_labels[field] = field_label.encode('utf-8').decode()

        context['field_labels'] = field_labels

        search_form = FocusGlossSearchForm(self.request.GET, languages=dataset_languages)

        context['searchform'] = search_form

        context['input_names_fields_and_labels'] = {}

        for topic in ['main','phonology','semantics']:

            context['input_names_fields_and_labels'][topic] = []

            for fieldname in settings.FIELDS[topic]:

                if fieldname == 'derivHist' and not settings.USE_DERIVATIONHISTORY:
                    continue
                if fieldname in settings.MINIMAL_PAIRS_SEARCH_FIELDS:
                    # exclude the dependent fields for Handedness, Strong Hand, and Weak Hand for purposes of nested dependencies in Search form
                    if fieldname not in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
                        field = search_form[fieldname]
                        label = field.label
                        context['input_names_fields_and_labels'][topic].append((fieldname,field,label))

        # pass these to the template to populate the search form with the search parameters
        gloss_fields_to_populate = dict()
        for veld in self.request.GET.keys():
            if veld in ['search_type', 'filter']:
                continue
            veld_value = self.request.GET[veld]
            if veld_value == '' or veld_value == '0':
                continue
            if veld[-2:] == '[]' :
                veld_list = self.request.GET.getlist(veld)
                if not veld_list:
                    continue
                veld_value = veld_list
            gloss_fields_to_populate[veld] = veld_value
        gloss_fields_to_populate_keys = list(gloss_fields_to_populate.keys())
        context['gloss_fields_to_populate'] = json.dumps(gloss_fields_to_populate)
        context['gloss_fields_to_populate_keys'] = gloss_fields_to_populate_keys

        context['page_number'] = context['page_obj'].number

        context['objects_on_page'] = [ g.id for g in context['page_obj'].object_list ]

        context['paginate_by'] = self.request.GET.get('paginate_by', self.paginate_by)

        return context

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)

    def render_to_response(self, context):
        if 'csv' in self.request.GET:
            return self.render_to_csv_response(context)
        else:
            return super(MinimalPairsListView, self).render_to_response(context)

    def render_to_csv_response(self, context):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        # this ends up being English for Global Signbank
        language_code = settings.DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
        dataset = context['dataset']

        # this can take a long time if the entire dataset is queried
        rows = write_csv_for_minimalpairs(self, dataset, language_code=language_code)

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dictionary-export-minimalpairs.csv"'

        import csv
        csvwriter = csv.writer(response)

        # write the actual file
        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            header = ['Dataset', 'Focus Gloss', 'ID', 'Minimal Pair Gloss', 'ID', 'Field Name', 'Source Sign Value',
                      'Contrasting Sign Value']
        else:
            header = ['Focus Gloss', 'ID', 'Minimal Pair Gloss', 'ID', 'Field Name', 'Source Sign Value',
                      'Contrasting Sign Value']

        csvwriter.writerow(header)

        for row in rows:
            csvwriter.writerow(row)

        return response

    def get_queryset(self):

        get = self.request.GET

        if not get:
            # to speed things up, don't show anything on initial visit
            qs = Gloss.objects.none()
            self.request.session['search_results'] = []
            self.request.session.modified = True
            return qs

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        from signbank.dictionary.forms import check_language_fields
        valid_regex, search_fields = check_language_fields(FocusGlossSearchForm, get, dataset_languages)

        if not valid_regex:
            error_message_1 = _('Error in search field ')
            error_message_2 = ', '.join(search_fields)
            error_message_3 = _(': Please use a backslash before special characters.')
            error_message = error_message_1 + error_message_2 + error_message_3
            messages.add_message(self.request, messages.ERROR, error_message)
            qs = Gloss.objects.none()
            self.request.session['search_results'] = []
            self.request.session.modified = True
            return qs

        # grab gloss ids for finger spelling glosses, identified by text #.

        finger_spelling_glosses = [ a_idgloss_trans.gloss_id
                                    for a_idgloss_trans in AnnotationIdglossTranslation.objects.filter(text__startswith="#") ]

        q_number_or_letter = Q(**{'domhndsh_number': True}) | Q(**{'subhndsh_number': True}) | \
                             Q(**{'domhndsh_letter': True}) | Q(**{'subhndsh_letter': True})

        handedness_filter = 'handedness__name__in'
        handedness_null = 'handedness__isnull'
        strong_hand_filter = 'domhndsh__name__in'
        strong_hand_null = 'domhndsh__isnull'
        empty_value = ['-','N/A']

        glosses_with_phonology = Gloss.none_morpheme_objects().select_related('lemma').filter(
                                        lemma__dataset__in=selected_datasets).exclude(
                                        id__in=finger_spelling_glosses)

        glosses_with_phonology = glosses_with_phonology.exclude(
                        (Q(**{handedness_null: True}))).exclude(
                        (Q(**{strong_hand_null: True}))).exclude(
                        (Q(**{handedness_filter: empty_value}))).exclude(
                        (Q(**{strong_hand_filter: empty_value}))).exclude(q_number_or_letter)

        if 'showall' in get:
            return glosses_with_phonology

        qs = glosses_with_phonology
        # Evaluate all gloss/language search fields
        for get_key, get_value in get.items():
            if get_key.startswith(GlossSearchForm.gloss_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(GlossSearchForm.gloss_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                qs = qs.filter(annotationidglosstranslation__text__iregex=get_value,
                               annotationidglosstranslation__language=language)
            elif get_key.startswith(GlossSearchForm.lemma_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(GlossSearchForm.lemma_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                qs = qs.filter(lemma__lemmaidglosstranslation__text__iregex=get_value,
                               lemma__lemmaidglosstranslation__language=language)
            elif get_key.startswith(GlossSearchForm.keyword_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(GlossSearchForm.keyword_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                qs = qs.filter(translation__translation__text__iregex=get_value,
                               translation__language=language)

        fieldnames = settings.MINIMAL_PAIRS_SEARCH_FIELDS
        fields_with_choices = fields_to_fieldcategory_dict()
        multiple_select_gloss_fields = [field.name for field in Gloss._meta.fields
                                                    if field.name in fieldnames
                                                    and field.name in fields_with_choices.keys()]

        for fieldnamemulti in multiple_select_gloss_fields:
            fieldnamemultiVarname = fieldnamemulti + '[]'
            if fieldnamemulti == 'semField':
                fieldnameQuery = 'semField' + '__machine_value__in'
            else:
                fieldnameQuery = fieldnamemulti + '__machine_value__in'

            vals = get.getlist(fieldnamemultiVarname)
            if vals != []:
                qs = qs.filter(**{ fieldnameQuery: vals })

        # phonology and semantics field filters
        fieldnames = [ f for f in fieldnames if f not in multiple_select_gloss_fields ]

        for fieldname in fieldnames:

            if fieldname in get and get[fieldname] != '':
                field_obj = Gloss._meta.get_field(fieldname)

                if type(field_obj) in [CharField,TextField] and not hasattr(field_obj, 'field_choice_category'):
                    key = fieldname + '__icontains'
                else:
                    key = fieldname + '__exact'

                val = get[fieldname]

                if isinstance(field_obj,BooleanField):
                    val = {'0':'','1': None, '2': True, '3': False}[val]

                if val != '':
                    kwargs = {key:val}
                    qs = qs.filter(**kwargs)
        qs = qs.select_related('lemma')

        return qs

class QueryListView(ListView):
    # not sure what model should be used here, it applies to all the glosses in a dataset
    model = Dataset
    template_name = 'dictionary/admin_query_list.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(QueryListView, self).get_context_data(**kwargs)

        language_code = self.request.LANGUAGE_CODE

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'GLOSS_LIST_DISPLAY_FIELDS'):
            context['GLOSS_LIST_DISPLAY_FIELDS'] = settings.GLOSS_LIST_DISPLAY_FIELDS
        else:
            context['GLOSS_LIST_DISPLAY_FIELDS'] = []

        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []
        if search_results and len(search_results) > 0:
            if self.request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []

        (objects_on_page, object_list) = map_search_results_to_gloss_list(search_results)
        if 'query_parameters' in self.request.session.keys() and self.request.session['query_parameters'] not in ['', '{}']:
            # if the query parameters are available, convert them to a dictionary
            session_query_parameters = self.request.session['query_parameters']
            query_parameters = json.loads(session_query_parameters)
        else:
            # local query parameters
            query_parameters = {}
            # save the default query parameters to the sessin variable
            self.request.session['query_parameters'] = json.dumps(query_parameters)
            self.request.session.modified = True

        query_parameters_mapping = pretty_print_query_fields(dataset_languages, query_parameters.keys())

        query_parameters_values_mapping = pretty_print_query_values(dataset_languages, query_parameters)

        gloss_search_field_prefix = "glosssearch_"
        lemma_search_field_prefix = "lemma_"
        keyword_search_field_prefix = "keyword_"
        query_fields_focus = []
        query_fields_parameters = []
        for qp_key in query_parameters.keys():
            if qp_key == 'search_type':
                continue
            elif qp_key[-2:] == '[]':
                qp_key = qp_key[:-2]
            if qp_key.startswith(gloss_search_field_prefix) or \
                    qp_key.startswith(lemma_search_field_prefix) or \
                        qp_key.startswith(keyword_search_field_prefix):
                continue
            if qp_key in settings.GLOSS_LIST_DISPLAY_FIELDS:
                continue
            query_fields_focus.append(qp_key)
            if qp_key == 'hasRelation':
                # save type of relation
                query_fields_parameters.append(query_parameters[qp_key])

        if 'hasRelationToForeignSign' in query_fields_focus and 'relationToForeignSign' not in query_fields_focus:
            if query_parameters['hasRelationToForeignSign'] == '1':
                # if this is a query with hasRelationToForeignSign True, then also show the relations in the result table
                query_fields_focus.append('relationToForeignSign')

        phonology_focus = settings.GLOSS_LIST_DISPLAY_FIELDS + query_fields_focus

        toggle_gloss_list_display_fields = []
        if hasattr(settings, 'GLOSS_LIST_DISPLAY_FIELDS'):

            for gloss_list_field in settings.GLOSS_LIST_DISPLAY_FIELDS:
                gloss_list_field_parameters = (gloss_list_field,
                                                GlossSearchForm.__dict__['base_fields'][gloss_list_field].label.encode(
                                                    'utf-8').decode())
                toggle_gloss_list_display_fields.append(gloss_list_field_parameters)

        toggle_query_parameter_fields = []
        for query_field in query_fields_focus:
            if query_field == 'search_type':
                # don't show a button for this
                continue
            elif query_field == 'hasothermedia':
                toggle_query_parameter = (query_field, _("Other Media"))
            elif query_field in GlossSearchForm.__dict__['base_fields']:
                toggle_query_parameter = (query_field,GlossSearchForm.__dict__['base_fields'][query_field].label.encode('utf-8').decode())
            elif query_field == 'dialect':
                toggle_query_parameter = (query_field, _("Dialect"))
            elif query_field == 'hasComponentOfType':
                toggle_query_parameter = (query_field, _("Sequential Morphology"))
            elif query_field == 'hasMorphemeOfType':
                toggle_query_parameter = (query_field, _("Morpheme Type"))
            elif query_field == 'morpheme':
                toggle_query_parameter = (query_field, _("Simultaneous Morphology"))
            else:
                toggle_query_parameter = (query_field,query_field.capitalize())
            toggle_query_parameter_fields.append(toggle_query_parameter)

        toggle_publication_fields = []
        if hasattr(settings, 'SEARCH_BY') and 'publication' in settings.SEARCH_BY.keys():

            for publication_field in settings.SEARCH_BY['publication']:
                publication_field_parameters = (publication_field,
                                                GlossSearchForm.__dict__['base_fields'][publication_field].label.encode(
                                                    'utf-8').decode())
                toggle_publication_fields.append(publication_field_parameters)

        context['objects_on_page'] = objects_on_page
        context['object_list'] = object_list
        context['display_fields'] = phonology_focus
        context['query_fields_parameters'] = query_fields_parameters
        context['TOGGLE_QUERY_PARAMETER_FIELDS'] = toggle_query_parameter_fields
        context['TOGGLE_PUBLICATION_FIELDS'] = toggle_publication_fields
        context['TOGGLE_GLOSS_LIST_DISPLAY_FIELDS'] = toggle_gloss_list_display_fields
        context['query_parameters'] = query_parameters
        context['query_parameters_mapping'] = query_parameters_mapping
        context['query_parameters_values_mapping'] = query_parameters_values_mapping
        available_parameters_to_save = available_query_parameters_in_search_history()
        context['available_query_parameters_in_search_history'] = available_parameters_to_save
        query_parameter_keys = query_parameters.keys()
        context['query_parameter_keys'] = query_parameters.keys()

        all_parameters_available_to_save = True
        for param in query_parameter_keys:
            if param not in available_parameters_to_save:
                all_parameters_available_to_save = False
        context['all_parameters_available_to_save'] = all_parameters_available_to_save

        return context
    def get_queryset(self):

        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []
        if search_results and len(search_results) > 0:
            if self.request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []

        (objects_on_page, object_list) = map_search_results_to_gloss_list(search_results)

        return object_list

    def render_to_response(self, context):
        if self.request.GET.get('save_query') == 'Save':
            return self.render_to_save_query(context)
        else:
            return super(QueryListView, self).render_to_response(context)

    def render_to_save_query(self, context):
        query_parameters = context['query_parameters']
        query_name = _("Query View Save")
        field_names = fieldnames_from_query_parameters(query_parameters)
        available_field_names = available_query_parameters_in_search_history()
        # TO DO test that the field names queried upon are supported in the search history
        # give feedback
        save_query_parameters(self.request, query_name, query_parameters)
        return super(QueryListView, self).render_to_response(context)


class SearchHistoryView(ListView):
    # not sure what model should be used here, it applies to all the glosses in a dataset
    model = Dataset
    template_name = 'dictionary/admin_search_history.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SearchHistoryView, self).get_context_data(**kwargs)

        language_code = self.request.LANGUAGE_CODE

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        # this gets the query parameters fields currently being stored by the code
        # see if we need to do anything with this qua feedback
        classnames = available_query_parameters_in_search_history()

        # create a lookup table mapping queries to languages
        selected_datasets_contain_query_languages = {}
        all_queries_user = SearchHistory.objects.filter(user=self.request.user)
        for query in all_queries_user:
            query_languages_this_query = query.query_languages()
            query_languages_in_dataset = True
            for lang in query_languages_this_query:
                if lang not in dataset_languages:
                    query_languages_in_dataset = False
            selected_datasets_contain_query_languages[query] = query_languages_in_dataset
        context['selected_datasets_contain_query_languages'] = selected_datasets_contain_query_languages

        query_to_display_parameters = {}
        for query in all_queries_user:
            query_to_display_parameters[query] = display_parameters(query)
        context['query_to_display_parameters'] = query_to_display_parameters

        return context

    def get_queryset(self):

        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []
        if search_results and len(search_results) > 0:
            if self.request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []

        qs = SearchHistory.objects.filter(user=self.request.user).order_by('queryDate').reverse()

        # for sh in qs:
        #     languages = languages_in_query(sh.id)
        #     if len(languages):
        #         print('result of languages in query: ', languages)

        return qs

    def render_to_response(self, context):
        if self.request.GET.get('run_query') == 'Run':
            queryid = self.request.GET.get('queryid')
            languages = languages_in_query(queryid)
            dataset_languages = context['dataset_languages']
            # the template does not show the run_query button if the languages are not present
            # this is a safety measure
            for lang in languages:
                if lang not in dataset_languages:
                    messages.add_message(self.request, messages.ERROR, _('Language '+lang.name+' is missing from the selected datasets.'))
                    return HttpResponseRedirect(settings.PREFIX_URL + '/analysis/search_history/')

            return self.render_to_run_query(context, queryid)
        else:
            return super(SearchHistoryView, self).render_to_response(context)

    def render_to_run_query(self, context, queryid):
        query = get_object_or_404(SearchHistory, id=queryid)
        query_parameters = get_query_parameters(query)
        self.request.session['query_parameters'] = json.dumps(query_parameters)
        self.request.session.modified = True
        return HttpResponseRedirect(settings.PREFIX_URL + '/signs/search/?query')


class FrequencyListView(ListView):
    # not sure what model should be used here, it applies to all the glosses in a dataset
    model = Dataset
    template_name = 'dictionary/admin_frequency_list.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(FrequencyListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        context['dataset_ids'] = [ ds.id for ds in selected_datasets]

        # sort the phonology fields based on field label in the designated language
        # this is used for display in the template, by lookup
        field_labels = dict()
        for field in FIELDS['phonology']:
            if field in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
                continue
            if field not in [f.name for f in Gloss._meta.fields]:
                continue
            if fieldname_to_kind(field) == 'list':
                field_label = Gloss._meta.get_field(field).verbose_name
                field_labels[field] = field_label.encode('utf-8').decode()

        # note on context variables below: there are two variables for the same data
        # the context variable field_labels_list is iterated over in the template to generate the pull-down menu
        # this pull-down has to be sorted in the destination language
        # the menu generation is done by Django as part of the form
        # after Django generates the form, it is modified by javascript to convert the options to a multiple-select
        # the javascript makes use of the labels generated by Django
        # there were some issues getting the other dict variable (field_labels) to remain sorted in the template
        # the field_labels dict is used to lookup the display names, it does not need to be sorted

        field_labels_list = [ (k, v) for (k, v) in sorted(field_labels.items(), key=lambda x: x[1])]
        context['field_labels'] = field_labels
        context['field_labels_list'] = field_labels_list

        # sort the field choices based on the designated language
        # this is used for display in the template, by lookup
        field_labels_choices = dict()
        for field, label in field_labels.items():
            gloss_field = Gloss._meta.get_field(field)

            # Get and save the choice list for this field
            if isinstance(gloss_field, models.ForeignKey) and gloss_field.related_model == Handshape:
                field_choices = Handshape.objects.all().order_by('name')
            elif hasattr(gloss_field, 'field_choice_category'):
                field_category = gloss_field.field_choice_category
                field_choices = FieldChoice.objects.filter(field__iexact=field_category).order_by('name')
            else:
                field_category = field
                field_choices = FieldChoice.objects.filter(field__iexact=field_category).order_by('name')
            translated_choices = choicelist_queryset_to_translated_dict(field_choices,ordered=False,id_prefix='_',shortlist=False)
            field_labels_choices[field] = dict(translated_choices)

        context['field_labels_choices'] = field_labels_choices

        # do the same for the semantics fields
        # the code is here to keep phonology and semantics in separate dicts,
        # but at the moment all results are displayed in one table in the template

        field_labels_semantics = dict()
        for field in FIELDS['semantics']:
            if fieldname_to_kind(field) == 'list':
                field_label = Gloss._meta.get_field(field).verbose_name
                field_labels_semantics[field] = field_label.encode('utf-8').decode()

        field_labels_semantics_list = [ (k, v) for (k, v) in sorted(field_labels_semantics.items(), key=lambda x: x[1])]
        context['field_labels_semantics'] = field_labels_semantics
        context['field_labels_semantics_list'] = field_labels_semantics_list

        field_labels_semantics_choices = dict()
        for field, label in field_labels_semantics.items():
            gloss_field = Gloss._meta.get_field(field)
            # Get and save the choice list for this field
            if hasattr(gloss_field, 'field_choice_category'):
                field_category = gloss_field.field_choice_category
                field_choices = FieldChoice.objects.filter(field__iexact=field_category).order_by('name')
            elif field in ['semField']:
                field_choices = SemanticField.objects.all()
            elif field in ['derivHist']:
                field_choices = DerivationHistory.objects.all()
            else:
                field_choices = []

            translated_choices = choicelist_queryset_to_translated_dict(field_choices,ordered=False,id_prefix='_',shortlist=False)
            field_labels_semantics_choices[field] = dict(translated_choices)

        context['field_labels_semantics_choices'] = field_labels_semantics_choices

        # for ease of implementation in the template, the results of the two kinds of frequencies
        # (phonology fields, semantics fields) are displayed in the same table, the lookup tables are merged so only one loop is needed

        context['all_field_labels'] = dict(field_labels, **field_labels_semantics)

        if hasattr(settings, 'SHOW_QUERY_PARAMETERS_AS_BUTTON') and settings.SHOW_QUERY_PARAMETERS_AS_BUTTON:
            context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = settings.SHOW_QUERY_PARAMETERS_AS_BUTTON
        else:
            context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = False

        return context

    def get_queryset(self):

        user = self.request.user

        if user.is_authenticated:
            selected_datasets = get_selected_datasets_for_user(self.request.user)
            from django.db.models import Prefetch
            qs = Dataset.objects.filter(id__in=selected_datasets).prefetch_related(
                Prefetch(
                    "userprofile_set",
                    queryset=UserProfile.objects.filter(user=user),
                    to_attr="user"
                )
            )

            checker = ObjectPermissionChecker(user)

            checker.prefetch_perms(qs)

            for dataset in qs:
                checker.has_perm('can_view_dataset', dataset) or checker.has_perm('view_dataset', dataset)

            return qs
        else:
            # User is not authenticated
            return None


class GlossFrequencyView(DetailView):

    model = Gloss
    context_object_name = 'gloss'
    last_used_dataset = None
    pk_url_kwarg = 'gloss_id'

    template_name = "dictionary/gloss_frequency.html"

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested gloss does not exist.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})
        if self.object.lemma == None or self.object.lemma.dataset == None:
            translated_message = _('Requested gloss has no lemma or dataset.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        if not request.user.is_authenticated:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_gloss = self.object.lemma.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=False, any_perm=True)

        if dataset_of_requested_gloss not in selected_datasets:
            translated_message = _('The gloss you are trying to view is not in your selected datasets.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })
        if dataset_of_requested_gloss not in datasets_user_can_view:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss',kwargs={'glossid':self.object.pk}))
            else:
                translated_message = _('The gloss you are trying to view is not in a dataset you can view.')
                return render(request, 'dictionary/warning.html',
                              {'warning': translated_message,
                               'dataset_languages': dataset_languages,
                               'selected_datasets': selected_datasets,
                               'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(GlossFrequencyView, self).get_context_data(**kwargs)

        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []
        if search_results and len(search_results) > 0:
            if self.request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        #Pass info about which fields we want to see
        gl = context['gloss']
        context['active_id'] = gl.id
        labels = gl.field_labels()

        # set a session variable to be able to pass the gloss's id to the ajax_complete method
        # the last_used_dataset name is updated to that of this gloss
        # if a sequesce of glosses are being created by hand, this keeps the dataset setting the same
        if gl.dataset:
            self.request.session['datasetid'] = gl.dataset.id
            self.last_used_dataset = gl.dataset.acronym
        else:
            self.request.session['datasetid'] = get_default_language_id()

        # CHECK THIS
        self.request.session['last_used_dataset'] = self.last_used_dataset

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        context['dataset_ids'] = [ ds.id for ds in selected_datasets]
        context['dataset_names'] = [ds.acronym for ds in selected_datasets]

        context['frequency_regions'] = gl.dataset.frequency_regions()

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['dataset_choices'] = {}
            user = self.request.user
            if user.is_authenticated:
                qs = get_objects_for_user(user, ['view_dataset', 'can_view_dataset'],
                                          Dataset, accept_global_perms=False, any_perm=True)
                dataset_choices = {}
                for dataset in qs:
                    dataset_choices[dataset.acronym] = dataset.acronym
                context['dataset_choices'] = json.dumps(dataset_choices)

        try:
            context['corpus'] = Corpus.objects.get(name=gl.dataset.acronym)
        except ObjectDoesNotExist:
            context['corpus'] = None

        total_occurrences, data_datasets = gl.data_datasets()
        context['data_datasets'] = data_datasets
        context['num_occurrences'] = total_occurrences

        # has_frequency_data returns a count of the number of GlossFrequency objects for this gloss
        context['has_frequency_data'] = gl.has_frequency_data()

        # the following collects the speakers distributed over a range of ages to display on the x axis
        # for display in chartjs, the age labels are stored separately from the number of speakers having that age
        speakers_summary = gl.speaker_age_data()

        age_range = [ False for i in range(0, 100)]

        (speaker_age_data, age_range) = collect_speaker_age_data(speakers_summary, age_range)
        # more ages will be added to age_range below for variants, so they are not yet stored in the context variables

        context['speaker_age_data'] = speaker_age_data

        context['speaker_data'] = gl.speaker_data()

        context['num_signers'] = len(get_corpus_speakers(gl.dataset.acronym))

        # incorporates legacy relations
        # a variant pattern is only a variant if there are no other relations between the focus gloss and other glosses under consideration
        # variants might be explictly stored as relations to other glosses
        # the has_variants method only catches explicitly stored variants
        # the pattern variants method excludes glosses with explictly stored relations (including variant relations) to the focus gloss
        # therefore we first try pattern variants

        # for the purposes of frequency charts in the template, the focus gloss is included in the variants
        # this simplifies generating tables for variants inside of a loop in the javascript
        pattern_variants = [ pv for pv in gl.pattern_variants() ]
        other_variants = gl.has_variants()
        variants = pattern_variants + [ ov for ov in other_variants if ov not in pattern_variants ]

        context['variants'] = variants
        # the gloss itself is included among the variants, check that there are other glosses in the list
        context['has_variants'] = len(variants) > 1

        (variants_data_quick_access, sorted_variants_with_keys) = collect_variants_data(variants)

        context['variants_data_quick_access'] = variants_data_quick_access

        variant_labels = []
        for (og_igloss, og) in sorted_variants_with_keys:
            if og_igloss not in variant_labels:
                variant_labels.append(og_igloss)
        context['variant_labels'] = variant_labels

        (variants_age_range_distribution_data, age_range) = collect_variants_age_range_data(sorted_variants_with_keys, age_range)
        context['variants_age_range_distribution_data'] = variants_age_range_distribution_data
        context['age_range'] = json.dumps(age_range)

        (variants_sex_distribution_data_raw,
         variants_sex_distribution_data_percentage,
         variants_age_distribution_data_raw,
         variants_age_distribution_data_percentage) = collect_variants_age_sex_raw_percentage(sorted_variants_with_keys,
                                                                                              variants_data_quick_access)

        context['variants_sex_distribution_data'] = variants_sex_distribution_data_raw
        context['variants_sex_distribution_data_percentage'] = variants_sex_distribution_data_percentage

        context['variants_age_distribution_data'] = variants_age_distribution_data_raw
        context['variants_age_distribution_data_percentage'] = variants_age_distribution_data_percentage

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'SHOW_LETTER_NUMBER_PHONOLOGY'):
            context['SHOW_LETTER_NUMBER_PHONOLOGY'] = settings.SHOW_LETTER_NUMBER_PHONOLOGY
        else:
            context['SHOW_LETTER_NUMBER_PHONOLOGY'] = False

        if hasattr(settings, 'SHOW_QUERY_PARAMETERS_AS_BUTTON') and settings.SHOW_QUERY_PARAMETERS_AS_BUTTON:
            context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = settings.SHOW_QUERY_PARAMETERS_AS_BUTTON
        else:
            context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = False

        gloss_default_annotationidglosstranslation = gl.annotationidglosstranslation_set.get(language=default_language).text
        # Put annotation_idgloss per language in the context
        context['annotation_idgloss'] = {}
        for language in gl.dataset.translation_languages.all():
            try:
                annotation_translation = gl.annotationidglosstranslation_set.get(language=language).text
            except (ValueError):
                annotation_translation = gloss_default_annotationidglosstranslation
            context['annotation_idgloss'][language] = annotation_translation

        if interface_language in context['annotation_idgloss'].keys():
            gloss_idgloss = context['annotation_idgloss'][interface_language]
        else:
            gloss_idgloss = context['annotation_idgloss'][default_language]
        context['gloss_idgloss'] = gloss_idgloss

        context['view_type'] = 'percentage'

        return context


class LemmaFrequencyView(DetailView):

    model = Gloss
    context_object_name = 'gloss'
    last_used_dataset = None
    pk_url_kwarg = 'gloss_id'

    template_name = "dictionary/lemma_frequency.html"

    def get_context_data(self, **kwargs):

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        # Call the base implementation first to get a context
        context = super(LemmaFrequencyView, self).get_context_data(**kwargs)

        #Pass info about which fields we want to see
        gl = context['gloss']
        labels = gl.field_labels()

        # set a session variable to be able to pass the gloss's id to the ajax_complete method
        # the last_used_dataset name is updated to that of this gloss
        # if a sequesce of glosses are being created by hand, this keeps the dataset setting the same
        if gl.dataset:
            self.request.session['datasetid'] = gl.dataset.id
            self.last_used_dataset = gl.dataset.acronym
        else:
            self.request.session['datasetid'] = get_default_language_id()

        # CHECK THIS
        self.request.session['last_used_dataset'] = self.last_used_dataset

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        context['dataset_ids'] = [ ds.id for ds in selected_datasets]
        context['dataset_names'] = [ds.acronym for ds in selected_datasets]

        context['frequency_regions'] = gl.dataset.frequency_regions()

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['dataset_choices'] = {}
            user = self.request.user
            if user.is_authenticated:
                qs = get_objects_for_user(user, ['view_dataset', 'can_view_dataset'],
                                          Dataset, accept_global_perms=False, any_perm=True)
                dataset_choices = {}
                for dataset in qs:
                    dataset_choices[dataset.acronym] = dataset.acronym
                context['dataset_choices'] = json.dumps(dataset_choices)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'SHOW_LETTER_NUMBER_PHONOLOGY'):
            context['SHOW_LETTER_NUMBER_PHONOLOGY'] = settings.SHOW_LETTER_NUMBER_PHONOLOGY
        else:
            context['SHOW_LETTER_NUMBER_PHONOLOGY'] = False

        # Put annotation_idgloss per language in the context
        gloss_default_annotationidglosstranslation = gl.annotationidglosstranslation_set.get(language=default_language).text
        context['annotation_idgloss'] = {}
        for language in gl.dataset.translation_languages.all():
            try:
                annotation_text = gl.annotationidglosstranslation_set.get(language=language).text
            except (ObjectDoesNotExist):
                annotation_text = gloss_default_annotationidglosstranslation
            context['annotation_idgloss'][language] = annotation_text
        if interface_language in context['annotation_idgloss'].keys():
            gloss_idgloss = context['annotation_idgloss'][interface_language]
        else:
            gloss_idgloss = context['annotation_idgloss'][default_language]
        context['gloss_idgloss'] = gloss_idgloss

        try:
            lemma_group_count = gl.lemma.gloss_set.count()
            if lemma_group_count > 1:
                context['lemma_group'] = True
                lemma_group_url_params = {'search_type': 'sign', 'view_type': 'lemma_groups'}
                for lemmaidglosstranslation in gl.lemma.lemmaidglosstranslation_set.prefetch_related('language'):
                    lang_code_2char = lemmaidglosstranslation.language.language_code_2char
                    lemma_group_url_params['lemma_'+lang_code_2char] = '^' + lemmaidglosstranslation.text + '$'
                from urllib.parse import urlencode
                url_query = urlencode(lemma_group_url_params)
                url_query = ("?" + url_query) if url_query else ''
                context['lemma_group_url'] = reverse_lazy('signs_search') + url_query
            else:
                context['lemma_group'] = False
                context['lemma_group_url'] = ''
        except:
            print("lemma_group_count: except")
            context['lemma_group'] = False
            context['lemma_group_url'] = ''

        lemma_group_glosses = gl.lemma.gloss_set.all()
        glosses_in_lemma_group = []

        total_occurrences = 0
        data_lemmas = []
        if lemma_group_glosses:
            for gl_lem in lemma_group_glosses:
                data_lemmas_dict = {}
                lemma_dict = {}
                if gl_lem.dataset:
                    for language in gl_lem.dataset.translation_languages.all():
                        lemma_dict[language.language_code_2char] = gl_lem.annotationidglosstranslation_set.filter(language=language)
                else:
                    language = Language.objects.get(id=get_default_language_id())
                    lemma_dict[language.language_code_2char] = gl_lem.annotationidglosstranslation_set.filter(language=language)
                if interface_language_code in lemma_dict.keys():
                    gl_lem_display = lemma_dict[interface_language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    gl_lem_display = lemma_dict[default_language_code][0].text

                glosses_in_lemma_group.append((gl_lem,gl_lem_display))
                data_lemmas_dict['label'] = gl_lem_display
                total_occurrences_lemma, gl_lem_data_datasets_dict = gl_lem.data_datasets()
                total_occurrences += total_occurrences_lemma
                data_lemmas_dict['data'] = gl_lem_data_datasets_dict[0]['data']
                data_lemmas.append(data_lemmas_dict)

        context['data_lemmas'] = json.dumps(data_lemmas)

        context['num_occurrences'] = total_occurrences

        context['glosses_in_lemma_group'] = glosses_in_lemma_group

        return context


class HandshapeListView(ListView):

    model = Handshape
    template_name = 'dictionary/admin_handshape_list.html'
    search_type = 'handshape'
    show_all = False

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(HandshapeListView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books

        search_form = HandshapeSearchForm(self.request.GET)

        # Retrieve the search_type,so that we know whether the search should be Gloss or not
        if 'search_type' in self.request.GET:
            self.search_type = self.request.GET['search_type']
        else:
            self.search_type = 'handshape'

        # self.request.session['search_type'] = self.search_type

        context['searchform'] = search_form
        context['search_type'] = self.search_type

        context['handshapefieldchoicecount'] = Handshape.objects.filter(machine_value__gt=1).count()

        if self.request.user.is_authenticated:
            selected_datasets = get_selected_datasets_for_user(self.request.user)
        elif 'selected_datasets' in self.request.session.keys():
            selected_datasets = Dataset.objects.filter(acronym__in=self.request.session['selected_datasets'])
        else:
            selected_datasets = Dataset.objects.filter(acronym=settings.DEFAULT_DATASET_ACRONYM)
        context['selected_datasets'] = selected_datasets

        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages
        
        context['signscount'] = Gloss.objects.filter(lemma__dataset__in=selected_datasets).count()

        context['HANDSHAPE_RESULT_FIELDS'] = settings.HANDSHAPE_RESULT_FIELDS

        if 'show_all' in self.kwargs.keys():
            context['show_all'] = self.kwargs['show_all']
        else:
            context['show_all'] = False

        context['handshapescount'] = Handshape.objects.filter(machine_value__gt=1).count()

        # this is needed to avoid crashing the browser if you go to the last page
        # of an extremely long list and go to Details on the objects

        list_of_objects = self.object_list

        # construct scroll bar
        # the following retrieves language code for English (or DEFAULT LANGUAGE)
        # so the sorting of the scroll bar matches the default sorting of the results in Gloss List View

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        dataset_display_languages = []
        for lang in dataset_languages:
            dataset_display_languages.append(lang.language_code_2char)
        if interface_language_code in dataset_display_languages:
            lang_attr_name = interface_language_code
        else:
            lang_attr_name = default_language_code

        items = construct_scrollbar(list_of_objects, self.search_type, lang_attr_name)
        self.request.session['search_results'] = items

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        # this is a shorthand for use in the template
        handshape_to_fields = dict()
        if list_of_objects:
            for handshape in list_of_objects:
                if isinstance(handshape, Handshape):
                    # the list of objects might be glosses that have the handshape that was queried
                    handshape_fields = []
                    for handshape_field in settings.HANDSHAPE_RESULT_FIELDS:
                        if handshape_field in ['machine_value', 'name']:
                            continue
                        mapped_handshape_value = getattr(handshape, handshape_field)
                        handshape_fields.append((handshape_field, mapped_handshape_value))
                    handshape_to_fields[handshape] = handshape_fields

        context['handshape_to_fields'] = handshape_to_fields
        return context

    def render_to_response(self, context):
        # Look for a 'format=json' GET argument
        if self.request.GET.get('format') == 'CSV':
            return self.render_to_csv_response(context)
        else:
            return super(HandshapeListView, self).render_to_response(context)

    def render_to_csv_response(self, context):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dictionary-export-handshapes.csv"'

        writer = csv.writer(response)

        if self.search_type and self.search_type == 'handshape':

            writer = write_csv_for_handshapes(self, writer)
        else:
            print('search type is sign')

        return response

    def get_queryset(self):

        handshape_fields = {}
        for f in Handshape._meta.fields:
            handshape_fields[f.name] = f

        # get query terms from self.request
        get = self.request.GET

        #First check whether we want to show everything or a subset
        if 'show_all' in self.kwargs.keys():
            show_all = self.kwargs['show_all']
        else:
            show_all = False

        #Then check what kind of stuff we want
        if 'search_type' in get:
            self.search_type = get['search_type']
        else:
            self.search_type = 'handshape'

        setattr(self.request.session, 'search_type', self.search_type)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        from signbank.dictionary.forms import check_multilingual_fields
        valid_regex, search_fields = check_multilingual_fields(Handshape, get, dataset_languages)

        if not valid_regex:
            error_message_1 = _('Error in search field ')
            error_message_2 = ', '.join(search_fields)
            error_message_3 = _(': Please use a backslash before special characters.')
            error_message = error_message_1 + error_message_2 + error_message_3
            messages.add_message(self.request, messages.ERROR, error_message)
            qs = Handshape.objects.none()
            return qs

        qs = Handshape.objects.filter(machine_value__gt=1).order_by('machine_value')

        if show_all:
            if ('sortOrder' in get and get['sortOrder'] != 'machine_value'):
                # User has toggled the sort order for the column
                qs = order_handshape_queryset_by_sort_order(self.request.GET, qs)
            else:
                # The default is to order the signs alphabetically by whether there is an angle bracket
                qs = order_handshape_by_angle(qs)
            return qs

        fieldnames = ['machine_value', 'name']+FIELDS['handshape']

        ## phonology and semantics field filters
        for fieldname in fieldnames:
            field = handshape_fields[fieldname]
            if fieldname in get:
                key = fieldname + '__exact'
                val = get[fieldname]

                if fieldname == 'hsNumSel' and val != '':
                    query_hsNumSel = field.name
                    with override('en'):
                        # the override is necessary in order to use the total fingers rather than each finger
                        try:
                            fieldlabel = FieldChoice.objects.get(field=field.field_choice_category,
                                                                          machine_value=val).name
                        except (ObjectDoesNotExist, KeyError):
                            fieldlabel = ''

                    if fieldlabel == 'one':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__exact=1) | Q(**{query_hsNumSel:val}))
                    elif fieldlabel == 'two':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__exact=2) | Q(**{query_hsNumSel:val}))
                    elif fieldlabel == 'three':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__exact=3) | Q(**{query_hsNumSel:val}))
                    elif fieldlabel == 'four':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__exact=4) | Q(**{query_hsNumSel:val}))
                    elif fieldlabel == 'all':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__gt=4) | Q(**{query_hsNumSel:val}))

                if isinstance(Handshape._meta.get_field(fieldname), BooleanField):
                    val = {'0': False, '1': True, 'True': True, 'False': False, 'None': '', '': '' }[val]

                if fieldname == 'name' and val != '':
                    query = Q(name__iregex=val)
                    qs = qs.filter(query)

                if val not in ['', '0'] and fieldname not in ['hsNumSel', 'name']:

                    if isinstance(Handshape._meta.get_field(fieldname), FieldChoiceForeignKey):
                        key = fieldname + '__machine_value'
                        kwargs = {key: int(val)}
                        qs = qs.filter(**kwargs)
                    else:
                        kwargs = {key: val}
                        qs = qs.filter(**kwargs)

        if ('sortOrder' in get and get['sortOrder'] != 'machine_value'):
            # User has toggled the sort order for the column
            qs = order_handshape_queryset_by_sort_order(self.request.GET, qs)
        else:
            # The default is to order the signs alphabetically by whether there is an angle bracket
            qs = order_handshape_by_angle(qs)

        if self.search_type == 'sign_handshape':

            # search for signs with found hadnshapes
            # find relevant machine values for handshapes
            selected_handshapes = [ h.machine_value for h in qs ]
            selected_datasets = get_selected_datasets_for_user(self.request.user)

            # set up filters, obscuring whether the _fk field names are used
            strong_hand = 'domhndsh'
            strong_hand_in = strong_hand + '__machine_value__in'
            weak_hand = 'subhndsh'
            weak_hand_in = weak_hand + '__machine_value__in'

            qs = Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(
                        (Q(**{strong_hand_in: selected_handshapes}) |
                         Q(**{weak_hand_in: selected_handshapes}) ))

        self.request.session['search_type'] = self.search_type

        return qs


class DatasetListView(ListView):
    model = Dataset
    # set the default dataset, this should not be empty
    dataset_name = settings.DEFAULT_DATASET_ACRONYM


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DatasetListView, self).get_context_data(**kwargs)

        if not self.request.user.is_authenticated:
            if 'selected_datasets' in self.request.session.keys():
                selected_dataset_acronyms = self.request.session['selected_datasets']
                selected_datasets = Dataset.objects.filter(acronym__in=selected_dataset_acronyms)
            else:
                selected_datasets = get_selected_datasets_for_user(self.request.user)
                self.request.session['selected_datasets'] = [ ds.acronym for ds in selected_datasets ]
        else:
            selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        nr_of_public_glosses = {}
        nr_of_glosses = {}
        datasets_with_public_glosses = get_datasets_with_public_glosses()

        for ds in datasets_with_public_glosses:
            nr_of_public_glosses[ds] = Gloss.objects.filter(lemma__dataset=ds, inWeb=True).count()
            nr_of_glosses[ds] = Gloss.objects.filter(lemma__dataset=ds).count()

        context['nr_of_public_glosses'] = nr_of_public_glosses
        context['nr_of_glosses'] = nr_of_glosses

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        context['messages'] = messages.get_messages(self.request)
        return context

    def get_template_names(self):
        if 'select' in self.kwargs:
            return ['dictionary/admin_dataset_select_list.html']
        return ['dictionary/admin_dataset_list.html']

    def render_to_response(self, context):
        if self.request.GET.get('export_ecv') == 'ECV':
            return self.render_to_ecv_export_response(context)
        elif self.request.GET.get('request_view_access') == 'VIEW':
            return self.render_to_request_response(context)
        else:
            return super(DatasetListView, self).render_to_response(context)

    def render_to_request_response(self, context):

        # check that the user is logged in
        if self.request.user.is_authenticated:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        try:
            dataset_object = Dataset.objects.get(name=self.dataset_name)
        except ObjectDoesNotExist:
            translated_message = _('No dataset found with that name.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        # check that the dataset has an owner
        owners_of_dataset = dataset_object.owners.all()
        if len(owners_of_dataset) <1:
            messages.add_message(self.request, messages.ERROR, _('Dataset must have at least one owner.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        # make sure the user can write to this dataset
        from guardian.shortcuts import get_objects_for_user, assign_perm
        user_view_datasets = get_objects_for_user(self.request.user, ['view_dataset', 'can_view_dataset'],
                                                  Dataset, accept_global_perms=False, any_perm=True)
        may_request_dataset = True
        if dataset_object.is_public and not dataset_object in user_view_datasets:
            # the user currently has no view permission for the requested dataset
            # Give permission to access dataset
            may_request_dataset = True
            assign_perm('can_view_dataset', self.request.user, dataset_object)
            messages.add_message(self.request, messages.INFO,
                                             _('View permission for user successfully granted.'))
        elif not dataset_object.is_public and not dataset_object in user_view_datasets:
            may_request_dataset = False
            messages.add_message(self.request, messages.INFO,
                                             _('View permission for user requested.'))
        else:
            # this should not happen from the html page. the check is made to catch a user adding a parameter to the url
            may_request_dataset = False
            messages.add_message(self.request, messages.INFO, _('You can already view this dataset.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        motivation = ''
        if 'motivation_for_use' in get:
            motivation = get['motivation_for_use']  # motivation is a required field in the form

        # notify the dataset owner(s) about the access request
        from django.contrib.auth.models import Group
        group_manager = Group.objects.get(name='Dataset_Manager')

        for owner in owners_of_dataset:

            groups_of_user = owner.groups.all()
            if group_manager not in groups_of_user:
                # this owner can't manage users
                continue

            # send email to the dataset manager
            from django.core.mail import send_mail
            current_site = Site.objects.get_current()
            
            # send email to notify dataset managers that user was GIVEN access
            if may_request_dataset:
                subject = render_to_string('registration/dataset_to_owner_existing_user_given_access_subject.txt',
                                        context={'dataset': dataset_object.name,
                                                    'site': current_site})
                # Email subject *must not* contain newlines
                subject = ''.join(subject.splitlines())

                message = render_to_string('registration/dataset_to_owner_existing_user_given_access.txt',
                                        context={'user': self.request.user,
                                                    'dataset': dataset_object.name,
                                                    'motivation': motivation,
                                                    'site': current_site})

                # for debug purposes on local machine
                if settings.DEBUG_EMAILS_ON:
                    print('grant access subject: ', subject)
                    print('message: ', message)
                    print('owner of dataset: ', owner.username, ' with email: ', owner.email)
                    print('user email: ', self.request.user.email)
                    print('Settings: ', settings.DEFAULT_FROM_EMAIL)

                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [owner.email])
            
            # send email to notify dataset managers that user REQUESTS access
            elif not may_request_dataset:
                subject = render_to_string('registration/dataset_to_owner_user_requested_access_subject.txt',
                                        context={'dataset': dataset_object.name,
                                                    'site': current_site})
                # Email subject *must not* contain newlines
                subject = ''.join(subject.splitlines())

                message = render_to_string('registration/dataset_to_owner_user_requested_access.txt',
                                        context={'user': self.request.user,
                                                    'dataset': dataset_object.name,
                                                    'motivation': motivation,
                                                    'site': current_site})

                # for debug purposes on local machine
                if settings.DEBUG_EMAILS_ON:
                    print('grant access subject: ', subject)
                    print('message: ', message)
                    print('owner of dataset: ', owner.username, ' with email: ', owner.email)
                    print('user email: ', self.request.user.email)
                    print('Settings: ', settings.DEFAULT_FROM_EMAIL)

                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [owner.email])

        return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

    def render_to_ecv_export_response(self, context):

        # check that the user is logged in
        if self.request.user.is_authenticated:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        try:
            dataset_object = Dataset.objects.get(acronym=self.dataset_name)
        except ObjectDoesNotExist:
            translated_message = _('No dataset found with that acronym.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # make sure the user can write to this dataset
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = get_objects_for_user(self.request.user, 'change_dataset', Dataset, accept_global_perms=False)
        if user_change_datasets and dataset_object in user_change_datasets:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, _('No permission to export dataset.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # make sure the dataset is non-empty, don't create an empty ecv file
        dataset_count = dataset_object.count_glosses()
        if not dataset_count:
            messages.add_message(self.request, messages.INFO, _('The dataset is empty, export ECV is not available.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # if we get to here, the user is authenticated and has permission to export the dataset
        ecv_file = write_ecv_file_for_dataset(self.dataset_name)

        if ecv_file:
            messages.add_message(self.request, messages.INFO, _('ECV successfully updated.'))
        else:
            messages.add_message(self.request, messages.INFO, _('No ECV created for the dataset.'))
        # return HttpResponse('ECV successfully updated.')
        return HttpResponseRedirect(reverse('admin_dataset_view'))

    def get_queryset(self):
        user = self.request.user

        # get query terms from self.request
        get = self.request.GET

        # Then check what kind of stuff we want
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        # otherwise the default dataset_name DEFAULT_DATASET_ACRONYM is used

        # not sure what this accomplishes
        # setattr(self.request, 'dataset_name', self.dataset_name)

        if user.is_authenticated:
            from django.db.models import Prefetch
            qs = Dataset.objects.all().prefetch_related(
                Prefetch(
                    "userprofile_set",
                    queryset=UserProfile.objects.filter(user=user),
                    to_attr="user"
                )
            )

            checker = ObjectPermissionChecker(user)

            checker.prefetch_perms(qs)

            for dataset in qs:
                checker.has_perm('can_view_dataset', dataset) or checker.has_perm('view_dataset', dataset)

            qs = qs.annotate(Count('lemmaidgloss__gloss')).order_by('acronym')

            return qs
        else:
            # User is not authenticated
            # check if the session variable has been set
            # this reverts to publically available datasets or the default dataset

            if 'selected_datasets' in self.request.session.keys():
                selected_dataset_acronyms = self.request.session['selected_datasets']
                selected_dataset_ids = [ ds.id for ds in Dataset.objects.filter(acronym__in=selected_dataset_acronyms) ]
            else:
                # this is the first time the session variable is set, set it to the default via the called function
                selected_datasets = get_selected_datasets_for_user(self.request.user)
                self.request.session['selected_datasets'] = [ds.acronym for ds in selected_datasets]
                selected_dataset_ids = [ ds.id for ds in selected_datasets ]

            datasets_with_public_glosses = get_datasets_with_public_glosses()
            viewable_datasets = list(
                set([ds.id for ds in datasets_with_public_glosses]))

            qs = Dataset.objects.filter(id__in=viewable_datasets)
            datasets_to_choose_from = qs.annotate(checked=ExpressionWrapper(Q(id__in=selected_dataset_ids),
                                                                            output_field=BooleanField())).order_by('acronym')
            return datasets_to_choose_from


class DatasetManagerView(ListView):
    model = Dataset
    template_name = 'dictionary/admin_dataset_manager.html'

    # set the default dataset, this should not be empty
    dataset_name = settings.DEFAULT_DATASET_ACRONYM


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DatasetManagerView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        form = EAFFilesForm()

        default_language_choice_dict = dict()
        for language in dataset_languages:
            default_language_choice_dict[language.name] = language.name
        context['default_language_choice_list'] = json.dumps(default_language_choice_dict)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        context['messages'] = messages.get_messages(self.request)

        return context

    def render_to_response(self, context):
        if 'add_view_perm' in self.request.GET or 'add_change_perm' in self.request.GET \
                    or 'delete_view_perm' in self.request.GET or 'delete_change_perm' in self.request.GET:
            return self.render_to_add_user_response(context)
        elif 'default_language' in self.request.GET:
            return self.render_to_set_default_language()
        elif 'format' in self.request.GET:
            return self.render_to_csv_response()
        else:
            return super(DatasetManagerView, self).render_to_response(context)

    def check_user_permissions_for_managing_dataset(self, dataset_object):
        """
        Checks whether the logged in user has permission to manage the dataset object
        :return: 
        """
        # check that the user is logged in
        if self.request.user.is_authenticated:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        # check if the user can manage this dataset
        from django.contrib.auth.models import Group, User

        try:
            group_manager = Group.objects.get(name='Dataset_Manager')
        except ObjectDoesNotExist:
            messages.add_message(self.request, messages.ERROR, _('No group Dataset_Manager found.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        groups_of_user = self.request.user.groups.all()
        if group_manager not in groups_of_user:
            messages.add_message(self.request, messages.ERROR,
                                 _('You must be in group Dataset Manager to modify dataset permissions.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        # make sure the user can write to this dataset
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = get_objects_for_user(self.request.user, 'change_dataset', Dataset,
                                                    accept_global_perms=False)
        if user_change_datasets and dataset_object in user_change_datasets:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, _('No permission to modify dataset permissions.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        # Everything is alright
        return None

    def get_dataset_from_request(self):
        """
        Use the 'dataset_name' GET query string parameter to find a dataset object 
        :return: tuple of a dataset object and HttpResponse in which either is None
        """
        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return None, HttpResponseRedirect(reverse('admin_dataset_manager'))

        try:
            return Dataset.objects.get(name=self.dataset_name), None
        except ObjectDoesNotExist:
            translated_message = _('No dataset found with that name.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return None, HttpResponseRedirect(reverse('admin_dataset_manager'))

    def get_user_from_request(self):
        """
        Use the 'username' GET query string parameter to find a user object 
        :return: tuple of a dataset object and HttpResponse in which either is None
        """
        get = self.request.GET
        username = ''
        if 'username' in get:
            username = get['username']
        if username == '':
            messages.add_message(self.request, messages.ERROR,
                                 _('Username must be non-empty. Please make a selection using the drop-down list.'))
            return None, HttpResponseRedirect(reverse('admin_dataset_manager'))

        try:
            return User.objects.get(username=username), None
        except ObjectDoesNotExist:
            translated_message = _('No user with that username found.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return None, HttpResponseRedirect(reverse('admin_dataset_manager'))

    def render_to_set_default_language(self):
        """
        Sets the default language for a dataset
        :return: a HttpResponse object
        """
        dataset_object, response = self.get_dataset_from_request()
        if response:
            return response

        response = self.check_user_permissions_for_managing_dataset(dataset_object)
        if response:
            return response

        try:
            language = Language.objects.get(id=self.request.GET['default_language'])
            if language in dataset_object.translation_languages.all():
                dataset_object.default_language = language
                dataset_object.save()
                messages.add_message(self.request, messages.INFO,
                                     _('The default language of {} is set to {}.'
                                      .format(dataset_object.acronym, language.name)))
            else:
                messages.add_message(self.request, messages.INFO,
                                     _('{} is not in the set of languages of dataset {}.'
                                      .format(language.name, dataset_object.acronym)))
        except (ObjectDoesNotExist, KeyError):
            messages.add_message(self.request, messages.ERROR,
                                 _('Something went wrong setting the default language for '
                                  + dataset_object.acronym))
        return HttpResponseRedirect(reverse('admin_dataset_manager'))

    def render_to_add_user_response(self, context):
        dataset_object, response = self.get_dataset_from_request()
        if response:
            return response
        
        response = self.check_user_permissions_for_managing_dataset(dataset_object)
        if response:
            return response

        user_object, response = self.get_user_from_request()
        if response:
            return response
        username = user_object.username

        # user has permission to modify dataset permissions for other users
        manage_identifier = 'dataset_' + dataset_object.acronym.replace(' ','')

        from guardian.shortcuts import assign_perm, remove_perm
        datasets_user_can_change = get_objects_for_user(user_object, 'change_dataset', Dataset, accept_global_perms=False)
        datasets_user_can_view = get_objects_for_user(user_object, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=False, any_perm=True)
        groups_user_is_in = Group.objects.filter(user=user_object)

        if 'add_view_perm' in self.request.GET:
            manage_identifier += '_manage_view'
            if dataset_object in datasets_user_can_view:
                if user_object.is_staff or user_object.is_superuser:
                    messages.add_message(self.request, messages.INFO,
                                     _('User already has view permission for this dataset as staff or superuser.'))
                else:
                    messages.add_message(self.request, messages.INFO,
                                     _('User already has view permission for this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_manager')+'?'+manage_identifier)

            try:
                assign_perm('can_view_dataset', user_object, dataset_object)
                messages.add_message(self.request, messages.INFO,
                                 _('View permission for user successfully granted.'))

                if not user_object.is_active:
                    user_object.is_active = True
                    assign_perm('dictionary.search_gloss', user_object)
                    user_object.save()

                # send email to user
                from django.core.mail import send_mail
                current_site = Site.objects.get_current()

                subject = render_to_string('registration/dataset_to_user_existing_user_given_access_subject.txt',
                                           context={'dataset': dataset_object.name,
                                                    'site': current_site})
                # Email subject *must not* contain newlines
                subject = ''.join(subject.splitlines())

                message = render_to_string('registration/dataset_to_user_existing_user_given_access.txt',
                                           context={'dataset': dataset_object.name,
                                                    'site': current_site})

                # for debug purposes on local machine
                if settings.DEBUG_EMAILS_ON:
                    print('grant access subject: ', subject)
                    print('message: ', message)
                    print('user email: ', user_object.email)
                    print('Settings: ', settings.DEFAULT_FROM_EMAIL)

                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_object.email])

            except:
                messages.add_message(self.request, messages.ERROR, _('Error assigning view dataset permission to user.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager')+'?'+manage_identifier)

        if 'add_change_perm' in self.request.GET:
            manage_identifier += '_manage_change'

            if dataset_object in datasets_user_can_change and 'Editor' in groups_user_is_in:
                if user_object.is_staff or user_object.is_superuser:
                    messages.add_message(self.request, messages.INFO,
                                         _('User already has change permission for this dataset as staff or superuser.'))
                else:
                    messages.add_message(self.request, messages.INFO,
                                 _('User already has change permission for this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)

            if dataset_object not in datasets_user_can_view:
                messages.add_message(self.request, messages.WARNING,
                                     _('User does not have view permission for this dataset. Please grant view permission first.'))

                # open Manage View Dataset pane instead of Manage Change Dataset
                manage_identifier = 'dataset_' + dataset_object.acronym.replace(' ', '')
                manage_identifier += '_manage_view'
                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)
            try:
                assign_perm('change_dataset', user_object, dataset_object)

                # put user in Editor group
                editor_group = Group.objects.get(name='Editor')
                editor_group.user_set.add(user_object)
                editor_group.save()

                if not user_object.has_perm('dictionary.change_gloss'):
                    assign_perm('dictionary.change_gloss', user_object)
                if not user_object.has_perm('dictionary.add_gloss'):
                    assign_perm('dictionary.add_gloss', user_object)

                messages.add_message(self.request, messages.INFO,
                                     _('Change permission for user successfully granted.'))
            except:
                messages.add_message(self.request, messages.ERROR, _('Error assigning change dataset permission to user.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)

        if 'delete_view_perm' in self.request.GET:
            manage_identifier += '_manage_view'

            if dataset_object in datasets_user_can_view:
                if user_object.is_staff or user_object.is_superuser:
                    messages.add_message(self.request, messages.ERROR,
                                         _('User has view permission for this dataset as staff or superuser. This cannot be modified here.'))
                else:
                    # can remove permission
                    try:
                        # also need to remove change_dataset perm in this case
                        from guardian.shortcuts import remove_perm
                        remove_perm('can_view_dataset', user_object, dataset_object)
                        remove_perm('change_dataset', user_object, dataset_object)
                        messages.add_message(self.request, messages.INFO,
                                             _('View (and change) permission for user successfully revoked.'))
                    except:
                        messages.add_message(self.request, messages.ERROR,
                                             _('Error revoking view dataset permission for user.'))

                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)
            else:
                messages.add_message(self.request, messages.ERROR, _('User currently has no permission to view this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)

        if 'delete_change_perm' in self.request.GET:
            manage_identifier += '_manage_change'

            if dataset_object in datasets_user_can_change:
                if user_object.is_staff or user_object.is_superuser:
                    messages.add_message(self.request, messages.ERROR,
                                         _('User has change permission for this dataset as staff or superuser. This cannot be modified here.'))
                else:
                    # can remove permission
                    try:
                        remove_perm('change_dataset', user_object, dataset_object)
                        other_datasets_user_can_change = get_objects_for_user(user_object, 'change_dataset', Dataset,
                                                                            accept_global_perms=True)
                        if len(other_datasets_user_can_change) == 0:
                            # this was the only dataset the user could change
                            remove_perm('dictionary.change_gloss', user_object)
                            remove_perm('dictionary.add_gloss', user_object)
                            # remove user from Editor group as they can no longer change any datasets
                            editor_group = Group.objects.get(name='Editor')
                            editor_group.user_set.remove(user_object)
                            editor_group.save()
                        messages.add_message(self.request, messages.INFO,
                                             _('Change permission for user successfully revoked.'))
                    except:
                        messages.add_message(self.request, messages.ERROR,
                                             _('Error revoking change dataset permission for user.'))

                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)
            else:
                messages.add_message(self.request, messages.ERROR, _('User currently has no permission to change this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)

        # the code doesn't seem to get here. if somebody puts something else in the url (else case), there is no (hidden) csrf token.
        messages.add_message(self.request, messages.ERROR, _('Unrecognised argument to dataset manager url.'))
        return HttpResponseRedirect(reverse('admin_dataset_manager'))

    def render_to_csv_response(self):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        if not self.request.user.is_authenticated:
            raise PermissionDenied

        dataset_object, response = self.get_dataset_from_request()
        if response:
            return response

        response = self.check_user_permissions_for_managing_dataset(dataset_object)
        if response:
            return response

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        lang_attr_name = 'name_' + DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']

        annotationidglosstranslation_fields = ["Annotation ID Gloss" + " (" + getattr(language, lang_attr_name) + ")" for language in
                                               dataset_languages]

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dictionary-dataset_links.csv"'
        writer = csv.writer(response)

        with override(LANGUAGE_CODE):
            header = ['Signbank ID', 'Dataset'] + annotationidglosstranslation_fields + ['glossvideo url', 'glossimage url']

        writer.writerow(header)
        queryset = Gloss.objects.filter(lemma__dataset_id=dataset_object.id)
        for gloss in queryset:
            row = [str(gloss.pk), gloss.lemma.dataset.acronym]

            for language in dataset_languages:
                annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
                if annotationidglosstranslations and len(annotationidglosstranslations) == 1:
                    row.append(annotationidglosstranslations[0].text)
                else:
                    row.append("")

            def form_full_url(path):
                hyperlink_domain = settings.URL + settings.PREFIX_URL
                protected_media_url = os.path.join('dictionary','protected_media').encode('utf-8')
                return hyperlink_domain + os.path.join(protected_media_url, path.encode('utf-8')).decode()

            gloss_video_path = gloss.get_video_url()
            if gloss_video_path:
                full_url = form_full_url(gloss_video_path)
                row.append(full_url)
            else:
                row.append(gloss_video_path)

            gloss_image_path = gloss.get_image_url()
            if gloss_image_path:
                full_url = form_full_url(gloss_image_path)
                row.append(full_url)
            else:
                row.append(gloss_image_path)

            #Make it safe for weird chars
            safe_row = []
            for column in row:
                try:
                    safe_row.append(column.encode('utf-8').decode())
                except AttributeError:
                    safe_row.append(None)

            writer.writerow(row)

        return response

    def get_queryset(self):
        user = self.request.user

        # get query terms from self.request
        get = self.request.GET

        # Then check what kind of stuff we want
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        # otherwise the default dataset_name DEFAULT_DATASET_ACRONYM is used

        setattr(self.request, 'dataset_name', self.dataset_name)

        if user.is_authenticated:

            # determine if user is a dataset manager
            from django.contrib.auth.models import Group, User
            try:
                group_manager = Group.objects.get(name='Dataset_Manager')
            except ObjectDoesNotExist:
                messages.add_message(self.request, messages.ERROR, _('No group Dataset_Manager found.'))
                return None

            groups_of_user = self.request.user.groups.all()
            if group_manager not in groups_of_user:
                messages.add_message(self.request, messages.ERROR, _('You must be in group Dataset_Manager to use the requested functionality.'))
                return None

            from django.db.models import Prefetch
            qs = Dataset.objects.all().prefetch_related(
                Prefetch(
                    "userprofile_set",
                    queryset=UserProfile.objects.filter(user=user),
                    to_attr="user"
                )
            )

            checker = ObjectPermissionChecker(user)

            checker.prefetch_perms(qs)

            for dataset in qs:
                checker.has_perm('change_dataset', dataset)

            return qs
        else:
            # User is not authenticated
            return None

class DatasetDetailView(DetailView):
    model = Dataset
    context_object_name = 'dataset'
    template_name = 'dictionary/dataset_detail.html'

    # set the default dataset, this should not be empty
    dataset_name = settings.DEFAULT_DATASET_ACRONYM

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested dataset does not exist.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DatasetDetailView, self).get_context_data(**kwargs)

        dataset = context['dataset']

        context['default_language_choice_list'] = {}
        translation_languages = dataset.translation_languages.all()
        default_language_choice_dict = dict()
        for language in translation_languages:
            default_language_choice_dict[language.name] = language.name
        context['default_language_choice_list'] = json.dumps(default_language_choice_dict)

        datasetform = DatasetUpdateForm(languages=context['default_language_choice_list'])
        context['datasetform'] = datasetform

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        nr_of_glosses = 0
        nr_of_public_glosses = 0

        # This code is slowing things down

        for gloss in Gloss.objects.filter(lemma__dataset=dataset):

            nr_of_glosses += 1

            if gloss.inWeb:
                nr_of_public_glosses += 1

        context['nr_of_glosses'] = nr_of_glosses
        context['nr_of_public_glosses'] = nr_of_public_glosses

        context['messages'] = messages.get_messages(self.request)

        return context

    def render_to_response(self, context):
        if 'add_owner' in self.request.GET:
            return self.render_to_add_owner_response(context)
        elif 'request_access' in self.request.GET:
            return self.render_to_request_access(context)
        else:
            return super(DatasetDetailView, self).render_to_response(context)

    def render_to_request_access(self, context):
        dataset = context['dataset']
        # check that the user is logged in
        if self.request.user.is_authenticated or not dataset.is_public:
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/' + dataset.acronym)
        else:
            self.request.session['requested_datasets'] = [dataset.name]
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/accounts/register/')

    def render_to_add_owner_response(self, context):

        # check that the user is logged in
        if self.request.user.is_authenticated:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        # check if the user can manage this dataset
        from django.contrib.auth.models import Group, User

        try:
            group_manager = Group.objects.get(name='Dataset_Manager')
        except ObjectDoesNotExist:
            messages.add_message(self.request, messages.ERROR, _('No group Dataset_Manager found.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        groups_of_user = self.request.user.groups.all()
        if group_manager not in groups_of_user:
            messages.add_message(self.request, messages.ERROR, _('You must be in group Dataset Manager to modify dataset permissions.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        try:
            dataset_object = Dataset.objects.get(name=self.dataset_name)
        except ObjectDoesNotExist:
            translated_message = _('No dataset with that name found.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        username = ''
        if 'username' in get:
            username = get['username']
        if username == '':
            messages.add_message(self.request, messages.ERROR, _('Username must be non-empty.'))
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        try:
            user_object = User.objects.get(username=username)
        except ObjectDoesNotExist:
            translated_message = _('No user with that username found.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available')

        # if we get to here, we have a dataset object and a user object to add as an owner of the dataset

        dataset_object.owners.add(user_object)
        dataset_object.save()

        messages.add_message(self.request, messages.INFO,
                     _('User successfully made (co-)owner of this dataset.'))

        return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/' + dataset_object.acronym)


def dataset_detail_view_by_acronym(request, acronym):
    if request.method == 'GET':
        dataset = get_object_or_404(Dataset, acronym=acronym)
        return DatasetDetailView.as_view()(request, pk=dataset.pk)
    raise Http404()


class DatasetFieldChoiceView(ListView):
    model = Dataset
    template_name = 'dictionary/dataset_field_choices.html'

    # set the default dataset, this should not be empty
    dataset_name = settings.DEFAULT_DATASET_ACRONYM

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DatasetFieldChoiceView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        managed_datasets = []
        change_dataset_permission = get_objects_for_user(self.request.user, 'change_dataset', Dataset)
        for dataset in selected_datasets:
            if dataset in change_dataset_permission:
                dataset_excluded_choices = dataset.exclude_choices.all();
                list_of_excluded_ids = []
                for ec in dataset_excluded_choices:
                    list_of_excluded_ids.append(ec.pk)
                managed_datasets.append((dataset, list_of_excluded_ids))

        context['datasets'] = managed_datasets

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'SHOW_FIELD_CHOICE_COLORS'):
            context['SHOW_FIELD_CHOICE_COLORS'] = settings.SHOW_FIELD_CHOICE_COLORS
        else:
            context['SHOW_FIELD_CHOICE_COLORS'] = False

        all_choice_lists = {}
        for topic in ['main', 'phonology', 'semantics', 'frequency']:

            fields_with_choices = [(field, field.field_choice_category) for field in Gloss._meta.fields if
                                   field.name in FIELDS[topic] and hasattr(field, 'field_choice_category')
                                   and field.name not in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh'] ]

            for (field, fieldchoice_category) in fields_with_choices:

                # Get and save the choice list for this field
                choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)
                if len(choice_list) > 0:
                    all_choice_lists[fieldchoice_category] = choicelist_queryset_to_translated_dict(choice_list, choices_to_exclude=[])
                    choice_list_machine_values = choicelist_queryset_to_machine_value_dict(choice_list)

                    for choice_list_field, machine_value in choice_list_machine_values:

                        if machine_value == 0:
                            frequency_for_field = Gloss.objects.filter(Q(lemma__dataset__in=selected_datasets),
                                                                       Q(**{field.name + '__isnull': True}) |
                                                                       Q(**{field.name: 0})).count()

                        else:
                            variable_column = field.name
                            search_filter = 'exact'
                            filter = variable_column + '__' + search_filter
                            frequency_for_field = Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(
                                **{filter: machine_value}).count()

                        try:
                            all_choice_lists[fieldchoice_category][choice_list_field] += ' [' + str(
                                frequency_for_field) + ']'
                        except KeyError:
                            continue

        field_choices = {}
        for field_choice_category in all_choice_lists.keys():
            field_choices[field_choice_category] = []

        for field_choice_category in all_choice_lists.keys():
            for machine_value_string, display_with_frequency in all_choice_lists[field_choice_category].items():
                if machine_value_string != '_0' and machine_value_string != '_1':
                    mvid, mvv = machine_value_string.split('_')
                    machine_value = int(mvv)

                    try:
                        field_choice_object = FieldChoice.objects.get(field=field_choice_category,
                                                                      machine_value=machine_value)
                    except (ObjectDoesNotExist, MultipleObjectsReturned):
                        try:
                            field_choice_object = \
                            FieldChoice.objects.filter(field=field_choice_category, machine_value=machine_value)[0]
                        except (ObjectDoesNotExist, IndexError):
                            print('Multiple ', field_choice_category, ' objects share the same machine value: ',
                                  machine_value)
                            continue
                    # field_display_with_frequency = field_choice_object.field + ': ' + display_with_frequency
                    field_choices[field_choice_category].append((field_choice_object, display_with_frequency))
        context['field_choices'] = field_choices

        context['messages'] = messages.get_messages(self.request)

        return context

    def get_queryset(self):
        user = self.request.user

        # get query terms from self.request
        get = self.request.GET

        # Then check what kind of stuff we want
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        # otherwise the default dataset_name DEFAULT_DATASET_ACRONYM is used

        setattr(self.request, 'dataset_name', self.dataset_name)

        if user.is_authenticated:

            # determine if user is a dataset manager
            from django.contrib.auth.models import Group, User
            try:
                group_manager = Group.objects.get(name='Dataset_Manager')
            except ObjectDoesNotExist:
                messages.add_message(self.request, messages.ERROR, _('No group Dataset_Manager found.'))
                return None

            groups_of_user = self.request.user.groups.all()
            if group_manager not in groups_of_user:
                messages.add_message(self.request, messages.ERROR, _('You must be in group Dataset_Manager to use the requested functionality.'))
                return None

            from django.db.models import Prefetch
            qs = Dataset.objects.all().prefetch_related(
                Prefetch(
                    "userprofile_set",
                    queryset=UserProfile.objects.filter(user=user),
                    to_attr="user"
                )
            )

            checker = ObjectPermissionChecker(user)

            checker.prefetch_perms(qs)

            for dataset in qs:
                checker.has_perm('change_dataset', dataset)

            return qs
        else:
            # User is not authenticated
            messages.add_message(self.request, messages.ERROR, _('Please login to use the requested functionality.'))
            return None

class FieldChoiceView(ListView):
    model = FieldChoice
    template_name = 'dictionary/dataset_field_choice_colors.html'

    # set the default dataset, this should not be empty
    dataset_name = settings.DEFAULT_DATASET_ACRONYM

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(FieldChoiceView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        user_object = self.request.user

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'SHOW_FIELD_CHOICE_COLORS'):
            context['SHOW_FIELD_CHOICE_COLORS'] = settings.SHOW_FIELD_CHOICE_COLORS
        else:
            context['SHOW_FIELD_CHOICE_COLORS'] = False

        choice_categories = fields_to_categories()
        fields_for_category_table = category_to_fields()
        field_choices = {}

        for category in choice_categories:
            fields = fields_for_category_table[category]
            choices_for_category = get_frequencies_for_category(category, fields, selected_datasets)
            field_choices[category] = choices_for_category

        context['field_choices'] = field_choices

        choices_colors = {}
        display_choices = {}
        for category in choice_categories:
            if category in CATEGORY_MODELS_MAPPING.keys():
                field_choices = CATEGORY_MODELS_MAPPING[category].objects.all()
            else:
                field_choices = FieldChoice.objects.filter(field__iexact=category)
            choices_colors[category] = choicelist_queryset_to_colors(field_choices, shortlist=False)
            display_choices[category] = choicelist_queryset_to_translated_dict(field_choices, shortlist=False)

        context['static_choice_lists'] = display_choices
        context['static_choice_list_colors'] = choices_colors

        return context

    def get_queryset(self):
        user = self.request.user

        if user.is_authenticated:

            if user.is_superuser:

                # this is not actually used in the view
                # the lists to display are computed in the context
                field_choices = FieldChoice.objects.all()
                return field_choices

            else:
                # User is not authenticated
                messages.add_message(self.request, messages.ERROR,
                                     _('You must be superuser to use the requested functionality.'))
                return None
        else:
            # User is not authenticated
            messages.add_message(self.request, messages.ERROR, _('Please login to use the requested functionality.'))
            return None

class DatasetFrequencyView(DetailView):

    model = Dataset
    context_object_name = 'dataset'
    template_name = 'dictionary/dataset_frequency.html'
    dataset_name = ''

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested dataset does not exist.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('registration:login'))

        dataset = self.object
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=False, any_perm=True)

        if dataset not in datasets_user_can_view:
                translated_message = _('You do not have permission to view this corpus.')
                return render(request, 'dictionary/warning.html',
                              {'warning': translated_message,
                               'dataset_languages': dataset_languages,
                               'selected_datasets': selected_datasets,
                               'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })
        if dataset not in selected_datasets:
            translated_message = _('Please select the dataset first to view its corpus.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DatasetFrequencyView, self).get_context_data(**kwargs)

        dataset = context['dataset']

        context['default_language_choice_list'] = {}
        translation_languages = dataset.translation_languages.all()
        default_language_choice_dict = dict()
        for language in translation_languages:
            default_language_choice_dict[language.name] = language.name
        context['default_language_choice_list'] = json.dumps(default_language_choice_dict)

        datasetform = DatasetUpdateForm(languages=context['default_language_choice_list'])
        context['datasetform'] = datasetform

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        corpus_name = dataset.acronym
        # create a Corpus object if it does not exist
        try:
            corpus = Corpus.objects.get(name=corpus_name)
        except ObjectDoesNotExist:
            corpus = None
        context['corpus'] = corpus

        (update_eaf_files, new_eaf_files, missing_eaf_files) = get_names_of_updated_eaf_files(corpus_name)

        updated_documents = document_identifiers_from_paths(update_eaf_files)

        document_objects = Document.objects.filter(corpus=corpus).order_by('identifier')

        # some additional data is collected about the eaf files versus the documents in the database
        gloss_frequency_objects_per_document = {}
        documents_without_data = []
        more_recent_eaf_files = []

        for d_identifier in missing_eaf_files:
            remove_document_from_corpus(corpus_name, d_identifier)

        document_objects = Document.objects.filter(corpus=corpus).order_by('identifier')
        # at this point, documents associated with missing eaf files have been removed
        # as well as any frequency objects for that document
        for d_obj in document_objects:
            # this is done in a separate variable instead of in the if expression
            # the function on the right hand side looks at the file
            has_been_updated = document_has_been_updated(corpus_name, d_obj.identifier)
            if has_been_updated:
                more_recent_eaf_files += [d_obj.identifier]
            frequency_objects_for_document = GlossFrequency.objects.filter(document=d_obj)
            gloss_frequency_objects_per_document[d_obj.identifier] = frequency_objects_for_document
            if not frequency_objects_for_document:
                documents_without_data.append(d_obj.identifier)

        def document_toelichting(document_identifier):
            if document_identifier in updated_documents:
                return _('Modified')
            else:
                return ''

        context['document_identifiers'] = [ do.identifier for do in document_objects ]
        context['documents'] = [ (do.identifier,
                                  do.creation_time.date,
                                  document_to_number_of_glosses(corpus_name, do.identifier),
                                  document_toelichting(do.identifier) ) for do in document_objects ]

        frequencies = GlossFrequency.objects.filter(document__in=document_objects)

        speakers_in_corpus = frequencies.values('speaker__identifier').distinct()
        speaker_indentifiers = []
        for s in speakers_in_corpus:
            speaker_indentifiers.append(s['speaker__identifier'])
        speaker_objects_frequency_objects = Speaker.objects.filter(identifier__in=speaker_indentifiers).order_by('identifier')
        speaker_objects_corpus = Speaker.objects.filter(identifier__endswith='_'+corpus_name).order_by('identifier')

        # speakers_to_documents = dictionary_speakers_to_documents(corpus_name)

        GENDER_MAPPING = { 'm': _('Male'), 'f': _('Female'), 'o': _('Other') }
        HANDEDNESS_MAPPING = {'r': _('Right'), 'l': _('Left'), 'a': _('Ambidextrous'), '': _('Unknown') }
        speaker_tuples = []
        for so in speaker_objects_corpus:
            speaker_tuples.append((so.participant, GENDER_MAPPING[so.gender], so.age, so.location, HANDEDNESS_MAPPING[so.handedness]))
        context['speakers'] = speaker_tuples
        # the code below ends up being really slow
        # speaker_tuples_documents = []
        # for so in speaker_objects_frequency_objects:
        #     participant = so.participant()
        #     speaker_tuples_documents.append((participant, speakers_to_documents[participant]))
        # context['speakers_in_documents'] = speaker_tuples_documents

        newly_uploaded_eafs = eaf_file_from_paths(new_eaf_files)
        context['new_eaf_files'] = newly_uploaded_eafs

        (eaf_paths_dict, duplicates) = documents_paths_dictionary(corpus_name)

        context['sorted_document_identifiers'] = sorted(eaf_paths_dict.keys())
        context['duplicates'] = duplicates
        context['overview_eaf_files'] = eaf_paths_dict

        return context

    def render_to_response(self, context):
        if self.request.GET.get('process_speakers') == self.object.acronym:
            return self.render_to_process_speakers_response(context)
        elif self.request.GET.get('create_corpus') == self.object.acronym:
            return self.render_to_create_corpus_response(context)
        elif self.request.GET.get('update_corpus') == self.object.acronym:
            return self.render_to_update_corpus_response(context)
        else:
            return super(DatasetFrequencyView, self).render_to_response(context)

    def render_to_process_speakers_response(self, context):
        # check that the user is logged in
        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        try:
            dataset_object = Dataset.objects.get(acronym=self.dataset_name)
        except ObjectDoesNotExist:
            translated_message = _('No dataset with that acronym found.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # make sure the user can write to this dataset
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = get_objects_for_user(self.request.user, 'change_dataset', Dataset, accept_global_perms=False)
        if not user_change_datasets.exists() or dataset_object not in user_change_datasets:
            messages.add_message(self.request, messages.ERROR, _('No permission to import speakers for this dataset.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # configure the speakers
        errors = import_corpus_speakers(dataset_object.acronym)

        if errors:
            messages.add_message(self.request, messages.ERROR, _('Error processing participants meta data for this dataset.'))
            return HttpResponseRedirect(reverse('admin_dataset_frequency', args=(dataset_object.id,)))
        else:
            messages.add_message(self.request, messages.INFO, _('Speakers successfully processed.'))
            return HttpResponseRedirect(reverse('admin_dataset_frequency', args=(dataset_object.id,)))

    def render_to_create_corpus_response(self, context):

        # check that the user is logged in
        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        try:
            dataset_object = Dataset.objects.get(acronym=self.dataset_name)
        except ObjectDoesNotExist:
            translated_message = _('No dataset with that acronym found.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # make sure the user can write to this dataset
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = get_objects_for_user(self.request.user, 'change_dataset', Dataset, accept_global_perms=False)
        if not user_change_datasets.exists() or dataset_object not in user_change_datasets:
            messages.add_message(self.request, messages.ERROR, _('No permission to create a corpus for this dataset.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # configure the speakers
        errors = import_corpus_speakers(dataset_object.acronym)

        if errors:
            messages.add_message(self.request, messages.ERROR, _('Error processing participants meta data for this dataset.'))
            return HttpResponseRedirect(reverse('admin_dataset_frequency', args=(dataset_object.id,)))

        configure_corpus_documents_for_dataset(dataset_object.acronym)
        translated_message = _('Corpus successfully created.')
        messages.add_message(self.request, messages.INFO, translated_message)
        return HttpResponseRedirect(reverse('admin_dataset_frequency', args=(dataset_object.id,)))

    def render_to_update_corpus_response(self, context):
        # check that the user is logged in
        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        try:
            dataset_object = Dataset.objects.get(acronym=self.dataset_name)
        except ObjectDoesNotExist:
            translated_message = _('No dataset with that acronym found.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # make sure the user can write to this dataset
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = get_objects_for_user(self.request.user, 'change_dataset', Dataset, accept_global_perms=False)
        if not user_change_datasets.exists() or dataset_object not in user_change_datasets:
            messages.add_message(self.request, messages.ERROR, _('No permission to update the corpus for this dataset.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # importing updates the speakers
        # check format of spekaer identifiers
        speakers_have_correct_format = speaker_identifiers_contain_dataset_acronym(dataset_object.acronym)

        if not speakers_have_correct_format:
            # process speakers again to newest version
            errors = import_corpus_speakers(dataset_object.acronym)
            if errors:
                messages.add_message(self.request, messages.ERROR, _('Error processing participants meta data for this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_frequency', args=(dataset_object.id,)))

        update_corpus_counts(dataset_object.acronym)

        # this message doesn't work anymore because this is now an ajax call method
        messages.add_message(self.request, messages.INFO, _('Corpus successfully updated.'))

        return HttpResponseRedirect(reverse('admin_dataset_frequency', args=(dataset_object.id,)))


def order_handshape_queryset_by_sort_order(get, qs):
    """Change the sort-order of the query set, depending on the form field [sortOrder]

    This function is used by by HandshapeListView.
    The value of [sortOrder] is 'machine_value' by default.
    [sortOrder] is a hidden field inside the "adminsearch" html form in the template admin_handshape_list.html
    Its value is changed by clicking the up/down buttons in the second row of the search result table
    """

    # Set the default sort order
    sort_order = 'machine_value'  # Default sort order if nothing is specified
    # See if the form contains any sort-order information
    if ('sortOrder' in get and get['sortOrder'] != ''):
        # Take the user-indicated sort order
        sort_order = get['sortOrder']

    reverse = False
    if sort_order[0] == '-':
        # A starting '-' sign means: descending order
        sort_order = sort_order[1:]
        reverse = True

    if hasattr(Handshape._meta.get_field(sort_order), 'field_choice_category'):
        # The Handshape field is a FK to a FieldChoice
        field_choice_category = Handshape._meta.get_field(sort_order).field_choice_category
        order_dict = dict([(v, i) for i, v in enumerate(
            list(FieldChoice.objects.filter(field=field_choice_category, machine_value__lt=2)
                 .values_list('machine_value', flat=True))
            + list(FieldChoice.objects.filter(field=field_choice_category, machine_value__gt=1)
                   .order_by('name').values_list('machine_value', flat=True))
        )])

        ordered_handshapes = sorted(qs, key=lambda handshape_obj: order_dict[getattr(handshape_obj, sort_order).machine_value]
                            if getattr(handshape_obj, sort_order) else -1, reverse=reverse)

    else:
        # Not a FK to FieldChoice field; sort by
        qs_letters = qs.filter(**{sort_order+'__regex':r'^[a-zA-Z]'})
        qs_special = qs.filter(**{sort_order+'__regex':r'^[^a-zA-Z]'})

        ordered_handshapes = sorted(qs_letters, key=lambda x: getattr(x, sort_order))
        ordered_handshapes += sorted(qs_special, key=lambda x: getattr(x, sort_order))

        if reverse:
            ordered_handshapes.reverse()

    # return the ordered list
    return ordered_handshapes


def order_handshape_by_angle(qs):
    # put the handshapes with an angle bracket > in the name after the others
    # the language code is that of the interface

    qs_no_angle = qs.filter(**{'name__regex':r'^[^>]+$'})
    qs_angle = qs.filter(**{'name__regex':r'^.+>.+$'})
    ordered = sorted(qs_no_angle, key=lambda x: x.name)
    ordered += sorted(qs_angle, key=lambda x: x.name)

    return ordered

class MorphemeDetailView(DetailView):
    model = Morpheme
    context_object_name = 'morpheme'
    last_used_dataset = None
    search_type = 'morpheme'

    # Overriding the get method get permissions right

    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested morpheme does not exist.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})
        if self.object.lemma == None or self.object.lemma.dataset == None:
            translated_message = _('Requested morpheme has no lemma or dataset.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        if not request.user.is_authenticated:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_morpheme = self.object.lemma.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=False, any_perm=True)

        if dataset_of_requested_morpheme not in selected_datasets:
            translated_message = _('The morpheme you are trying to view is not in your selected datasets.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })
        if dataset_of_requested_morpheme not in datasets_user_can_view:
            translated_message = _('The morpheme you are trying to view is not in a dataset you can view.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []

        if search_results and len(search_results) > 0:
            if self.request.session['search_results'][0]['href_type'] not in ['morpheme', 'gloss']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['morpheme', 'sign_or_morpheme']:
                # user has not queried morphemes
                # search_type is 'handshape', 'sign', 'sign_handshape'
                self.request.session['search_results'] = []
        else:
            self.request.session['search_type'] = self.search_type

        # Call the base implementation first to get a context
        context = super(MorphemeDetailView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['tagform'] = TagUpdateForm()
        context['videoform'] = VideoUploadForGlossForm()
        context['imageform'] = ImageUploadForGlossForm()
        context['definitionform'] = DefinitionForm()
        context['relationform'] = RelationForm()
        context['othermediaform'] = OtherMediaForm()

        # Get the set of all the Gloss signs that point to me
        other_glosses_that_point_to_morpheme = SimultaneousMorphologyDefinition.objects.filter(morpheme_id__exact=context['morpheme'].id)
        context['appears_in'] = []

        for sim_morph in other_glosses_that_point_to_morpheme:
            parent_gloss = sim_morph.parent_gloss
            if parent_gloss.wordClass:
                translated_word_class = parent_gloss.wordClass.name
            else:
                translated_word_class = ''

            context['appears_in'].append((parent_gloss, translated_word_class))

        context['glosscount'] = Morpheme.objects.count()

        # Pass info about which fields we want to see
        gl = context['morpheme']
        context['active_id'] = gl.id
        labels = gl.field_labels()

        # set a session variable to be able to pass the gloss's id to the ajax_complete method
        # the last_used_dataset name is updated to that of this gloss
        # if a sequesce of glosses are being created by hand, this keeps the dataset setting the same
        if gl.dataset:
            self.request.session['datasetid'] = gl.dataset.id
            self.last_used_dataset = gl.dataset.acronym
        else:
            self.request.session['datasetid'] = get_default_language_id()

        self.request.session['last_used_dataset'] = self.last_used_dataset

        context['choice_lists'] = {}

        phonology_list_kinds = []

        context['static_choice_lists'] = {}
        context['static_choice_list_colors'] = {}
        # Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['phonology', 'semantics']:
            context[topic + '_fields'] = []
        for field in settings.MORPHEME_DISPLAY_FIELDS + FIELDS['semantics']:
            # handshapes are not included in the morphemedetailview #638
            kind = fieldname_to_kind(field)

            if field in FIELDS['phonology']:
                topic = 'phonology'
                if kind == 'list':
                    phonology_list_kinds.append(field)
            else:
                topic = 'semantics'

            (static_choice_lists, static_choice_list_colors) = get_static_choice_lists(field)

            context['static_choice_lists'][field] = static_choice_lists
            context['static_choice_list_colors'][field] = static_choice_list_colors

            if field in ['semField', 'derivHist']:
                # these are many to many fields and not in the gloss/morpheme table of the database
                # they are not fields of Morpheme
                continue

            # Take the human value in the language we are using
            gloss_field = Morpheme._meta.get_field(field)

            field_value = getattr(gl, gloss_field.name)
            if isinstance(field_value, FieldChoice):
                human_value = field_value.name if field_value else field_value
            elif fieldname_to_kind(field) == 'text' and (field_value is None or field_value in ['-', ' ', '------', '']):
                # otherwise, it's a value, not a choice
                # take care of different representations of empty text in database
                human_value = ''
            else:
                human_value = field_value

            # And add the kind of field
            context[topic + '_fields'].append([human_value, field, labels[field], kind])

        context['phonology_list_kinds'] = phonology_list_kinds

        # Regroup notes
        note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType')
        notes = context['morpheme'].definition_set.all()
        notes_groupedby_role = {}
        for note in notes:
            if note.role is not None:
                translated_note_role = note.role.name
            else:
                translated_note_role = ''
            role_id = (note.role, translated_note_role)
            if role_id not in notes_groupedby_role:
                notes_groupedby_role[role_id] = []
            notes_groupedby_role[role_id].append(note)
        context['notes_groupedby_role'] = notes_groupedby_role

        # Gather the OtherMedia
        context['other_media'] = []
        context['other_media_field_choices'] = {}
        other_media_type_choice_list = FieldChoice.objects.filter(field__iexact='OthermediaType')

        for other_media in gl.othermedia_set.all():
            media_okay, path, other_media_filename = other_media.get_othermedia_path(gl.id, check_existence=True)

            human_value_media_type = other_media.type.name

            import mimetypes
            file_type = mimetypes.guess_type(path, strict=True)[0]

            context['other_media'].append([media_okay, other_media.pk, path, file_type, human_value_media_type, other_media.alternative_gloss, other_media_filename])

            # Save the other_media_type choices (same for every other_media, but necessary because they all have other ids)
            context['other_media_field_choices'][
                'other-media-type_' + str(other_media.pk)] = choicelist_queryset_to_translated_dict(other_media_type_choice_list)
        context['other_media_field_choices'] = json.dumps(context['other_media_field_choices'])

        morpheme_type_choice_list = FieldChoice.objects.filter(field__iexact='MorphemeType')
        morpheme_type_choices = choicelist_queryset_to_translated_dict(morpheme_type_choice_list,
                                                                       shortlist=False)
        morpheme_type_choices_colors = choicelist_queryset_to_colors(morpheme_type_choice_list)
        context['morph_type'] = json.dumps(morpheme_type_choices)
        context['morph_type_colors'] = json.dumps(morpheme_type_choices_colors)

        # make lemma group empty for Morpheme (ask Onno about this)
        context['lemma_group'] = False
        context['lemma_group_url'] = ''

        # Put annotation_idgloss per language in the context
        context['annotation_idgloss'] = {}
        if gl.dataset:
            for language in gl.dataset.translation_languages.all():
                context['annotation_idgloss'][language] = gl.annotationidglosstranslation_set.filter(language=language)
        else:
            language = Language.objects.get(id=get_default_language_id())
            context['annotation_idgloss'][language] = gl.annotationidglosstranslation_set.filter(language=language)

        translated_morph_type = gl.mrpType.name if gl.mrpType else '-'

        context['morpheme_type'] = translated_morph_type

        gloss_semanticfields = []
        for sf in gl.semField.all():
            gloss_semanticfields.append(sf)

        context['gloss_semanticfields'] = gloss_semanticfields

        gloss_derivationhistory = []
        for sf in gl.derivHist.all():
            gloss_derivationhistory.append(sf)

        context['gloss_derivationhistory'] = gloss_derivationhistory

        # Put translations (keywords) per language in the context
        context['translations_per_language'] = {}
        if gl.dataset:
            for language in gl.dataset.translation_languages.all():
                context['translations_per_language'][language] = gl.translation_set.filter(language=language).order_by('translation__index')
        else:
            language = Language.objects.get(id=get_default_language_id())
            context['translations_per_language'][language] = gl.translation_set.filter(language=language).order_by('translation__index')


        context['separate_english_idgloss_field'] = SEPARATE_ENGLISH_IDGLOSS_FIELD

        bad_dialect = False
        morpheme_dialects = []

        try:
            gloss_signlanguage = gl.lemma.dataset.signlanguage
        except:
            gloss_signlanguage = None
            # this is needed to catch legacy code
        initial_gloss_dialects = gl.dialect.all()
        if gloss_signlanguage:
            gloss_dialect_choices = Dialect.objects.filter(signlanguage=gloss_signlanguage)
        else:
            gloss_dialect_choices = []

        for gd in initial_gloss_dialects:
            if gd in gloss_dialect_choices:
                morpheme_dialects.append(gd)
            else:
                bad_dialect = True
                print('Bad dialect found in morpheme ', gl.pk, ': ', gd)

        context['morpheme_dialects'] = morpheme_dialects

        # This is a patch
        if bad_dialect:
            print('PATCH: Remove bad dialect from morpheme ', gl.pk)
            # take care of bad dialects due to evolution of Lemma, Dataset, SignLanguage setup
            gl.dialect.clear()
            for d in morpheme_dialects:
                gl.dialect.add(d)


        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['dataset_choices'] = {}
            user = self.request.user
            if user.is_authenticated:
                qs = get_objects_for_user(user, ['view_dataset', 'can_view_dataset'],
                                          Dataset, accept_global_perms=False, any_perm=True)
                dataset_choices = dict()
                for dataset in qs:
                    dataset_choices[dataset.acronym] = dataset.acronym
                context['dataset_choices'] = json.dumps(dataset_choices)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'MORPHEME_DISPLAY_FIELDS'):
            context['MORPHEME_DISPLAY_FIELDS'] = settings.MORPHEME_DISPLAY_FIELDS
        else:
            context['MORPHEME_DISPLAY_FIELDS'] = []

        if hasattr(settings, 'USE_DERIVATIONHISTORY') and settings.USE_DERIVATIONHISTORY:
            context['USE_DERIVATIONHISTORY'] = settings.USE_DERIVATIONHISTORY
        else:
            context['USE_DERIVATIONHISTORY'] = False

        context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix
        return context

def gloss_ajax_search_results(request):
    """Returns a JSON list of glosses that match the previous search stored in sessions"""
    if 'search_type' in request.session.keys() and 'search_results' in request.session.keys() \
            and request.session['search_type'] in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape']:
        return JsonResponse(request.session['search_results'], safe=False)
    else:
        return JsonResponse([])

def handshape_ajax_search_results(request):
    """Returns a JSON list of handshapes that match the previous search stored in sessions"""
    if 'search_type' in request.session.keys() and 'search_results' in request.session.keys() \
            and request.session['search_type'] == 'handshape':
        return JsonResponse(request.session['search_results'], safe=False)
    else:
        return JsonResponse([])

def lemma_ajax_search_results(request):
    """Returns a JSON list of handshapes that match the previous search stored in sessions"""
    if 'search_type' in request.session.keys() and 'search_results' in request.session.keys() \
            and request.session['search_type'] == 'lemma':
        return JsonResponse(request.session['search_results'], safe=False)
    else:
        return JsonResponse([])

def gloss_ajax_complete(request, prefix):
    """Return a list of glosses matching the search term
    as a JSON structure suitable for typeahead."""

    if 'datasetid' in request.session.keys():
        datasetid = request.session['datasetid']
    else:
        datasetid = settings.DEFAULT_DATASET_PK
    dataset = Dataset.objects.get(id=datasetid)
    default_language = dataset.default_language

    interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[request.LANGUAGE_CODE]
    interface_language = Language.objects.get(language_code_3char=interface_language_3char)

    # language is not empty
    # the following query only retrieves annotations for the language that match the prefix
    query = Q(annotationidglosstranslation__text__istartswith=prefix,
              annotationidglosstranslation__language=interface_language)
    qs = Gloss.objects.filter(query).distinct()

    result = []
    for g in qs:
        if g.dataset == dataset:
            try:
                annotationidglosstranslation = g.annotationidglosstranslation_set.get(language=interface_language)
                default_annotationidglosstranslation = annotationidglosstranslation.text
            except ObjectDoesNotExist:
                annotationidglosstranslation = g.annotationidglosstranslation_set.get(language=default_language)
                default_annotationidglosstranslation = annotationidglosstranslation.text
            result.append({'annotation_idgloss': default_annotationidglosstranslation, 'idgloss': g.idgloss, 'sn': g.sn, 'pk': "%s" % (g.id)})

    sorted_result = sorted(result, key=lambda x : (x['annotation_idgloss'], len(x['annotation_idgloss'])))

    return JsonResponse(sorted_result, safe=False)

def handshape_ajax_complete(request, prefix):
    """Return a list of handshapes matching the search term
    as a JSON structure suitable for typeahead."""
    qs = Handshape.objects.filter(name__istartswith=prefix)

    result = []
    for g in qs:
        result.append({'name': g.name, 'machine_value': g.machine_value})

    return JsonResponse(result, safe=False)

def morph_ajax_complete(request, prefix):
    """Return a list of morphemes matching the search term
    as a JSON structure suitable for typeahead."""

    # the following query retrieves morphemes with annotations that match the prefix
    query = Q(annotationidglosstranslation__text__istartswith=prefix)
    qs = Morpheme.objects.filter(query).distinct()

    result = []
    for g in qs:
        annotationidglosstranslations = g.annotationidglosstranslation_set.all()
        if not annotationidglosstranslations:
            continue
        # if there are results, just grab the first one
        default_annotationidglosstranslation = annotationidglosstranslations.first().text
        result.append({'annotation_idgloss': default_annotationidglosstranslation, 'idgloss': g.idgloss,
                       'pk': "%s" % (g.id)})

    return JsonResponse(result, safe=False)

def user_ajax_complete(request, prefix):
    """Return a list of users matching the search term
    as a JSON structure suitable for typeahead."""

    query = Q(username__istartswith=prefix) | \
            Q(first_name__istartswith=prefix) | \
            Q(last_name__startswith=prefix)

    qs = User.objects.filter(query).distinct()

    result = []
    for u in qs:
        result.append({'first_name': u.first_name, 'last_name': u.last_name, 'username': u.username})

    return JsonResponse(result, safe=False)


def lemma_ajax_complete(request, dataset_id, language_code, q):

    # check that the user is logged in
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, _('Please login to use this functionality.'))
        return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

    # the following code allows for specifying a language for the dataset in the add_gloss.html template

    # other code uses the language code in request
    # the language code parameter in the url is needed for some reason in order to parse the url
    # otherwise it thinks the q parameter is part of the dataset id
    # this may have something to do with dynamic construction of the url path in the javascript functions that call this routine
    # via the url
    interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[language_code]
    interface_language = Language.objects.get(language_code_3char=interface_language_3char)
    interface_language_id = interface_language.id

    dataset = Dataset.objects.get(id=dataset_id)
    dataset_default_language_id = dataset.default_language.id

    lemmas = LemmaIdgloss.objects.filter(dataset_id=dataset_id,
                                         lemmaidglosstranslation__language_id=interface_language_id,
                                         lemmaidglosstranslation__text__istartswith=q)\
        .order_by('lemmaidglosstranslation__text')
    # lemmas_dict = [{'pk': lemma.pk, 'lemma': str(lemma)} for lemma in set(lemmas)]

    lemmas_dict_list = []
    for lemma in set(lemmas):
        trans_dict = {}
        for translation in lemma.lemmaidglosstranslation_set.all():
            if translation.language.id == interface_language_id:
                trans_dict['pk'] = lemma.pk
                trans_dict['lemma'] = translation.text
                lemmas_dict_list.append(trans_dict)
    sorted_lemmas_dict = sorted(lemmas_dict_list, key=lambda x : (x['lemma'], len(x['lemma'])))
    return JsonResponse(sorted_lemmas_dict, safe=False)

def homonyms_ajax_complete(request, gloss_id):

    try:
        this_gloss = Gloss.objects.get(id=gloss_id)
        homonym_objects = this_gloss.homonym_objects()
    except ObjectDoesNotExist:
        homonym_objects = []

    (interface_language, interface_language_code,
     default_language, default_language_code) = get_interface_language_and_default_language_codes(request)

    result = []
    for homonym in homonym_objects:
        translations = homonym.get_annotationidglosstranslation_texts()

        if interface_language_code in translations.keys():
            translation = translations[interface_language_code]
        else:
            translation = translations[default_language_code]
        result.append({ 'id': str(homonym.id), 'gloss': translation })

    homonyms_dict = { str(gloss_id) : result }

    return JsonResponse(homonyms_dict, safe=False)

def minimalpairs_ajax_complete(request, gloss_id, gloss_detail=False):

    if 'gloss_detail' in request.GET:
        gloss_detail = request.GET['gloss_detail']

    language_code = request.LANGUAGE_CODE

    if language_code == "zh-hans":
        language_code = "zh"

    this_gloss = Gloss.objects.get(id=gloss_id)
    try:
        minimalpairs_objects = this_gloss.minimal_pairs_dict()
    except Exception as e:
        print(e)
        minimalpairs_objects = {}

    translation_focus_gloss = ""
    translations_this_gloss = this_gloss.annotationidglosstranslation_set.filter(language__language_code_2char=language_code)
    if translations_this_gloss is not None and len(translations_this_gloss) > 0:
        translation_focus_gloss = translations_this_gloss[0].text
    else:
        translations_this_gloss = this_gloss.annotationidglosstranslation_set.filter(language__language_code_3char='eng')
        if translations_this_gloss is not None and len(translations_this_gloss) > 0:
            translation_focus_gloss = translations_this_gloss[0].text
    result = []
    for minimalpairs_object, minimal_pairs_dict in minimalpairs_objects.items():

        other_gloss_dict = dict()
        other_gloss_dict['id'] = str(minimalpairs_object.id)
        other_gloss_dict['other_gloss'] = minimalpairs_object

        for field, values in minimal_pairs_dict.items():

            other_gloss_dict['field'] = field
            other_gloss_dict['field_display'] = values[0]
            other_gloss_dict['field_category'] = values[1]

            focus_gloss_choice = values[2]
            other_gloss_choice = values[3]

            if focus_gloss_choice:
                pass
            else:
                focus_gloss_choice = ''
            if other_gloss_choice:
                pass
            else:
                other_gloss_choice = ''

            field_kind = values[4]
            if field_kind == 'list':
                focus_gloss_value = focus_gloss_choice
            elif field_kind == 'check':
                # the value is a Boolean or it might not be set
                if focus_gloss_choice == 'True' or focus_gloss_choice == True:
                    focus_gloss_value = _('Yes')
                elif focus_gloss_choice == 'Neutral' and field in settings.HANDEDNESS_ARTICULATION_FIELDS:
                    focus_gloss_value = _('Neutral')
                else:
                    focus_gloss_value = _('No')
            else:
                # translate Boolean fields
                focus_gloss_value = focus_gloss_choice
            other_gloss_dict['focus_gloss_value'] = focus_gloss_value
            if field_kind == 'list':
                other_gloss_value = other_gloss_choice
            elif field_kind == 'check':
                # the value is a Boolean or it might not be set
                if other_gloss_choice == 'True' or other_gloss_choice == True:
                    other_gloss_value = _('Yes')
                elif other_gloss_choice == 'Neutral' and field in settings.HANDEDNESS_ARTICULATION_FIELDS:
                    other_gloss_value = _('Neutral')
                else:
                    other_gloss_value = _('No')
            else:
                other_gloss_value = other_gloss_choice
            other_gloss_dict['other_gloss_value'] = other_gloss_value
            other_gloss_dict['field_kind'] = field_kind

        translation = ""
        translations = minimalpairs_object.annotationidglosstranslation_set.filter(language__language_code_2char=language_code)
        if translations is not None and len(translations) > 0:
            translation = translations[0].text
        else:
            translations = minimalpairs_object.annotationidglosstranslation_set.filter(language__language_code_3char='eng')
            if translations is not None and len(translations) > 0:
                translation = translations[0].text

        other_gloss_dict['other_gloss_idgloss'] = translation
        result.append(other_gloss_dict)

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        SHOW_DATASET_INTERFACE_OPTIONS = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        SHOW_DATASET_INTERFACE_OPTIONS = False

    if gloss_detail:
        return render(request, 'dictionary/minimalpairs_gloss_table.html', { 'focus_gloss': this_gloss,
                                                                             'focus_gloss_translation': translation_focus_gloss,
                                                                             'SHOW_DATASET_INTERFACE_OPTIONS' : SHOW_DATASET_INTERFACE_OPTIONS,
                                                                             'minimal_pairs_dict' : result })
    else:
        return render(request, 'dictionary/minimalpairs_row.html', { 'focus_gloss': this_gloss,
                                                                     'focus_gloss_translation': translation_focus_gloss,
                                                                     'SHOW_DATASET_INTERFACE_OPTIONS' : SHOW_DATASET_INTERFACE_OPTIONS,
                                                                     'minimal_pairs_dict' : result })

def glosslist_ajax_complete(request, gloss_id):

    user = request.user

    display_fields = settings.GLOSS_LIST_DISPLAY_FIELDS

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' and request.method == 'GET':
        if 'query' in request.GET and 'display_fields' in request.GET and 'query_fields_parameters' in request.GET:
            display_fields = json.loads(request.GET['display_fields'])
            query_fields_parameters = json.loads(request.GET['query_fields_parameters'])

    is_anonymous = user.is_authenticated

    this_gloss = Gloss.objects.get(id=gloss_id)

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        SHOW_DATASET_INTERFACE_OPTIONS = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        SHOW_DATASET_INTERFACE_OPTIONS = False

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = get_dataset_languages(selected_datasets)

    # Put translations (keywords) per language in the context
    translations_per_language = []
    for language in dataset_languages:
        translations_per_language.append((language,this_gloss.translation_set.filter(language=language).order_by('translation__index')))

    column_values = []
    for fieldname in display_fields:
        if fieldname == 'semField':
            semanticfields = ", ".join([str(sf.name) for sf in this_gloss.semField.all()])
            column_values.append((fieldname, semanticfields))
        elif fieldname == 'derivHist':
            derivationhistories = ", ".join([str(dh.name) for dh in this_gloss.derivHist.all()])
            column_values.append((fieldname, derivationhistories))
        elif fieldname == 'dialect':
            dialects = ", ".join([str(d.signlanguage.name) + '/' + str(d.name) for d in this_gloss.dialect.all()])
            column_values.append((fieldname, dialects))
        elif fieldname == 'signlanguage':
            # this is a ManyToManyField field
            signlanguages = ", ".join([str(sl.name) for sl in this_gloss.signlanguage.all()])
            column_values.append((fieldname, signlanguages))
        elif fieldname == 'definitionRole':
            # this is a Note
            definitions_this_gloss = ", ".join([str(df.role.name) for df in this_gloss.definition_set.all()])
            column_values.append((fieldname, definitions_this_gloss))
        elif fieldname == 'hasothermedia':
            other_media_paths = []
            for other_media in this_gloss.othermedia_set.all():
                media_okay, path, other_media_filename = other_media.get_othermedia_path(this_gloss.id, check_existence=True)
                if media_okay:
                    other_media_paths.append(other_media_filename)
            other_media = ", ".join(other_media_paths)
            column_values.append((fieldname, other_media))
        elif fieldname == 'hasComponentOfType':
            morphemes = " + ".join([x.__str__() for x in this_gloss.parent_glosses.all()])
            column_values.append((fieldname, morphemes))
        elif fieldname == 'hasMorphemeOfType':
            # the inheritance only works this way in this version of Django/Python
            # the morphemes are filtered on this glosses id, then the morpheme is used
            target_morphemes = Morpheme.objects.filter(id=this_gloss.id)
            if target_morphemes:
                morph_typ_choices = FieldChoice.objects.filter(field__iexact='MorphemeType')
                target_morpheme = target_morphemes.first()
                morpheme_type_machine_value = target_morpheme.mrpType.machine_value if target_morpheme.mrpType else 0
                translated_morph_type = machine_value_to_translated_human_value(morpheme_type_machine_value, morph_typ_choices)
            else:
                translated_morph_type = ''
            column_values.append((fieldname, translated_morph_type))
        elif fieldname == 'morpheme':
            morphemes = " + ".join([x.morpheme.__str__() for x in this_gloss.simultaneous_morphology.all()])
            column_values.append((fieldname, morphemes))
        elif fieldname == 'hasRelation':
            if query_fields_parameters and query_fields_parameters[0] != 'all':
                relations_of_type = [ r for r in this_gloss.relation_sources.all() if r.role in query_fields_parameters ]
                relations = ", ".join([r.target.__str__() for r in relations_of_type])
            else:
                relations = ", ".join([r.role + ':' + r.target.__str__() for r in this_gloss.relation_sources.all()])
            # has_relation = _('Yes') if (this_gloss.relation_sources.count() > 0) else _('No')
            column_values.append((fieldname, relations))
        elif fieldname == 'relation':
            relations_to_signs = Relation.objects.filter(source=this_gloss)
            relations = ", ".join([x.role + ':' + x.target.__str__() for x in relations_to_signs])
            column_values.append((fieldname, relations))
        elif fieldname == 'hasRelationToForeignSign':
            has_relations = _('Yes') if (this_gloss.relationtoforeignsign_set.count() > 0) else _('No')
            column_values.append((fieldname, has_relations))
        elif fieldname == 'relationToForeignSign':
            relations_to_foreign_signs = RelationToForeignSign.objects.filter(gloss=this_gloss)
            relations = ", ".join([x.other_lang + ':' + x.other_lang_gloss for x in relations_to_foreign_signs])
            column_values.append((fieldname, relations))
        elif fieldname not in [ f.name for f in Gloss._meta.fields ]:
            continue
        else:
            machine_value = getattr(this_gloss, fieldname)
            gloss_field = Gloss._meta.get_field(fieldname)
            if machine_value and isinstance(machine_value, Handshape):
                human_value = machine_value.name
            elif machine_value and isinstance(machine_value, FieldChoice):
                human_value = machine_value.name
            else:
                human_value = machine_value
            if human_value:
                column_values.append((fieldname,human_value))
            else:
                column_values.append((fieldname,'-'))
    return render(request, 'dictionary/gloss_row.html', { 'focus_gloss': this_gloss,
                                                          'dataset_languages': dataset_languages,
                                                          'selected_datasets': selected_datasets,
                                                          'translations_per_language': translations_per_language,
                                                          'column_values': column_values,
                                                          'SHOW_DATASET_INTERFACE_OPTIONS' : SHOW_DATASET_INTERFACE_OPTIONS })

def glosslistheader_ajax(request):

    user = request.user

    display_fields = settings.GLOSS_LIST_DISPLAY_FIELDS
    query_fields_parameters = []

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' and request.method == 'GET':
        if 'query' in request.GET and 'display_fields' in request.GET and 'query_fields_parameters' in request.GET:
            display_fields = json.loads(request.GET['display_fields'])
            query_fields_parameters = json.loads(request.GET['query_fields_parameters'])

    is_anonymous = user.is_authenticated

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        SHOW_DATASET_INTERFACE_OPTIONS = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        SHOW_DATASET_INTERFACE_OPTIONS = False

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = get_dataset_languages(selected_datasets)

    fieldname_to_column_header = {'dialect': _("Dialect"),
                                  'signlanguage': _("Sign Language"),
                                  'definitionRole': _("Note Type"),
                                  'hasothermedia': _("Other Media"),
                                  'hasComponentOfType': _("Sequential Morphology"),
                                  'morpheme': _("Simultaneous Morphology"),
                                  'hasMorphemeOfType': _("Morpheme Type"),
                                  'relation': _("Gloss of Related Sign"),
                                  'hasRelationToForeignSign': _("Related to Foreign Sign"),
                                  'relationToForeignSign': _("Gloss of Foreign Sign")
                                  }

    column_headers = []
    for fieldname in display_fields:
        if fieldname in fieldname_to_column_header.keys():
            column_headers.append((fieldname, fieldname_to_column_header[fieldname]))
        elif fieldname == 'hasRelation':
            if query_fields_parameters:
                # this is a singleton type of relation
                relation_type = _("Type of Relation") + ':' + query_fields_parameters[0].capitalize()
                column_headers.append((fieldname, relation_type))
            else:
                column_headers.append((fieldname, _("Type of Relation")))
        elif fieldname not in [ f.name for f in Gloss._meta.fields ]:
            continue
        else:
            field_label = Gloss._meta.get_field(fieldname).verbose_name
            column_headers.append((fieldname, field_label))

    sortOrder = ''

    if 'HTTP_REFERER' in request.META.keys():
        sortOrderURL = request.META['HTTP_REFERER']
        sortOrderParameters = sortOrderURL.split('&sortOrder=')
        if len(sortOrderParameters) > 1:
            sortOrder = sortOrderParameters[1].split('&')[0]

    return render(request, 'dictionary/glosslist_headerrow.html', { 'dataset_languages': dataset_languages,
                                                                    'selected_datasets': selected_datasets,
                                                                    'column_headers': column_headers,
                                                                    'sortOrder': str(sortOrder),
                                                                    'SHOW_DATASET_INTERFACE_OPTIONS' : SHOW_DATASET_INTERFACE_OPTIONS })


def lemmaglosslist_ajax_complete(request, gloss_id):

    user = request.user

    is_anonymous = user.is_authenticated

    this_gloss = Gloss.objects.get(id=gloss_id)

    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
        SHOW_DATASET_INTERFACE_OPTIONS = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        SHOW_DATASET_INTERFACE_OPTIONS = False

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = get_dataset_languages(selected_datasets)

    # Put translations (keywords) per language in the context
    translations_per_language = {}
    for language in dataset_languages:
        translations_per_language[language] = this_gloss.translation_set.filter(language=language).order_by('translation__index')

    column_values = []
    gloss_list_display_fields = settings.GLOSS_LIST_DISPLAY_FIELDS
    for fieldname in gloss_list_display_fields:

        machine_value = getattr(this_gloss,fieldname)

        gloss_field = Gloss._meta.get_field(fieldname)
        if machine_value and isinstance(machine_value, Handshape):
            human_value = machine_value.name
        elif machine_value and isinstance(machine_value, FieldChoice):
            human_value = machine_value.name
        else:
            human_value = machine_value
        if human_value:
            column_values.append((fieldname, human_value))
        else:
            column_values.append((fieldname, '-'))

    return render(request, 'dictionary/lemma_gloss_row.html', { 'focus_gloss': this_gloss,
                                                          'dataset_languages': dataset_languages,
                                                          'translations_per_language': translations_per_language,
                                                          'column_values': column_values,
                                                          'SHOW_DATASET_INTERFACE_OPTIONS' : SHOW_DATASET_INTERFACE_OPTIONS })

class LemmaListView(ListView):
    model = LemmaIdgloss
    template_name = 'dictionary/admin_lemma_list.html'
    paginate_by = 50
    show_all = False
    search_type = 'lemma'

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)

    def get_queryset(self, **kwargs):

        get = self.request.GET

        queryset = super(LemmaListView, self).get_queryset()

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        from signbank.dictionary.forms import check_language_fields
        valid_regex, search_fields = check_language_fields(LemmaSearchForm, get, dataset_languages)

        if not valid_regex:
            error_message_1 = _('Error in search field ')
            error_message_2 = ', '.join(search_fields)
            error_message_3 = _(': Please use a backslash before special characters.')
            error_message = error_message_1 + error_message_2 + error_message_3
            messages.add_message(self.request, messages.ERROR, error_message)
            qs = LemmaIdgloss.objects.none()
            return qs

        qs = queryset.filter(dataset__in=selected_datasets)

        if len(get) == 0:
            # show all if there are no query parameters
            return qs

        # There are only Lemma ID Gloss fields
        for get_key, get_value in get.items():
            if get_key.startswith(LemmaSearchForm.lemma_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(LemmaSearchForm.lemma_search_field_prefix):]
                language = Language.objects.get(language_code_2char=language_code_2char)
                qs = qs.filter(lemmaidglosstranslation__text__iregex=get_value,
                               lemmaidglosstranslation__language=language)
        return qs

    def get_annotated_queryset(self, **kwargs):
        # this method adds a gloss count column to the results for display
        get = self.request.GET

        if hasattr(self, 'object_list') and not self.object_list:
            # check to make sure get_queryset has already been called
            # the post method does not seem to have this attribute when called from LemmaTests
            # either there was something wrong with the regex check and it returned empty results
            # or no matches to the query
            # in any case, there is nothing to annotate
            return (self.object_list, 0)

        qs = self.get_queryset()

        if len(get) == 0:
            results = qs.annotate(num_gloss=Count('gloss'))
            num_gloss_zero_matches = results.filter(num_gloss=0).count()
            return (results, num_gloss_zero_matches)

        only_show_no_glosses = False
        only_show_has_glosses = False

        for get_key, get_value in get.items():
            if get_key == 'no_glosses' and get_value == '1':
                only_show_no_glosses = True
            if get_key == 'has_glosses' and get_value == '1':
                only_show_has_glosses = True

        results = qs.annotate(num_gloss=Count('gloss'))
        if only_show_no_glosses and not only_show_has_glosses:
            results = results.filter(num_gloss=0)
            num_gloss_zero_matches = results.count()
        elif only_show_has_glosses and not only_show_no_glosses:
            results = results.filter(num_gloss__gt=0)
            num_gloss_zero_matches = 0
        else:
            num_gloss_zero_matches = results.filter(num_gloss=0).count()
        return (results,num_gloss_zero_matches)

    def get_context_data(self, **kwargs):
        context = super(LemmaListView, self).get_context_data(**kwargs)
        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        context['page_number'] = context['page_obj'].number

        context['objects_on_page'] = [ g.id for g in context['page_obj'].object_list ]

        context['paginate_by'] = self.request.GET.get('paginate_by', self.paginate_by)

        (results, num_gloss_zero_matches) = self.get_annotated_queryset()
        context['search_results'] = results
        context['num_gloss_zero_matches'] = num_gloss_zero_matches
        context['lemma_count'] = LemmaIdgloss.objects.filter(dataset__in=selected_datasets).count()

        context['search_matches'] = context['search_results'].count()

        search_form = LemmaSearchForm(self.request.GET, languages=dataset_languages)

        context['searchform'] = search_form
        context['search_type'] = 'lemma'

        list_of_objects = self.object_list

        # to accomodate putting lemma's in the scroll bar in the LemmaUpdateView (aka LemmaDetailView),
        # look at available translations, choose the Interface language if it is a Dataset language
        # some legacy lemma's have missing translations,
        # the language code is used when more than one is available,
        # otherwise the Default language will be used, if available
        # otherwise the Lemma ID will be used in the scroll bar

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        dataset_display_languages = []
        for lang in dataset_languages:
            dataset_display_languages.append(lang.language_code_2char)
        if interface_language_code in dataset_display_languages:
            lang_attr_name = interface_language_code
        else:
            # construct scroll bar
            # the following retrieves language code for English (or DEFAULT LANGUAGE)
            # so the sorting of the scroll bar matches the default sorting of the results in Lemma List View
            lang_attr_name = default_language_code

        items = construct_scrollbar(list_of_objects, self.search_type, lang_attr_name)
        self.request.session['search_results'] = items

        return context

    def render_to_response(self, context, **kwargs):
        if self.request.GET.get('format') == 'CSV':
            return self.render_to_csv_response(context)
        else:
            return super(LemmaListView, self).render_to_response(context)

    def render_to_csv_response(self, context):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        lang_attr_name = 'name_' + DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']

        lemmaidglosstranslation_fields = ["Lemma ID Gloss" + " (" + getattr(language, lang_attr_name) + ")"
                                          for language in dataset_languages]

        rows = []
        (queryset, num_gloss_zero_matches) = self.get_annotated_queryset()
        for lemma in queryset:
            row = [str(lemma.pk), lemma.dataset.acronym]
            for language in dataset_languages:
                lemmaidglosstranslations = lemma.lemmaidglosstranslation_set.filter(language=language)
                if lemmaidglosstranslations and len(lemmaidglosstranslations) == 1:
                    row.append(lemmaidglosstranslations[0].text)
                else:
                    row.append("")
            row.append(str(lemma.num_gloss))
            #Make it safe for weird chars
            safe_row = []
            for column in row:
                try:
                    safe_row.append(column.encode('utf-8').decode())
                except AttributeError:
                    safe_row.append(None)
            rows.append(safe_row)

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dictionary-export-lemmas.csv"'

        writer = csv.writer(response)

        with override(LANGUAGE_CODE):
            header = ['Lemma ID', 'Dataset'] + lemmaidglosstranslation_fields + ['Number of glosses']

        writer.writerow(header)

        for row in rows:
            writer.writerow(row)

        return response

    def post(self, request, *args, **kwargs):
        # this method deletes lemmas in the query that have no glosses
        # plus their dependent translations
        if not self.request.user.has_perm('dictionary.delete_lemmaidgloss'):
            messages.add_message(request, messages.WARNING, _("You have no permission to delete lemmas."))
            return HttpResponseRedirect(reverse('dictionary:admin_lemma_list'))
        delete_lemmas_confirmed = self.request.POST.get('delete_lemmas', 'false')
        if delete_lemmas_confirmed != 'delete_lemmas':
            # the template sets POST value 'delete_lemmas' to value 'delete_lemmas'
            messages.add_message(request, messages.WARNING, _("Incorrect deletion code."))
            return HttpResponseRedirect(reverse('dictionary:admin_lemma_list'))
        datasets_user_can_change = get_objects_for_user(request.user, 'change_dataset', Dataset, accept_global_perms=False)
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        (queryset, num_gloss_zero_matches) = self.get_annotated_queryset()
        # check permissions, if fails, do nothing and show error message
        for lemma in queryset:
            if lemma.num_gloss == 0:
                # the get_annotated_queryset which in turn calls get_queryset has already filtered on lemma's in the selected dataset
                dataset_of_requested_lemma = lemma.dataset
                if dataset_of_requested_lemma not in datasets_user_can_change:
                    messages.add_message(request, messages.WARNING,
                                         _("You do not have change permission on the dataset of the lemma you are atteempting to delete."))
                    return HttpResponseRedirect(reverse('dictionary:admin_lemma_list'))
        for lemma in queryset:
            if lemma.num_gloss == 0:
                lemma_translation_objects = lemma.lemmaidglosstranslation_set.all()
                for trans in lemma_translation_objects:
                    trans.delete()
                lemma.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_lemma_list'))


class LemmaCreateView(CreateView):
    model = LemmaIdgloss
    template_name = 'dictionary/add_lemma.html'
    last_used_dataset = None
    fields = []

    def get_context_data(self, **kwargs):
        context = super(CreateView, self).get_context_data(**kwargs)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if len(selected_datasets) == 1:
            self.last_used_dataset = selected_datasets[0].acronym
        elif 'last_used_dataset' in self.request.session.keys():
            self.last_used_dataset = self.request.session['last_used_dataset']

        context['last_used_dataset'] = self.last_used_dataset

        context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE
        context['add_lemma_form'] = LemmaCreateForm(self.request.GET, languages=dataset_languages, user=self.request.user, last_used_dataset=self.last_used_dataset)
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

        return context

    def post(self, request, *args, **kwargs):
        dataset = None
        if 'dataset' in request.POST and request.POST['dataset'] is not None:
            dataset = Dataset.objects.get(pk=request.POST['dataset'])
            selected_datasets = Dataset.objects.filter(pk=request.POST['dataset'])
        else:
            selected_datasets = get_selected_datasets_for_user(request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        form = LemmaCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=self.last_used_dataset)

        for item, value in request.POST.items():
            if item.startswith(form.lemma_create_field_prefix):
                language_code_2char = item[len(form.lemma_create_field_prefix):]
                language = Language.objects.get(language_code_2char=language_code_2char)
                lemmas_for_this_language_and_annotation_idgloss = LemmaIdgloss.objects.filter(
                    lemmaidglosstranslation__language=language,
                    lemmaidglosstranslation__text__exact=value.upper(),
                    dataset=dataset)
                if len(lemmas_for_this_language_and_annotation_idgloss) != 0:
                    translated_message = _('Lemma ID Gloss is not unique for that language.')
                    return render(request, 'dictionary/warning.html',
                                  {'warning': translated_message,
                                   'dataset_languages': dataset_languages,
                                   'selected_datasets': selected_datasets,
                                   'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

        if form.is_valid():
            try:
                lemma = form.save()
                print("LEMMA " + str(lemma.pk))
            except ValidationError as ve:
                messages.add_message(request, messages.ERROR, ve.message)
                return render(request, 'dictionary/add_lemma.html',
                              {'add_lemma_form': LemmaCreateForm(request.POST,
                                                                 languages=dataset_languages,
                                                                 user=request.user,
                                                                 last_used_dataset=self.last_used_dataset),
                                                                     'dataset_languages': dataset_languages,
                                                                     'selected_datasets': get_selected_datasets_for_user(request.user),
                                                                        'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

            # return HttpResponseRedirect(reverse('dictionary:admin_lemma_list', kwargs={'pk': lemma.id}))
            return HttpResponseRedirect(reverse('dictionary:admin_lemma_list'))
        else:
            return render(request, 'dictionary/add_lemma.html', {'add_lemma_form': form,
                                                             'dataset_languages': dataset_languages,
                                                             'selected_datasets': get_selected_datasets_for_user(request.user),
                                                                'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })


def create_lemma_for_gloss(request, glossid):
    try:
        gloss = Gloss.objects.get(id=glossid)
    except ObjectDoesNotExist:
        try:
            gloss = Morpheme.objects.get(id=glossid).gloss
        except ObjectDoesNotExist:
            messages.add_message(request, messages.ERROR, _("The specified gloss does not exist."))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    # get data from gloss before updating anything
    dataset = gloss.lemma.dataset
    dataset_languages = dataset.translation_languages.all()
    # the last used dataset is a hidden field in the form, set by Django
    last_used_dataset = request.POST['last_used_dataset']
    form = LemmaCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=last_used_dataset)
    for item, value in request.POST.items():
        value = value.strip()
        if item.startswith(form.lemma_create_field_prefix):
            language_code_2char = item[len(form.lemma_create_field_prefix):]
            language = Language.objects.get(language_code_2char=language_code_2char)
            lemmas_for_this_language_and_annotation_idgloss = LemmaIdgloss.objects.filter(
                lemmaidglosstranslation__language=language,
                lemmaidglosstranslation__text__exact=value.upper(),
                dataset=dataset)
            if len(lemmas_for_this_language_and_annotation_idgloss) != 0:
                messages.add_message(request, messages.ERROR, _('Lemma ID Gloss not unique for language.'))
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    if form.is_valid():
        try:
            with atomic():
                lemma = form.save()
                gloss.lemma = lemma
                gloss.save()
        except ValidationError as ve:
            messages.add_message(request, messages.ERROR, ve.message)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
        messages.add_message(request, messages.ERROR, _("The form contains errors."))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class LemmaUpdateView(UpdateView):
    model = LemmaIdgloss
    success_url = reverse_lazy('dictionary:admin_lemma_list')
    page_in_lemma_list = ''
    template_name = 'dictionary/update_lemma.html'
    fields = []
    gloss_found = False
    gloss_id = ''
    search_type = 'lemma'

    def get_context_data(self, **kwargs):
        context = super(LemmaUpdateView, self).get_context_data(**kwargs)

        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []
        if search_results and len(search_results) > 0:
            if not self.request.session['search_results'][0]['href_type'] == 'lemma/update':
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if not self.request.session['search_type'] == 'lemma':
                # search_type is 'handshape'
                self.request.session['search_results'] = []
        self.request.session['search_type'] = self.search_type

        context['active_id'] = self.object.pk

        # this is needed by the menu bar
        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        # get the page of the lemma list on which this lemma appears in order ro return to it after update
        request_path = self.request.META.get('HTTP_REFERER')
        if not request_path:
            context['caller'] = 'lemma_list'
        else:
            path_parms = request_path.split('?page=')
            if len(path_parms) > 1:
                self.page_in_lemma_list = str(path_parms[1])
            if 'gloss' in path_parms[0]:
                self.gloss_found = True
                context['caller'] = 'gloss_detail_view'
                # caller was Gloss Details
                import re
                try:
                    m = re.search('/dictionary/gloss/(\d+)(/|$|\?)', path_parms[0])
                    gloss_id_pattern = m.group(1)
                    self.gloss_id = gloss_id_pattern
                except (AttributeError):
                    # it is unknown what gloss we were looking at, something went wrong with pattern matching on the url
                    # restore callback to lemma list
                    context['caller'] = 'lemma_list'
                    self.gloss_found = False
            else:
                context['caller'] = 'lemma_list'
        # These are needed for return to the Gloss Details
        # They are passed to the POST handling via hidden variables in the template
        context['gloss_id'] = self.gloss_id
        context['gloss_found'] = self.gloss_found

        context['page_in_lemma_list'] = self.page_in_lemma_list
        dataset = self.object.dataset
        context['dataset'] = dataset
        dataset_languages = Language.objects.filter(dataset=dataset).distinct()
        context['dataset_languages'] = dataset_languages
        context['change_lemma_form'] = LemmaUpdateForm(instance=self.object, page_in_lemma_list=self.page_in_lemma_list)
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

        # lemnma group

        # Make sure these are evaluated ih Python
        lemma_group_count = self.object.gloss_set.count()
        lemma_group_glossset = Gloss.objects.filter(lemma=self.object)
        lemma_group_list = []
        for lemma in lemma_group_glossset:
            annotation_idgloss = {}
            if lemma.dataset:
                for language in lemma.dataset.translation_languages.all():
                    annotation_idgloss[language] = lemma.annotationidglosstranslation_set.filter(
                        language=language)
            else:
                language = Language.objects.get(id=get_default_language_id())
                annotation_idgloss[language] = lemma.annotationidglosstranslation_set.filter(language=language)
            lemma_group_list.append((lemma, annotation_idgloss))
        context['lemma_group_count'] = lemma_group_count
        context['lemma_group_list'] = lemma_group_list
        return context

    def post(self, request, *args, **kwargs):
        # set context variables for warning.html
        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        instance = self.get_object()
        dataset = instance.dataset
        form = LemmaUpdateForm(request.POST, instance=instance)

        for item, value in request.POST.items():
            value = value.strip()
            if item.startswith(form.lemma_update_field_prefix):
                if value != '':
                    language_code_2char = item[len(form.lemma_update_field_prefix):]
                    language = Language.objects.get(language_code_2char=language_code_2char)
                    lemmas_for_this_language_and_annotation_idgloss = LemmaIdgloss.objects.filter(
                        lemmaidglosstranslation__language=language,
                        lemmaidglosstranslation__text__exact=value.upper(),
                        dataset=dataset)
                    if len(lemmas_for_this_language_and_annotation_idgloss) != 0:
                        for nextLemma in lemmas_for_this_language_and_annotation_idgloss:
                            if nextLemma.id != instance.id:
                                # found a different lemma with same translation
                                translated_message = _('Lemma ID Gloss is not unique for that language.')
                                return render(request, 'dictionary/warning.html',
                                              {'warning': translated_message,
                                               'dataset_languages': dataset_languages,
                                               'selected_datasets': selected_datasets,
                                               'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

                else:
                    # intent to set lemma translation to empty
                    pass
            elif item.startswith('page') and value:
                # page of the lemma list where the gloss to update is displayed
                self.page_in_lemma_list = value
            elif item.startswith('gloss_found') and value:
                # this was obtained in get_context_data and put in the hidden variable of the template
                self.gloss_found = value
            elif item.startswith('gloss_id') and value:
                # this was obtained in get_context_data and put in the hidden variable of the template
                self.gloss_id = value

        if form.is_valid():

            request_path = self.request.META.get('HTTP_REFERER')
            path_parms = request_path.split('?page=')
            if len(path_parms) > 1:
                self.page_in_lemma_list = str(path_parms[1])

            try:
                form.save()
                messages.add_message(request, messages.INFO, _("The changes to the lemma have been saved."))

            except Exception as e:
                print(e)
                # a specific message is put into the messages frmaework rather than the message caught in the exception
                # if it's not done this way, it gives a runtime error
                if self.page_in_lemma_list:
                    messages.add_message(request, messages.ERROR, _("There must be at least one translation for this lemma."))
                else:
                    return HttpResponseRedirect(reverse_lazy('dictionary:change_lemma', kwargs={'pk': instance.id}))

            # return to the same page in the list of lemmas, if available
            if self.page_in_lemma_list:
                return HttpResponseRedirect(self.success_url + '?page='+self.page_in_lemma_list)
            elif self.gloss_found and self.gloss_id:
                # return to Gloss Details
                gloss_detail_view_url = reverse_lazy('dictionary:admin_gloss_view', kwargs={'pk': self.gloss_id})
                return HttpResponseRedirect(gloss_detail_view_url)
            else:
                return HttpResponseRedirect(self.success_url)

        else:
            return HttpResponseRedirect(reverse_lazy('dictionary:change_lemma', kwargs={'pk': instance.id}))

    def get(self, request, *args, **kwargs):
        # set the context parameters for warning.html
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            show_dataset_interface = False

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested lemma does not exist.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})
        if self.object.dataset == None:
            translated_message = _('Requested lemma has no dataset.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_lemma = self.object.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=False, any_perm=True)

        if dataset_of_requested_lemma not in selected_datasets:
            translated_message = _('The lemma you are trying to view is not in your selected datasets.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })
        if dataset_of_requested_lemma not in datasets_user_can_view:
            translated_message = _('The lemma you are trying to view is not in a dataset you can view.')
            return render(request, 'dictionary/warning.html',
                          {'warning': translated_message,
                           'dataset_languages': dataset_languages,
                           'selected_datasets': selected_datasets,
                           'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface })

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

class LemmaDeleteView(DeleteView):
    model = LemmaIdgloss
    success_url = reverse_lazy('dictionary:admin_lemma_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.gloss_set.all():
            messages.add_message(request, messages.ERROR, _("There are glosses using this lemma."))
        else:
            self.object.delete()
        return HttpResponseRedirect(self.get_success_url())


class KeywordListView(ListView):

    model = Gloss
    template_name = 'dictionary/admin_keyword_list.html'
    paginate_by = 50
    query_parameters = dict()

    def get(self, request, *args, **kwargs):
        return super(KeywordListView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(KeywordListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets

        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        if not selected_datasets:
            dataset_language = Language.objects.get(id=get_default_language_id())
        else:
            dataset_language = selected_datasets.first().default_language
        context['dataset_language'] = dataset_language

        search_form = KeyMappingSearchForm(self.request.GET, languages=dataset_languages)

        context['searchform'] = search_form

        multiple_select_gloss_fields = ['tags']
        context['MULTIPLE_SELECT_GLOSS_FIELDS'] = multiple_select_gloss_fields

        # data structures to store the query parameters in order to keep them in the form
        context['query_parameters'] = json.dumps(self.query_parameters)
        query_parameters_keys = list(self.query_parameters.keys())
        context['query_parameters_keys'] = json.dumps(query_parameters_keys)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        return context

    def get_queryset(self):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        if not selected_datasets or selected_datasets.count() > 1:
            feedback_message = _('Please select a single dataset to view keywords.')
            messages.add_message(self.request, messages.ERROR, feedback_message)
            # the query set is a list of tuples (gloss, keyword_translations, senses_groups)
            return []

        get = self.request.GET

        dataset_language = selected_datasets.first().default_language

        # multilingual
        dataset_languages = get_dataset_languages(selected_datasets)

        # exclude morphemes
        glosses_of_datasets = Gloss.none_morpheme_objects().filter(lemma__dataset__in=selected_datasets)

        # data structure to store the query parameters in order to keep them in the form
        query_parameters = dict()

        if 'tags[]' in get:
            vals = get.getlist('tags[]')
            if vals != []:
                query_parameters['tags[]'] = vals
                glosses_with_tag = list(
                    TaggedItem.objects.filter(tag__name__in=vals).values_list('object_id', flat=True))
                glosses_of_datasets = glosses_of_datasets.filter(id__in=glosses_with_tag)

        self.query_parameters = query_parameters

        glossesXsenses = []
        for gloss in glosses_of_datasets:
            keyword_translations_per_language = dict()
            sense_groups_per_language = dict()
            for language in dataset_languages:
                keyword_translations = gloss.translation_set.filter(language=language).order_by('orderIndex', 'index')
                senses_groups = dict()
                for trans in keyword_translations:
                    if trans.orderIndex not in senses_groups.keys():
                        senses_groups[trans.orderIndex] = []
                    senses_groups[trans.orderIndex].append(trans)
                keyword_translations_per_language[language] = keyword_translations
                sense_groups_per_language[language] = senses_groups
            translated_senses = dict()
            sense_translations = gloss.translation_set.all().order_by('orderIndex', 'index')
            for sense_translation in sense_translations:
                orderIndex = sense_translation.orderIndex
                if orderIndex not in translated_senses.keys():
                    translated_senses[orderIndex] = dict()
                    for language in dataset_languages:
                        # initialize all dataset languages for looping purposes in the template
                        translated_senses[orderIndex][language] = dict()
                language = sense_translation.language
                if sense_translation.id not in translated_senses[orderIndex][language].keys():
                    translated_senses[orderIndex][language][sense_translation.id] = dict()
                translated_senses[orderIndex][language][sense_translation.id][sense_translation.index] = sense_translation
            glossesXsenses.append((gloss,
                                   keyword_translations_per_language,
                                   sense_groups_per_language,
                                   translated_senses))
        return glossesXsenses

