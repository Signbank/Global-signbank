
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.core.paginator import Paginator
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.db.models import F, ExpressionWrapper, IntegerField, Count
from django.db.models import OuterRef, Subquery
from django.db.models.query import QuerySet
from django.db.models.functions import Concat
from django.db.models import Q, Count, CharField, TextField, Value as V
from django.db.models.fields import BooleanField
from django.db.models.sql.where import NothingNode, WhereNode
from django.http import HttpResponse, HttpResponseRedirect, \
    QueryDict, JsonResponse, StreamingHttpResponse
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.translation import override, gettext_lazy as _, activate
from django.shortcuts import *
from django.contrib import messages
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.contrib.auth.models import User, Group

import csv
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_objects_for_user

from signbank.feedback.models import *
from signbank.video.forms import VideoUploadForObjectForm
from signbank.video.models import GlossVideoDescription, GlossVideo, GlossVideoNME
from tagging.models import Tag, TaggedItem
from signbank.settings.server_specific import *

from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value, \
    choicelist_queryset_to_translated_dict, choicelist_queryset_to_machine_value_dict, choicelist_queryset_to_colors, \
    choicelist_queryset_to_field_colors
from signbank.dictionary.field_choices import get_static_choice_lists, get_frequencies_for_category, category_to_fields, \
    fields_to_categories, fields_to_fieldcategory_dict

from signbank.dictionary.forms import *
from signbank.tools import (get_selected_datasets_for_user, write_ecv_file_for_dataset,
                            construct_scrollbar, get_dataset_languages, get_datasets_with_public_glosses,
                            searchform_panels, map_search_results_to_gloss_list,
                            get_interface_language_and_default_language_codes, get_default_annotationidglosstranslation)
from signbank.csv_interface import (csv_gloss_to_row, csv_header_row_glosslist, csv_header_row_morphemelist,
                                    csv_morpheme_to_row, csv_header_row_handshapelist, csv_handshape_to_row,
                                    csv_header_row_lemmalist, csv_lemma_to_row,
                                    csv_header_row_minimalpairslist, csv_focusgloss_to_minimalpairs)
from signbank.dictionary.consistency_senses import consistent_senses, check_consistency_senses, \
    reorder_sensetranslations, reorder_senses
from signbank.query_parameters import (convert_query_parameters_to_filter, pretty_print_query_fields,
                                       pretty_print_query_values, query_parameters_this_gloss,
                                       apply_language_filters_to_results, apply_video_filters_to_results,
                                       search_fields_from_get, queryset_from_get,
                                       set_up_fieldchoice_translations, set_up_language_fields,
                                       set_up_signlanguage_dialects_fields,
                                       queryset_glosssense_from_get, query_parameters_from_get,
                                       queryset_sentences_from_get, query_parameters_toggle_fields)
from signbank.search_history import available_query_parameters_in_search_history, languages_in_query, display_parameters, \
    get_query_parameters, save_query_parameters, fieldnames_from_query_parameters
from signbank.frequency import import_corpus_speakers, configure_corpus_documents_for_dataset, update_corpus_counts, \
    speaker_identifiers_contain_dataset_acronym, get_names_of_updated_eaf_files, update_corpus_document_counts, \
    dictionary_speakers_to_documents, document_has_been_updated, document_to_number_of_glosses, \
    document_to_glosses, get_corpus_speakers, remove_document_from_corpus, document_identifiers_from_paths, \
    eaf_file_from_paths, documents_paths_dictionary
from signbank.dictionary.frequency_display import (collect_speaker_age_data, collect_variants_data,
                                                   collect_variants_age_range_data,
                                                   collect_variants_age_sex_raw_percentage)
from signbank.dictionary.senses_display import (senses_per_language, senses_per_language_list,
                                                sensetranslations_per_language_dict,
                                                senses_translations_per_language_list,
                                                senses_sentences_per_language_list)
from signbank.dictionary.context_data import (get_context_data_for_list_view, get_context_data_for_gloss_search_form,
                                              get_web_search)
from signbank.dictionary.related_objects import (morpheme_is_related_to, gloss_is_related_to, gloss_related_objects,
                                                 okay_to_move_gloss, same_translation_languages, okay_to_move_glosses,
                                                 glosses_in_lemma_group, transitive_related_objects)
from signbank.manage_videos import listing_uploaded_videos
from signbank.zip_interface import *


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
        if sOrder[0:1] == '-':
            # A starting '-' sign means: descending order
            sOrder = sOrder[1:]
        def lambda_sort_tuple(x, bReversed):
            # Order by the string-values in the tuple list
            getattr_sOrder = getattr(x, sOrder)
            if getattr_sOrder is None:
                # if the field is not set, use the machine value 0 choice
                return True, dict(tpList)[0]
            elif getattr_sOrder.machine_value in [0,1]:
                return True, dict(tpList)[getattr_sOrder.machine_value]
            else:
                return bReversed, dict(tpList)[getattr(x, sOrder).machine_value]

        return sorted(qs, key=lambda x: lambda_sort_tuple(x, bReversed), reverse=bReversed)

    def order_queryset_by_annotationidglosstranslation(qs, sOrder):
        language_code_2char = sOrder[-2:]
        sOrderAsc = sOrder
        if sOrder[0:1] == '-':
            # A starting '-' sign means: descending order
            sOrderAsc = sOrder[1:]
        annotationidglosstranslation = AnnotationIdglossTranslation.objects.filter(gloss=OuterRef('pk')).filter(language__language_code_2char__iexact=language_code_2char).distinct()
        qs = qs.annotate(**{sOrderAsc: Subquery(annotationidglosstranslation.values('text')[:1])}).order_by(sOrder)
        return qs

    def order_queryset_by_lemmaidglosstranslation(qs, sOrder):
        language_code_2char = sOrder[-2:]
        sOrderAsc = sOrder
        if sOrder[0:1] == '-':
            # A starting '-' sign means: descending order
            sOrderAsc = sOrder[1:]
        lemmaidglosstranslation = LemmaIdglossTranslation.objects.filter(lemma=OuterRef('lemma'), language__language_code_2char__iexact=language_code_2char)
        qs = qs.annotate(**{sOrderAsc: Subquery(lemmaidglosstranslation.values('text')[:1])}).order_by(sOrder)
        return qs

    def order_queryset_by_translation(qs, sOrder):
        language_code_2char = sOrder[-2:]
        sOrderAsc = sOrder
        if sOrder[0:1] == '-':
            # A starting '-' sign means: descending order
            sOrderAsc = sOrder[1:]
        translations = Translation.objects.filter(sensetranslation__sense__glosssense__gloss=OuterRef('pk')).filter(language__language_code_2char__iexact=language_code_2char)
        qs = qs.annotate(**{sOrderAsc: Subquery(translations.values('translation__text')[:1])}).order_by(sOrder)
        return qs

    # Set the default sort order
    default_sort_order = True
    bReversed = False
    bText = True

    # See if the form contains any sort-order information
    if 'sortOrder' in get and get['sortOrder']:
        # Take the user-indicated sort order
        sOrder = get['sortOrder']
        default_sort_order = False
        if sOrder[0:1] == '-':
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
    if sOrder.endswith('handedness'):
        bText = False
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Handedness", bReversed)
    elif sOrder.endswith('domhndsh') or sOrder.endswith('subhndsh'):
        bText = False
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Handshape", bReversed)
    elif sOrder.endswith('locprim'):
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


def error_message_regular_expression(request, search_fields, field_values):
    error_message_1 = _('Error in search field ')
    error_message_2 = ', '.join(search_fields)
    error_message_3 = _(': A regular expression is expected due to special characters. ')
    error_message_4 = _('Please use a backslash before special characters: ')
    error_message_5 = ' '.join(field_values)
    error_message = error_message_1 + error_message_2 + error_message_3 + error_message_4 + error_message_5
    messages.add_message(request, messages.ERROR, error_message)
    return


def show_warning(request, translated_message, selected_datasets):
    # this function is used by the get methods of detail views below
    dataset_languages = get_dataset_languages(selected_datasets)
    show_dataset_interface = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
    use_regular_expressions = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)
    messages.add_message(request, messages.ERROR, translated_message)
    return render(request, 'dictionary/warning.html',
                  {'dataset_languages': dataset_languages,
                   'selected_datasets': get_selected_datasets_for_user(request.user),
                   'USE_REGULAR_EXPRESSIONS': use_regular_expressions,
                   'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})


class Echo:
    """An object that implements just the write method of the file-like
    interface. This is based on an example in the Django 4.2 documentation
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


class GlossListView(ListView):

    model = Gloss
    paginate_by = 100
    only_export_ecv = False
    search_type = 'sign'
    view_type = 'gloss_list'
    web_search = False
    show_all = False
    dataset_name = settings.DEFAULT_DATASET_ACRONYM
    last_used_dataset = None
    queryset_language_codes = []
    query_parameters = dict()
    search_form_data = QueryDict(mutable=True)
    search_form = GlossSearchForm()

    def get_template_names(self):
        return ['dictionary/admin_gloss_list.html']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields_with_choices = fields_to_fieldcategory_dict(settings.GLOSS_CHOICE_FIELDS)
        set_up_fieldchoice_translations(self.search_form, fields_with_choices)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(GlossListView, self).get_context_data(**kwargs)

        set_up_language_fields(Gloss, self, self.search_form)
        set_up_signlanguage_dialects_fields(self, self.search_form)

        context = get_context_data_for_list_view(self.request, self, self.kwargs, context)
        self.queryset_language_codes = context['queryset_language_codes']
        self.show_all = context['show_all']

        context = get_context_data_for_gloss_search_form(self.request, self, self.search_form, self.kwargs, context)

        # it is necessary to sort the object list by lemma_id in order for all glosses with the same lemma to be grouped
        # correctly in the template
        list_of_object_ids = [ g.id for g in self.object_list ]
        glosses_ordered_by_lemma_id = Gloss.objects.filter(id__in=list_of_object_ids).order_by('lemma_id')
        context['glosses_ordered_by_lemma_id'] = glosses_ordered_by_lemma_id

        if context['search_type'] == 'sign' or not self.request.user.is_authenticated:
            # Only count the none-morpheme glosses
            # this branch is slower than the other one
            context['glosscount'] = Gloss.none_morpheme_objects().select_related('lemma').select_related(
                'dataset').filter(lemma__dataset__in=context['selected_datasets']).count()
        else:
            context['glosscount'] = Gloss.objects.select_related('lemma').select_related(
                'dataset').filter(lemma__dataset__in=context['selected_datasets']).count()

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
        for lang in context['dataset_languages']:
            dataset_display_languages.append(lang.language_code_2char)
        if interface_language_code in dataset_display_languages:
            lang_attr_name = interface_language_code
        else:
            lang_attr_name = default_language_code

        if context['search_type'] in ['sense']:
            # this is GlossListView, show a scrollbar for Glosses from a previous search
            self.search_type = 'sign'
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
            field_label = Gloss.get_field(fieldname).verbose_name
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

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format') == 'CSV':
            return self.render_to_csv_response()
        elif self.request.GET.get('export_ecv') == 'ECV' or self.only_export_ecv:
            return self.render_to_ecv_export_response()
        else:
            return super(GlossListView, self).render_to_response(context, **response_kwargs)

    def render_to_ecv_export_response(self):

        # check that the user is logged in
        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/signs/search/')

        # if the dataset is the default dataset since this option is only offered when
        # there is only one dataset
        try:
            dataset_object = Dataset.objects.get(acronym=self.dataset_name)
        except ObjectDoesNotExist:
            messages.add_message(self.request, messages.ERROR, _('No dataset with that name found.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/signs/search/')

        # make sure the user can write to this dataset
        import guardian
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = guardian.shortcuts.get_objects_for_user(self.request.user, 'change_dataset', Dataset)
        if not user_change_datasets or dataset_object not in user_change_datasets:
            messages.add_message(self.request, messages.ERROR, _('No permission to export dataset.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/signs/search/')

        # if we get to here, the user is authenticated and has permission to export the dataset
        success, ecv_file = write_ecv_file_for_dataset(self.dataset_name)

        if success:
            messages.add_message(self.request, messages.INFO, _('ECV successfully updated.'))
        else:
            messages.add_message(self.request, messages.INFO, _('No ECV created for dataset.'))
        return HttpResponseRedirect(settings.PREFIX_URL + '/signs/search/')

    def render_to_csv_response(self):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + FIELDS['frequency'] + ['inWeb', 'isNew']
        fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        header = csv_header_row_glosslist(dataset_languages)
        csv_rows = [header]

        if self.object_list:
            query_set = self.object_list
        else:
            query_set = self.get_queryset()

        if isinstance(query_set, QuerySet):
            query_set = list(query_set)

        for gloss in query_set:
            safe_row = csv_gloss_to_row(gloss, dataset_languages, fields)
            csv_rows.append(safe_row)

        # this is based on an example in the Django 4.2 documentation
        pseudo_buffer = Echo()
        new_writer = csv.writer(pseudo_buffer)
        return StreamingHttpResponse(
            (new_writer.writerow(row) for row in csv_rows),
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="dictionary-export.csv"'},
        )

    def get_queryset(self):
        get = self.request.GET

        self.show_all = self.kwargs.get('show_all', self.show_all)
        self.search_type = self.request.GET.get('search_type', 'sign')
        setattr(self.request.session, 'search_type', self.search_type)
        self.view_type = self.request.GET.get('view_type', 'gloss_list')
        setattr(self.request, 'view_type', self.view_type)
        self.web_search = get_web_search(self.request)
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

        valid_regex, search_fields, field_values = check_language_fields(self.search_form, GlossSearchForm, get, dataset_languages)

        if USE_REGULAR_EXPRESSIONS and not valid_regex:
            error_message_regular_expression(self.request, search_fields, field_values)
            qs = Gloss.objects.none()
            return qs

        # Get the initial selection
        if self.show_all or (len(get) > 0 and 'query' not in self.request.GET):
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
            qs = apply_video_filters_to_results('Gloss', qs, self.query_parameters)

            query = convert_query_parameters_to_filter(self.query_parameters)
            if query:
                qs = qs.filter(query).distinct()

            sorted_qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)
            return sorted_qs

        # No filters or 'show_all' specified? show nothing
        else:
            qs = Gloss.objects.none()

        if not self.request.user.is_authenticated or not self.request.user.has_perm('dictionary.search_gloss'):
            qs = qs.filter(inWeb__exact=True)

        # If we wanted to get everything, we're done now
        if self.show_all:
            # sort the results
            sorted_qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)
            return sorted_qs

        # this is a temporary query_parameters variable
        # it is saved to self.query_parameters after the parameters are processed
        query_parameters = dict()

        if 'search' in get and get['search']:
            # menu bar gloss search, return the results
            val = get['search']
            query_parameters['search'] = val
            if USE_REGULAR_EXPRESSIONS:
                query = Q(annotationidglosstranslation__text__iregex=val)
            else:
                query = Q(annotationidglosstranslation__text__icontains=val)

            if re.match(r'^\d+$', val):
                query = query | Q(sn__exact=val)

            qs = qs.filter(query).distinct()

            self.request.session['query_parameters'] = json.dumps(query_parameters)
            self.request.session.modified = True
            self.query_parameters = query_parameters

            sorted_qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)
            return sorted_qs

        if 'translation' in get and get['translation']:
            # menu bar senses search, return the results
            val = get['translation']
            query_parameters['translation'] = val
            if USE_REGULAR_EXPRESSIONS:
                query = Q(senses__senseTranslations__translations__translation__text__iregex=val)
            else:
                query = Q(senses__senseTranslations__translations__translation__text__icontains=val)
            qs = qs.filter(query).distinct()

            self.request.session['query_parameters'] = json.dumps(query_parameters)
            self.request.session.modified = True
            self.query_parameters = query_parameters

            sorted_qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)
            return sorted_qs

        if self.search_type != 'sign':
            query_parameters['search_type'] = self.search_type

        qs = queryset_glosssense_from_get('Gloss', GlossSearchForm, self.search_form, get, qs)
        query_parameters = query_parameters_from_get(self.search_form, get, query_parameters)
        qs = apply_video_filters_to_results('Gloss', qs, query_parameters)

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


class SenseListView(ListView):

    model = GlossSense
    paginate_by = 50
    search_type = 'sense'
    view_type = 'sense_list'
    web_search = False
    dataset_name = settings.DEFAULT_DATASET_ACRONYM
    last_used_dataset = None
    queryset_language_codes = []
    query_parameters = dict()
    search_form_data = QueryDict(mutable=True)
    template_name = 'dictionary/admin_senses_list.html'
    search_form = GlossSearchForm()
    sentence_search_form = SentenceForm()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields_with_choices = fields_to_fieldcategory_dict(settings.GLOSSSENSE_CHOICE_FIELDS)
        set_up_fieldchoice_translations(self.search_form, fields_with_choices)
        sentence_fields_with_choices = {'sentenceType': 'SentenceType'}
        set_up_fieldchoice_translations(self.sentence_search_form, sentence_fields_with_choices)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SenseListView, self).get_context_data(**kwargs)

        set_up_language_fields(GlossSense, self, self.search_form)
        set_up_signlanguage_dialects_fields(self, self.search_form)

        context = get_context_data_for_list_view(self.request, self, self.kwargs, context)

        context = get_context_data_for_gloss_search_form(self.request, self, self.search_form, self.kwargs,
                                                         context, self.sentence_search_form)

        context['sensecount'] = Sense.objects.filter(glosssense__gloss__lemma__dataset__in=context['selected_datasets']).count()

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
        for lang in context['dataset_languages']:
            dataset_display_languages.append(lang.language_code_2char)
        if interface_language_code in dataset_display_languages:
            lang_attr_name = interface_language_code
        else:
            lang_attr_name = default_language_code

        items = construct_scrollbar(list_of_objects, context['search_type'], lang_attr_name)
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

        return context

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        if 'paginate_by' in self.request.GET:
            paginate_by = int(self.request.GET.get('paginate_by'))
            self.request.session['paginate_by'] = paginate_by
        else:
            if 'paginate_by' in self.request.session.keys():
                # restore any previous paginate setting
                paginate_by = self.request.session['paginate_by']
            else:
                paginate_by = self.paginate_by

        return paginate_by

    def get_queryset(self):
        get = self.request.GET

        self.search_type = self.request.GET.get('search_type', 'sense')
        setattr(self.request.session, 'search_type', self.search_type)
        self.view_type = self.request.GET.get('view_type', 'sense_list')
        setattr(self.request, 'view_type', self.view_type)
        self.web_search = get_web_search(self.request)
        setattr(self.request, 'web_search', self.web_search)

        if 'query' not in self.request.GET:
            # erase the previous query
            self.query_parameters = dict()
            self.request.session['query_parameters'] = json.dumps(self.query_parameters)
            self.request.session.modified = True
        else:
            # the 'query' needs to be handed off from SearchHistoryView to use the parameters in the Senses Search
            session_query_parameters = self.request.session['query_parameters']
            self.query_parameters = json.loads(session_query_parameters)

        if self.request.user.is_authenticated:
            selected_datasets = get_selected_datasets_for_user(self.request.user)
        elif 'selected_datasets' in self.request.session.keys():
            selected_datasets = Dataset.objects.filter(acronym__in=self.request.session['selected_datasets'])
        else:
            selected_datasets = Dataset.objects.filter(acronym=settings.DEFAULT_DATASET_ACRONYM)
        dataset_languages = get_dataset_languages(selected_datasets)

        valid_regex, search_fields, field_values = check_language_fields(self.search_form, GlossSearchForm, get, dataset_languages)

        if USE_REGULAR_EXPRESSIONS and not valid_regex:
            error_message_regular_expression(self.request, search_fields, field_values)
            qs = GlossSense.objects.none()
            return qs

        # Get the initial selection
        if len(get) > 0 and 'query' not in self.request.GET:
            qs = GlossSense.objects.filter(gloss__lemma__dataset__in=selected_datasets)
            qs = qs.order_by('gloss__id', 'order')

        elif self.query_parameters and 'query' in self.request.GET:
            gloss_query = Gloss.objects.all().prefetch_related('lemma').filter(lemma__dataset__in=selected_datasets)
            gloss_query = apply_language_filters_to_results(gloss_query, self.query_parameters)
            gloss_query = apply_video_filters_to_results('GlossSense', gloss_query, self.query_parameters)
            gloss_query = gloss_query.distinct()

            query = convert_query_parameters_to_filter(self.query_parameters)
            if query:
                gloss_query = gloss_query.filter(query).distinct()
            qs = GlossSense.objects.filter(gloss__in=gloss_query)
            qs = qs.order_by('gloss__id', 'order')
            return qs

        else:
            qs = GlossSense.objects.none()

        if not self.request.user.is_authenticated or not self.request.user.has_perm('dictionary.search_gloss'):
            qs = qs.filter(gloss__inWeb__exact=True)

        qs = queryset_glosssense_from_get('GlossSense', GlossSearchForm, self.search_form, get, qs)
        # this is a temporary query_parameters variable
        query_parameters = dict()
        # it is saved to self.query_parameters after the parameters are processed
        query_parameters = query_parameters_from_get(self.search_form, get, query_parameters)
        qs = apply_video_filters_to_results('GlossSense', qs, query_parameters)

        if self.search_type != 'sign':
            query_parameters['search_type'] = self.search_type

        qs = queryset_sentences_from_get(self.sentence_search_form, get, qs)
        query_parameters = query_parameters_from_get(self.sentence_search_form, get, query_parameters)

        # save the query parameters to a session variable
        self.request.session['query_parameters'] = json.dumps(query_parameters)
        self.request.session.modified = True
        self.query_parameters = query_parameters

        self.request.session['search_type'] = self.search_type
        self.request.session['web_search'] = self.web_search

        if 'last_used_dataset' not in self.request.session.keys():
            self.request.session['last_used_dataset'] = self.last_used_dataset

        # Return the resulting filtered (not sorted) queryset
        return qs


class GlossDetailView(DetailView):

    model = Gloss
    context_object_name = 'gloss'
    last_used_dataset = None
    query_parameters = dict()

    def get_template_names(self):
        return ['dictionary/gloss_detail.html']

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested gloss does not exist.')
            return show_warning(request, translated_message, selected_datasets)

        if not self.object.lemma or not self.object.lemma.dataset:
            translated_message = _('Requested gloss has no lemma or dataset.')
            return show_warning(request, translated_message, selected_datasets)

        if not request.user.is_authenticated:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_gloss = self.object.lemma.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=True, any_perm=True)

        if dataset_of_requested_gloss not in selected_datasets:
            translated_message = _('The gloss you are trying to view is not in your selected datasets.')
            return show_warning(request, translated_message, selected_datasets)

        if dataset_of_requested_gloss not in datasets_user_can_view:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                translated_message = _('The gloss you are trying to view is not in a dataset you can view.')
                return show_warning(request, translated_message, selected_datasets)

        senses_consistent = consistent_senses(self.object, include_translations=True,
                                              allow_empty_language=True)
        if not senses_consistent:
            if settings.DEBUG_SENSES:
                print('GlossDetailView get: gloss senses are not consistent: ', str(self.object.id))
            check_consistency_senses(self.object, delete_empty=True)
            # the senses and their translation objects are renumbered so orderIndex matches sense number
            # somehow this gets mis-matched
            reorder_senses(self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []
        if search_results and len(search_results) > 0:
            if self.request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme', 'sense']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['sign', 'sense', 'morpheme', 'sign_or_morpheme', 'sign_handshape']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []
        else:
            self.request.session['search_type'] = 'sign'

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        # Call the base implementation first to get a context
        context = super(GlossDetailView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        phonology_matrix = context['gloss'].phonology_matrix_homonymns(use_machine_value=True)
        phonology_focus = [field for field in phonology_matrix.keys()
                           if phonology_matrix[field] is not None
                           and phonology_matrix[field] not in ['Neutral',  '0', '1', 'False']]
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

        context['tagform'] = TagUpdateForm()
        context['affiliationform'] = AffiliationUpdateForm()
        context['videoform'] = VideoUploadForObjectForm(languages=dataset_languages)
        context['nmevideoform'] = VideoUploadForObjectForm(languages=dataset_languages)
        context['imageform'] = ImageUploadForGlossForm()
        context['definitionform'] = DefinitionForm()
        context['relationform'] = RelationForm()
        context['morphologyform'] = GlossMorphologyForm()
        context['morphemeform'] = GlossMorphemeForm()
        context['blendform'] = GlossBlendForm()
        context['othermediaform'] = OtherMediaForm()
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

        context['handedness'] = (int(self.object.handedness.machine_value) > 1) \
            if self.object.handedness and self.object.handedness.machine_value else 0  # minimal machine value is 2
        context['domhndsh'] = (int(self.object.domhndsh.machine_value) > 1) \
            if self.object.domhndsh and self.object.domhndsh.machine_value else 0        # minimal machine value -s 3
        context['tokNo'] = self.object.tokNo                 # Number of occurrences of Sign, used to display Stars

        # check for existence of strong hand and weak hand shapes
        if self.object.domhndsh:
            strong_hand_obj = Handshape.objects.filter(machine_value=self.object.domhndsh.machine_value).first()
        else:
            strong_hand_obj = None
        context['StrongHand'] = self.object.domhndsh.machine_value if strong_hand_obj else 0
        context['WeakHand'] = self.object.subhndsh.machine_value if self.object.subhndsh else 0

        context['SemanticFieldDefined'] = self.object.semField.all().count() > 0

        context['DerivationHistoryDefined'] = self.object.derivHist.all().count() > 0

        # Pass info about which fields we want to see
        gl = context['gloss']
        context['active_id'] = gl.id
        labels = gl.field_labels()

        # the lemma field is non-empty because it's caught in the get method
        dataset_of_requested_gloss = gl.lemma.dataset

        # set a session variable to be able to pass the gloss's id to the ajax_complete method
        # the last_used_dataset name is updated to that of this gloss
        # if a sequence of glosses are being created by hand, this keeps the dataset setting the same
        if dataset_of_requested_gloss:
            self.request.session['datasetid'] = dataset_of_requested_gloss.pk
            self.last_used_dataset = dataset_of_requested_gloss.acronym
        else:
            # in this case the gloss does not have a dataset assigned
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
        # Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['main', 'phonology', 'semantics']:
            context[topic+'_fields'] = []
            for field in FIELDS[topic]:
                # these do not appear in the phonology querying list
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

                    # Take the human value in the language we are using
                    field_value = getattr(gl, field)
                    if isinstance(field_value, FieldChoice) or isinstance(field_value, Handshape):
                        human_value = field_value.name if field_value else field_value
                    else:
                        # take care of different representations of empty text in database
                        if fieldname_to_kind(field) == 'text' and (field_value is None or field_value in ['-',' ','------','']):
                            human_value = ''
                        else:
                            human_value = field_value

                    context[topic+'_fields'].append([human_value,field,labels[field],kind])

        context['gloss_phonology'] = gloss_phonology
        context['phonology_list_kinds'] = phonology_list_kinds

        # Collect morphology definitions for sequential morphology section
        morphdefs = []
        for morphdef in context['gloss'].parent_glosses.all():

            translated_role = morphdef.role.name if morphdef.role else ''

            sign_display = str(morphdef.morpheme.id)
            morph_texts = morphdef.morpheme.get_annotationidglosstranslation_texts()
            if morph_texts.keys():
                if interface_language_code in morph_texts.keys():
                    sign_display = morph_texts[interface_language_code]
                else:
                    sign_display = morph_texts[default_language_code]

            morphdefs.append((morphdef, translated_role, sign_display))

        morphdefs = sorted(morphdefs, key=lambda tup: tup[1])
        context['morphdefs'] = morphdefs
        context['sequential_morphology_display'] = [(md[0].morpheme.pk, md[2]) for md in morphdefs]

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
                    # default language if the interface language hasn't been set for this gloss
                    homo_display = homo_trans[default_language_code][0].text

                homonyms_but_not_saved.append((homonym,homo_display))

        context['homonyms_but_not_saved'] = homonyms_but_not_saved

        # Regroup notes
        notes = context['gloss'].definition_set.all()
        notes_groupedby_role = {}
        for note in notes:
            translated_note_role = note.role.name if note.role else '-'
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

            # Save the other_media_type choices (same for every other_media,
            # but necessary because they all have other ids)
            context['other_media_field_choices'][
                'other-media-type_' + str(other_media.pk)] = choicelist_queryset_to_translated_dict(other_media_type_choice_list)

        context['other_media_field_choices'] = json.dumps(context['other_media_field_choices'])

        context['separate_english_idgloss_field'] = SEPARATE_ENGLISH_IDGLOSS_FIELD

        lemma_group = gl.lemma.gloss_set.all()
        if lemma_group.count() > 1:
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
            except ObjectDoesNotExist:
                annotation_text = gloss_default_annotationidglosstranslation
            context['annotation_idgloss'][language] = annotation_text

        # Put translations (keywords) per language in the context
        context['sensetranslations_per_language'] = {}
        if gl.dataset:
            for language in gl.dataset.translation_languages.all():
                context['sensetranslations_per_language'][language] = gl.translation_set.filter(language=language).order_by('translation__index')
        else:
            language = Language.objects.get(id=get_default_language_id())
            context['sensetranslations_per_language'][language] = gl.translation_set.filter(language=language).order_by('translation__index')

        sentencetype_choices = FieldChoice.objects.filter(field__iexact='SentenceType').order_by('machine_value')
        sentencetype_choice_list = choicelist_queryset_to_translated_dict(sentencetype_choices, id_prefix='', ordered=False)
        context['sentencetypes'] = sentencetype_choice_list
        context['senses'] = gl.senses.all().order_by('glosssense')

        sense_to_similar_senses = dict()
        for sns in context['senses']:
            # use the sns.id as the domain rather than a sense object since this is being used in the template
            sense_to_similar_senses[sns.id] = sns.get_senses_with_similar_sensetranslations_dict(gl)

        context['sense_to_similar_senses'] = sense_to_similar_senses

        annotated_sentences_1 = AnnotatedSentence.objects.filter(annotated_glosses__gloss=gl, annotated_glosses__isRepresentative=True).distinct().annotate(is_representative=V(1, output_field=IntegerField()))
        annotated_sentences_2 = AnnotatedSentence.objects.filter(annotated_glosses__gloss=gl, annotated_glosses__isRepresentative=False).distinct().annotate(is_representative=V(0, output_field=IntegerField()))
        annotated_sentences = annotated_sentences_1.union(annotated_sentences_2).order_by('-is_representative')
        annotated_sentences_with_video = []
        for annotated_sentence in annotated_sentences:
            if annotated_sentence.has_video() and annotated_sentence not in annotated_sentences_with_video:
                annotated_sentences_with_video.append(annotated_sentence)
        annotated_sentences = annotated_sentences_with_video
        if len(annotated_sentences) <= 3:
            context['annotated_sentences'] = annotated_sentences
        else:
            context['annotated_sentences'] = annotated_sentences[0:3]

        bad_dialect = False
        gloss_dialects = []

        gloss_signlanguage = gl.lemma.dataset.signlanguage if gl.lemma and gl.lemma.dataset else None

        initial_gloss_dialects = gl.dialect.all()
        gloss_dialect_choices = list(Dialect.objects.filter(signlanguage=gloss_signlanguage))

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

        context['gloss_semanticfields'] = list(gl.semField.all())

        context['gloss_derivationhistory'] = list(gl.derivHist.all())

        simultaneous_morphology = []
        for sim_morph in gl.simultaneous_morphology.all():
            translated_morph_type = sim_morph.morpheme.mrpType.name if sim_morph.morpheme.mrpType else ''
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
                # default language if the interface language hasn't been set for this gloss
                morpheme_display = morpheme_annotation_idgloss[default_language_code][0].text

            simultaneous_morphology.append((sim_morph, morpheme_display, translated_morph_type))

        context['simultaneous_morphology'] = simultaneous_morphology
        context['simultaneous_morphology_display'] = [(sm[0].morpheme.pk, sm[1]) for sm in simultaneous_morphology]

        # Obtain the number of morphemes in the dataset of this gloss
        # The template will not show the facility to add simultaneous morphology
        # if there are no morphemes to choose from
        dataset_id_of_gloss = gl.dataset
        count_morphemes_in_dataset = Morpheme.objects.filter(lemma__dataset=dataset_id_of_gloss).count()
        context['count_morphemes_in_dataset'] = count_morphemes_in_dataset

        blend_morphology = []
        for ble_morph in gl.blend_morphology.all():
            morpheme_display = get_default_annotationidglosstranslation(ble_morph.glosses)
            blend_morphology.append((ble_morph, morpheme_display))
        context['blend_morphology'] = blend_morphology

        otherrelations = []
        for oth_rel in gl.relation_sources.all():
            otherrelations.append((oth_rel, oth_rel.get_target_display()))
        context['otherrelations'] = otherrelations

        context['related_objects'] = gloss_is_related_to(gl, interface_language_code, default_language_code)

        related_objects = [get_default_annotationidglosstranslation(ro) for ro in transitive_related_objects(gl)]
        context['extended_related_objects'] = ', '.join(related_objects)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['dataset_choices'] = {}
            user = self.request.user
            if user.is_authenticated:
                qs = get_objects_for_user(user, ['view_dataset', 'can_view_dataset'], Dataset, accept_global_perms=True, any_perm=True)
                dataset_choices = {}
                for dataset in qs:
                    dataset_choices[dataset.acronym] = dataset.acronym
                context['dataset_choices'] = json.dumps(dataset_choices)

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)
        context['SHOW_LETTER_NUMBER_PHONOLOGY'] = getattr(settings, 'SHOW_LETTER_NUMBER_PHONOLOGY', False)
        context['USE_DERIVATIONHISTORY'] = getattr(settings, 'USE_DERIVATIONHISTORY', False)
        context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = getattr(settings, 'SHOW_QUERY_PARAMETERS_AS_BUTTON', False)

        gloss_is_duplicate = False
        annotationidglosstranslations = gl.annotationidglosstranslation_set.all()
        for annotation in annotationidglosstranslations:
            if "-duplicate" in annotation.text:
                gloss_is_duplicate = True
        context['gloss_is_duplicate'] = gloss_is_duplicate

        # Put nme video descriptions per language in the context
        glossnmevideos = GlossVideoNME.objects.filter(gloss=gl)
        nme_video_descriptions = dict()
        for nmevideo in glossnmevideos:
            nme_video_descriptions[nmevideo] = {}
            for language in gl.dataset.translation_languages.all():
                try:
                    description_text = GlossVideoDescription.objects.get(nmevideo=nmevideo, language=language).text
                except ObjectDoesNotExist:
                    description_text = ""
                nme_video_descriptions[nmevideo][language] = description_text
        context['nme_video_descriptions'] = nme_video_descriptions

        return context

    def post(self, request, *args, **kwargs):
        if request.method != "POST" or not request.POST or request.POST.get('use_default_query_parameters') != 'default_parameters':
            return redirect(settings.PREFIX_URL + '/dictionary/gloss/' + str(kwargs['pk']))
        # set up gloss details default parameters here
        default_parameters = request.POST.get('default_parameters')
        request.session['query_parameters'] = default_parameters
        request.session.modified = True
        return redirect(settings.PREFIX_URL + '/signs/search/?query')

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format') == 'Copy':
            return self.copy_gloss(context)
        elif self.request.GET.get('format') == 'Move':
            return self.move_gloss(context)
        else:
            return super(GlossDetailView, self).render_to_response(context, **response_kwargs)

    def copy_gloss(self, context):
        gl = context['gloss']
        context['active_id'] = gl.id

        annotationidglosstranslations = gl.annotationidglosstranslation_set.all()
        for annotation in annotationidglosstranslations:
            if "-duplicate" in annotation.text:
                # go back to the same page, this is already a duplicate
                return HttpResponseRedirect(settings.PREFIX_URL + '/dictionary/gloss/' + str(gl.id))

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
        user_affiliations = AffiliatedUser.objects.filter(user=self.request.user)
        if user_affiliations.count() > 0:
            for ua in user_affiliations:
                new_affiliation, created = AffiliatedGloss.objects.get_or_create(affiliation=ua.affiliation,
                                                                                 gloss=new_gloss)
        annotationidglosstranslations = gl.annotationidglosstranslation_set.all()
        for annotation in annotationidglosstranslations:
            new_annotation_text = annotation.text+'-duplicate'
            duplication_annotation = AnnotationIdglossTranslation(gloss=new_gloss, language=annotation.language, text=new_annotation_text)
            duplication_annotation.save()

        self.request.session['last_used_dataset'] = dataset.acronym

        return HttpResponseRedirect(settings.PREFIX_URL + '/dictionary/gloss/'+str(new_gloss.id) + '?edit')

    def move_gloss(self, context):
        gl = context['gloss']
        context['active_id'] = gl.id
        related_objects = transitive_related_objects(gl)

        user = self.request.user
        if not user.is_superuser:
            messages.add_message(self.request, messages.ERROR,
                                 _('You must be superuser to use the requested functionality.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/dictionary/gloss/' + str(gl.id))

        dataset_pk = self.request.GET.get('dataset')
        dataset = Dataset.objects.get(pk=dataset_pk)

        if not same_translation_languages(gl.lemma.dataset, dataset):
            messages.add_message(self.request, messages.ERROR,
                                 _('The target dataset has different translation languages.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/dictionary/gloss/' + str(gl.id))

        if gl.lemma.dataset != dataset:
            okay_to_move, feedback = okay_to_move_gloss(gl, dataset)
            if not okay_to_move:
                feedback_message = _('A similar gloss already exists in the target dataset: ') + ', '.join(feedback)

                messages.add_message(self.request, messages.ERROR, feedback_message)
                return HttpResponseRedirect(settings.PREFIX_URL + '/dictionary/gloss/' + str(gl.id))

        okay_to_move, feedback = okay_to_move_glosses(related_objects, dataset)
        if not okay_to_move:
            feedback_message = _('A related gloss already exists in the target dataset: ') + ', '.join(feedback)
            messages.add_message(self.request, messages.ERROR, feedback_message)
            return HttpResponseRedirect(settings.PREFIX_URL + '/dictionary/gloss/' + str(gl.id))

        gloss_lemma = gl.lemma
        try:
            with atomic():
                if gloss_lemma.dataset != dataset:
                    setattr(gloss_lemma, 'dataset', dataset)
                    gloss_lemma.save()
                for related_gloss in related_objects:
                    related_gloss_lemma = related_gloss.lemma
                    if related_gloss_lemma.dataset != dataset:
                        setattr(related_gloss_lemma, 'dataset', dataset)
                        related_gloss_lemma.save()
        except (ObjectDoesNotExist, PermissionDenied, PermissionError):
            messages.add_message(self.request, messages.ERROR,
                                 _('Error moving the gloss and related glosses to the requested dataset.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/dictionary/gloss/'+str(gl.id))

        self.request.session['last_used_dataset'] = dataset.acronym

        success_message = _('Gloss moved to dataset ') + dataset.acronym
        messages.add_message(self.request, messages.INFO, success_message)

        return HttpResponseRedirect(settings.PREFIX_URL + '/dictionary/gloss/'+str(gl.id))


class GlossVideosView(DetailView):

    model = Gloss
    context_object_name = 'gloss'
    last_used_dataset = None
    template_name = 'dictionary/gloss_videos.html'

    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested gloss does not exist.')
            return show_warning(request, translated_message, selected_datasets)

        if not self.object.lemma or not self.object.lemma.dataset:
            translated_message = _('Requested gloss has no lemma or dataset.')
            return show_warning(request, translated_message, selected_datasets)

        if not request.user.is_authenticated:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_gloss = self.object.lemma.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=True, any_perm=True)

        if dataset_of_requested_gloss not in selected_datasets:
            translated_message = _('The gloss you are trying to view is not in your selected datasets.')
            return show_warning(request, translated_message, selected_datasets)

        if dataset_of_requested_gloss not in datasets_user_can_view:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                translated_message = _('The gloss you are trying to view is not in a dataset you can view.')
                return show_warning(request, translated_message, selected_datasets)

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
        else:
            self.request.session['search_type'] = 'sign'

        # Call the base implementation first to get a context
        context = super(GlossVideosView, self).get_context_data(**kwargs)

        # Pass info about which fields we want to see
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

        context['senses'] = gl.senses.all().order_by('glosssense')

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        return context


class GlossRelationsDetailView(DetailView):
    model = Gloss
    template_name = 'dictionary/related_signs_detail_view.html'
    context_object_name = 'gloss'

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested gloss does not exist.')
            return show_warning(request, translated_message, selected_datasets)

        if not self.object.lemma or not self.object.lemma.dataset:
            translated_message = _('Requested gloss has no lemma or dataset.')
            return show_warning(request, translated_message, selected_datasets)

        if not request.user.is_authenticated:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_gloss = self.object.lemma.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=True, any_perm=True)

        if dataset_of_requested_gloss not in selected_datasets:
            translated_message = _('The gloss you are trying to view is not in your selected datasets.')
            return show_warning(request, translated_message, selected_datasets)

        if dataset_of_requested_gloss not in datasets_user_can_view:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                translated_message = _('The gloss you are trying to view is not in a dataset you can view.')
                return show_warning(request, translated_message, selected_datasets)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        # Call the base implementation first to get a context
        context = super(GlossRelationsDetailView, self).get_context_data(**kwargs)

        context['language'] = interface_language

        # Pass info about which fields we want to see
        gl = context['gloss']
        context['active_id'] = gl.id

        lemma_group = gl.lemma.gloss_set.all()
        if lemma_group.count() > 1:
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

        glosses_in_lemma_group = []
        if lemma_group:
            for gl_lem in lemma_group:
                # This display is set to the default language for the dataset of this gloss
                gl_lem_display = gl_lem.annotation_idgloss(gl_lem.lemma.dataset.default_language.language_code_2char)
                glosses_in_lemma_group.append((gl_lem, gl_lem_display))

        context['glosses_in_lemma_group'] = glosses_in_lemma_group

        otherrelations = []

        if gl.relation_sources:
            for oth_rel in gl.relation_sources.all():
                if oth_rel.source.id == oth_rel.target.id:
                    print('circular relation found: ', gl, ' (', str(gl.id), ') ', oth_rel, oth_rel.role)
                    continue
                # This display is set to the default language for the dataset of this gloss
                target_display = oth_rel.target.annotation_idgloss(oth_rel.target.lemma.dataset.default_language.language_code_2char)
                otherrelations.append((oth_rel, senses_per_language(oth_rel.target), target_display))

        context['otherrelations'] = otherrelations

        pattern_variant_glosses = gl.pattern_variants()
        # the pattern_variants method result includes the gloss itself
        pattern_variants = [v for v in pattern_variant_glosses if not v.id == gl.id]
        other_variants = gl.has_variants()

        all_variants = pattern_variants + [ov for ov in other_variants if ov not in pattern_variants]
        has_variants = all_variants
        variants = []
        for gl_var in has_variants:
            # This display is set to the default language for the dataset of the variant
            gl_var_display = gl_var.annotation_idgloss(gl_var.lemma.dataset.default_language.language_code_2char)
            variants.append((gl_var, senses_per_language(gl_var), gl_var_display))
        context['variants'] = variants

        minimal_pairs_dict = gl.minimal_pairs_dict()
        minimalpairs = []
        for mpg, dict in minimal_pairs_dict.items():
            # This display is set to the default language for the dataset of the minimal pair gloss
            minpar_display = mpg.annotation_idgloss(mpg.lemma.dataset.default_language.language_code_2char)
            minimalpairs.append((mpg, dict, minpar_display))
        context['minimalpairs'] = minimalpairs

        compounds = []
        reverse_morphdefs = gl.parent_glosses.all()
        for rm in reverse_morphdefs:
            parent_glosses = rm.parent_gloss.parent_glosses.all()
            parent_glosses_display = []
            for pg in parent_glosses:
                parent_glosses_display.append(get_default_annotationidglosstranslation(pg.morpheme))
            compounds.append((rm.morpheme, ' + '.join(parent_glosses_display)))
        context['compounds'] = compounds

        appearsin = []
        reverse_morphdefs = MorphologyDefinition.objects.filter(morpheme=gl)
        for rm in reverse_morphdefs:
            parent_glosses = rm.parent_gloss.parent_glosses.all()
            parent_glosses_display = []
            for pg in parent_glosses:
                parent_glosses_display.append(get_default_annotationidglosstranslation(pg.morpheme))
            appearsin.append((rm.parent_gloss, ' + '.join(parent_glosses_display)))
        context['appearsin'] = appearsin

        appearsinblend = []
        reverse_blends = BlendMorphology.objects.filter(glosses=gl)
        for rb in reverse_blends:
            parent_glosses = rb.parent_gloss.blend_morphology.all()
            parent_glosses_display = []
            for pg in parent_glosses:
                parent_glosses_display.append(get_default_annotationidglosstranslation(pg.glosses) + ': ' + pg.role)
            appearsinblend.append((rb.parent_gloss, ' + '.join(parent_glosses_display)))
        context['appearsinblend'] = appearsinblend

        blends = []
        reverse_blends = gl.blend_morphology.all()
        for rb in reverse_blends:
            parent_glosses = rb.parent_gloss.blend_morphology.all()
            parent_glosses_display = []
            for pg in parent_glosses:
                parent_glosses_display.append(get_default_annotationidglosstranslation(pg.glosses) + ': ' + pg.role)
            blends.append((rb.glosses, ' + '.join(parent_glosses_display)))
        context['blends'] = blends

        simultaneous_morphology = []
        for sim_morph in gl.simultaneous_morphology.all():
            morpheme_display = get_default_annotationidglosstranslation(sim_morph.morpheme)
            simultaneous_morphology.append((sim_morph, morpheme_display))
        context['simultaneous_morphology'] = simultaneous_morphology

        gloss_default_annotationidglosstranslation = gl.annotationidglosstranslation_set.get(language=default_language).text
        # Put annotation_idgloss per language in the context
        context['annotation_idgloss'] = {}
        for language in gl.dataset.translation_languages.all().order_by('id'):
            try:
                annotation_text = gl.annotationidglosstranslation_set.get(language=language).text
            except ObjectDoesNotExist:
                annotation_text = gloss_default_annotationidglosstranslation
            context['annotation_idgloss'][language] = annotation_text

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets).order_by('id')
        context['dataset_languages'] = dataset_languages

        context['sensetranslations_per_language'] = senses_per_language(gl)
        context['sensetranslations_per_language_dict'] = sensetranslations_per_language_dict(gl)

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)
        context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = getattr(settings, 'SHOW_QUERY_PARAMETERS_AS_BUTTON', False)

        return context


class MorphemeListView(ListView):
    """The morpheme list view basically copies the gloss list view"""

    model = Morpheme
    search_type = 'morpheme'
    show_all = False
    dataset_name = settings.DEFAULT_DATASET_ACRONYM
    last_used_dataset = None
    template_name = 'dictionary/admin_morpheme_list.html'
    paginate_by = 25
    queryset_language_codes = []
    search_form = MorphemeSearchForm()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # this is needed because the MorphemeSearchForm is initialized without the request and
        # the model translation language is unknown
        fields_with_choices = fields_to_fieldcategory_dict(settings.MORPHEME_CHOICE_FIELDS)
        set_up_fieldchoice_translations(self.search_form, fields_with_choices)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(MorphemeListView, self).get_context_data(**kwargs)

        set_up_language_fields(Morpheme, self, self.search_form)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        default_dataset = Dataset.objects.get(acronym=settings.DEFAULT_DATASET_ACRONYM)

        for lang in dataset_languages:
            if lang.language_code_2char not in self.queryset_language_codes:
                self.queryset_language_codes.append(lang.language_code_2char)
        if not self.queryset_language_codes:
            self.queryset_language_codes = [ default_dataset.default_language.language_code_2char ]

        if len(selected_datasets) == 1:
            self.last_used_dataset = selected_datasets[0].acronym
        elif 'last_used_dataset' in self.request.session.keys():
            self.last_used_dataset = self.request.session['last_used_dataset']

        context['last_used_dataset'] = self.last_used_dataset

        self.show_all = self.kwargs.get('show_all', self.show_all)
        context['show_all'] = self.show_all

        context['searchform'] = self.search_form

        # use these to fill the form fields of a just done query
        populate_keys, populate_fields = search_fields_from_get(self.search_form, self.request.GET)
        context['populate_fields'] = json.dumps(populate_fields)
        context['populate_fields_keys'] = json.dumps(populate_keys)

        context['glosscount'] = Morpheme.objects.filter(lemma__dataset__in=selected_datasets).count()

        self.request.session['search_type'] = self.search_type

        context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE
        context['add_morpheme_form'] = MorphemeCreateForm(self.request.GET, languages=dataset_languages, user=self.request.user, last_used_dataset=self.last_used_dataset)

        context['input_names_fields_and_labels'] = {}

        for topic in ['main', 'phonology', 'semantics']:
            context['input_names_fields_and_labels'][topic] = []
            for fieldname in settings.FIELDS[topic]:
                if fieldname not in self.search_form.fields:
                    continue
                context['input_names_fields_and_labels'][topic].append((fieldname,
                                                                        self.search_form[fieldname],
                                                                        self.search_form[fieldname].label))
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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

        fieldnames = FIELDS['main']+settings.MORPHEME_DISPLAY_FIELDS+FIELDS['semantics']+['inWeb', 'isNew', 'mrpType']
        if not settings.USE_DERIVATIONHISTORY and 'derivHist' in fieldnames:
            fieldnames.remove('derivHist')

        multiple_select_morpheme_categories = fields_to_fieldcategory_dict(fieldnames)
        multiple_select_morpheme_categories['definitionRole'] = 'NoteType'

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
            context['search_by_publication_fields'] = searchform_panels(self.search_form,
                                                                        settings.SEARCH_BY['morpheme_publication'])
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

        self.show_all = self.kwargs.get('show_all', self.show_all)
        setattr(self.request.session, 'search_type', self.search_type)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        valid_regex, search_fields, field_values = check_language_fields(self.search_form, MorphemeSearchForm, get, dataset_languages)

        if USE_REGULAR_EXPRESSIONS and not valid_regex:
            error_message_regular_expression(self.request, search_fields, field_values)
            qs = Morpheme.objects.none()
            return qs

        if len(get) > 0 or self.show_all:
            qs = Morpheme.objects.filter(lemma__dataset__in=selected_datasets)
        else:
            qs = Morpheme.objects.none()

        if not self.request.user.has_perm('dictionary.search_gloss'):
            qs = qs.filter(inWeb__exact=True)

        if self.show_all:
            qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)
            return qs

        qs = queryset_from_get(MorphemeSearchForm, self.search_form, get, qs)
        qs = qs.distinct()

        # Sort the queryset by the parameters given
        qs = order_queryset_by_sort_order(self.request.GET, qs, self.queryset_language_codes)

        self.request.session['search_type'] = 'morpheme'

        if 'last_used_dataset' not in self.request.session.keys():
            self.request.session['last_used_dataset'] = self.last_used_dataset

        # Return the resulting filtered and sorted queryset
        return qs

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format') == 'CSV':
            return self.render_to_csv_response()
        else:
            return super(MorphemeListView, self).render_to_response(context, **response_kwargs)

    def render_to_csv_response(self):
        """Convert all Morphemes into a CSV

        This function is derived from and similar to the one used in class GlossListView
        Differences:
        1 - this one adds the field [mrpType]
        2 - the filename is different"""

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        fieldnames = FIELDS['main']+settings.MORPHEME_DISPLAY_FIELDS+FIELDS['semantics']+FIELDS['frequency']+['inWeb', 'isNew']
        fields = [Morpheme.get_field(fname) for fname in fieldnames if fname in Morpheme.get_field_names()]

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        header = csv_header_row_morphemelist(dataset_languages, fields)
        csv_rows = [header]

        if self.object_list:
            query_set = self.object_list
        else:
            query_set = self.get_queryset()

        if isinstance(query_set, QuerySet):
            query_set = list(query_set)

        for morpheme in query_set:

            safe_row = csv_morpheme_to_row(morpheme, dataset_languages, fields)
            csv_rows.append(safe_row)

        # this is based on an example in the Django 4.2 documentation
        pseudo_buffer = Echo()
        new_writer = csv.writer(pseudo_buffer)
        return StreamingHttpResponse(
            (new_writer.writerow(row) for row in csv_rows),
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="dictionary-morph-export.csv"'},
        )


class HandshapeDetailView(DetailView):
    model = Handshape
    template_name = 'dictionary/handshape_detail.html'
    context_object_name = 'handshape'
    search_type = 'handshape'

    class Meta:
        verbose_name_plural = "Handshapes"
        ordering = ['machine_value']

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        match_machine_value = int(kwargs['pk'])
        try:
            # GET A HANDSHAPE OBJECT WITH THE REQUESTED MACHINE VALUE
            # see if Handshape object exists for this machine_value
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            # The handshape machine value does not exist as a Handshape
            translated_message = _('Handshape not configured.')
            return show_warning(request, translated_message, selected_datasets)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        context = super(HandshapeDetailView, self).get_context_data(**kwargs)

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
        for fname in Handshape.get_field_names():
            if fname in settings.FIELDS['handshape']:
                handshape_fields_lookup[fname] = Handshape.get_field(fname)

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        return context


class SemanticFieldDetailView(DetailView):
    model = SemanticField
    template_name = 'dictionary/semanticfield_detail.html'
    context_object_name = 'semanticfield'

    class Meta:
        ordering = ['name']

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        # Get the machine value in the URL
        match_machine_value = int(kwargs['pk'])
        try:
            self.object = SemanticField.objects.get(machine_value=match_machine_value)
        except ObjectDoesNotExist:
            # No SemanticField exists for this machine value
            translated_message = _('SemanticField not configured for this machine value.')
            return show_warning(request, translated_message, selected_datasets)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        context = super(SemanticFieldDetailView, self).get_context_data(**kwargs)

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        return context

    def get_queryset(self):

        qs = SemanticField.objects.filter(machine_value__gt=1).order_by('name')

        return qs


class DerivationHistoryDetailView(DetailView):
    model = DerivationHistory
    template_name = 'dictionary/derivationhistory_detail.html'
    context_object_name = 'derivationhistory'

    class Meta:
        ordering = ['name']

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        # Get the machine value in the URL
        match_machine_value = int(kwargs['pk'])
        try:
            self.object = DerivationHistory.objects.get(machine_value=match_machine_value)
        except ObjectDoesNotExist:
            # No DerivationHistory exists for this machine value
            translated_message = _('DerivationHistory not configured for this machine value.')
            return show_warning(request, translated_message, selected_datasets)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        context = super(DerivationHistoryDetailView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets

        context['translations'] = [ (translation.language.name, translation.name)
                                    for translation in self.object.derivationhistorytranslation_set.all() ]
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        return context

    def get_queryset(self):

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
            context['language'] = languages.first()
        else:
            context['language'] = Language.objects.get(id=get_default_language_id())

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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
    show_all = False
    search_form = FocusGlossSearchForm()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields_with_choices = fields_to_fieldcategory_dict(settings.MINIMAL_PAIRS_CHOICE_FIELDS)
        set_up_fieldchoice_translations(self.search_form, fields_with_choices)

    def get_context_data(self, **kwargs):
        context = super(MinimalPairsListView, self).get_context_data(**kwargs)

        set_up_language_fields(Gloss, self, self.search_form)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        if not selected_datasets or selected_datasets.count() > 1:
            feedback_message = _('Please select a single dataset to view minimal pairs.')
            messages.add_message(self.request, messages.ERROR, feedback_message)

        dataset = selected_datasets.first()
        context['dataset'] = dataset
        context['dataset_name'] = dataset.acronym
        self.request.session['last_used_dataset'] = dataset.acronym
        self.request.session.modified = True

        context['MINIMAL_PAIRS_CHOICE_FIELDS'] = MINIMAL_PAIRS_CHOICE_FIELDS

        context['searchform'] = self.search_form

        self.show_all = self.request.GET.get('show_all', self.show_all)
        context['show_all'] = self.show_all

        context['input_names_fields_and_labels'] = {}
        for topic in ['main', 'phonology', 'semantics']:
            context['input_names_fields_and_labels'][topic] = []
            for fieldname in settings.FIELDS[topic]:
                if fieldname in settings.MINIMAL_PAIRS_SEARCH_FIELDS:
                    field = self.search_form[fieldname]
                    label = field.label
                    context['input_names_fields_and_labels'][topic].append((fieldname, field, label))

        # pass these to the template to populate the search form with the search parameters
        # of a just done query
        populate_keys, populate_fields = search_fields_from_get(self.search_form, self.request.GET)
        context['gloss_fields_to_populate'] = json.dumps(populate_fields)
        context['gloss_fields_to_populate_keys'] = json.dumps(populate_keys)

        context['page_number'] = context['page_obj'].number

        context['objects_on_page'] = [g.id for g in context['page_obj'].object_list]

        context['paginate_by'] = self.request.GET.get('paginate_by', self.paginate_by)

        return context

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format') == 'CSV':
            return self.render_to_csv_response()
        else:
            return super(MinimalPairsListView, self).render_to_response(context, **response_kwargs)

    def render_to_csv_response(self):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        # this ends up being English for Global Signbank
        language_code = settings.DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset = selected_datasets.first()

        if self.object_list:
            query_set = self.object_list
        else:
            query_set = self.get_queryset()

        if isinstance(query_set, QuerySet):
            query_set = list(query_set)

        header = csv_header_row_minimalpairslist()
        csv_rows = [header]

        for focusgloss in query_set:
            # multiple rows are generated for each gloss, hence the csv_rows is passed as a state variable
            csv_rows = csv_focusgloss_to_minimalpairs(focusgloss, dataset, language_code, csv_rows)

        # this is based on an example in the Django 4.2 documentation
        pseudo_buffer = Echo()
        new_writer = csv.writer(pseudo_buffer)
        return StreamingHttpResponse(
            (new_writer.writerow(row) for row in csv_rows),
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="dictionary-export-minimalpairs.csv"'},
        )

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

        valid_regex, search_fields, field_values = check_language_fields(self.search_form, FocusGlossSearchForm, get, dataset_languages)

        if USE_REGULAR_EXPRESSIONS and not valid_regex:
            error_message_regular_expression(self.request, search_fields, field_values)
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
        empty_value = ['-', 'N/A']

        glosses_with_phonology = Gloss.none_morpheme_objects().select_related('lemma').filter(
                                        lemma__dataset__in=selected_datasets).exclude(
                                        id__in=finger_spelling_glosses)

        glosses_with_phonology = glosses_with_phonology.exclude(
                        (Q(**{handedness_null: True}))).exclude(
                        (Q(**{strong_hand_null: True}))).exclude(
                        (Q(**{handedness_filter: empty_value}))).exclude(
                        (Q(**{strong_hand_filter: empty_value}))).exclude(q_number_or_letter)

        if 'show_all_minimal_pairs' in get and get['show_all_minimal_pairs']:
            self.show_all = True
            return glosses_with_phonology

        if self.show_all:
            return glosses_with_phonology

        if not get or ('reset' in get and get['reset']):
            qs = Gloss.objects.none()
            return qs

        qs = glosses_with_phonology
        qs = queryset_glosssense_from_get('Gloss', FocusGlossSearchForm, self.search_form, get, qs)

        qs = qs.select_related('lemma')

        return qs


class QueryListView(ListView):
    # not sure what model should be used here, it applies to all the glosses in a dataset
    model = Dataset
    template_name = 'dictionary/admin_query_list.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(QueryListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)
        context['GLOSS_LIST_DISPLAY_FIELDS'] = getattr(settings, 'GLOSS_LIST_DISPLAY_FIELDS', [])

        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
        else:
            search_results = []
        if search_results and len(search_results) > 0:
            if self.request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape', 'sense']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []
        else:
            self.request.session['search_type'] = 'sign'

        (objects_on_page, object_list) = map_search_results_to_gloss_list(search_results)
        if 'query_parameters' in self.request.session.keys() and self.request.session['query_parameters'] not in ['', '{}']:
            # if the query parameters are available, convert them to a dictionary
            session_query_parameters = self.request.session.get('query_parameters', '{}')
            query_parameters = json.loads(session_query_parameters)
        else:
            # local query parameters
            query_parameters = {}
            # save the default query parameters to the sessin variable
            self.request.session['query_parameters'] = json.dumps(query_parameters)
            self.request.session.modified = True

        query_parameters_mapping = pretty_print_query_fields(dataset_languages, query_parameters.keys())

        query_parameters_values_mapping = pretty_print_query_values(dataset_languages, query_parameters)

        query_fields_focus, query_fields_parameters, \
            toggle_gloss_list_display_fields, toggle_query_parameter_fields, toggle_publication_fields = \
            query_parameters_toggle_fields(query_parameters)

        context['objects_on_page'] = objects_on_page
        context['object_list'] = object_list
        context['display_fields'] = settings.GLOSS_LIST_DISPLAY_FIELDS + query_fields_focus
        context['query_fields_parameters'] = query_fields_parameters
        context['TOGGLE_QUERY_PARAMETER_FIELDS'] = toggle_query_parameter_fields
        context['TOGGLE_PUBLICATION_FIELDS'] = toggle_publication_fields
        context['TOGGLE_GLOSS_LIST_DISPLAY_FIELDS'] = toggle_gloss_list_display_fields
        context['query_parameters'] = query_parameters
        context['query_parameters_mapping'] = query_parameters_mapping
        context['query_parameters_values_mapping'] = query_parameters_values_mapping
        context['query_parameter_keys'] = query_parameters.keys()

        available_parameters_to_save = available_query_parameters_in_search_history()
        context['available_query_parameters_in_search_history'] = available_parameters_to_save
        all_parameters_available_to_save = True
        for param in query_parameters.keys():
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
            if self.request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape', 'sense']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []
        else:
            self.request.session['search_type'] = 'sign'

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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
            if self.request.session['search_results'][0]['href_type'] not in ['gloss', 'morpheme', 'sense']:
                self.request.session['search_results'] = []
        if 'search_type' in self.request.session.keys():
            if self.request.session['search_type'] not in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape', 'sense']:
                # search_type is 'handshape'
                self.request.session['search_results'] = []
        else:
            self.request.session['search_type'] = 'sign'

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        context['dataset_ids'] = [ ds.id for ds in selected_datasets]

        # sort the phonology fields based on field label in the designated language
        # this is used for display in the template, by lookup
        field_labels = dict()
        for field in FIELDS['phonology']:
            if field in settings.HANDSHAPE_ETYMOLOGY_FIELDS + settings.HANDEDNESS_ARTICULATION_FIELDS:
                continue
            if field not in Gloss.get_field_names():
                continue
            if fieldname_to_kind(field) == 'list':
                field_label = Gloss.get_field(field).verbose_name
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
            gloss_field = Gloss.get_field(field)

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
                field_label = Gloss.get_field(field).verbose_name
                field_labels_semantics[field] = field_label.encode('utf-8').decode()

        field_labels_semantics_list = [ (k, v) for (k, v) in sorted(field_labels_semantics.items(), key=lambda x: x[1])]
        context['field_labels_semantics'] = field_labels_semantics
        context['field_labels_semantics_list'] = field_labels_semantics_list

        field_labels_semantics_choices = dict()
        for field, label in field_labels_semantics.items():
            gloss_field = Gloss.get_field(field)
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
        # (phonology fields, semantics fields) are displayed in the same table,
        # the lookup tables are merged so only one loop is needed

        context['all_field_labels'] = dict(field_labels, **field_labels_semantics)

        context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = getattr(settings, 'SHOW_QUERY_PARAMETERS_AS_BUTTON', False)

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

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested gloss does not exist.')
            return show_warning(request, translated_message, selected_datasets)

        if not self.object.lemma or not self.object.lemma.dataset:
            translated_message = _('Requested gloss has no lemma or dataset.')
            return show_warning(request, translated_message, selected_datasets)

        if not request.user.is_authenticated:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_gloss = self.object.lemma.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=True, any_perm=True)

        if dataset_of_requested_gloss not in selected_datasets:
            translated_message = _('The gloss you are trying to view is not in your selected datasets.')
            return show_warning(request, translated_message, selected_datasets)

        if dataset_of_requested_gloss not in datasets_user_can_view:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                translated_message = _('The gloss you are trying to view is not in a dataset you can view.')
                return show_warning(request, translated_message, selected_datasets)

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
        else:
            self.request.session['search_type'] = 'sign'

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)

        # Pass info about which fields we want to see
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
                                          Dataset, accept_global_perms=True, any_perm=True)
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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)
        context['SHOW_LETTER_NUMBER_PHONOLOGY'] = getattr(settings, 'SHOW_LETTER_NUMBER_PHONOLOGY', False)
        context['SHOW_QUERY_PARAMETERS_AS_BUTTON'] = getattr(settings, 'SHOW_QUERY_PARAMETERS_AS_BUTTON', False)

        gloss_default_annotationidglosstranslation = gl.annotationidglosstranslation_set.get(language=default_language).text
        # Put annotation_idgloss per language in the context
        context['annotation_idgloss'] = {}
        for language in gl.dataset.translation_languages.all():
            try:
                annotation_translation = gl.annotationidglosstranslation_set.get(language=language).text
            except ValueError:
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

        # Pass info about which fields we want to see
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
                                          Dataset, accept_global_perms=True, any_perm=True)
                dataset_choices = {}
                for dataset in qs:
                    dataset_choices[dataset.acronym] = dataset.acronym
                context['dataset_choices'] = json.dumps(dataset_choices)

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)
        context['SHOW_LETTER_NUMBER_PHONOLOGY'] = getattr(settings, 'SHOW_LETTER_NUMBER_PHONOLOGY', False)

        # Put annotation_idgloss per language in the context
        gloss_default_annotationidglosstranslation = gl.annotationidglosstranslation_set.get(language=default_language).text
        context['annotation_idgloss'] = {}
        for language in gl.dataset.translation_languages.all():
            try:
                annotation_text = gl.annotationidglosstranslation_set.get(language=language).text
            except ObjectDoesNotExist:
                annotation_text = gloss_default_annotationidglosstranslation
            context['annotation_idgloss'][language] = annotation_text
        if interface_language in context['annotation_idgloss'].keys():
            gloss_idgloss = context['annotation_idgloss'][interface_language]
        else:
            gloss_idgloss = context['annotation_idgloss'][default_language]
        context['gloss_idgloss'] = gloss_idgloss

        lemma_group = gl.lemma.gloss_set.all()
        if lemma_group.count() > 1:
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

        glosses_in_lemma_group = []
        total_occurrences = 0
        data_lemmas = []
        if lemma_group:
            for gl_lem in lemma_group:
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
                    # This should be set to the default language
                    # if the interface language hasn't been set for this gloss
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

        context['searchform'] = search_form

        self.search_type = self.request.GET.get('search_type', self.search_type)
        context['search_type'] = self.search_type
        setattr(self.request.session, 'search_type', self.search_type)
        context['show_all'] = self.kwargs.get('show_all', self.show_all)

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format') == 'CSV':
            return self.render_to_csv_response()
        else:
            return super(HandshapeListView, self).render_to_response(context, **response_kwargs)

    def render_to_csv_response(self):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        if self.object_list:
            query_set = self.object_list
        else:
            query_set = self.get_queryset()

        if isinstance(query_set, QuerySet):
            query_set = list(query_set)

        if query_set and self.request.session['search_type'] == 'sign_handshape':
            filename = "dictionary-export-handshapes-signs.csv"

            fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + FIELDS['frequency'] + ['inWeb',
                                                                                                             'isNew']
            fields = [Gloss.get_field(fname) for fname in fieldnames if fname in Gloss.get_field_names()]

            selected_datasets = get_selected_datasets_for_user(self.request.user)
            dataset_languages = get_dataset_languages(selected_datasets)

            header = csv_header_row_glosslist(dataset_languages, fields)
            csv_rows = [header]

            for gloss in query_set:
                safe_row = csv_gloss_to_row(gloss, dataset_languages, fields)
                csv_rows.append(safe_row)
        else:
            filename = "dictionary-export-handshapes.csv"

            fields = [Handshape.get_field(fieldname) for fieldname in settings.HANDSHAPE_RESULT_FIELDS]

            header = csv_header_row_handshapelist(fields)

            csv_rows = [header]
            for handshape in query_set:

                safe_row = csv_handshape_to_row(handshape, fields)
                csv_rows.append(safe_row)

        # this is based on an example in the Django 4.2 documentation
        pseudo_buffer = Echo()
        new_writer = csv.writer(pseudo_buffer)
        return StreamingHttpResponse(
            (new_writer.writerow(row) for row in csv_rows),
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename='+filename},
        )

    def get_queryset(self):

        handshape_fields = {}
        for fname in Handshape.get_field_names():
            handshape_fields[fname] = Handshape.get_field(fname)

        get = self.request.GET

        self.show_all = self.kwargs.get('show_all', self.show_all)
        self.search_type = self.request.GET.get('search_type', self.search_type)
        setattr(self.request.session, 'search_type', self.search_type)

        if not self.show_all and not get or 'reset' in get:
            qs = Handshape.objects.none()
            return qs

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        valid_regex, search_fields, field_values = check_multilingual_fields(Handshape, get, dataset_languages)

        if USE_REGULAR_EXPRESSIONS and not valid_regex:
            error_message_regular_expression(self.request, search_fields, field_values)
            qs = Handshape.objects.none()
            return qs

        qs = Handshape.objects.filter(machine_value__gt=1).order_by('machine_value')

        if self.show_all:
            if 'sortOrder' in get and get['sortOrder'] != 'machine_value':
                # User has toggled the sort order for the column
                qs = order_handshape_queryset_by_sort_order(self.request.GET, qs)
            else:
                # The default is to order the signs alphabetically by whether there is an angle bracket
                qs = order_handshape_by_angle(qs)
            return qs

        fieldnames = ['machine_value', 'name']+FIELDS['handshape']

        # phonology and semantics field filters
        for fieldname in fieldnames:
            field = handshape_fields[fieldname]
            if fieldname in get:
                val = get[fieldname]
                if fieldname == 'hsNumSel' and val:
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
                                                        output_field=IntegerField())).filter(Q(count_fs1__exact=5) | Q(**{query_hsNumSel:val}))

                if isinstance(Handshape.get_field(fieldname), BooleanField):
                    val = {'0': False, '1': True, 'True': True, 'False': False, 'None': '', '': ''}[val]

                if fieldname == 'name' and val:
                    query = Q(name__iregex=val)
                    qs = qs.filter(query)

                if val not in ['', '0', False] and fieldname not in ['hsNumSel', 'name']:
                    if isinstance(Handshape.get_field(fieldname), FieldChoiceForeignKey):
                        key = fieldname + '__machine_value'
                        kwargs = {key: int(val)}
                        qs = qs.filter(**kwargs)
                    else:
                        # is boolean
                        key = fieldname + '__exact'
                        kwargs = {key: val}
                        qs = qs.filter(**kwargs)

        if 'sortOrder' in get and get['sortOrder'] != 'machine_value':
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
    dataset_acronym = settings.DEFAULT_DATASET_ACRONYM


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

        nr_of_public_glosses, nr_of_glosses = {}, {}
        datasets_with_public_glosses = get_datasets_with_public_glosses()

        for ds in Dataset.objects.all():
            if self.request.user.is_authenticated or ds in datasets_with_public_glosses:
                glosses = Gloss.objects.filter(lemma__dataset=ds, morpheme=None)
                nr_of_glosses[ds] = glosses.count()
                nr_of_public_glosses[ds] = glosses.filter(inWeb=True).count()

        context['nr_of_public_glosses'] = nr_of_public_glosses
        context['nr_of_glosses'] = nr_of_glosses

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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
        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

        # if the dataset is specified in the url parameters, set the dataset_acronym variable
        get = self.request.GET
        if 'dataset_acronym' in get:
            self.dataset_acronym = get['dataset_acronym']
        if not self.dataset_acronym:
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

        try:
            dataset_object = Dataset.objects.get(acronym=self.dataset_acronym)
        except ObjectDoesNotExist:
            translated_message = _('No dataset found with that name.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

        # check that the dataset has an owner
        owners_of_dataset = dataset_object.owners.all()
        if len(owners_of_dataset) < 1:
            messages.add_message(self.request, messages.ERROR, _('Dataset must have at least one owner.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

        # make sure the user can write to this dataset
        from guardian.shortcuts import get_objects_for_user, assign_perm
        user_view_datasets = get_objects_for_user(self.request.user, ['view_dataset', 'can_view_dataset'],
                                                  Dataset, accept_global_perms=True, any_perm=True)
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
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

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
        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # if the dataset is specified in the url parameters, set the dataset_acronym variable
        get = self.request.GET
        if 'dataset_acronym' in get:
            self.dataset_acronym = get['dataset_acronym']
        if not self.dataset_acronym:
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        try:
            dataset_object = Dataset.objects.get(acronym=self.dataset_acronym)
        except ObjectDoesNotExist:
            translated_message = _('No dataset found with that acronym.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # make sure the user can write to this dataset
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = get_objects_for_user(self.request.user, 'change_dataset', Dataset, accept_global_perms=False)
        if not user_change_datasets or dataset_object not in user_change_datasets:
            messages.add_message(self.request, messages.ERROR, _('No permission to export dataset.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # make sure the dataset is non-empty, don't create an empty ecv file
        dataset_count = dataset_object.count_glosses()
        if not dataset_count:
            messages.add_message(self.request, messages.INFO, _('The dataset is empty, export ECV is not available.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # if we get to here, the user is authenticated and has permission to export the dataset
        ecv_file = write_ecv_file_for_dataset(self.dataset_acronym)

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
        if 'dataset_acronym' in get:
            self.dataset_acronym = get['dataset_acronym']
        # otherwise the default dataset_acronym DEFAULT_DATASET_ACRONYM is used

        # not sure what this accomplishes
        # setattr(self.request, 'dataset_acronym', self.dataset_acronym)

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
    dataset_acronym = settings.DEFAULT_DATASET_ACRONYM


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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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
        if not self.request.user.is_authenticated:
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
        if not user_change_datasets or dataset_object not in user_change_datasets:
            messages.add_message(self.request, messages.ERROR, _('No permission to modify dataset permissions.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        # Everything is alright
        return None

    def get_dataset_from_request(self):
        """
        Use the 'dataset_acronym' GET query string parameter to find a dataset object
        :return: tuple of a dataset object and HttpResponse in which either is None
        """
        # if the dataset is specified in the url parameters, set the dataset_acronym variable
        get = self.request.GET
        if 'dataset_acronym' in get:
            self.dataset_acronym = get['dataset_acronym']
        if self.dataset_acronym == '':
            messages.add_message(self.request, messages.ERROR, _('Dataset name must be non-empty.'))
            return None, HttpResponseRedirect(reverse('admin_dataset_manager'))

        try:
            return Dataset.objects.get(acronym=self.dataset_acronym), None
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

            except (PermissionError, SystemError, OSError):
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
            except (PermissionError, SystemError, OSError):
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
                    except (PermissionError, SystemError, OSError):
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
                    except (PermissionError, SystemError, OSError):
                        messages.add_message(self.request, messages.ERROR,
                                             _('Error revoking change dataset permission for user.'))

                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)
            else:
                messages.add_message(self.request, messages.ERROR, _('User currently has no permission to change this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)

        # the code doesn't seem to get here. if somebody puts something else in the url (else case),
        # there is no (hidden) csrf token.
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
                if annotationidglosstranslations.count() > 0:
                    row.append(annotationidglosstranslations.first().text)
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

            # Make it safe for weird chars
            safe_row = []
            for column in row:
                try:
                    safe_row.append(column.encode('utf-8').decode())
                except AttributeError:
                    safe_row.append("")

            writer.writerow(row)

        return response

    def get_queryset(self):
        user = self.request.user

        # get query terms from self.request
        get = self.request.GET

        # Then check what kind of stuff we want
        if 'dataset_acronym' in get:
            self.dataset_acronym = get['dataset_acronym']
        # otherwise the default dataset_acronym DEFAULT_DATASET_ACRONYM is used

        setattr(self.request, 'dataset_acronym', self.dataset_acronym)

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
    dataset_acronym = settings.DEFAULT_DATASET_ACRONYM

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested dataset does not exist.')
            return show_warning(request, translated_message, selected_datasets)

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        glosses = Gloss.objects.filter(lemma__dataset=dataset, morpheme=None)
        nr_of_glosses = glosses.count()
        nr_of_public_glosses = glosses.filter(inWeb=True).count()

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
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/' + dataset.acronym)
        else:
            self.request.session['requested_datasets'] = [dataset.name]
            return HttpResponseRedirect(settings.PREFIX_URL + '/accounts/register/')

    def render_to_add_owner_response(self, context):

        # check that the user is logged in
        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR, _('Please login to use this functionality.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

        # check if the user can manage this dataset
        from django.contrib.auth.models import Group, User

        try:
            group_manager = Group.objects.get(name='Dataset_Manager')
        except ObjectDoesNotExist:
            messages.add_message(self.request, messages.ERROR, _('No group Dataset_Manager found.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

        groups_of_user = self.request.user.groups.all()
        if group_manager not in groups_of_user:
            messages.add_message(self.request, messages.ERROR, _('You must be in group Dataset Manager to modify dataset permissions.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

        get = self.request.GET
        username = ''
        if 'username' in get:
            username = get['username']
        if username == '':
            messages.add_message(self.request, messages.ERROR, _('Username must be non-empty.'))
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

        try:
            user_object = User.objects.get(username=username)
        except ObjectDoesNotExist:
            translated_message = _('No user with that username found.')
            messages.add_message(self.request, messages.ERROR, translated_message)
            return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

        # if we get to here, we have a dataset object and a user object to add as an owner of the dataset
        dataset_object = self.object
        dataset_object.owners.add(user_object)
        dataset_object.save()

        messages.add_message(self.request, messages.INFO,
                     _('User successfully made (co-)owner of this dataset.'))

        return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/' + dataset_object.acronym)


def dataset_detail_view_by_acronym(request, acronym):
    if request.method == 'GET':
        dataset = get_object_or_404(Dataset, acronym=acronym)
        return DatasetDetailView.as_view()(request, pk=dataset.pk)
    raise Http404()


class DatasetMediaView(DetailView):
    model = Dataset
    context_object_name = 'dataset'
    template_name = 'dictionary/dataset_media_manager.html'

    # set the default dataset, this should not be empty
    dataset_acronym = settings.DEFAULT_DATASET_ACRONYM

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested dataset does not exist.')
            return show_warning(request, translated_message, selected_datasets)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DatasetMediaView, self).get_context_data(**kwargs)

        dataset = context['dataset']

        zippedvideosform = ZippedVideosForm()
        context['zippedvideosform'] = zippedvideosform

        uploaded_video_files = listing_uploaded_videos(dataset)
        context['uploaded_video_files'] = uploaded_video_files

        zipped_archives = uploaded_zip_archives(dataset)
        context['zipped_archives'] = zipped_archives

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        glosses = Gloss.objects.filter(lemma__dataset=dataset, morpheme=None)
        nr_of_glosses = glosses.count()
        nr_of_public_glosses = glosses.filter(inWeb=True).count()

        context['nr_of_glosses'] = nr_of_glosses
        context['nr_of_public_glosses'] = nr_of_public_glosses

        context['messages'] = messages.get_messages(self.request)

        return context


class DatasetFieldChoiceView(ListView):
    model = Dataset
    template_name = 'dictionary/dataset_field_choices.html'

    # set the default dataset, this should not be empty
    dataset_acronym = settings.DEFAULT_DATASET_ACRONYM

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DatasetFieldChoiceView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        managed_datasets = []
        change_dataset_permission = get_objects_for_user(self.request.user, 'change_dataset', Dataset)
        for dataset in selected_datasets:
            if dataset in change_dataset_permission:
                dataset_excluded_choices = dataset.exclude_choices.all()
                list_of_excluded_ids = []
                for ec in dataset_excluded_choices:
                    list_of_excluded_ids.append(ec.pk)
                managed_datasets.append((dataset, list_of_excluded_ids))

        context['datasets'] = managed_datasets

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)
        context['SHOW_FIELD_CHOICE_COLORS'] = getattr(settings, 'SHOW_FIELD_CHOICE_COLORS', False)

        gloss_fields = [Gloss.get_field(fname) for fname in Gloss.get_field_names()]

        all_choice_lists = {}
        for topic in ['main', 'phonology', 'semantics', 'frequency']:

            fields_with_choices = [(field, field.field_choice_category) for field in gloss_fields
                                   if field.name in FIELDS[topic] and hasattr(field, 'field_choice_category')
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
                if machine_value_string not in ['_0', '_1']:
                    mvid, mvv = machine_value_string.split('_')
                    machine_value = int(mvv)

                    try:
                        field_choice_object = FieldChoice.objects.get(field=field_choice_category,
                                                                      machine_value=machine_value)
                    except (ObjectDoesNotExist, MultipleObjectsReturned):
                        try:
                            field_choice_object = \
                            FieldChoice.objects.filter(field=field_choice_category, machine_value=machine_value).first()
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
        if 'dataset_acronym' in get:
            self.dataset_acronym = get['dataset_acronym']
        # otherwise the default dataset_acronym DEFAULT_DATASET_ACRONYM is used

        setattr(self.request, 'dataset_acronym', self.dataset_acronym)

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
    dataset_acronym = settings.DEFAULT_DATASET_ACRONYM

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(FieldChoiceView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        user_object = self.request.user

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)
        context['SHOW_FIELD_CHOICE_COLORS'] = getattr(settings, 'SHOW_FIELD_CHOICE_COLORS', False)

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

    # Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested dataset does not exist.')
            return show_warning(request, translated_message, selected_datasets)

        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('registration:login'))

        dataset = self.object
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=True, any_perm=True)

        if dataset not in datasets_user_can_view:
            translated_message = _('You do not have permission to view this corpus.')
            return show_warning(request, translated_message, selected_datasets)

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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
    if 'sortOrder' in get and get['sortOrder']:
        # Take the user-indicated sort order
        sort_order = get['sortOrder']

    reverse = False
    if sort_order[0] == '-':
        # A starting '-' sign means: descending order
        sort_order = sort_order[1:]
        reverse = True

    if hasattr(Handshape.get_field(sort_order), 'field_choice_category'):
        # The Handshape field is a FK to a FieldChoice
        field_choice_category = Handshape.get_field(sort_order).field_choice_category
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
        selected_datasets = get_selected_datasets_for_user(self.request.user)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested morpheme does not exist.')
            return show_warning(request, translated_message, selected_datasets)

        if not self.object.lemma or not self.object.lemma.dataset:
            translated_message = _('Requested morpheme has no lemma or dataset.')
            return show_warning(request, translated_message, selected_datasets)

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
            return show_warning(request, translated_message, selected_datasets)

        if dataset_of_requested_morpheme not in datasets_user_can_view:
            translated_message = _('The morpheme you are trying to view is not in a dataset you can view.')
            return show_warning(request, translated_message, selected_datasets)

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

        (interface_language, interface_language_code,
         default_language, default_language_code) = get_interface_language_and_default_language_codes(self.request)
        languages = self.object.lemma.dataset.translation_languages.all()

        # Call the base implementation first to get a context
        context = super(MorphemeDetailView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['tagform'] = TagUpdateForm()
        context['videoform'] = VideoUploadForObjectForm(languages=languages)
        context['imageform'] = ImageUploadForGlossForm()
        context['definitionform'] = DefinitionForm()
        context['relationform'] = RelationForm()
        context['othermediaform'] = OtherMediaForm()

        # Get the set of all the Gloss signs that point to me
        other_glosses_that_point_to_morpheme = SimultaneousMorphologyDefinition.objects.filter(morpheme_id__exact=context['morpheme'].id)
        context['appears_in'] = []
        for sim_morph in other_glosses_that_point_to_morpheme:
            parent_gloss = sim_morph.parent_gloss
            translated_word_class = parent_gloss.wordClass.name if parent_gloss.wordClass else '-'
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
            gloss_field = Morpheme.get_field(field)

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
        notes = context['morpheme'].definition_set.all()
        notes_groupedby_role = {}
        for note in notes:
            translated_note_role = note.role.name if note.role else '-'
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

        default_language = Language.objects.get(id=get_default_language_id())
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
            except ObjectDoesNotExist:
                annotation_text = gloss_default_annotationidglosstranslation
            context['annotation_idgloss'][language] = annotation_text

        translated_morph_type = gl.mrpType.name if gl.mrpType else '-'

        context['morpheme_type'] = translated_morph_type

        context['related_objects'] = morpheme_is_related_to(gl, interface_language_code, default_language_code)

        gloss_semanticfields = []
        for sf in gl.semField.all():
            gloss_semanticfields.append(sf)

        context['gloss_semanticfields'] = gloss_semanticfields

        gloss_derivationhistory = []
        for sf in gl.derivHist.all():
            gloss_derivationhistory.append(sf)

        context['gloss_derivationhistory'] = gloss_derivationhistory

        # morphemes keep using keywords, not senses
        # Put translations (keywords) per language in the context
        context['translations_per_language'] = {}
        if gl.dataset:
            for language in gl.dataset.translation_languages.all():
                context['translations_per_language'][language] = gl.translation_set.filter(language=language).order_by('index')
        else:
            language = Language.objects.get(id=get_default_language_id())
            context['translations_per_language'][language] = gl.translation_set.filter(language=language).order_by('index')

        context['separate_english_idgloss_field'] = SEPARATE_ENGLISH_IDGLOSS_FIELD

        bad_dialect = False
        morpheme_dialects = []

        # this is needed to catch legacy code
        gloss_signlanguage = gl.lemma.dataset.signlanguage if gl.lemma and gl.lemma.dataset else None

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

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)
        context['MORPHEME_DISPLAY_FIELDS'] = getattr(settings, 'MORPHEME_DISPLAY_FIELDS', [])
        context['USE_DERIVATIONHISTORY'] = getattr(settings, 'USE_DERIVATIONHISTORY', False)

        context['default_dataset_lang'] = dataset_languages.first().language_code_2char if dataset_languages else LANGUAGE_CODE
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix
        return context

def gloss_ajax_search_results(request):
    """Returns a JSON list of glosses that match the previous search stored in sessions"""
    if 'search_type' in request.session.keys() and 'search_results' in request.session.keys() \
            and request.session['search_type'] in ['sign', 'morpheme', 'sign_or_morpheme', 'sign_handshape', 'sense']:
        return JsonResponse(request.session['search_results'], safe=False)
    else:
        return JsonResponse([], safe=False)

def handshape_ajax_search_results(request):
    """Returns a JSON list of handshapes that match the previous search stored in sessions"""
    if 'search_type' in request.session.keys() and 'search_results' in request.session.keys() \
            and request.session['search_type'] == 'handshape':
        return JsonResponse(request.session['search_results'], safe=False)
    else:
        return JsonResponse([], safe=False)

def lemma_ajax_search_results(request):
    """Returns a JSON list of lemmas that match the previous search stored in sessions"""
    if 'search_type' in request.session.keys() and 'search_results' in request.session.keys() \
            and request.session['search_type'] == 'lemma':
        return JsonResponse(request.session['search_results'], safe=False)
    else:
        return JsonResponse([], safe=False)

def gloss_ajax_complete(request, prefix):
    """Return a list of glosses matching the search term
    as a JSON structure suitable for typeahead."""

    if 'datasetid' in request.session.keys():
        datasetid = request.session['datasetid']
    else:
        datasetid = settings.DEFAULT_DATASET_PK
    dataset = Dataset.objects.get(id=datasetid)
    default_language = dataset.default_language

    if request.LANGUAGE_CODE in dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR).keys():
        interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[request.LANGUAGE_CODE]
    else:
        # this assumes the default language (settings.LANGUAGE_CODE) in included in the LANGUAGES_LANGUAGE_CODE_3CHAR setting
        interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[settings.LANGUAGE_CODE]
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
            result.append({'annotation_idgloss': default_annotationidglosstranslation, 'idgloss': g.idgloss, 'sn': g.sn, 'pk': "%s" % g.id})

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

    if 'datasetid' in request.session.keys():
        datasetid = request.session['datasetid']
    else:
        datasetid = settings.DEFAULT_DATASET_PK
    dataset = Dataset.objects.get(id=datasetid)

    # the following query retrieves morphemes with annotations that match the prefix
    query = Q(lemma__dataset=dataset, annotationidglosstranslation__text__istartswith=prefix)
    qs = Morpheme.objects.filter(query).distinct()

    result = []
    for g in qs:
        annotationidglosstranslations = g.annotationidglosstranslation_set.all()
        if not annotationidglosstranslations:
            continue
        # if there are results, just grab the first one
        default_annotationidglosstranslation = annotationidglosstranslations.first().text
        result.append({'annotation_idgloss': default_annotationidglosstranslation, 'idgloss': g.idgloss,
                       'pk': "%s" % g.id})

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
    if language_code in dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR).keys():
        interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[language_code]
    else:
        # this assumes the default language (settings.LANGUAGE_CODE) in included in the LANGUAGES_LANGUAGE_CODE_3CHAR setting
        interface_language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[settings.LANGUAGE_CODE]
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

def sensetranslation_ajax_complete(request, dataset_id, language_code, q):

    # Only suggest if at least three characters are provided in the query
    if len(q)<1:
        return JsonResponse({}, safe=False)
    
    # check that the user is logged in
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, _('Please login to use this functionality.'))
        return HttpResponseRedirect(settings.PREFIX_URL + '/datasets/available')

    # the following code allows for specifying a language for the dataset in the add_gloss.html template

    # ideally, filter the results by language, but this is not implemented at the moment
    # language_3char = dict(settings.LANGUAGES_LANGUAGE_CODE_3CHAR)[language_code]
    # language = Language.objects.get(language_code_3char=interface_language_3char)

    dataset = Dataset.objects.get(id=dataset_id)

    sensetranslations = SenseTranslation.objects.filter(sense__glosssense__gloss__lemma__dataset = dataset, translations__translation__text__icontains=q).order_by('translations')
    sensetranslations_dict_list = []
    for sensetranslation in set(sensetranslations):
        trans_dict = {}
        for translation in sensetranslation.translations.all():
            trans_dict['pk'] = sensetranslation.pk
            trans_dict['language'] = str(sensetranslation.language)
            trans_dict['sensetranslation'] = sensetranslation.get_translations_return()
            # Only sugges a sensetranslation (text) once
            if not any(d['sensetranslation'] == trans_dict['sensetranslation'] for d in sensetranslations_dict_list):
                sensetranslations_dict_list.append(trans_dict)
    sorted_sensetranslations_dict = sorted(sensetranslations_dict_list, key=lambda x : len(x['sensetranslation']))
    return JsonResponse(sorted_sensetranslations_dict, safe=False)

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
        gloss_detail = request.GET['gloss_detail'] == 'true'
    language_code = request.LANGUAGE_CODE

    if language_code == "zh-hans":
        language_code = "zh"

    this_gloss = Gloss.objects.get(id=gloss_id)
    try:
        minimalpairs_objects = this_gloss.minimal_pairs_dict()
    except Exception as e:
        print(e)
        minimalpairs_objects = {}

    if gloss_detail:
        # if we are in gloss detail view or relations view, only show minimal pairs in
        # primary language of dataset
        language_code = this_gloss.lemma.dataset.default_language.language_code_2char
        caller_url = 'dictionary/minimalpairs_gloss_table.html'
    else:
        caller_url = 'dictionary/minimalpairs_row.html'

    translation_focus_gloss = str(this_gloss.id)
    translations_this_gloss = this_gloss.annotationidglosstranslation_set.filter(language__language_code_2char=language_code)
    if translations_this_gloss:
        translation_focus_gloss = translations_this_gloss.first().text
    else:
        translations_this_gloss = this_gloss.annotationidglosstranslation_set.filter(language__language_code_3char='eng')
        if translations_this_gloss:
            translation_focus_gloss = translations_this_gloss.first().text

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

            if not focus_gloss_choice:
                focus_gloss_choice = ''
            if not other_gloss_choice:
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

        translation = str(minimalpairs_object.id)
        translations = minimalpairs_object.annotationidglosstranslation_set.filter(language__language_code_2char=language_code)
        if translations:
            translation = translations.first().text
        else:
            translations = minimalpairs_object.annotationidglosstranslation_set.filter(language__language_code_3char='eng')
            if translations:
                translation = translations.first().text

        other_gloss_dict['other_gloss_idgloss'] = translation
        result.append(other_gloss_dict)

    SHOW_DATASET_INTERFACE_OPTIONS = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
    USE_REGULAR_EXPRESSIONS = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

    return render(request, caller_url, {'focus_gloss': this_gloss,
                                        'focus_gloss_translation': translation_focus_gloss,
                                        'USE_REGULAR_EXPRESSIONS': USE_REGULAR_EXPRESSIONS,
                                        'SHOW_DATASET_INTERFACE_OPTIONS': SHOW_DATASET_INTERFACE_OPTIONS,
                                        'minimal_pairs_dict': result})


def glosslist_ajax_complete(request, gloss_id):

    display_fields = settings.GLOSS_LIST_DISPLAY_FIELDS
    query_fields_parameters = []

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' and request.method == 'GET':
        if 'query' in request.GET and 'display_fields' in request.GET and 'query_fields_parameters' in request.GET:
            display_fields = json.loads(request.GET['display_fields'])
            query_fields_parameters = json.loads(request.GET['query_fields_parameters'])

    this_gloss = Gloss.objects.get(id=gloss_id)
    default_language = this_gloss.lemma.dataset.default_language.language_code_2char

    # TO DO could use the following method to generate the column values
    # but the domain of that method is the column header
    # gloss_data = this_gloss.get_fields_dict(display_fields)
    # list_gloss_data = list(gloss_data)
    # print(list_gloss_data)

    SHOW_DATASET_INTERFACE_OPTIONS = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
    USE_REGULAR_EXPRESSIONS = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = get_dataset_languages(selected_datasets)

    sensetranslations_per_language = sensetranslations_per_language_dict(this_gloss)

    column_values = []
    for fieldname in display_fields:
        if fieldname in ['semField', 'derivHist', 'dialect', 'signlanguage',
                         'definitionRole', 'hasothermedia', 'hasComponentOfType',
                         'mrpType', 'isablend', 'ispartofablend', 'morpheme', 'relation',
                         'hasRelationToForeignSign', 'relationToForeignSign']:
            display_method = 'get_' + fieldname + '_display'
            field_value = getattr(this_gloss, display_method)()
            column_values.append((fieldname, field_value))
        elif fieldname == 'hasRelation':
            # this field has a list of roles as a parameter
            if query_fields_parameters:
                # query_fields_parameters ends up being a list of list for this field
                field_paramters = query_fields_parameters[0]
                relations_of_type = [r for r in this_gloss.relation_sources.all() if r.role in field_paramters]
                relations = ", ".join([r.target.annotation_idgloss(default_language) for r in relations_of_type])
                column_values.append((fieldname, relations))
        elif fieldname not in Gloss.get_field_names():
            continue
        else:
            machine_value = getattr(this_gloss, fieldname)
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

    return render(request, 'dictionary/gloss_row.html',
                  {'focus_gloss': this_gloss,
                   'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'width_senses_columns': len(dataset_languages),
                   'width_gloss_columns': len(dataset_languages),
                   'width_lemma_columns': len(dataset_languages),
                   'sensetranslations_per_language': sensetranslations_per_language,
                   'column_values': column_values,
                   'USE_REGULAR_EXPRESSIONS': USE_REGULAR_EXPRESSIONS,
                   'SHOW_DATASET_INTERFACE_OPTIONS': SHOW_DATASET_INTERFACE_OPTIONS})


def glosslistheader_ajax(request):

    display_fields = settings.GLOSS_LIST_DISPLAY_FIELDS
    query_fields_parameters = []

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' and request.method == 'GET':
        if 'query' in request.GET and 'display_fields' in request.GET and 'query_fields_parameters' in request.GET:
            display_fields = json.loads(request.GET['display_fields'])
            query_fields_parameters = json.loads(request.GET['query_fields_parameters'])

    SHOW_DATASET_INTERFACE_OPTIONS = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
    USE_REGULAR_EXPRESSIONS = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = get_dataset_languages(selected_datasets)

    fieldname_to_column_header = {'dialect': _("Dialect"),
                                  'signlanguage': _("Sign Language"),
                                  'definitionRole': _("Note Type"),
                                  'hasothermedia': _("Other Media"),
                                  'hasComponentOfType': _("Sequential Morphology"),
                                  'morpheme': _("Simultaneous Morphology"),
                                  'isablend': _("Blend"),
                                  'ispartofablend': _("Part of Blend"),
                                  'mrpType': _("Morpheme Type"),
                                  'relation': _("Gloss of Related Sign"),
                                  'hasRelationToForeignSign': _("Related to Foreign Sign"),
                                  'relationToForeignSign': _("Gloss of Foreign Sign")
                                  }

    column_headers = []
    for fieldname in display_fields:
        if fieldname in fieldname_to_column_header.keys():
            column_headers.append((fieldname, fieldname_to_column_header[fieldname]))
        elif fieldname == 'hasRelation':
            fields_parameters = query_fields_parameters[0]
            field_parameters = ', '.join([field_param.capitalize() for field_param in fields_parameters])
            if len(fields_parameters) == 1:
                column_headers.append((fieldname, field_parameters))
            else:
                column_headers.append((fieldname, _("Relation: ") + field_parameters))
        elif fieldname not in Gloss.get_field_names():
            continue
        else:
            field_label = Gloss.get_field(fieldname).verbose_name
            column_headers.append((fieldname, field_label))

    sortOrder = ''
    if 'HTTP_REFERER' in request.META.keys():
        sortOrderURL = request.META['HTTP_REFERER']
        sortOrderParameters = sortOrderURL.split('&sortOrder=')
        if len(sortOrderParameters) > 1:
            sortOrder = sortOrderParameters[1].split('&')[0]

    return render(request, 'dictionary/glosslist_headerrow.html',
                  {'dataset_languages': dataset_languages,
                   'selected_datasets': selected_datasets,
                   'width_senses_columns': len(dataset_languages),
                   'width_gloss_columns': len(dataset_languages),
                   'width_lemma_columns': len(dataset_languages),
                   'column_headers': column_headers,
                   'sortOrder': str(sortOrder),
                   'USE_REGULAR_EXPRESSIONS': USE_REGULAR_EXPRESSIONS,
                   'SHOW_DATASET_INTERFACE_OPTIONS': SHOW_DATASET_INTERFACE_OPTIONS})


def senselist_ajax_complete(request, sense_id):

    this_sense = Sense.objects.get(id=sense_id)
    this_gloss = GlossSense.objects.filter(sense=this_sense).first().gloss
    sense_order = str(GlossSense.objects.filter(sense=this_sense).first().order)

    SHOW_DATASET_INTERFACE_OPTIONS = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
    USE_REGULAR_EXPRESSIONS = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = get_dataset_languages(selected_datasets)

    sensetranslations_per_language = senses_translations_per_language_list(this_sense)

    sentences_per_language = senses_sentences_per_language_list(this_sense)

    return render(request, 'dictionary/sense_row.html', { 'focus_sense': this_sense,
                                                          'focus_gloss': this_gloss,
                                                          'dataset_languages': dataset_languages,
                                                          'width_senses_columns': len(dataset_languages)+1,
                                                          'width_gloss_columns': len(dataset_languages),
                                                          'width_sentences_columns': len(dataset_languages)+2,
                                                          'sense_order': sense_order,
                                                          'selected_datasets': selected_datasets,
                                                          'sensetranslations_per_language': sensetranslations_per_language,
                                                          'sentences_per_language': sentences_per_language,
                                                          'USE_REGULAR_EXPRESSIONS': USE_REGULAR_EXPRESSIONS,
                                                          'SHOW_DATASET_INTERFACE_OPTIONS': SHOW_DATASET_INTERFACE_OPTIONS })


def senselistheader_ajax(request):

    display_fields = settings.GLOSS_LIST_DISPLAY_FIELDS
    query_fields_parameters = []

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' and request.method == 'GET':
        if 'query' in request.GET and 'display_fields' in request.GET and 'query_fields_parameters' in request.GET:
            display_fields = json.loads(request.GET['display_fields'])
            query_fields_parameters = json.loads(request.GET['query_fields_parameters'])

    SHOW_DATASET_INTERFACE_OPTIONS = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
    USE_REGULAR_EXPRESSIONS = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = get_dataset_languages(selected_datasets)

    fieldname_to_column_header = {'dialect': _("Dialect"),
                                  'signlanguage': _("Sign Language"),
                                  'definitionRole': _("Note Type"),
                                  'hasothermedia': _("Other Media"),
                                  'hasComponentOfType': _("Sequential Morphology"),
                                  'morpheme': _("Simultaneous Morphology"),
                                  'isablend': _("Is a Blend"),
                                  'ispartofablend': _("Is Part of a Blend"),
                                  'mrpType': _("Morpheme Type"),
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
        elif fieldname not in Gloss.get_field_names():
            continue
        else:
            field_label = Gloss.get_field(fieldname).verbose_name
            column_headers.append((fieldname, field_label))

    sortOrder = ''

    if 'HTTP_REFERER' in request.META.keys():
        sortOrderURL = request.META['HTTP_REFERER']
        sortOrderParameters = sortOrderURL.split('&sortOrder=')
        if len(sortOrderParameters) > 1:
            sortOrder = sortOrderParameters[1].split('&')[0]

    return render(request, 'dictionary/senselist_headerrow.html', { 'dataset_languages': dataset_languages,
                                                                    'width_senses_columns': len(dataset_languages)+1,
                                                                    'width_gloss_columns': len(dataset_languages),
                                                                    'width_sentences_columns': len(dataset_languages)+2,
                                                                    'selected_datasets': selected_datasets,
                                                                    'column_headers': column_headers,
                                                                    'sortOrder': str(sortOrder),
                                                                    'USE_REGULAR_EXPRESSIONS': USE_REGULAR_EXPRESSIONS,
                                                                    'SHOW_DATASET_INTERFACE_OPTIONS': SHOW_DATASET_INTERFACE_OPTIONS })


def lemmaglosslist_ajax_complete(request, gloss_id):

    this_gloss = Gloss.objects.get(id=gloss_id)

    SHOW_DATASET_INTERFACE_OPTIONS = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
    USE_REGULAR_EXPRESSIONS = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

    selected_datasets = get_selected_datasets_for_user(request.user)
    dataset_languages = get_dataset_languages(selected_datasets)

    sensetranslations_per_language = senses_per_language_list(this_gloss)

    column_values = []
    gloss_list_display_fields = settings.GLOSS_LIST_DISPLAY_FIELDS
    for fieldname in gloss_list_display_fields:

        machine_value = getattr(this_gloss, fieldname)

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

    return render(request, 'dictionary/lemma_gloss_row.html',
                  {'focus_gloss': this_gloss,
                   'dataset_languages': dataset_languages,
                   'sensetranslations_per_language': sensetranslations_per_language,
                   'column_values': column_values,
                   'USE_REGULAR_EXPRESSIONS': USE_REGULAR_EXPRESSIONS,
                   'SHOW_DATASET_INTERFACE_OPTIONS': SHOW_DATASET_INTERFACE_OPTIONS})


class LemmaListView(ListView):
    model = LemmaIdgloss
    template_name = 'dictionary/admin_lemma_list.html'
    paginate_by = 100
    show_all = False
    search_type = 'lemma'
    search_form = LemmaSearchForm()

    def __int__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)

    def get_queryset(self, **kwargs):

        get = self.request.GET

        page_number = self.request.GET.get("page", 1)

        # this view accommodates both Show All Lemmas and Lemma Search
        # the show_all argument is True for Show All Lemmas
        # if it is missing, a Lemma Search is being done and starts with no results
        self.show_all = self.kwargs.get('show_all', False)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        valid_regex, search_fields, field_values = check_language_fields(self.search_form, LemmaSearchForm, get, dataset_languages)

        if USE_REGULAR_EXPRESSIONS and not valid_regex:
            error_message_regular_expression(self.request, search_fields, field_values)
            qs = LemmaIdgloss.objects.none()
            return qs

        qs = LemmaIdgloss.objects.filter(dataset__in=selected_datasets).order_by('id')

        if 'show_all_lemmas' in get and get['show_all_lemmas']:
            self.show_all = True
            return qs

        if self.show_all:
            return qs

        if not self.show_all and not get:
            qs = LemmaIdgloss.objects.none()
            return qs

        if 'reset' in get and get['reset']:
            qs = LemmaIdgloss.objects.none()
            return qs

        # There are only Lemma ID Gloss fields
        for get_key, get_value in get.items():
            if get_key.startswith(LemmaSearchForm.lemma_search_field_prefix) and get_value:
                language_code_2char = get_key[len(LemmaSearchForm.lemma_search_field_prefix):]
                language = Language.objects.get(language_code_2char=language_code_2char)
                qs = qs.filter(lemmaidglosstranslation__text__icontains=get_value,
                               lemmaidglosstranslation__language=language)

        if len(get) == 0:
            return qs

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
        elif only_show_has_glosses and not only_show_no_glosses:
            results = results.filter(num_gloss__gt=0)

        return results

    def get_context_data(self, **kwargs):
        context = super(LemmaListView, self).get_context_data(**kwargs)

        set_up_language_fields(LemmaIdgloss, self, self.search_form)

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets
        dataset_languages = get_dataset_languages(selected_datasets)
        context['dataset_languages'] = dataset_languages

        # use these to fill the form fields of a just done query
        populate_keys, populate_fields = search_fields_from_get(self.search_form, self.request.GET)
        context['populate_fields'] = json.dumps(populate_fields)
        context['populate_fields_keys'] = json.dumps(populate_keys)

        context['paginate_by'] = self.paginate_by

        results = self.get_queryset()
        context['is_paginated'] = results.count() > self.paginate_by

        page_number = self.request.GET.get("page", 1)

        paginator = Paginator(results, self.paginate_by)
        context['page_obj'] = paginator.get_page(page_number)

        context['page_number'] = page_number

        lemmas_zero_glosses = [lem for lem in results if lem.num_gloss == 0]
        num_gloss_zero_matches = len(lemmas_zero_glosses)
        context['num_gloss_zero_matches'] = num_gloss_zero_matches
        context['lemma_count'] = LemmaIdgloss.objects.filter(dataset__in=selected_datasets).count()

        context['search_matches'] = results.count()

        context['searchform'] = self.search_form
        context['search_type'] = 'lemma'
        context['show_all'] = self.show_all

        # to accommodate putting lemma's in the scroll bar in the LemmaUpdateView (aka LemmaDetailView),
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

        items = construct_scrollbar(results, self.search_type, lang_attr_name)
        self.request.session['search_results'] = items

        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format') == 'CSV':
            return self.render_to_csv_response()
        else:
            return super(LemmaListView, self).render_to_response(context, **response_kwargs)

    def render_to_csv_response(self):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = get_dataset_languages(selected_datasets)

        header = csv_header_row_lemmalist(dataset_languages)
        csv_rows = [header]

        queryset = self.get_queryset()
        for lemma in queryset:
            safe_row = csv_lemma_to_row(lemma, dataset_languages)
            csv_rows.append(safe_row)

        # this is based on an example in the Django 4.2 documentation
        pseudo_buffer = Echo()
        new_writer = csv.writer(pseudo_buffer)
        return StreamingHttpResponse(
            (new_writer.writerow(row) for row in csv_rows),
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="dictionary-export-lemmas.csv"'},
        )

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
        datasets_user_can_change = get_objects_for_user(request.user, 'change_dataset', Dataset,
                                                        accept_global_perms=False)
        if not datasets_user_can_change:
            messages.add_message(request, messages.WARNING,
                                 _("You do not have change permission on the dataset of the lemma you are attempting to delete."))
            return HttpResponseRedirect(reverse('dictionary:admin_lemma_list'))

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        queryset = self.get_queryset()

        # check permissions, if fails, do nothing and show error message
        for lemma in queryset:
            if lemma.num_gloss == 0:
                dataset_of_requested_lemma = lemma.dataset
                if dataset_of_requested_lemma not in datasets_user_can_change:
                    messages.add_message(request, messages.WARNING,
                         _("You do not have change permission on the dataset of the lemma you are attempting to delete."))
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
        context = super(LemmaCreateView, self).get_context_data(**kwargs)

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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

        show_dataset_interface = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        use_regular_expressions = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

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
                    return show_warning(request, translated_message, selected_datasets)

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
                               'USE_REGULAR_EXPRESSIONS': use_regular_expressions,
                               'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

            # return HttpResponseRedirect(reverse('dictionary:admin_lemma_list', kwargs={'pk': lemma.id}))
            return HttpResponseRedirect(reverse('dictionary:admin_lemma_list'))
        else:
            return render(request, 'dictionary/add_lemma.html', {'add_lemma_form': form,
                                                             'dataset_languages': dataset_languages,
                                                             'selected_datasets': get_selected_datasets_for_user(request.user),
                                                             'USE_REGULAR_EXPRESSIONS': use_regular_expressions,
                                                             'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})


def create_lemma_for_gloss(request, glossid):
    print('create lemma for gloss')
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
        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        # get the page of the lemma list on which this lemma appears in order ro return to it after update
        request_path = self.request.META.get('HTTP_REFERER')

        # if there was a query, return to the query results in the template on button Return to Lemma List
        context['request_path'] = request_path

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
                    m = re.search(r'/dictionary/gloss/(\d+)(/|$|\?)', path_parms[0])
                    gloss_id_pattern = m.group(1)
                    self.gloss_id = gloss_id_pattern
                except AttributeError:
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

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        instance = self.get_object()
        dataset = instance.dataset
        form = LemmaUpdateForm(request.POST, instance=instance)

        for item, value in request.POST.items():
            value = value.strip()
            if item.startswith(form.lemma_update_field_prefix):
                if value:
                    language_code_2char = item[len(form.lemma_update_field_prefix):]
                    language = Language.objects.get(language_code_2char=language_code_2char)
                    lemmas_for_this_language_and_annotation_idgloss = LemmaIdgloss.objects.filter(
                        lemmaidglosstranslation__language=language,
                        lemmaidglosstranslation__text__exact=value.upper(),
                        dataset=dataset)
                    if lemmas_for_this_language_and_annotation_idgloss.count() > 0:
                        for nextLemma in lemmas_for_this_language_and_annotation_idgloss:
                            if nextLemma.id != instance.id:
                                # found a different lemma with same translation
                                translated_message = _('Lemma ID Gloss is not unique for that language.')
                                return show_warning(request, translated_message, selected_datasets)

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

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        try:
            self.object = super().get_object()
        except (Http404, ObjectDoesNotExist):
            translated_message = _('The requested lemma does not exist.')
            return show_warning(request, translated_message, selected_datasets)

        if not self.object.dataset:
            translated_message = _('Requested lemma has no dataset.')
            return show_warning(request, translated_message, selected_datasets)

        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('registration:login'))

        dataset_of_requested_lemma = self.object.dataset
        datasets_user_can_view = get_objects_for_user(request.user, ['view_dataset', 'can_view_dataset'],
                                                      Dataset, accept_global_perms=False, any_perm=True)

        if dataset_of_requested_lemma not in selected_datasets:
            translated_message = _('The lemma you are trying to view is not in your selected datasets.')
            return show_warning(request, translated_message, selected_datasets)

        if dataset_of_requested_lemma not in datasets_user_can_view:
            translated_message = _('The lemma you are trying to view is not in a dataset you can view.')
            return show_warning(request, translated_message, selected_datasets)

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
    template_name = 'dictionary/admin_batch_edit_senses.html'
    paginate_by = 25
    query_parameters = dict()

    def get(self, request, *args, **kwargs):
        return super(KeywordListView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(KeywordListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets

        if not selected_datasets or selected_datasets.count() > 1:
            feedback_message = _('Please select a single dataset to view keywords.')
            messages.add_message(self.request, messages.ERROR, feedback_message)

        dataset_languages = get_dataset_languages(selected_datasets).order_by('id')
        context['dataset_languages'] = list(dataset_languages)

        new_text_labels = {str(lang.id): lang.name + ' ' + gettext("Text") for lang in dataset_languages}
        context['new_text_labels'] = new_text_labels

        search_form = KeyMappingSearchForm(self.request.GET, languages=dataset_languages)

        context['searchform'] = search_form

        multiple_select_gloss_fields = ['tags']
        context['MULTIPLE_SELECT_GLOSS_FIELDS'] = multiple_select_gloss_fields

        # data structures to store the query parameters in order to keep them in the form
        context['query_parameters'] = json.dumps(self.query_parameters)
        query_parameters_keys = list(self.query_parameters.keys())
        context['query_parameters_keys'] = json.dumps(query_parameters_keys)

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        return context

    def get_queryset(self):
        # this is a ListView for a complicated data structure

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        if not selected_datasets or selected_datasets.count() > 1:
            feedback_message = _('Please select a single dataset to view keywords.')
            messages.add_message(self.request, messages.ERROR, feedback_message)
            # the query set is a list of tuples (gloss, keyword_translations, senses_groups)
            return []

        if 'search_results' in self.request.session.keys():
            search_results = self.request.session['search_results']
            if len(search_results) > 0:
                if search_results[0]['href_type'] not in ['gloss']:
                    search_results = []
        else:
            search_results = []

        (objects_on_page, object_list) = map_search_results_to_gloss_list(search_results)

        get = self.request.GET

        # this needs to be sorted for jquery purposes
        dataset_languages = get_dataset_languages(selected_datasets).order_by('id')

        # exclude morphemes
        if not get:
            glosses_of_datasets = object_list
        else:
            glosses_of_datasets = Gloss.none_morpheme_objects().filter(lemma__dataset__in=selected_datasets)

        # data structure to store the query parameters in order to keep them in the form
        query_parameters = dict()

        if 'tags[]' in get:
            vals = get.getlist('tags[]')
            if vals:
                query_parameters['tags[]'] = vals
                glosses_with_tag = list(
                    TaggedItem.objects.filter(tag__id__in=vals).values_list('object_id', flat=True))
                glosses_of_datasets = glosses_of_datasets.filter(id__in=glosses_with_tag)

        if glosses_of_datasets.count() > 100:
            feedback_message = _('Please refine your query to retrieve fewer than 100 glosses to use this functionality.')
            messages.add_message(self.request, messages.ERROR, feedback_message)
            # the query set is a list of tuples (gloss, keyword_translations, senses_groups)
            return []

        # save the query parameters to a session variable
        self.request.session['query_parameters'] = json.dumps(query_parameters)
        self.request.session.modified = True
        self.query_parameters = query_parameters

        for gloss in glosses_of_datasets:
            consistent = consistent_senses(gloss, include_translations=True,
                                           allow_empty_language=True)
            if not consistent:
                if settings.DEBUG_SENSES:
                    print('gloss senses are not consistent: ', gloss, str(gloss.id))
                # the following method prints whether duplicate senses with no translations have been found
                check_consistency_senses(gloss, delete_empty=True)
                # the senses and their translation objects are renumbered in case anything was deleted
                reorder_senses(gloss)
            gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
            for gs in gloss_senses:
                gs_sense_translations = gs.sense.senseTranslations.all()
                for st in gs_sense_translations:
                    # the code below tries to repair Translation objects that have consistency problems
                    # by fixing, if necessary, the gloss, language, and orderIndex fields to match the sense
                    # conventiently, the index fields are also renumbered here
                    # anything in the result was not able to be fixed
                    inconsistent_translations = reorder_sensetranslations(gs.gloss, st, gs.order,
                                                                     reset=True, force_reset=True)
                    if inconsistent_translations:
                        print('inconsisten translations: ', gloss, st, inconsistent_translations)

        glossesXsenses = []
        for gloss in glosses_of_datasets:
            gloss_senses = GlossSense.objects.filter(gloss=gloss).order_by('order')
            list_of_gloss_senses = [(gs.order, gs.sense) for gs in gloss_senses]
            keyword_translations_per_language = dict()
            sense_groups_per_language = dict()
            for language in dataset_languages:
                sense_groups_per_language[language] = dict()
                keyword_translations_per_language[language] = []
                senses_groups = dict()
                for order, sense in list_of_gloss_senses:
                    if order not in senses_groups.keys():
                        senses_groups[order] = []
                    # first() is used below to avoid crashing if the SenseTranslation object is missing for the language
                    # greater than one has been caught in the consistency and repair code above
                    translations_for_language_for_sense = sense.senseTranslations.filter(language=language).first()
                    if not translations_for_language_for_sense:
                        sense_groups_per_language[language][order] = senses_groups[order]
                    else:
                        for trans in translations_for_language_for_sense.translations.all().order_by('index'):
                            keyword_translations_per_language[language].append(trans)
                            senses_groups[order].append(trans)
                        sense_groups_per_language[language][order] = senses_groups[order]

            # the matrix dimensions tells the view how many cells are needed in the sense number/language matrix
            matrix_dimensions = dict()
            for order, sense in list_of_gloss_senses:
                matrix_dimensions[order] = dict()
                keywords_count = []
                for language in dataset_languages:
                    if order in sense_groups_per_language[language].keys():
                        keywords_count.append(len(sense_groups_per_language[language][order]))
                    else:
                        keywords_count.append(0)
                for language in dataset_languages:
                    matrix_dimensions[order][language] = dict()
                    count = len(sense_groups_per_language[language][order])
                    matrix_dimensions[order][language]['range'] = range(max(keywords_count))
                    matrix_dimensions[order][language]['count'] = count
                    matrix_dimensions[order][language]['max'] = max(keywords_count)
                    matrix_dimensions[order][language]['padding'] = range(max(keywords_count)-count)

            # the following is needed for the matrix, which is ordered by sense number, then language
            translated_senses = dict()
            for order, sense in list_of_gloss_senses:
                translated_senses[order] = dict()
                for language in dataset_languages:
                    translated_senses[order][language] = []
                    sense_translations = sense_groups_per_language[language][order]
                    for trans in sense_translations:
                        translated_senses[order][language].append(trans)
            glossesXsenses.append((gloss,
                                   keyword_translations_per_language,
                                   sense_groups_per_language,
                                   translated_senses,
                                   matrix_dimensions))
        return glossesXsenses


class ToggleListView(ListView):

    model = Gloss
    template_name = 'dictionary/admin_toggle_view.html'
    paginate_by = 25
    search_type = 'sign'
    query_parameters = dict()

    def get(self, request, *args, **kwargs):
        return super(ToggleListView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ToggleListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets

        if not selected_datasets or selected_datasets.count() > 1:
            dataset_languages = Language.objects.filter(id=get_default_language_id())
        else:
            dataset_languages = get_dataset_languages(selected_datasets).order_by('id')

        context['dataset_languages'] = dataset_languages

        search_form = KeyMappingSearchForm(self.request.GET, languages=dataset_languages)

        context['searchform'] = search_form

        multiple_select_gloss_fields = ['tags']
        context['MULTIPLE_SELECT_GLOSS_FIELDS'] = multiple_select_gloss_fields

        context['available_tags'] = [tag for tag in Tag.objects.all()]

        context['available_semanticfields'] = [semfield for semfield in SemanticField.objects.filter(
            machine_value__gt=1).order_by('name')]

        context['available_wordclass'] = [wc for wc in FieldChoice.objects.filter(
            field='WordClass', machine_value__gt=1).order_by('name')]

        context['available_namedentity'] = [wc for wc in FieldChoice.objects.filter(
            field='NamedEntity', machine_value__gt=1).order_by('name')]

        # data structures to store the query parameters in order to keep them in the form
        context['query_parameters'] = json.dumps(self.query_parameters)
        query_parameters_keys = list(self.query_parameters.keys())
        context['query_parameters_keys'] = json.dumps(query_parameters_keys)

        context['SHOW_DATASET_INTERFACE_OPTIONS'] = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)
        context['USE_REGULAR_EXPRESSIONS'] = getattr(settings, 'USE_REGULAR_EXPRESSIONS', False)

        # construct scroll bar
        # the following retrieves language code for English (or DEFAULT LANGUAGE)
        # so the sorting of the scroll bar matches the default sorting of the results in Gloss List View

        list_of_objects = self.object_list

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

        return context

    def get_queryset(self):
        # this is a ListView for a complicated data structure

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        if not selected_datasets or selected_datasets.count() > 1:
            feedback_message = _('Please select a single dataset to view keywords.')
            messages.add_message(self.request, messages.ERROR, feedback_message)
            # the query set is a list of tuples (gloss, keyword_translations, senses_groups)
            return []

        get = self.request.GET

        # multilingual
        # this needs to be sorted for jquery purposes
        dataset_languages = get_dataset_languages(selected_datasets).order_by('id')

        if get:
            glosses_of_datasets = Gloss.none_morpheme_objects().filter(lemma__dataset__in=selected_datasets)
        else:
            recently_added_signs_since_date = DT.datetime.now(tz=get_current_timezone()) - RECENTLY_ADDED_SIGNS_PERIOD
            glosses_of_datasets = Gloss.objects.filter(morpheme=None, lemma__dataset__in=selected_datasets).filter(
                creationDate__range=[recently_added_signs_since_date, DT.datetime.now(tz=get_current_timezone())]).order_by(
                'creationDate')

        # data structure to store the query parameters in order to keep them in the form
        query_parameters = dict()

        if 'tags[]' in get:
            vals = get.getlist('tags[]')
            if vals:
                query_parameters['tags[]'] = vals
                glosses_with_tag = list(
                    TaggedItem.objects.filter(tag__id__in=vals).values_list('object_id', flat=True))
                glosses_of_datasets = glosses_of_datasets.filter(id__in=glosses_with_tag)
        if 'createdBy' in get and get['createdBy']:
            get_value = get['createdBy']
            query_parameters['createdBy'] = get_value.strip()
            created_by_search_string = ' '.join(get_value.strip().split())  # remove redundant spaces
            glosses_of_datasets = glosses_of_datasets.annotate(
                created_by=Concat('creator__first_name', V(' '), 'creator__last_name', output_field=CharField())) \
                .filter(created_by__icontains=created_by_search_string)

        # save the query parameters to a session variable
        self.request.session['query_parameters'] = json.dumps(query_parameters)
        self.request.session.modified = True
        self.query_parameters = query_parameters

        return glosses_of_datasets
