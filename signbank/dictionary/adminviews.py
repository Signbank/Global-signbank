from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.db.models import Q, F, ExpressionWrapper, IntegerField, Count
from django.db.models import CharField, TextField, Value as V
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Concat
from django.db.models.fields import NullBooleanField
from django.db.models.sql.where import NothingNode, WhereNode
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.translation import override, ugettext_lazy as _
from django.forms.fields import TypedChoiceField, ChoiceField
from django.shortcuts import *
from django.contrib import messages
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from signbank.dictionary.templatetags.field_choice import get_field_choice

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
from signbank.settings.base import ECV_FILE,EARLIEST_GLOSS_CREATION_DATE, FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD, LANGUAGE_CODE, ECV_SETTINGS, URL, LANGUAGE_CODE_MAP
from signbank.settings import server_specific
from signbank.settings.server_specific import *

from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value, choicelist_queryset_to_translated_dict, choicelist_queryset_to_machine_value_dict
from signbank.dictionary.forms import GlossSearchForm, MorphemeSearchForm

from signbank.tools import get_selected_datasets_for_user, write_ecv_file_for_dataset, write_csv_for_handshapes


def order_queryset_by_sort_order(get, qs):
    """Change the sort-order of the query set, depending on the form field [sortOrder]

    This function is used both by GlossListView as well as by MorphemeListView.
    The value of [sortOrder] is 'lemma__lemmaidglosstranslation__text' by default.
    [sortOrder] is a hidden field inside the "adminsearch" html form in the template admin_gloss_list.html
    Its value is changed by clicking the up/down buttons in the second row of the search result table
    """

    def get_string_from_tuple_list(lstTuples, number):
        """Get the string value corresponding to a number in a list of number-string tuples"""
        sBack = [tup[1] for tup in lstTuples if tup[0] == number]
        return sBack

    # Helper: order a queryset on field [sOrder], which is a number from a list of tuples named [sListName]
    def order_queryset_by_tuple_list(qs, sOrder, sListName):
        """Order a queryset on field [sOrder], which is a number from a list of tuples named [sListName]"""

        # Get a list of tuples for this sort-order
        tpList = build_choice_list(sListName)
        # Determine sort order: ascending is default
        bReversed = False
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrder = sOrder[1:]
            bReversed = True

        # Order the list of tuples alphabetically
        # (NOTE: they are alphabetical from 'build_choice_list()', except for the values 0,1)
        tpList = sorted(tpList, key=operator.itemgetter(1))
        # Order by the string-values in the tuple list
        return sorted(qs, key=lambda x: get_string_from_tuple_list(tpList, getattr(x, sOrder)), reverse=bReversed)

    def order_queryset_by_annotationidglosstranslation(qs, sOrder):
        language_code_2char = sOrder[-2:]
        sOrderAsc = sOrder
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrderAsc = sOrder[1:]
        annotationidglosstranslation = AnnotationIdglossTranslation.objects.filter(gloss=OuterRef('pk'), language__language_code_2char__iexact=language_code_2char)
        qs = qs.annotate(**{sOrderAsc: Subquery(annotationidglosstranslation.values('text')[:1])}).order_by(sOrder)
        return qs

    # Set the default sort order
    sOrder = 'lemma__lemmaidglosstranslation__text'  # Default sort order if nothing is specified
    # See if the form contains any sort-order information
    if ('sortOrder' in get and get['sortOrder'] != ''):
        # Take the user-indicated sort order
        sOrder = get['sortOrder']

    # The ordering method depends on the kind of field:
    # (1) text fields are ordered straightforwardly
    # (2) fields made from a choice_list need special treatment
    if (sOrder.endswith('handedness')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Handedness")
    elif (sOrder.endswith('domhndsh') or sOrder.endswith('subhndsh')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Handshape")
    elif (sOrder.endswith('locprim')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Location")
    elif "annotationidglosstranslation_order_" in sOrder:
        ordered = order_queryset_by_annotationidglosstranslation(qs, sOrder)
    else:
        # Use straightforward ordering on field [sOrder]

        bReversed = False
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrder = sOrder[1:]
            bReversed = True
        qs_letters = qs.filter(**{sOrder+'__regex':r'^[a-zA-Z]'})
        qs_special = qs.filter(**{sOrder+'__regex':r'^[^a-zA-Z]'})

        sort_key = sOrder[:sOrder.find('__')]
        ordered = list(qs_letters.order_by(sort_key))
        ordered += list(qs_special.order_by(sort_key))

        if bReversed:
            ordered.reverse()

    # return the ordered list
    return ordered


class GlossListView(ListView):

    model = Gloss
    template_name = 'dictionary/admin_gloss_list.html'
    paginate_by = 500
    only_export_ecv = False #Used to call the 'export ecv' functionality of this view without the need for an extra GET parameter
    search_type = 'sign'
    view_type = 'gloss_list'
    web_search = False
    show_all = False
    dataset_name = DEFAULT_DATASET
    last_used_dataset = None

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(GlossListView, self).get_context_data(**kwargs)

        # Retrieve the search_type,so that we know whether the search should be restricted to Gloss or not
        if 'search_type' in self.request.GET:
            self.search_type = self.request.GET['search_type']

        # self.request.session['search_type'] = self.search_type

        if 'view_type' in self.request.GET:
            # user is adjusting the view, leave the rest of the context alone
            self.view_type = self.request.GET['view_type']
            context['view_type'] = self.view_type

        if 'last_used_dataset' in self.request.session.keys():
            self.last_used_dataset = self.request.session['last_used_dataset']
        if 'inWeb' in self.request.GET:
            # user is searching for signs / morphemes visible to anonymous uers
            self.web_search = self.request.GET['inWeb'] == '2'
        elif not self.request.user.is_authenticated():
            self.web_search = True
        context['web_search'] = self.web_search

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        selected_datasets_signlanguage = list(SignLanguage.objects.filter(dataset__in=selected_datasets))
        sign_languages = []
        for sl in selected_datasets_signlanguage:
            if not ((str(sl.id),sl.name) in sign_languages):
                sign_languages.append((str(sl.id), sl.name))

        selected_datasets_dialects = Dialect.objects.filter(signlanguage__in=selected_datasets_signlanguage)\
            .prefetch_related('signlanguage').distinct()
        dialects = []
        for dl in selected_datasets_dialects:
            dialect_name = dl.signlanguage.name + "/" + dl.name
            dialects.append((str(dl.id),dialect_name))

        search_form = GlossSearchForm(self.request.GET, languages=dataset_languages, sign_languages=sign_languages,
                                      dialects=dialects, language_code=self.request.LANGUAGE_CODE)

        #Translations for field choices dropdown menu
        fields_that_need_translated_options = ['hasComponentOfType','hasMorphemeOfType']

        for field_group in FIELDS.values():
            for field in field_group:
                fields_that_need_translated_options.append(field)

        for field in fields_that_need_translated_options:
            try:
                if isinstance(search_form.fields[field], TypedChoiceField):
                    choices = FieldChoice.objects.filter(field__iexact=fieldname_to_category(field))
                    translated_choices = [('','---------')]+choicelist_queryset_to_translated_dict(choices,self.request.LANGUAGE_CODE,
                                                                                ordered=False,id_prefix='')
                    search_form.fields[field] = forms.ChoiceField(label=search_form.fields[field].label,
                                                                    choices=translated_choices,
                                                                    widget=forms.Select(attrs={'class':'form-control'}))
            except KeyError:
                continue

        context['searchform'] = search_form
        context['search_type'] = self.search_type
        context['view_type'] = self.view_type
        context['web_search'] = self.web_search

        if self.search_type == 'sign' or not self.request.user.is_authenticated():
            context['glosscount'] = Gloss.none_morpheme_objects().filter(lemma__dataset__in=selected_datasets).count()   # Only count the none-morpheme glosses
        else:
            context['glosscount'] = Gloss.objects.filter(lemma__dataset__in=selected_datasets).count()  # Count the glosses + morphemes

        context['add_gloss_form'] = GlossCreateForm(self.request.GET, languages=dataset_languages, user=self.request.user, last_used_dataset=self.last_used_dataset)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and self.request.user.is_authenticated():
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'SHOW_MORPHEME_SEARCH') and self.request.user.is_authenticated():
            context['SHOW_MORPHEME_SEARCH'] = settings.SHOW_MORPHEME_SEARCH
        else:
            context['SHOW_MORPHEME_SEARCH'] = False

        context['MULTIPLE_SELECT_GLOSS_FIELDS'] = settings.MULTIPLE_SELECT_GLOSS_FIELDS

        context['input_names_fields_and_labels'] = {}

        for topic in ['main','phonology','semantics']:

            context['input_names_fields_and_labels'][topic] = []

            for fieldname in settings.FIELDS[topic]:

                # exclude the dependent fields for Handedness, Strong Hand, and Weak Hand for purposes of nested dependencies in Search form
                if fieldname not in ['weakprop', 'weakdrop', 'domhndsh_letter', 'domhndsh_number', 'subhndsh_letter', 'subhndsh_number']:
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

        try:
            if self.kwargs['show_all']:
                context['show_all'] = True
        except KeyError:
            context['show_all'] = False

        context['paginate_by'] = self.request.GET.get('paginate_by', self.paginate_by)

        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

        context['generate_translated_choice_list_table'] = generate_translated_choice_list_table()

        if self.search_type == 'sign' or not self.request.user.is_authenticated():
            # Only count the none-morpheme glosses
            # this branch is slower than the other one
            context['glosscount'] = Gloss.none_morpheme_objects().select_related('lemma').select_related('dataset').filter(lemma__dataset__in=selected_datasets).count()
        else:
            context['glosscount'] = Gloss.objects.select_related('lemma').select_related('dataset').filter(lemma__dataset__in=selected_datasets).count()  # Count the glosses + morphemes

        return context


    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)


    def render_to_response(self, context):
        # Look for a 'format=json' GET argument
        if self.request.GET.get('format') == 'CSV':
            return self.render_to_csv_response(context)
        elif self.request.GET.get('export_ecv') == 'ECV' or self.only_export_ecv:
            return self.render_to_ecv_export_response(context)
        else:
            return super(GlossListView, self).render_to_response(context)

    def render_to_ecv_export_response(self, context):

        # check that the user is logged in
        if self.request.user.is_authenticated():
            pass
        else:
            messages.add_message(self.request, messages.ERROR, ('Please login to use this functionality.'))
            return HttpResponseRedirect(URL + '/signs/search/')

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, ('Dataset name must be non-empty.'))
            return HttpResponseRedirect(URL + '/signs/search/')

        try:
            dataset_object = Dataset.objects.get(name=self.dataset_name)
        except:
            messages.add_message(self.request, messages.ERROR, ('No dataset with name '+self.dataset_name+' found.'))
            return HttpResponseRedirect(URL + '/signs/search/')

        # make sure the user can write to this dataset
        import guardian
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = guardian.shortcuts.get_objects_for_user(self.request.user, 'change_dataset', Dataset)
        if user_change_datasets and dataset_object in user_change_datasets:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, ('No permission to export dataset.'))
            return HttpResponseRedirect(URL + '/signs/search/')

        # if we get to here, the user is authenticated and has permission to export the dataset
        ecv_file = write_ecv_file_for_dataset(self.dataset_name)

        messages.add_message(self.request, messages.INFO, ('ECV ' + self.dataset_name + ' successfully updated.'))
        return HttpResponseRedirect(URL + '/signs/search/')

    # noinspection PyInterpreter,PyInterpreter
    def render_to_csv_response(self, context):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dictionary-export.csv"'


#        fields = [f.name for f in Gloss._meta.fields]
        #We want to manually set which fields to export here

        fieldnames = FIELDS['main']+FIELDS['phonology']+FIELDS['semantics']+FIELDS['frequency']+['inWeb', 'isNew']

        fields = [Gloss._meta.get_field(fieldname) for fieldname in fieldnames]

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        lang_attr_name = 'name_' + DEFAULT_KEYWORDS_LANGUAGE['language_code_2char']
        annotationidglosstranslation_fields = ["Annotation ID Gloss" + " (" + getattr(language, lang_attr_name) + ")"
                                               for language in dataset_languages]
        lemmaidglosstranslation_fields = ["Lemma ID Gloss" + " (" + getattr(language, lang_attr_name) + ")"
                                          for language in dataset_languages]

        writer = csv.writer(response)

        with override(LANGUAGE_CODE):
            header = ['Signbank ID', 'Dataset'] + lemmaidglosstranslation_fields + annotationidglosstranslation_fields + [f.verbose_name.encode('ascii','ignore').decode() for f in fields]

        for extra_column in ['SignLanguages','Dialects','Keywords','Sequential Morphology', 'Simultaneous Morphology', 'Blend Morphology',
                             'Relations to other signs','Relations to foreign signs', 'Tags']:
            header.append(extra_column)

        writer.writerow(header)

        for gloss in self.get_queryset():
            row = [str(gloss.pk), gloss.lemma.dataset]

            for language in dataset_languages:
                lemmaidglosstranslations = gloss.lemma.lemmaidglosstranslation_set.filter(language=language)
                if lemmaidglosstranslations and len(lemmaidglosstranslations) == 1:
                    row.append(lemmaidglosstranslations[0].text)
                else:
                    row.append("")

            for language in dataset_languages:
                annotationidglosstranslations = gloss.annotationidglosstranslation_set.filter(language=language)
                if annotationidglosstranslations and len(annotationidglosstranslations) == 1:
                    row.append(annotationidglosstranslations[0].text)
                else:
                    row.append("")

            for f in fields:

                #Try the value of the choicelist
                try:
                    value = getattr(gloss, 'get_' + f.name + '_display')()

                #If it's not there, try the raw value
                except AttributeError:
                    value = getattr(gloss,f.name)

                    if f.name == 'weakdrop' or f.name == 'weakprop':
                        if value == None:
                            value = 'Neutral'

                    # This was disabled with the move to Python 3... might not be needed anymore?
                    # if isinstance(value,unicode):
                    #     value = str(value.encode('ascii','xmlcharrefreplace'))

                if not isinstance(value,str):
                    value = str(value)

                # A handshape name can begin with =. To avoid Office thinking this is a formula, preface with '
                if value[:1] == '=':
                    value = '\'' + value

                row.append(value)

            # get languages
            signlanguages = [signlanguage.name for signlanguage in gloss.signlanguage.all()]
            row.append(", ".join(signlanguages))

            # get dialects
            dialects = [dialect.name for dialect in gloss.dialect.all()]
            row.append(", ".join(dialects))

            # get translations (keywords)
            trans = [t.translation.text + ":" + t.language.language_code_2char for t in gloss.translation_set.all()]
            row.append(", ".join(trans))

            # get morphology
            # Sequential Morphology
            morphemes = [str(morpheme.morpheme.id) for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]
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
        try:
            if self.kwargs['show_all']:
                show_all = True
        except (KeyError,TypeError):
            show_all = False

        #Then check what kind of stuff we want
        if 'search_type' in get:
            self.search_type = get['search_type']
        else:
            self.search_type = 'sign'

        setattr(self.request, 'search_type', self.search_type)

        if 'view_type' in get:
            self.view_type = get['view_type']
            # don't change query, just change display
            # return self.request.session['search_results']
        else:
            # set to default
            self.view_type = 'gloss_list'

        setattr(self.request, 'view_type', self.view_type)

        if 'inWeb' in self.request.GET:
            # user is searching for signs / morphemes visible to anonymous uers
            self.web_search = self.request.GET['inWeb'] == '2'
        elif not self.request.user.is_authenticated():
            self.web_search = True

        setattr(self.request, 'web_search', self.web_search)

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        #Get the initial selection
        if len(get) > 0 or show_all:
            # anonymous users can search signs, make sure no morphemes are in the results
            if self.search_type == 'sign' or not self.request.user.is_authenticated():
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

        #No filters or 'show_all' specified? show nothing
        else:
            qs = Gloss.objects.none()

        if not self.request.user.has_perm('dictionary.search_gloss'):
            qs = qs.filter(inWeb__exact=True)

        #If we wanted to get everything, we're done now
        if show_all:
            return order_queryset_by_sort_order(self.request.GET, qs)
            # return qs

        #If not, we will go trhough a long list of filters
        if 'search' in get and get['search'] != '':
            val = get['search']
            query = Q(annotationidglosstranslation__text__iregex=val)

            if re.match('^\d+$', val):
                query = query | Q(sn__exact=val)

            qs = qs.filter(query)

        # Evaluate all gloss/language search fields
        for get_key, get_value in get.items():
            if get_key.startswith(GlossSearchForm.gloss_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(GlossSearchForm.gloss_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char)
                qs = qs.filter(annotationidglosstranslation__text__iregex=get_value,
                               annotationidglosstranslation__language=language)
            elif get_key.startswith(GlossSearchForm.lemma_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(GlossSearchForm.lemma_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char)
                qs = qs.filter(lemma__lemmaidglosstranslation__text__iregex=get_value,
                               lemma__lemmaidglosstranslation__language=language)
            elif get_key.startswith(GlossSearchForm.keyword_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(GlossSearchForm.keyword_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char)
                qs = qs.filter(translation__translation__text__iregex=get_value,
                               translation__language=language)

        if 'keyword' in get and get['keyword'] != '':
            val = get['keyword']
            qs = qs.filter(translation__translation__text__iregex=val)

        # NULLBOOLEANCHOICES = [(0, '---------'), (1, 'Unknown'), (2, 'True'), (3, 'False')]

        if 'inWeb' in get and get['inWeb'] != '0':
            # Don't apply 'inWeb' filter, if it is unspecified ('0' according to the NULLBOOLEANCHOICES)
            val = get['inWeb'] == '2'
            qs = qs.filter(inWeb__exact=val)

        if 'hasvideo' in get and get['hasvideo'] != 'unspecified':
            val = get['hasvideo'] == 'no'

            qs = qs.filter(glossvideo__isnull=val)

        if 'defspublished' in get and get['defspublished'] != 'unspecified':
            val = get['defspublished'] == 'yes'

            qs = qs.filter(definition__published=val)


        fieldnames = ['idgloss', 'useInstr', 'sense', 'morph', 'StemSN', 'compound', 'rmrks',
                      'locVirtObj',
                      'repeat', 'altern',
                      'phonOth', 'mouthG', 'mouthing', 'phonetVar', 'weakprop', 'weakdrop',
                      'domhndsh_letter', 'domhndsh_number', 'subhndsh_letter', 'subhndsh_number',
                      'domSF', 'domFlex', 'oriChAbd', 'oriChFlex', 'iconImg', 'iconType', 'valence',
                      'lexCatNotes',
                      'inWeb', 'isNew','derivHist']


        # SignLanguage and basic property filters
        # allows for multiselect
        vals = get.getlist('dialect[]')
        if '' in vals:
            vals.remove('')
        if vals != []:
            qs = qs.filter(dialect__in=vals)

        # allows for multiselect
        vals = get.getlist('signlanguage[]')
        if '' in vals:
            vals.remove('')
        if vals != []:
            qs = qs.filter(signlanguage__in=vals)

        if 'useInstr' in get and get['useInstr'] != '':
            qs = qs.filter(useInstr__iregex=get['useInstr'])

        for fieldnamemulti in settings.MULTIPLE_SELECT_GLOSS_FIELDS:

            fieldnamemultiVarname = fieldnamemulti + '[]'
            fieldnameQuery = fieldnamemulti + '__in'

            vals = get.getlist(fieldnamemultiVarname)
            if '' in vals:
                vals.remove('')
            if vals != []:
                qs = qs.filter(**{ fieldnameQuery: vals })

        ## phonology and semantics field filters
        for fieldname in fieldnames:

            if fieldname in get and get[fieldname] != '':

                field_obj = Gloss._meta.get_field(fieldname)

                if type(field_obj) in [CharField,TextField] and len(field_obj.choices) == 0:
                    key = fieldname + '__iregex'
                else:
                    key = fieldname + '__exact'

                val = get[fieldname]

                if isinstance(field_obj,NullBooleanField):
                    val = {'0':'','1': None, '2': True, '3': False}[val]

                if val != '':
                    kwargs = {key:val}
                    qs = qs.filter(**kwargs)

        if 'defsearch' in get and get['defsearch'] != '':

            val = get['defsearch']

            if 'defrole' in get:
                role = get['defrole']
            else:
                role = 'all'

            if role == 'all':
                qs = qs.filter(definition__text__icontains=val)
            else:
                qs = qs.filter(definition__text__icontains=val, definition__role__exact=role)

        if 'tags' in get and get['tags'] != '':
            vals = get.getlist('tags')

            tags = []
            for t in vals:
                tags.extend(Tag.objects.filter(name=t))


            # search is an implicit AND so intersection
            tqs = TaggedItem.objects.get_intersection_by_model(Gloss, tags)

            # intersection
            qs = qs & tqs

        qs = qs.distinct()

        if 'nottags' in get and get['nottags'] != '':
            vals = get.getlist('nottags')

            tags = []
            for t in vals:
                tags.extend(Tag.objects.filter(name=t))

            # search is an implicit AND so intersection
            tqs = TaggedItem.objects.get_intersection_by_model(Gloss, tags)

            # exclude all of tqs from qs
            qs = [q for q in qs if q not in tqs]

        if 'relationToForeignSign' in get and get['relationToForeignSign'] != '':

            relations = RelationToForeignSign.objects.filter(other_lang_gloss__icontains=get['relationToForeignSign'])
            potential_pks = [relation.gloss.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if 'hasRelationToForeignSign' in get and get['hasRelationToForeignSign'] != '0':

            pks_for_glosses_with_relations = [relation.gloss.pk for relation in RelationToForeignSign.objects.all()]

            if get['hasRelationToForeignSign'] == '1': #We only want glosses with a relation to a foreign sign
                qs = qs.filter(pk__in=pks_for_glosses_with_relations)
            elif get['hasRelationToForeignSign'] == '2': #We only want glosses without a relation to a foreign sign
                qs = qs.exclude(pk__in=pks_for_glosses_with_relations)

        if 'relation' in get and get['relation'] != '':

            potential_targets = Gloss.objects.filter(idgloss__icontains=get['relation'])
            relations = Relation.objects.filter(target__in=potential_targets)
            potential_pks = [relation.source.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if 'hasRelation' in get and get['hasRelation'] != '':

            #Find all relations with this role
            if get['hasRelation'] == 'all':
                relations_with_this_role = Relation.objects.all()
            else:
                relations_with_this_role = Relation.objects.filter(role__exact=get['hasRelation'])

            #Remember the pk of all glosses that take part in the collected relations
            pks_for_glosses_with_correct_relation = [relation.source.pk for relation in relations_with_this_role]
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_relation)

        if 'morpheme' in get and get['morpheme'] != '':

            # morpheme is an integer
            input_morpheme = get['morpheme']
            # Filter all glosses that contain this morpheme in their simultaneous morphology
            try:
                selected_morpheme = Morpheme.objects.get(pk=get['morpheme'])
                potential_pks = [appears.parent_gloss.pk for appears in SimultaneousMorphologyDefinition.objects.filter(morpheme=selected_morpheme)]
                qs = qs.filter(pk__in=potential_pks)
            except:
                # This error should not occur, the input search form requires the selection of a morpheme from a list
                # If the user attempts to input a string, it is ignored by the gloss list search form
                print("Morpheme not found: ", str(input_morpheme))

        if 'hasComponentOfType' in get and get['hasComponentOfType'] != '':

            # Look for "compound-components" of the indicated type. Compound Components are defined in class[MorphologyDefinition]
            morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__exact=get['hasComponentOfType'])
            pks_for_glosses_with_morphdefs_with_correct_role = [morphdef.parent_gloss.pk for morphdef in morphdefs_with_correct_role]
            qs = qs.filter(pk__in=pks_for_glosses_with_morphdefs_with_correct_role)

        if 'hasMorphemeOfType' in get and get['hasMorphemeOfType'] != '':

            morpheme_type = get['hasMorphemeOfType']
            # Get all Morphemes of the indicated mrpType
            target_morphemes = Morpheme.objects.filter(mrpType__exact=morpheme_type)
            sim_morphemes = SimultaneousMorphologyDefinition.objects.filter(morpheme_id__in=target_morphemes)
            # Get all glosses that have one of the morphemes in this set
            glosses_with_correct_mrpType = Gloss.objects.filter(simultaneous_morphology__in=sim_morphemes)

            # Turn this into a list with pks
            pks_for_glosses_with_correct_mrpType = [glossdef.pk for glossdef in glosses_with_correct_mrpType]

            qs = qs.filter(pk__in=pks_for_glosses_with_correct_mrpType)

        if 'definitionRole' in get and get['definitionRole'] != '':

            #Find all definitions with this role
            if get['definitionRole'] == 'all':
                definitions_with_this_role = Definition.objects.all()
            else:
                definitions_with_this_role = Definition.objects.filter(role__exact=get['definitionRole'])

            #Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role]
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if 'definitionContains' in get and get['definitionContains'] != '':

            definitions_with_this_text = Definition.objects.filter(text__iregex=get['definitionContains'])

            #Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_text]
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if 'createdBefore' in get and get['createdBefore'] != '':

            created_before_date = DT.datetime.strptime(get['createdBefore'], "%m/%d/%Y").date()
            qs = qs.filter(creationDate__range=(EARLIEST_GLOSS_CREATION_DATE,created_before_date))

        if 'createdAfter' in get and get['createdAfter'] != '':

            created_after_date = DT.datetime.strptime(get['createdAfter'], "%m/%d/%Y").date()
            qs = qs.filter(creationDate__range=(created_after_date,DT.datetime.now()))

        if 'createdBy' in get and get['createdBy'] != '':
            created_by_search_string = ' '.join(get['createdBy'].strip().split()) # remove redundant spaces
            qs = qs.annotate(
                created_by=Concat('creator__first_name', V(' '), 'creator__last_name', output_field=CharField())) \
                .filter(created_by__icontains=created_by_search_string)

        # Saving querysets results to sessions, these results can then be used elsewhere (like in gloss_detail)
        # Flush the previous queryset (just in case)
        # self.request.session['search_results'] = None

        qs = qs.select_related('lemma')
        try:
            print('qs: ', qs.query.as_sql())
        except:
            pass
        # Make sure that the QuerySet has filters applied (user is searching for something instead of showing all results [objects.all()])
        if hasattr(qs.query.where, 'children') and len(qs.query.where.children) > 0:

        # if not isinstance(qs.query.where.children, NothingNode):
            items = []

            for item in qs:
                annotationidglosstranslations = item.annotationidglosstranslation_set.filter(
                    language__language_code_2char__exact=self.request.LANGUAGE_CODE
                )
                if annotationidglosstranslations and len(annotationidglosstranslations) > 0:
                    items.append(dict(id = item.id, gloss = annotationidglosstranslations[0].text))
                else:
                    annotationidglosstranslations = item.annotationidglosstranslation_set.filter(
                        language__language_code_2char__exact='en'
                    )
                    if annotationidglosstranslations and len(annotationidglosstranslations) > 0:
                        items.append(dict(id=item.id, gloss=annotationidglosstranslations[0].text))
                    else:
                        items.append(dict(id=item.id, gloss=item.idgloss))

            self.request.session['search_results'] = items

        # Sort the queryset by the parameters given
        qs = order_queryset_by_sort_order(self.request.GET, qs)

        self.request.session['search_type'] = self.search_type
        self.request.session['web_search'] = self.web_search

        if not 'last_used_dataset' in self.request.session.keys():
            self.request.session['last_used_dataset'] = self.last_used_dataset

        # Return the resulting filtered and sorted queryset
        return qs


class GlossDetailView(DetailView):

    model = Gloss
    context_object_name = 'gloss'
    last_used_dataset = None

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):

        try:
            self.object = self.get_object()
        # except Http404:
        except:
            # return custom template
            # return render(request, 'dictionary/warning.html', status=404)
            raise Http404()

        dataset_of_requested_gloss = self.object.dataset
        datasets_user_can_view = get_objects_for_user(request.user, 'view_dataset', Dataset, accept_global_perms=False)
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        if request.user.is_authenticated():
            if dataset_of_requested_gloss not in selected_datasets:
                return render(request, 'dictionary/warning.html',
                              {'warning': 'The gloss you are trying to view (' + str(
                                  self.object.id) + ') is not in your selected datasets.'})
            if dataset_of_requested_gloss not in datasets_user_can_view:
                if self.object.inWeb:
                    return HttpResponseRedirect(reverse('dictionary:public_gloss',kwargs={'glossid':self.object.pk}))
                else:
                    return render(request, 'dictionary/warning.html',
                                  {'warning': 'The gloss you are trying to view ('+str(self.object.id)+') is not assigned to a dataset.'})
        else:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:auth_login'))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        # reformat LANGUAGE_CODE for use in dictionary domain, accomodate multilingual codings
        from signbank.tools import convert_language_code_to_2char
        language_code = convert_language_code_to_2char(self.request.LANGUAGE_CODE)
        language = Language.objects.get(id=get_default_language_id())
        default_language_code = language.language_code_2char

        # Call the base implementation first to get a context
        context = super(GlossDetailView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['tagform'] = TagUpdateForm()
        context['videoform'] = VideoUploadForGlossForm()
        context['imageform'] = ImageUploadForGlossForm()
        context['definitionform'] = DefinitionForm()
        context['relationform'] = RelationForm()

        context['morphologyform'] = GlossMorphologyForm()
        context['morphologyform'].fields['role'] = forms.ChoiceField(label='Type', widget=forms.Select(attrs=ATTRS_FOR_FORMS),
            choices=choicelist_queryset_to_translated_dict(FieldChoice.objects.filter(field__iexact='MorphologyType'),
                                                                   self.request.LANGUAGE_CODE,ordered=False,id_prefix=''), required=True)

        context['morphemeform'] = GlossMorphemeForm()
        context['blendform'] = GlossBlendForm()
        context['othermediaform'] = OtherMediaForm()
        context['navigation'] = context['gloss'].navigation(True)
        context['interpform'] = InterpreterFeedbackForm()
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix

        context['SIGN_NAVIGATION']  = settings.SIGN_NAVIGATION
        context['handedness'] = (int(self.object.handedness) > 1) if self.object.handedness else 0  # minimal machine value is 2
        context['domhndsh'] = (int(self.object.domhndsh) > 2) if self.object.domhndsh else 0        # minimal machine value -s 3
        context['tokNo'] = self.object.tokNo                 # Number of occurrences of Sign, used to display Stars

        # check for existence of strong hand and weak hand shapes
        try:
            strong_hand_obj = Handshape.objects.get(machine_value = self.object.domhndsh)
        except Handshape.DoesNotExist:
            strong_hand_obj = None
        context['StrongHand'] = self.object.domhndsh if strong_hand_obj else 0
        context['WeakHand'] = self.object.subhndsh

        # context['NamedEntityDefined'] = (int(self.object.namEnt) > 1) if self.object.namEnt else 0        # minimal machine value is 2
        context['SemanticFieldDefined'] = (int(self.object.semField) > 1) if self.object.semField else 0  # minimal machine value is 2
        # context['ValenceDefined'] = (int(self.object.valence) > 1) if self.object.valence else 0          # minimal machine value is 2
        # context['IconicImageDefined'] = self.object.iconImage                                             # exists if not emtpy


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
        labels = gl.field_labels()

        # set a session variable to be able to pass the gloss's id to the ajax_complete method
        # the last_used_dataset name is updated to that of this gloss
        # if a sequesce of glosses are being created by hand, this keeps the dataset setting the same
        if gl.dataset:
            self.request.session['datasetid'] = gl.dataset.id
            self.last_used_dataset = gl.dataset.name
        else:
            self.request.session['datasetid'] = get_default_language_id()

        self.request.session['last_used_dataset'] = self.last_used_dataset

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

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

        context['choice_lists'] = {}

        #Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['main','phonology','semantics','frequency']:
            context[topic+'_fields'] = []

            for field in FIELDS[topic]:

                # the following check will be used when querying is added, at the moment these don't appear in the phonology list
                if field not in ['weakprop', 'weakdrop', 'domhndsh_number', 'domhndsh_letter', 'subhndsh_number', 'subhndsh_letter']:
                    #Get and save the choice list for this field
                    fieldchoice_category = fieldname_to_category(field)
                    choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)

                    if len(choice_list) > 0:
                        context['choice_lists'][field] = choicelist_queryset_to_translated_dict (choice_list,self.request.LANGUAGE_CODE)

                    #Take the human value in the language we are using
                    machine_value = getattr(gl,field)
                    human_value = machine_value_to_translated_human_value(machine_value,choice_list,self.request.LANGUAGE_CODE)

                    #And add the kind of field
                    kind = fieldname_to_kind(field)
                    context[topic+'_fields'].append([human_value,field,labels[field],kind])


        # ADD FREQUENCY (COUNT) TO THE VALUES IN THE PULL-DOWN LISTS FOR PHONOLOGY AND SEMANTICS

        # # to determine the frequency count of null or empty values for a field, a raw query is used
        # # the raw query selected datasets parameter needs to have form (dataset_id,...,,dataset_id)
        # selected_datasets_as_tuple_list = ""
        # for ds in selected_datasets:
        #     if selected_datasets_as_tuple_list:
        #         selected_datasets_as_tuple_list = selected_datasets_as_tuple_list + ',' + str(ds.id)
        #     else:
        #         selected_datasets_as_tuple_list = str(ds.id)
        # selected_datasets_as_tuple_list = '(' + selected_datasets_as_tuple_list + ')'

        context['frequency_lists_phonology_fields'] = {}
        for field in FIELDS['phonology']:
            if field not in ['weakprop', 'weakdrop', 'domhndsh_number', 'domhndsh_letter', 'subhndsh_number',
                             'subhndsh_letter']:
                fieldchoice_category = fieldname_to_category(field)
                choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)

                if len(choice_list) > 0:
                    choice_list_machine_values = choicelist_queryset_to_machine_value_dict(choice_list)
                    choice_list_frequencies = {}
                    choice_list_labels = {}
                    for choice_list_field, machine_value in choice_list_machine_values:
                        if machine_value == 0:

                            frequency_for_field = Gloss.objects.filter(Q(lemma__dataset__in=selected_datasets),
                                                                       Q(**{field + '__isnull': True}) |
                                                                       Q(**{field: 0})).count()

                            choice_list_frequencies[choice_list_field] = frequency_for_field
                        else:
                            variable_column = field
                            search_filter = 'exact'
                            filter = variable_column + '__' + search_filter
                            choice_list_frequencies[choice_list_field] = Gloss.objects.\
                                filter(lemma__dataset__in=selected_datasets).filter(**{filter: machine_value}).count()
                    context['frequency_lists_phonology_fields'][field] = choice_list_frequencies

        # concatenate the frequency count to each of the menu choices
        for field in FIELDS['phonology']:
            if field not in ['weakprop', 'weakdrop', 'domhndsh_number', 'domhndsh_letter', 'subhndsh_number',
                             'subhndsh_letter']:
                if field in context['choice_lists'].keys():
                    if field in context['frequency_lists_phonology_fields'].keys():
                        # revise entries in list with frequencies of choices
                        old_choice_list = context['choice_lists'][field]
                        for f_choice, f_freq in context['frequency_lists_phonology_fields'][field].items():
                            old_choice_list[f_choice] = old_choice_list[f_choice] + '      [' + str(f_freq) + ']'
                        context['choice_lists'][field] = old_choice_list


        context['frequency_lists_semantics_fields'] = {}
        for field in FIELDS['semantics']:
            fieldchoice_category = fieldname_to_category(field)
            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)
            if len(choice_list) > 0:
                choice_list_machine_values = choicelist_queryset_to_machine_value_dict(choice_list)
                choice_list_frequencies = {}
                for choice_list_field, machine_value in choice_list_machine_values:
                    if machine_value == 0:

                        frequency_for_field = Gloss.objects.filter(Q(lemma__dataset__in=selected_datasets),
                                                                   Q(**{field + '__isnull': True}) |
                                                                   Q(**{field: 0})).count()

                        choice_list_frequencies[choice_list_field] = frequency_for_field
                    else:
                        variable_column = field
                        search_filter = 'exact'
                        filter = variable_column + '__' + search_filter
                        choice_list_frequencies[choice_list_field] = Gloss.objects.\
                            filter(lemma__dataset__in=selected_datasets).filter(**{filter: machine_value}).count()
                context['frequency_lists_semantics_fields'][field] = choice_list_frequencies

        # concatenate the frequency count to each of the menu choices
        for field in FIELDS['semantics']:
            if field in context['choice_lists'].keys():
                if field in context['frequency_lists_semantics_fields'].keys():
                    # revise entries in list with frequencies of choices
                    old_choice_list = context['choice_lists'][field]
                    for f_choice, f_freq in context['frequency_lists_semantics_fields'][field].items():
                        old_choice_list[f_choice] = old_choice_list[f_choice] + '      [' + str(f_freq) + ']'
                    context['choice_lists'][field] = old_choice_list

        #Add morphology to choice lists
        context['choice_lists']['morphology_role'] = choicelist_queryset_to_translated_dict(FieldChoice.objects.filter(field__iexact='MorphologyType'),
                                                                                       self.request.LANGUAGE_CODE)

        context['choice_lists']['morph_type'] = choicelist_queryset_to_translated_dict(FieldChoice.objects.filter(field__iexact='MorphemeType'),
                                                                                       self.request.LANGUAGE_CODE)

        #Collect all morphology definitions for th sequential morphology section, and make some translations in advance
        morphdef_roles = FieldChoice.objects.filter(field__iexact='MorphologyType')
        morphdefs = []

        for morphdef in context['gloss'].parent_glosses.all():

            translated_role = machine_value_to_translated_human_value(morphdef.role,morphdef_roles,self.request.LANGUAGE_CODE)

            sign_display = str(morphdef.morpheme.id)
            morph_texts = morphdef.morpheme.get_annotationidglosstranslation_texts()
            if morph_texts.keys():
                if language_code in morph_texts.keys():
                    sign_display = morph_texts[language_code]
                else:
                    sign_display = morph_texts[default_language_code]

            morphdefs.append((morphdef,translated_role,sign_display))

        morphdefs = sorted(morphdefs, key=lambda tup: tup[1])
        context['morphdefs'] = morphdefs

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
            if language_code in minimal_pairs_trans.keys():
                minpar_display = minimal_pairs_trans[language_code][0].text
            else:
                # This should be set to the default language if the interface language hasn't been set for this gloss
                minpar_display = minimal_pairs_trans[default_language_code][0].text

            minimalpairs.append((mpg,dict,minpar_display))

        context['minimalpairs'] = minimalpairs


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
            if language_code in homo_trans:
                homo_display = homo_trans[language_code][0].text
            else:
                # This should be set to the default language if the interface language hasn't been set for this gloss
                homo_display = homo_trans[default_language_code][0].text

            homonyms_different_phonology.append((saved_gl,homo_display))

        context['homonyms_different_phonology'] = homonyms_different_phonology

        homonyms_but_not_saved = []

        for homonym in homonyms_not_saved:
            homo_trans = {}
            if homonym.dataset:
                for language in homonym.dataset.translation_languages.all():
                    homo_trans[language.language_code_2char] = homonym.annotationidglosstranslation_set.filter(language=language)
            else:
                language = Language.objects.get(id=get_default_language_id())
                homo_trans[language.language_code_2char] = homonym.annotationidglosstranslation_set.filter(language=language)
            if language_code in homo_trans:
                homo_display = homo_trans[language_code][0].text
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
            translated_note_role = machine_value_to_translated_human_value(note.role,note_role_choices,self.request.LANGUAGE_CODE)
            role_id = (note.role, translated_note_role)
            if role_id not in notes_groupedby_role:
                notes_groupedby_role[role_id] = []
            notes_groupedby_role[role_id].append(note)
        context['notes_groupedby_role'] = notes_groupedby_role

        #Gather the OtherMedia
        context['other_media'] = []
        other_media_type_choice_list = FieldChoice.objects.filter(field__iexact='OthermediaType')

        for other_media in gl.othermedia_set.all():

            human_value_media_type = machine_value_to_translated_human_value(other_media.type,other_media_type_choice_list,self.request.LANGUAGE_CODE)

            path = settings.URL+'dictionary/protected_media/othermedia/'+other_media.path
            if '/' in other_media.path:
                other_media_filename = other_media.path.split('/')[1]
            else:
                other_media_filename = other_media.path
            if other_media_filename.split('.')[-1] == 'mp4':
                file_type = 'video/mp4'
            elif other_media_filename.split('.')[-1] == 'png':
                file_type = 'image/png'
            else:
                file_type = ''

            context['other_media'].append([other_media.pk, path, file_type, human_value_media_type, other_media.alternative_gloss, other_media_filename])

            #Save the other_media_type choices (same for every other_media, but necessary because they all have other ids)
            context['choice_lists']['other-media-type_'+str(other_media.pk)] = choicelist_queryset_to_translated_dict(other_media_type_choice_list,self.request.LANGUAGE_CODE)

        context['choice_lists'] = json.dumps(context['choice_lists'])

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

        # Put annotation_idgloss per language in the context
        context['annotation_idgloss'] = {}
        if gl.dataset:
            for language in gl.dataset.translation_languages.all():
                context['annotation_idgloss'][language] = gl.annotationidglosstranslation_set.filter(language=language)
        else:
            language = Language.objects.get(id=get_default_language_id())
            context['annotation_idgloss'][language] = gl.annotationidglosstranslation_set.filter(language=language)

        # Put translations (keywords) per language in the context
        context['translations_per_language'] = {}
        if gl.dataset:
            for language in gl.dataset.translation_languages.all():
                context['translations_per_language'][language] = gl.translation_set.filter(language=language)
        else:
            language = Language.objects.get(id=get_default_language_id())
            context['translations_per_language'][language] = gl.translation_set.filter(language=language)

        simultaneous_morphology = []
        sim_morph_typ_choices = FieldChoice.objects.filter(field__iexact='MorphemeType')

        if gl.simultaneous_morphology:
            for sim_morph in gl.simultaneous_morphology.all():
                translated_morph_type = machine_value_to_translated_human_value(sim_morph.morpheme.mrpType,sim_morph_typ_choices,self.request.LANGUAGE_CODE)

                morpheme_annotation_idgloss = {}
                if sim_morph.morpheme.dataset:
                    for language in sim_morph.morpheme.dataset.translation_languages.all():
                        morpheme_annotation_idgloss[language.language_code_2char] = sim_morph.morpheme.annotationidglosstranslation_set.filter(language=language)
                else:
                    language = Language.objects.get(id=get_default_language_id())
                    morpheme_annotation_idgloss[language.language_code_2char] = sim_morph.morpheme.annotationidglosstranslation_set.filter(language=language)
                if language_code in morpheme_annotation_idgloss.keys():
                    morpheme_display = morpheme_annotation_idgloss[language_code][0].text
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
                if language_code in glosses_annotation_idgloss.keys():
                    morpheme_display = glosses_annotation_idgloss[language_code][0].text
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
                if language_code in other_relations_dict.keys():
                    target_display = other_relations_dict[language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    target_display = other_relations_dict[default_language_code][0].text

                otherrelations.append((oth_rel,target_display))

        context['otherrelations'] = otherrelations

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['dataset_choices'] = {}
            user = self.request.user
            if user.is_authenticated():
                qs = get_objects_for_user(user, 'view_dataset', Dataset, accept_global_perms=False)
                dataset_choices = {}
                for dataset in qs:
                    dataset_choices[dataset.name] = dataset.name
                context['dataset_choices'] = json.dumps(dataset_choices)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        if hasattr(settings, 'SHOW_LETTER_NUMBER_PHONOLOGY'):
            context['SHOW_LETTER_NUMBER_PHONOLOGY'] = settings.SHOW_LETTER_NUMBER_PHONOLOGY
        else:
            context['SHOW_LETTER_NUMBER_PHONOLOGY'] = False

        context['generate_translated_choice_list_table'] = generate_translated_choice_list_table()

        return context

class GlossRelationsDetailView(DetailView):
    model = Gloss
    template_name = 'dictionary/related_signs_detail_view.html'
    context_object_name = 'gloss'

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):

        try:
            self.object = self.get_object()
        except Http404:
            # return custom template
            return render(request, 'no_object.html', status=404)

        if request.user.is_authenticated():
            if self.object.dataset not in get_objects_for_user(request.user, 'view_dataset', Dataset, accept_global_perms=False):
                if self.object.inWeb:
                    return HttpResponseRedirect(reverse('dictionary:public_gloss',kwargs={'glossid':self.object.pk}))
                else:
                    return HttpResponse('')
        else:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:auth_login'))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        # reformat LANGUAGE_CODE for use in dictionary domain, accomodate multilingual codings
        from signbank.tools import convert_language_code_to_2char
        language_code = convert_language_code_to_2char(self.request.LANGUAGE_CODE)
        language = Language.objects.get(id=get_default_language_id())
        default_language_code = language.language_code_2char

        # Call the base implementation first to get a context
        context = super(GlossRelationsDetailView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['tagform'] = TagUpdateForm()
        context['videoform'] = VideoUploadForGlossForm()
        context['imageform'] = ImageUploadForGlossForm()
        context['definitionform'] = DefinitionForm()
        context['relationform'] = RelationForm()

        context['morphologyform'] = GlossMorphologyForm()
        context['morphologyform'].fields['role'] = forms.ChoiceField(label='Type', widget=forms.Select(attrs=ATTRS_FOR_FORMS),
            choices=choicelist_queryset_to_translated_dict(FieldChoice.objects.filter(field__iexact='MorphologyType'),
                                                                   self.request.LANGUAGE_CODE,ordered=False,id_prefix=''), required=True)

        context['morphemeform'] = GlossMorphemeForm()
        context['blendform'] = GlossBlendForm()
        context['othermediaform'] = OtherMediaForm()
        context['navigation'] = context['gloss'].navigation(True)
        context['interpform'] = InterpreterFeedbackForm()
        context['SIGN_NAVIGATION']  = settings.SIGN_NAVIGATION

        #Pass info about which fields we want to see
        gl = context['gloss']
        labels = gl.field_labels()

        context['choice_lists'] = {}

        #Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['main','phonology','semantics','frequency']:
            context[topic+'_fields'] = []

            for field in FIELDS[topic]:

                #Get and save the choice list for this field
                fieldchoice_category = fieldname_to_category(field)
                choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category)

                if len(choice_list) > 0:
                    context['choice_lists'][field] = choicelist_queryset_to_translated_dict (choice_list,self.request.LANGUAGE_CODE)

                #Take the human value in the language we are using
                machine_value = getattr(gl,field)
                human_value = machine_value_to_translated_human_value(machine_value,choice_list,self.request.LANGUAGE_CODE)

                #And add the kind of field
                kind = fieldname_to_kind(field)
                context[topic+'_fields'].append([human_value,field,labels[field],kind])

        #Add morphology to choice lists
        context['choice_lists']['morphology_role'] = choicelist_queryset_to_translated_dict(FieldChoice.objects.filter(field__iexact='MorphologyType'),
                                                                                       self.request.LANGUAGE_CODE)

        #Collect all morphology definitions for th sequential morphology section, and make some translations in advance
        morphdef_roles = FieldChoice.objects.filter(field__iexact='MorphologyType')
        morphdefs = []

        for morphdef in context['gloss'].parent_glosses.all():

            translated_role = machine_value_to_translated_human_value(morphdef.role,morphdef_roles,self.request.LANGUAGE_CODE)

            sign_display = str(morphdef.morpheme.id)
            morph_texts = morphdef.morpheme.get_annotationidglosstranslation_texts()
            if morph_texts.keys():
                if language_code in morph_texts.keys():
                    sign_display = morph_texts[language_code]
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
            print("lemma_group_count: except")
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
                if language_code in lemma_dict.keys():
                    gl_lem_display = lemma_dict[language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    gl_lem_display = lemma_dict[default_language_code][0].text

                glosses_in_lemma_group.append((gl_lem,gl_lem_display))

        context['glosses_in_lemma_group'] = glosses_in_lemma_group

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
                if language_code in other_relations_dict.keys():
                    target_display = other_relations_dict[language_code][0].text
                else:
                    # This should be set to the default language if the interface language hasn't been set for this gloss
                    target_display = other_relations_dict[default_language_code][0].text

                otherrelations.append((oth_rel,target_display))

        context['otherrelations'] = otherrelations

        has_variants = gl.has_variants()
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
                if language_code in variants_dict.keys():
                    gl_var_display = variants_dict[language_code][0].text
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
            if language_code in minimal_pairs_trans.keys():
                minpar_display = minimal_pairs_trans[language_code][0].text
            else:
                # This should be set to the default language if the interface language hasn't been set for this gloss
                minpar_display = minimal_pairs_trans[default_language_code][0].text

            minimalpairs.append((mpg,dict,minpar_display))

        context['minimalpairs'] = minimalpairs

        # Put annotation_idgloss per language in the context
        context['annotation_idgloss'] = {}
        if gl.dataset:
            for language in gl.dataset.translation_languages.all():
                context['annotation_idgloss'][language] = gl.annotationidglosstranslation_set.filter(language=language)
        else:
            language = Language.objects.get(id=get_default_language_id())
            context['annotation_idgloss'][language] = gl.annotationidglosstranslation_set.filter(language=language)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        return context


class MorphemeListView(ListView):
    """The morpheme list view basically copies the gloss list view"""

    model = Morpheme
    search_type = 'morpheme'
    dataset_name = DEFAULT_DATASET
    last_used_dataset = None
    template_name = 'dictionary/admin_morpheme_list.html'
    paginate_by = 500


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(MorphemeListView, self).get_context_data(**kwargs)

        # Retrieve the search_type,so that we know whether the search should be restricted to Gloss or not
        if 'search_type' in self.request.GET:
            self.search_type = self.request.GET['search_type']

        if 'last_used_dataset' in self.request.session.keys():
            self.last_used_dataset = self.request.session['last_used_dataset']

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        selected_datasets_signlanguage = [ ds.signlanguage for ds in selected_datasets ]
        sign_languages = []
        for sl in selected_datasets_signlanguage:
            if not ((str(sl.id), sl.name) in sign_languages):
                sign_languages.append((str(sl.id), sl.name))

        selected_datasets_dialects = Dialect.objects.filter(signlanguage__in=selected_datasets_signlanguage).distinct()
        dialects = []
        for dl in selected_datasets_dialects:
            dialect_name = dl.signlanguage.name + "/" + dl.name
            dialects.append((str(dl.id),dialect_name))

        search_form = MorphemeSearchForm(self.request.GET, languages=dataset_languages, sign_languages=sign_languages,
                                         dialects=dialects, language_code=self.request.LANGUAGE_CODE)

        context['searchform'] = search_form
        context['glosscount'] = Morpheme.objects.all().count()

        context['search_type'] = self.search_type

        context['add_morpheme_form'] = MorphemeCreateForm(self.request.GET, languages=dataset_languages, user=self.request.user, last_used_dataset=self.last_used_dataset)

        # make sure that the morpheme-type options are available to the listview
        oChoiceLists = {}
        choice_list = FieldChoice.objects.filter(field__iexact = fieldname_to_category('mrpType'))
        if (len(choice_list) > 0):
            ordered_dict = choicelist_queryset_to_translated_dict(choice_list, self.request.LANGUAGE_CODE)
            oChoiceLists['mrpType'] = ordered_dict

        # Make all choice lists available in the context (currently only mrpType)
        context['choice_lists'] = json.dumps(oChoiceLists)

        context['input_names_fields_and_labels'] = {}

        for topic in ['main', 'phonology', 'semantics']:

            context['input_names_fields_and_labels'][topic] = []

            for fieldname in settings.FIELDS[topic]:

                if fieldname not in ['weakprop', 'weakdrop', 'domhndsh_number', 'domhndsh_letter', 'subhndsh_number', 'subhndsh_letter']:
                    field = search_form[fieldname]
                    label = field.label

                    context['input_names_fields_and_labels'][topic].append((fieldname, field, label))

        context['paginate_by'] = self.request.GET.get('paginate_by', self.paginate_by)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix
        context['MULTIPLE_SELECT_MORPHEME_FIELDS'] = settings.MULTIPLE_SELECT_MORPHEME_FIELDS

        return context


    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)


    def get_queryset(self):

        # get query terms from self.request
        get = self.request.GET

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        if len(get) > 0:
            qs = Morpheme.objects.all().filter(lemma__dataset__in=selected_datasets)

        #Don't show anything when we're not searching yet
        else:
            qs = Morpheme.objects.none()

        # Evaluate all morpheme/language search fields
        for get_key, get_value in get.items():
            if get_key.startswith(MorphemeSearchForm.morpheme_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(MorphemeSearchForm.morpheme_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char)
                qs = qs.filter(annotationidglosstranslation__text__iregex=get_value,
                               annotationidglosstranslation__language=language)
            elif get_key.startswith(MorphemeSearchForm.keyword_search_field_prefix) and get_value != '':
                language_code_2char = get_key[len(MorphemeSearchForm.keyword_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char)
                qs = qs.filter(translation__translation__text__iregex=get_value,
                               translation__language=language)

        if 'lemmaGloss' in get and get['lemmaGloss'] != '':
            val = get['lemmaGloss']
            qs = qs.filter(idgloss__iregex=val)

        if 'keyword' in get and get['keyword'] != '':
            val = get['keyword']
            qs = qs.filter(translation__translation__text__iregex=val)

        if 'inWeb' in get and get['inWeb'] != '0':
            # Don't apply 'inWeb' filter, if it is unspecified ('0' according to the NULLBOOLEANCHOICES)
            val = get['inWeb'] == '2'
            qs = qs.filter(inWeb__exact=val)

        if 'hasvideo' in get and get['hasvideo'] != 'unspecified':
            val = get['hasvideo'] == 'no'

            qs = qs.filter(glossvideo__isnull=val)

        if 'defspublished' in get and get['defspublished'] != 'unspecified':
            val = get['defspublished'] == 'yes'

            qs = qs.filter(definition__published=val)


        fieldnames = ['idgloss', 'useInstr', 'sense', 'morph', 'StemSN',
                      'compound', 'rmrks', 'handedness',
                      'domhndsh', 'subhndsh', 'locprim', 'locVirtObj', 'relatArtic', 'relOriMov', 'relOriLoc', 'oriCh',
                      'handCh', 'repeat', 'altern',
                      'movSh', 'movDir', 'contType', 'phonOth', 'mouthG', 'mouthing', 'phonetVar', 'iconImg', 'iconType',
                      # 'namEnt', 'semField',
                      'valence',
                      'lexCatNotes', 'tokNo', 'tokNoSgnr', 'tokNoA', 'tokNoV', 'tokNoR', 'tokNoGe', 'tokNoGr', 'tokNoO',
                      'tokNoSgnrA',
                      'tokNoSgnrV', 'tokNoSgnrR', 'tokNoSgnrGe', 'tokNoSgnrGr', 'tokNoSgnrO', 'inWeb', 'isNew']


        # SignLanguage and basic property filters
        # allows for multiselect
        vals = get.getlist('dialect[]')
        if '' in vals:
            vals.remove('')
        if vals != []:
            qs = qs.filter(dialect__in=vals)

        # allows for multiselect
        vals = get.getlist('signlanguage[]')
        if '' in vals:
            vals.remove('')
        if vals != []:
            qs = qs.filter(signlanguage__in=vals)

        if 'useInstr' in get and get['useInstr'] != '':
            qs = qs.filter(useInstr__icontains=get['useInstr'])

        for fieldnamemulti in settings.MULTIPLE_SELECT_MORPHEME_FIELDS:

            fieldnamemultiVarname = fieldnamemulti + '[]'
            fieldnameQuery = fieldnamemulti + '__in'

            vals = get.getlist(fieldnamemultiVarname)
            if '' in vals:
                vals.remove('')
            if vals != []:
                qs = qs.filter(**{ fieldnameQuery: vals })

        ## phonology and semantics field filters
        for fieldname in fieldnames:

            if fieldname in get:
                key = fieldname + '__exact'
                val = get[fieldname]

                if isinstance(Gloss._meta.get_field(fieldname), NullBooleanField):
                    val = {'0': '', '1': None, '2': True, '3': False}[val]

                if val != '':
                    kwargs = {key: val}
                    qs = qs.filter(**kwargs)

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

        if 'defsearch' in get and get['defsearch'] != '':

            val = get['defsearch']

            if 'defrole' in get:
                role = get['defrole']
            else:
                role = 'all'

            if role == 'all':
                qs = qs.filter(definition__text__icontains=val)
            else:
                qs = qs.filter(definition__text__icontains=val, definition__role__exact=role)

        if 'tags' in get and get['tags'] != '':
            vals = get.getlist('tags')

            tags = []
            for t in vals:
                tags.extend(Tag.objects.filter(name=t))

            # search is an implicit AND so intersection
            tqs = TaggedItem.objects.get_intersection_by_model(Gloss, tags)

            # intersection
            qs = qs & tqs

        qs = qs.distinct()

        if 'nottags' in get and get['nottags'] != '':
            vals = get.getlist('nottags')

            tags = []
            for t in vals:
                tags.extend(Tag.objects.filter(name=t))

            # search is an implicit AND so intersection
            tqs = TaggedItem.objects.get_intersection_by_model(Gloss, tags)

            # exclude all of tqs from qs
            qs = [q for q in qs if q not in tqs]

        if 'relationToForeignSign' in get and get['relationToForeignSign'] != '':
            relations = RelationToForeignSign.objects.filter(other_lang_gloss__icontains=get['relationToForeignSign'])
            potential_pks = [relation.gloss.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if 'hasRelationToForeignSign' in get and get['hasRelationToForeignSign'] != '0':

            pks_for_glosses_with_relations = [relation.gloss.pk for relation in RelationToForeignSign.objects.all()]

            if get['hasRelationToForeignSign'] == '1':  # We only want glosses with a relation to a foreign sign
                qs = qs.filter(pk__in=pks_for_glosses_with_relations)
            elif get['hasRelationToForeignSign'] == '2':  # We only want glosses without a relation to a foreign sign
                qs = qs.exclude(pk__in=pks_for_glosses_with_relations)

        if 'relation' in get and get['relation'] != '':
            potential_targets = Gloss.objects.filter(idgloss__icontains=get['relation'])
            relations = Relation.objects.filter(target__in=potential_targets)
            potential_pks = [relation.source.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if 'hasRelation' in get and get['hasRelation'] != '':

            # Find all relations with this role
            if get['hasRelation'] == 'all':
                relations_with_this_role = Relation.objects.all()
            else:
                relations_with_this_role = Relation.objects.filter(role__exact=get['hasRelation'])

            # Remember the pk of all glosses that take part in the collected relations
            pks_for_glosses_with_correct_relation = [relation.source.pk for relation in relations_with_this_role]
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_relation)

        if 'morpheme' in get and get['morpheme'] != '':
            potential_morphemes = Gloss.objects.filter(idgloss__icontains=get['morpheme'])
            potential_morphdefs = MorphologyDefinition.objects.filter(
                morpheme__in=[morpheme.pk for morpheme in potential_morphemes])
            potential_pks = [morphdef.parent_gloss.pk for morphdef in potential_morphdefs]
            qs = qs.filter(pk__in=potential_pks)

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
            created_before_date = DT.datetime.strptime(get['createdBefore'], "%m/%d/%Y").date()
            qs = qs.filter(creationDate__range=(EARLIEST_GLOSS_CREATION_DATE, created_before_date))

        if 'createdAfter' in get and get['createdAfter'] != '':
            created_after_date = DT.datetime.strptime(get['createdAfter'], "%m/%d/%Y").date()
            qs = qs.filter(creationDate__range=(created_after_date, DT.datetime.now()))

        if 'createdBy' in get and get['createdBy'] != '':
            created_by_search_string = ' '.join(get['createdBy'].strip().split())  # remove redundant spaces
            qs = qs.annotate(
                created_by=Concat('creator__first_name', V(' '), 'creator__last_name', output_field=CharField())) \
                .filter(created_by__iregex=created_by_search_string)

        # Saving querysets results to sessions, these results can then be used elsewhere (like in gloss_detail)
        # Flush the previous queryset (just in case)
        self.request.session['search_results'] = None

        # Make sure that the QuerySet has filters applied (user is searching for something instead of showing all results [objects.all()])
        if hasattr(qs.query.where, 'children') and len(qs.query.where.children) > 0:

            items = []

            for item in qs:
                items.append(dict(id=item.id, gloss=item.idgloss))

            self.request.session['search_results'] = items

        # Sort the queryset by the parameters given
        qs = order_queryset_by_sort_order(self.request.GET, qs)

        self.request.session['search_type'] = self.search_type

        if not ('last_used_dataset' in self.request.session.keys()):
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

        fieldnames = ['idgloss', 'dataset',
                      'mrpType',
                      'useInstr', 'sense', 'StemSN', 'rmrks',
                      'handedness',
                      'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim', 'locVirtObj', 'relOriMov', 'relOriLoc',
                      'oriCh', 'contType',
                      'movSh', 'movDir', 'repeat', 'altern', 'phonOth', 'mouthG', 'mouthing', 'phonetVar',
                      'domSF', 'domFlex', 'oriChAbd', 'oriChFlex', 'iconImg', 'iconType',
                      'namEnt', 'semField', 'valence', 'lexCatNotes', 'tokNo', 'tokNoSgnr', 'tokNoA', 'tokNoV',
                      'tokNoR', 'tokNoGe',
                      'tokNoGr', 'tokNoO', 'tokNoSgnrA', 'tokNoSgnrV', 'tokNoSgnrR', 'tokNoSgnrGe',
                      'tokNoSgnrGr', 'tokNoSgnrO', 'inWeb', 'isNew']
        # Different from Gloss: we use Morpheme here
        fields = [Morpheme._meta.get_field(fieldname) for fieldname in fieldnames]

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
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

                # Try the value of the choicelist
                try:
                    row.append(getattr(gloss, 'get_' + f.name + '_display')())

                # If it's not there, try the raw value
                except AttributeError:
                    value = getattr(gloss, f.name)


                    # This was disabled with the move to Python 3... might not be needed anymore?
                    # if isinstance(value, unicode):
                    #     value = str(value.encode('ascii', 'xmlcharrefreplace'))
                    # elif not isinstance(value, str):

                    value = str(value)

                    row.append(value)

            # get languages
            signlanguages = [signlanguage.name for signlanguage in gloss.signlanguage.all()]
            row.append(", ".join(signlanguages))

            # get dialects
            dialects = [dialect.name for dialect in gloss.dialect.all()]
            row.append(", ".join(dialects))

            # get translations
            trans = [t.translation.text for t in gloss.translation_set.all()]
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

        match_machine_value = int(kwargs['pk'])

        try:
            self.object = self.get_object()
        except Http404:

            # check to see if this handshape has been created but not yet viewed
            # if that is the case, create a new handshape object and view that,
            # otherwise return an error

            handshapes = FieldChoice.objects.filter(field__iexact='Handshape')
            handshape_not_created = 1

            for o in handshapes:
                if o.machine_value == match_machine_value: # only one match
                    new_id = o.machine_value
                    new_machine_value = o.machine_value
                    new_english_name = o.english_name
                    new_dutch_name = o.dutch_name
                    new_chinese_name = o.chinese_name

                    new_handshape = Handshape(machine_value=new_machine_value, english_name=new_english_name,
                                              dutch_name=new_dutch_name, chinese_name=new_chinese_name)
                    new_handshape.save()
                    handshape_not_created = 0
                    self.object = new_handshape
                    break

            if handshape_not_created:
                return HttpResponse('<p>Handshape not configured.</p>')

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        try:
            context = super(HandshapeDetailView, self).get_context_data(**kwargs)
        except:
            # return custom template
            return HttpResponse('invalid', {'content-type': 'text/plain'})

        hs = context['handshape']

        setattr(self.request, 'search_type', self.search_type)

        labels = hs.field_labels()
        context['imageform'] = ImageUploadForHandshapeForm()

        context['choice_lists'] = {}
        context['handshape_fields'] = []
        oChoiceLists = {}

        context['handshape_fields_FS1'] = []
        context['handshape_fields_FS2'] = []
        context['handshape_fields_FC1'] = []
        context['handshape_fields_FC2'] = []
        context['handshape_fields_UF'] = []

        for field in FIELDS['handshape']:

            #Get and save the choice list for this field
            fieldchoice_category = fieldname_to_category(field)

            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category).order_by('machine_value')

            if len(choice_list) > 0:
                context['choice_lists'][field] = choicelist_queryset_to_translated_dict (choice_list,self.request.LANGUAGE_CODE)

            #Take the human value in the language we are using
            machine_value = getattr(hs, field)
            human_value = machine_value_to_translated_human_value(machine_value,choice_list,self.request.LANGUAGE_CODE)

            #And add the kind of field
            kind = fieldname_to_kind(field)

            field_label = labels[field]
            if field_label in ['Finger selection', 'T', 'I', 'M', 'R', 'P']:
                if field_label != 'Finger selection':
                    context['handshape_fields_FS1'].append([human_value, field, field_label, kind])
            elif field_label in ['Finger selection 2', 'T2', 'I2', 'M2', 'R2', 'P2']:
                if field_label != 'Finger selection 2':
                    context['handshape_fields_FS2'].append([human_value, field, field_label, kind])
            elif field_label in ['Unselected fingers', 'Tu', 'Iu', 'Mu', 'Ru', 'Pu']:
                if field_label != 'Unselected fingers':
                    context['handshape_fields_UF'].append([human_value, field, field_label, kind])
            # elif field_label == 'Finger configuration 1':
                # context['handshape_fields_FC1'].append([human_value, field, field_label, kind])
            elif field_label == 'Finger configuration 2':
                context['handshape_fields_FC2'].append([human_value, field, field_label, kind])
            else:
                context['handshape_fields'].append([human_value, field, field_label, kind])

        context['choice_lists'] = json.dumps(context['choice_lists'])

        # Check the type of the current search results

        if self.request.session['search_results'] and len(self.request.session['search_results']) > 0:
            if 'gloss' in self.request.session['search_results'][0].keys():
                self.request.session['search_results'] = None

        # if there are no current handshape search results in the current session, display all of them in the navigation bar
        if self.request.session['search_type'] != 'handshape' or self.request.session['search_results'] == None:

            self.request.session['search_type'] = self.search_type

            qs = Handshape.objects.all().order_by('machine_value')

            items = []

            for item in qs:
                if self.request.LANGUAGE_CODE == 'nl':
                    items.append(dict(id=item.machine_value, handshape=item.dutch_name))
                elif self.request.LANGUAGE_CODE == 'zh-hans':
                    items.append(dict(id=item.machine_value, handshape=item.chinese_name))
                else:
                    items.append(dict(id=item.machine_value, handshape=item.english_name))

            self.request.session['search_results'] = items

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        return context


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
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        # this is used to set up the ajax calls, one per each focus gloss in the table
        context['ids_of_all_glosses'] = [ g.id for g in Gloss.none_morpheme_objects().select_related('lemma').filter(lemma__dataset__in=selected_datasets).exclude((Q(**{'handedness__isnull': True}))).exclude((Q(**{'domhndsh__isnull': True}))) ]

        return context

    def get_queryset(self):

        # Get all existing saved Homonyms
        # relation_homonyms = Relation.objects.filter(role='homonym')

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        glosses_with_phonology = Gloss.none_morpheme_objects().select_related('lemma').filter(lemma__dataset__in=selected_datasets).exclude((Q(**{'handedness__isnull': True}))).exclude((Q(**{'domhndsh__isnull': True})))

        return glosses_with_phonology

class MinimalPairsListView(ListView):
    model = Gloss
    template_name = 'dictionary/admin_minimalpairs_list.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        # reformat LANGUAGE_CODE for use in dictionary domain, accomodate multilingual codings
        from signbank.tools import convert_language_code_to_2char
        language_code = convert_language_code_to_2char(self.request.LANGUAGE_CODE)
        language = Language.objects.get(id=get_default_language_id())
        default_language_code = language.language_code_2char

        # Refresh the "constant" translated choice lists table
        translated_choice_lists_table = generate_translated_choice_list_table()

        context = super(MinimalPairsListView, self).get_context_data(**kwargs)

        languages = Language.objects.filter(language_code_2char=self.request.LANGUAGE_CODE)
        if languages:
            context['language'] = languages[0]
        else:
            context['language'] = Language.objects.get(id=get_default_language_id())

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        field_names = []
        for field in FIELDS['phonology']:
            # the following fields are not considered for minimal pairs
            if field not in ['locVirtObj', 'phonOth', 'mouthG', 'mouthing', 'phonetVar']:
                field_names.append(field)

        field_labels = dict()
        for field in field_names:
            field_label = Gloss._meta.get_field(field).verbose_name
            field_labels[field] = field_label.encode('utf-8').decode()

        context['field_labels'] = field_labels

        context['page_number'] = context['page_obj'].number

        context['objects_on_page'] = [ g.id for g in context['page_obj'].object_list ]

        context['paginate_by'] = self.request.GET.get('paginate_by', self.paginate_by)

        return context

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)

    def get_queryset(self):

        selected_datasets = get_selected_datasets_for_user(self.request.user)

        # grab gloss ids for finger spelling glosses, identified by text #.

        finger_spelling_glosses = [ a_idgloss_trans.gloss_id for a_idgloss_trans in AnnotationIdglossTranslation.objects.filter(text__startswith="#") ]

        glosses_with_phonology = Gloss.none_morpheme_objects().select_related('lemma').filter(lemma__dataset__in=selected_datasets).exclude(id__in=finger_spelling_glosses).exclude((Q(**{'handedness__isnull': True}))).exclude((Q(**{'domhndsh__isnull': True})))

        return glosses_with_phonology

class FrequencyListView(ListView):
    # not sure what model should be used here, it applies to all the glosses in a dataset
    model = Dataset
    template_name = 'dictionary/admin_frequency_list.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(FrequencyListView, self).get_context_data(**kwargs)

        language_code = self.request.LANGUAGE_CODE
        if self.request.LANGUAGE_CODE == 'zh-hans':
            languages = Language.objects.filter(language_code_2char='zh')
            language_code = 'zh'
        else:
            languages = Language.objects.filter(language_code_2char=self.request.LANGUAGE_CODE)
        if languages:
            context['language'] = languages[0]
        else:
            context['language'] = Language.objects.get(id=get_default_language_id())

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        codes_to_adjectives = dict(settings.LANGUAGES)
        if language_code not in codes_to_adjectives.keys():
            adjective = 'english'
        else:
            adjective = codes_to_adjectives[language_code].lower()

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        context['dataset_ids'] = [ ds.id for ds in selected_datasets]

        # sort the phonology fields based on field label in the designated language
        # this is used for display in the template, by lookup
        field_labels = dict()
        for field in FIELDS['phonology']:
            if field not in ['weakprop', 'weakdrop', 'domhndsh_number', 'domhndsh_letter', 'subhndsh_number',
                             'subhndsh_letter']:
                field_kind = fieldname_to_kind(field)
                if field_kind == 'list':
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
            field_category = fieldname_to_category(field)
            field_choices = FieldChoice.objects.filter(field__iexact=field_category).order_by(adjective+'_name')
            translated_choices = choicelist_queryset_to_translated_dict(field_choices,self.request.LANGUAGE_CODE,ordered=False,id_prefix='_',shortlist=False)
            field_labels_choices[field] = dict(translated_choices)

        context['field_labels_choices'] = field_labels_choices

        # do the same for the semantics fields
        # the code is here to keep phonology and semantics in separate dicts,
        # but at the moment all results are displayed in one table in the template

        field_labels_semantics = dict()
        for field in FIELDS['semantics']:
            field_kind = fieldname_to_kind(field)
            if field_kind == 'list':
                field_label = Gloss._meta.get_field(field).verbose_name
                field_labels_semantics[field] = field_label.encode('utf-8').decode()

        field_labels_semantics_list = [ (k, v) for (k, v) in sorted(field_labels_semantics.items(), key=lambda x: x[1])]
        context['field_labels_semantics'] = field_labels_semantics
        context['field_labels_semantics_list'] = field_labels_semantics_list

        field_labels_semantics_choices = dict()
        for field, label in field_labels_semantics.items():
            field_category = fieldname_to_category(field)
            field_choices = FieldChoice.objects.filter(field__iexact=field_category).order_by(adjective+'_name')
            translated_choices = choicelist_queryset_to_translated_dict(field_choices,self.request.LANGUAGE_CODE,ordered=False,id_prefix='_',shortlist=False)
            field_labels_semantics_choices[field] = dict(translated_choices)

        context['field_labels_semantics_choices'] = field_labels_semantics_choices

        # for ease of implementation in the template, the results of the two kinds of frequencies
        # (phonology fields, semantics fields) are displayed in the same table, the lookup tables are merged so only one loop is needed

        context['all_field_labels_choices'] = dict(field_labels_choices, **field_labels_semantics_choices)

        context['all_field_labels'] = dict(field_labels, **field_labels_semantics)

        return context

    def get_queryset(self):

        user = self.request.user

        if user.is_authenticated():
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
                checker.has_perm('view_dataset', dataset)

            return qs
        else:
            # User is not authenticated
            return None

class HandshapeListView(ListView):

    model = Handshape
    template_name = 'dictionary/admin_handshape_list.html'
    search_type = 'handshape'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(HandshapeListView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books

        search_form = HandshapeSearchForm(self.request.GET)

        # Retrieve the search_type,so that we know whether the search should be restricted to Gloss or not
        if 'search_type' in self.request.GET:
            self.search_type = self.request.GET['search_type']
        else:
            self.search_type = 'handshape'

        # self.request.session['search_type'] = self.search_type

        context['searchform'] = search_form
        context['search_type'] = self.search_type
        # if self.search_type == 'sign_handshape':
        #     context['glosscount'] = Gloss.none_morpheme_objects().count()   # Only count the none-morpheme glosses
        # else:
        #     context['glosscount'] = Gloss.objects.count()  # Count the glosses + morphemes

        context['handshapefieldchoicecount'] = FieldChoice.objects.filter(field__iexact='Handshape').count()

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets
        context['signscount'] = Gloss.objects.filter(lemma__dataset__in=selected_datasets).count()

        context['HANDSHAPE_RESULT_FIELDS'] = settings.HANDSHAPE_RESULT_FIELDS

        context['handshape_fields_FS1'] = []

        context['choice_lists'] = {}

        for field in FIELDS['handshape']:

            # Get and save the choice list for this field
            fieldchoice_category = fieldname_to_category(field)

            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category).order_by('machine_value')

            if len(choice_list) > 0:
                context['choice_lists'][field] = choicelist_queryset_to_translated_dict(choice_list,
                                                                                        self.request.LANGUAGE_CODE, id_prefix='')

        context['choice_lists'] = json.dumps(context['choice_lists'])

        context['handshapescount'] = Handshape.objects.count()

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

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

        choice_lists = {}

        for field in FIELDS['handshape']:

            # Get and save the choice list for this field
            fieldchoice_category = fieldname_to_category(field)

            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category).order_by('machine_value')

            if len(choice_list) > 0:
                choice_lists[field] = choicelist_queryset_to_translated_dict(choice_list,
                                                                                        self.request.LANGUAGE_CODE, id_prefix='')

        # get query terms from self.request
        get = self.request.GET


        #Then check what kind of stuff we want
        if 'search_type' in get:
            self.search_type = get['search_type']
        else:
            self.search_type = 'handshape'

        setattr(self.request, 'search_type', self.search_type)

        qs = Handshape.objects.all().order_by('machine_value')

        handshapes = FieldChoice.objects.filter(field__iexact='Handshape')
        # Find out if any Handshapes exist for which no Handshape object has been created

        existing_handshape_objects_machine_values = [ o.machine_value for o in qs ]


        new_handshape_created = 0

        for h in handshapes:
            if h.machine_value in existing_handshape_objects_machine_values:
                pass
            else:
                # create a new Handshape object
                new_id = h.machine_value
                new_machine_value = h.machine_value
                new_english_name = h.english_name
                new_dutch_name = h.dutch_name
                new_chinese_name = h.chinese_name

                new_handshape = Handshape(machine_value=new_machine_value, english_name=new_english_name,
                                          dutch_name=new_dutch_name, chinese_name=new_chinese_name)
                new_handshape.save()
                new_handshape_created = 1


        if new_handshape_created: # if a new Handshape object was created, reload the query result

            qs = Handshape.objects.all().order_by('machine_value')

        fieldnames = ['machine_value', 'english_name', 'dutch_name', 'chinese_name',
                      'hsNumSel', 'hsFingSel', 'hsFingSel2', 'hsFingConf', 'hsFingConf2', 'hsAperture',
                      'hsThumb', 'hsSpread', 'hsFingUnsel', 'fsT', 'fsI', 'fsM', 'fsR', 'fsP',
                      'fs2T', 'fs2I', 'fs2M', 'fs2R', 'fs2P',
                      'ufT', 'ufI', 'ufM', 'ufR', 'ufP']

        ## phonology and semantics field filters
        for fieldname in fieldnames:

            if fieldname in get:
                key = fieldname + '__exact'
                val = get[fieldname]

                if fieldname == 'hsNumSel' and val != '':
                    fieldlabel = choice_lists[fieldname][val]
                    if fieldlabel == 'one':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__exact=1) | Q(hsNumSel=val))
                    elif fieldlabel == 'two':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__exact=2) | Q(hsNumSel=val))
                    elif fieldlabel == 'three':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__exact=3) | Q(hsNumSel=val))
                    elif fieldlabel == 'four':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__exact=4) | Q(hsNumSel=val))
                    elif fieldlabel == 'all':
                        qs = qs.annotate(
                            count_fs1=ExpressionWrapper(F('fsT') + F('fsI') + F('fsM') + F('fsR') + F('fsP'),
                                                        output_field=IntegerField())).filter(Q(count_fs1__gt=4) | Q(hsNumSel=val))

                if isinstance(Handshape._meta.get_field(fieldname), NullBooleanField):
                    val = {'0': False, '1': True, 'True': True, 'False': False, 'None': '', '': '' }[val]


                if self.request.LANGUAGE_CODE == 'nl' and fieldname == 'dutch_name' and val != '':
                    query = Q(dutch_name__icontains=val)
                    qs = qs.filter(query)

                if self.request.LANGUAGE_CODE == 'zh-hans' and fieldname == 'chinese_name' and val != '':
                    query = Q(chinese_name__icontains=val)
                    qs = qs.filter(query)

                if fieldname == 'english_name' and val != '':
                    query = Q(english_name__icontains=val)
                    qs = qs.filter(query)


                if val != '' and fieldname != 'hsNumSel' and fieldname != 'dutch_name' and fieldname != 'chinese_name' and fieldname != 'english_name':
                    kwargs = {key: val}
                    qs = qs.filter(**kwargs)

        # Handshape searching of signs relies on using the search_results in order to search signs that have the handshapes
        # The search_results is no longer set to None

        # Make sure that the QuerySet has filters applied (user is searching for something instead of showing all results [objects.all()])

        if hasattr(qs.query.where, 'children') and len(qs.query.where.children) > 0:

            items = []

            for item in qs:
                if self.request.LANGUAGE_CODE == 'nl':
                    items.append(dict(id = item.machine_value, handshape = item.dutch_name))
                elif self.request.LANGUAGE_CODE == 'zh-hans':
                    items.append(dict(id = item.machine_value, handshape = item.chinese_name))
                else:
                    items.append(dict(id = item.machine_value, handshape = item.english_name))

            self.request.session['search_results'] = items

        if ('sortOrder' in get and get['sortOrder'] != 'machine_value'):
            # User has toggled the sort order for the column
            qs = order_handshape_queryset_by_sort_order(self.request.GET, qs)
        else:
            # The default is to order the signs alphabetically by whether there is an angle bracket
            qs = order_handshape_by_angle(qs, self.request.LANGUAGE_CODE)

        if self.search_type == 'sign_handshape':

            # search for signs with found hadnshapes
            # find relevant machine values for handshapes
            selected_handshapes = [ h.machine_value for h in qs ]
            selected_datasets = get_selected_datasets_for_user(self.request.user)

            if len(selected_handshapes) == (Handshape.objects.all().count()):

                qs = Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(Q(domhndsh__in=selected_handshapes)
                                          | Q(domhndsh__isnull=True) | Q(domhndsh__exact='0')
                                          | Q(subhndsh__in=selected_handshapes) | Q(subhndsh__isnull=True) | Q(subhndsh__exact='0'))

            else:
                qs = Gloss.objects.filter(lemma__dataset__in=selected_datasets).filter(Q(domhndsh__in=selected_handshapes) | Q(subhndsh__in=selected_handshapes))

        self.request.session['search_type'] = self.search_type

        return qs


class DatasetListView(ListView):
    model = Dataset
    # set the default dataset, this should not be empty
    dataset_name = DEFAULT_DATASET


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DatasetListView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

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
        if self.request.user.is_authenticated():
            pass
        else:
            messages.add_message(self.request, messages.ERROR, ('Please login to use this functionality.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, ('Dataset name must be non-empty.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        try:
            dataset_object = Dataset.objects.get(name=self.dataset_name)
        except:
            messages.add_message(self.request, messages.ERROR, ('No dataset with name '+self.dataset_name+' found.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        # make sure the user can write to this dataset
        # from guardian.shortcuts import get_objects_for_user
        user_view_datasets = get_objects_for_user(self.request.user, 'view_dataset', Dataset, accept_global_perms=False)
        if user_view_datasets and not dataset_object in user_view_datasets:
            # the user currently has no view permission for the requested dataset
            pass
        else:
            # this should not happen from the html page. the check is made to catch a user adding a parameter to the url
            messages.add_message(self.request, messages.INFO, ('You can already view this dataset.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        from django.contrib.auth.models import Group, User
        group_manager = Group.objects.get(name='Dataset_Manager')

        owners_of_dataset = dataset_object.owners.all()
        dataset_manager_found = False
        for owner in owners_of_dataset:

            groups_of_user = owner.groups.all()
            if not group_manager in groups_of_user:
                # this owner can't manage users
                continue

            dataset_manager_found = True
            # send email to the dataset manager
            from django.core.mail import send_mail
            current_site = Site.objects.get_current()

            subject = render_to_string('registration/dataset_access_email_subject.txt',
                                       context={'dataset': dataset_object.name,
                                                'site': current_site})
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())

            message = render_to_string('registration/dataset_access_request_email.txt',
                                       context={'user': self.request.user,
                                                'dataset': dataset_object.name,
                                                'site': current_site})

            # for debug purposes on local machine
            # print('grant access subject: ', subject)
            # print('message: ', message)
            # print('owner of dataset: ', owner.username, ' with email: ', owner.email)
            # print('user email: ', owner.email)

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [owner.email])

        if not dataset_manager_found:
            messages.add_message(self.request, messages.ERROR, ('No dataset manager has been found for '+dataset_object.name+'. Your request could not be submitted.'))
        else:
            messages.add_message(self.request, messages.INFO, ('Your request for view access to dataset '+dataset_object.name+' has been submitted.'))
        return HttpResponseRedirect(URL + '/datasets/available')

    def render_to_ecv_export_response(self, context):

        # check that the user is logged in
        if self.request.user.is_authenticated():
            pass
        else:
            messages.add_message(self.request, messages.ERROR, ('Please login to use this functionality.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, ('Dataset name must be non-empty.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        try:
            dataset_object = Dataset.objects.get(name=self.dataset_name)
        except:
            messages.add_message(self.request, messages.ERROR, ('No dataset with name '+self.dataset_name+' found.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # make sure the user can write to this dataset
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = get_objects_for_user(self.request.user, 'change_dataset', Dataset, accept_global_perms=False)
        if user_change_datasets and dataset_object in user_change_datasets:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, ('No permission to export dataset.'))
            return HttpResponseRedirect(reverse('admin_dataset_view'))

        # if we get to here, the user is authenticated and has permission to export the dataset
        ecv_file = write_ecv_file_for_dataset(self.dataset_name)

        messages.add_message(self.request, messages.INFO, ('ECV ' + self.dataset_name + ' successfully updated.'))
        # return HttpResponse('ECV successfully updated.')
        return HttpResponseRedirect(reverse('admin_dataset_view'))

    def get_queryset(self):
        user = self.request.user

        # get query terms from self.request
        get = self.request.GET

        # Then check what kind of stuff we want
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        # otherwise the default dataset_name DEFAULT_DATASET is used

        setattr(self.request, 'dataset_name', self.dataset_name)

        if user.is_authenticated():
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
                checker.has_perm('view_dataset', dataset)

            qs = qs.annotate(Count('lemmaidgloss__gloss')).order_by('name')

            return qs
        else:
            # User is not authenticated
            return None

class DatasetManagerView(ListView):
    model = Dataset
    template_name = 'dictionary/admin_dataset_manager.html'

    # set the default dataset, this should not be empty
    dataset_name = DEFAULT_DATASET


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DatasetManagerView, self).get_context_data(**kwargs)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        return context

    def render_to_response(self, context):
        if 'add_view_perm' in self.request.GET or 'add_change_perm' in self.request.GET \
                    or 'delete_view_perm' in self.request.GET or 'delete_change_perm' in self.request.GET:
            return self.render_to_add_user_response(context)
        elif 'default_language' in self.request.GET:
            return self.render_to_set_default_language()
        else:
            return super(DatasetManagerView, self).render_to_response(context)

    def check_user_permissions_for_managing_dataset(self, dataset_object):
        """
        Checks whether the logged in user has permission to manage the dataset object
        :return: 
        """
        # check that the user is logged in
        if self.request.user.is_authenticated():
            pass
        else:
            messages.add_message(self.request, messages.ERROR, ('Please login to use this functionality.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        # check if the user can manage this dataset
        from django.contrib.auth.models import Group, User

        try:
            group_manager = Group.objects.get(name='Dataset_Manager')
        except:
            messages.add_message(self.request, messages.ERROR, ('No group Dataset_Manager found.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        groups_of_user = self.request.user.groups.all()
        if not group_manager in groups_of_user:
            messages.add_message(self.request, messages.ERROR,
                                 ('You must be in group Dataset Manager to modify dataset permissions.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager'))

        # make sure the user can write to this dataset
        # from guardian.shortcuts import get_objects_for_user
        user_change_datasets = get_objects_for_user(self.request.user, 'change_dataset', Dataset,
                                                    accept_global_perms=False)
        if user_change_datasets and dataset_object in user_change_datasets:
            pass
        else:
            messages.add_message(self.request, messages.ERROR, ('No permission to modify dataset permissions.'))
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
            messages.add_message(self.request, messages.ERROR, ('Dataset name must be non-empty.'))
            return None, HttpResponseRedirect(reverse('admin_dataset_manager'))

        try:
            return Dataset.objects.get(name=self.dataset_name), None
        except:
            messages.add_message(self.request, messages.ERROR,
                                 ('No dataset with name ' + self.dataset_name + ' found.'))
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
                                 ('Username must be non-empty. Please make a selection using the drop-down list.'))
            return None, HttpResponseRedirect(reverse('admin_dataset_manager'))

        try:
            return User.objects.get(username=username), None
        except:
            messages.add_message(self.request, messages.ERROR, ('No user with name ' + username + ' found.'))
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
                                     ('The default language of {} is set to {}.'
                                      .format(dataset_object.name, language.name)))
            else:
                messages.add_message(self.request, messages.INFO,
                                     ('{} is not in the set of languages of dataset {}.'
                                      .format(language.name, dataset_object.name)))
        except:
            messages.add_message(self.request, messages.ERROR,
                                 ('Something went wrong setting the default language for '
                                  + dataset_object.name))
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
        manage_identifier = 'dataset_' + dataset_object.name.replace(' ','')

        from guardian.shortcuts import assign_perm, remove_perm
        if 'add_view_perm' in self.request.GET:
            manage_identifier += '_manage_view'
            if dataset_object in get_objects_for_user(user_object, 'view_dataset', Dataset, accept_global_perms=False):
                if user_object.is_staff or user_object.is_superuser:
                    messages.add_message(self.request, messages.INFO,
                                     ('User ' + username + ' (' + user_object.first_name + ' ' + user_object.last_name +
                                      ') already has view permission for this dataset as staff or superuser.'))
                else:
                    messages.add_message(self.request, messages.INFO,
                                     ('User ' + username + ' (' + user_object.first_name + ' ' + user_object.last_name +
                                      ') already has view permission for this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_manager')+'?'+manage_identifier)

            try:
                assign_perm('view_dataset', user_object, dataset_object)
                messages.add_message(self.request, messages.INFO,
                                 ('View permission for user ' + username + ' (' + user_object.first_name + ' ' + user_object.last_name + ') successfully granted.'))

                if not user_object.is_active:
                    user_object.is_active = True
                    assign_perm('dictionary.search_gloss', user_object)
                    user_object.save()

                # send email to user
                from django.core.mail import send_mail
                current_site = Site.objects.get_current()

                subject = render_to_string('registration/dataset_access_granted_email_subject.txt',
                                           context={'dataset': dataset_object.name,
                                                    'site': current_site})
                # Email subject *must not* contain newlines
                subject = ''.join(subject.splitlines())

                message = render_to_string('registration/dataset_access_granted_email.txt',
                                           context={'dataset': dataset_object.name,
                                                    'site': current_site})

                # for debug purposes on local machine
                # print('grant access subject: ', subject)
                # print('message: ', message)
                # print('user email: ', user_object.email)

                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_object.email])

            except:
                messages.add_message(self.request, messages.ERROR, ('Error assigning view dataset permission to user '+username+'.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager')+'?'+manage_identifier)

        if 'add_change_perm' in self.request.GET:
            manage_identifier += '_manage_change'
            if dataset_object in get_objects_for_user(user_object, 'change_dataset', Dataset, accept_global_perms=False):
                if user_object.is_staff or user_object.is_superuser:
                    messages.add_message(self.request, messages.INFO,
                                         (
                                         'User ' + username + ' (' + user_object.first_name + ' ' + user_object.last_name +
                                         ') already has change permission for this dataset as staff or superuser.'))
                else:
                    messages.add_message(self.request, messages.INFO,
                                 ('User ' + username + ' (' + user_object.first_name + ' ' + user_object.last_name +
                                  ') already has change permission for this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)

            if not dataset_object in get_objects_for_user(user_object, 'view_dataset', Dataset, accept_global_perms=False):
                messages.add_message(self.request, messages.WARNING,
                                     (
                                     'User ' + username + ' (' + user_object.first_name + ' ' + user_object.last_name +
                                     ') does not have view permission for this dataset. Please grant view permission first.'))

                # open Manage View Dataset pane instead of Manage Change Dataset
                manage_identifier = 'dataset_' + dataset_object.name.replace(' ', '')
                manage_identifier += '_manage_view'
                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)
            try:
                assign_perm('change_dataset', user_object, dataset_object)

                # send email to new user
                # probably don't want to assign change permission to new users

                messages.add_message(self.request, messages.INFO,
                                     ('Change permission for user ' + username + ' successfully granted.'))
            except:
                messages.add_message(self.request, messages.ERROR, ('Error assigning change dataset permission to user '+username+'.'))
            return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)

        if 'delete_view_perm' in self.request.GET:
            manage_identifier += '_manage_view'

            if dataset_object in get_objects_for_user(user_object, 'view_dataset', Dataset, accept_global_perms=False):
                if user_object.is_staff or user_object.is_superuser:
                    messages.add_message(self.request, messages.ERROR,
                                         (
                                         'User ' + username + ' (' + user_object.first_name + ' ' + user_object.last_name +
                                         ') has view permission for this dataset as staff or superuser. This cannot be modified here.'))
                else:
                    # can remove permission
                    try:
                        # also need to remove change_dataset perm in this case
                        from guardian.shortcuts import remove_perm
                        remove_perm('view_dataset', user_object, dataset_object)
                        remove_perm('change_dataset', user_object, dataset_object)
                        messages.add_message(self.request, messages.INFO,
                                             ('View (and change) permission for user ' + username + ' successfully revoked.'))
                    except:
                        messages.add_message(self.request, messages.ERROR,
                                             ('Error revoking view dataset permission for user ' + username + '.'))

                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)
            else:
                messages.add_message(self.request, messages.ERROR, ('User '+username+' currently has no permission to view this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)

        if 'delete_change_perm' in self.request.GET:
            manage_identifier += '_manage_change'

            if dataset_object in get_objects_for_user(user_object, 'change_dataset', Dataset, accept_global_perms=False):
                if user_object.is_staff or user_object.is_superuser:
                    messages.add_message(self.request, messages.ERROR,
                                         (
                                         'User ' + username + ' (' + user_object.first_name + ' ' + user_object.last_name +
                                         ') has change permission for this dataset as staff or superuser. This cannot be modified here.'))
                else:
                    # can remove permission
                    try:
                        remove_perm('change_dataset', user_object, dataset_object)
                        messages.add_message(self.request, messages.INFO,
                                             ('Change permission for user ' + username + ' successfully revoked.'))
                    except:
                        messages.add_message(self.request, messages.ERROR,
                                             ('Error revoking change dataset permission for user ' + username + '.'))

                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)
            else:
                messages.add_message(self.request, messages.ERROR, ('User '+username+' currently has no permission to change this dataset.'))
                return HttpResponseRedirect(reverse('admin_dataset_manager') + '?' + manage_identifier)

        # the code doesn't seem to get here. if somebody puts something else in the url (else case), there is no (hidden) csrf token.
        messages.add_message(self.request, messages.ERROR, ('Unrecognised argument to dataset manager url.'))
        return HttpResponseRedirect(reverse('admin_dataset_manager'))

    def get_queryset(self):
        user = self.request.user

        # get query terms from self.request
        get = self.request.GET

        # Then check what kind of stuff we want
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        # otherwise the default dataset_name DEFAULT_DATASET is used

        setattr(self.request, 'dataset_name', self.dataset_name)

        if user.is_authenticated():

            # determine if user is a dataset manager
            from django.contrib.auth.models import Group, User
            try:
                group_manager = Group.objects.get(name='Dataset_Manager')
            except:
                messages.add_message(self.request, messages.ERROR, ('No group Dataset_Manager found.'))
                return HttpResponseRedirect(URL + '/datasets/available')

            groups_of_user = self.request.user.groups.all()
            if not group_manager in groups_of_user:
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
    dataset_name = DEFAULT_DATASET

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):

        try:
            self.object = self.get_object()
        # except Http404:
        except:
            # return custom template
            # return render(request, 'dictionary/warning.html', status=404)
            raise Http404()

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
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        return context

    def render_to_response(self, context):
        if 'add_owner' in self.request.GET:
            return self.render_to_add_owner_response(context)
        else:
            return super(DatasetDetailView, self).render_to_response(context)

    def render_to_add_owner_response(self, context):

        # check that the user is logged in
        if self.request.user.is_authenticated():
            pass
        else:
            messages.add_message(self.request, messages.ERROR, ('Please login to use this functionality.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        # check if the user can manage this dataset
        from django.contrib.auth.models import Group, User

        try:
            group_manager = Group.objects.get(name='Dataset_Manager')
        except:
            messages.add_message(self.request, messages.ERROR, ('No group Dataset_Manager found.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        groups_of_user = self.request.user.groups.all()
        if not group_manager in groups_of_user:
            messages.add_message(self.request, messages.ERROR, ('You must be in group Dataset Manager to modify dataset permissions.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        # if the dataset is specified in the url parameters, set the dataset_name variable
        get = self.request.GET
        if 'dataset_name' in get:
            self.dataset_name = get['dataset_name']
        if self.dataset_name == '':
            messages.add_message(self.request, messages.ERROR, ('Dataset name must be non-empty.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        try:
            dataset_object = Dataset.objects.get(name=self.dataset_name)
        except:
            messages.add_message(self.request, messages.ERROR, ('No dataset with name '+self.dataset_name+' found.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        username = ''
        if 'username' in get:
            username = get['username']
        if username == '':
            messages.add_message(self.request, messages.ERROR, ('Username must be non-empty.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        try:
            user_object = User.objects.get(username=username)
        except:
            messages.add_message(self.request, messages.ERROR, ('No user with name '+username+' found.'))
            return HttpResponseRedirect(URL + '/datasets/available')

        # if we get to here, we have a dataset object and a user object to add as an owner of the dataset

        dataset_object.owners.add(user_object)
        dataset_object.save()

        messages.add_message(self.request, messages.INFO,
                     ('User ' + username + ' successfully made (co-)owner of this dataset.'))

        return HttpResponseRedirect(URL + '/datasets/detail/' + str(dataset_object.id))


def order_handshape_queryset_by_sort_order(get, qs):
    """Change the sort-order of the query set, depending on the form field [sortOrder]

    This function is used both by HandshapeListView.
    The value of [sortOrder] is 'machine_value' by default.
    [sortOrder] is a hidden field inside the "adminsearch" html form in the template admin_handshape_list.html
    Its value is changed by clicking the up/down buttons in the second row of the search result table
    """

    def get_string_from_tuple_list(lstTuples, number):
        """Get the string value corresponding to a number in a list of number-string tuples"""
        sBack = [tup[1] for tup in lstTuples if tup[0] == number]
        return sBack

    # Helper: order a queryset on field [sOrder], which is a number from a list of tuples named [sListName]
    def order_queryset_by_tuple_list(qs, sOrder, sListName):
        """Order a queryset on field [sOrder], which is a number from a list of tuples named [sListName]"""

        # Get a list of tuples for this sort-order
        tpList = build_choice_list(sListName)
        # Determine sort order: ascending is default
        bReversed = False
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrder = sOrder[1:]
            bReversed = True

        # Order the list of tuples alphabetically
        # (NOTE: they are alphabetical from 'build_choice_list()', except for the values 0,1)
        tpList = sorted(tpList, key=operator.itemgetter(1))
        # Order by the string-values in the tuple list
        return sorted(qs, key=lambda x: get_string_from_tuple_list(tpList, getattr(x, sOrder)), reverse=bReversed)

    # Set the default sort order
    sOrder = 'machine_value'  # Default sort order if nothing is specified
    # See if the form contains any sort-order information
    if ('sortOrder' in get and get['sortOrder'] != ''):
        # Take the user-indicated sort order
        sOrder = get['sortOrder']

    # The ordering method depends on the kind of field:
    # (1) text fields are ordered straightforwardly
    # (2) fields made from a choice_list need special treatment
    if (sOrder.endswith('hsThumb')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Thumb")
    elif (sOrder.endswith('hsFingConf') or sOrder.endswith('hsFingConf2')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "JointConfiguration")
    elif (sOrder.endswith('hsAperture')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Aperture")
    elif (sOrder.endswith('hsSpread')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Spreading")
    elif (sOrder.endswith('hsNumSel')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "Quantity")
    elif (sOrder.endswith('hsFingSel') or sOrder.endswith('hsFingSel2') or sOrder.endswith('hsFingUnsel')):
        ordered = order_queryset_by_tuple_list(qs, sOrder, "FingerSelection")
    else:
        # Use straightforward ordering on field [sOrder]

        bReversed = False
        if (sOrder[0:1] == '-'):
            # A starting '-' sign means: descending order
            sOrder = sOrder[1:]
            bReversed = True

        qs_letters = qs.filter(**{sOrder+'__regex':r'^[a-zA-Z]'})
        qs_special = qs.filter(**{sOrder+'__regex':r'^[^a-zA-Z]'})

        ordered = sorted(qs_letters, key=lambda x: getattr(x, sOrder))
        ordered += sorted(qs_special, key=lambda x: getattr(x, sOrder))

        if bReversed:
            ordered.reverse()

    # return the ordered list
    return ordered

def order_handshape_by_angle(qs, language_code):
    # put the handshapes with an angle bracket > in the name after the others
    # the language code is that of the interface

    if language_code == 'nl':
        qs_no_angle = qs.filter(**{'dutch_name__regex':r'^[^>]+$'})
        qs_angle = qs.filter(**{'dutch_name__regex':r'^.+>.+$'})
        ordered = sorted(qs_no_angle, key=lambda x: x.dutch_name)
        ordered += sorted(qs_angle, key=lambda x: x.dutch_name)
    elif language_code == 'zh-hans':
        qs_no_angle = qs.filter(**{'chinese_name__regex':r'^[^>]*$'})
        qs_angle = qs.filter(**{'chinese_name__regex':r'^.+>.+$'})
        ordered = sorted(qs_no_angle, key=lambda x: x.chinese_name)
        ordered += sorted(qs_angle, key=lambda x: x.chinese_name)
    else:
        qs_no_angle = qs.filter(**{'english_name__regex':r'^[^>]+$'})
        qs_angle = qs.filter(**{'english_name__regex':r'^.+>.+$'})
        ordered = sorted(qs_no_angle, key=lambda x: x.english_name)
        ordered += sorted(qs_angle, key=lambda x: x.english_name)

    return ordered

class MorphemeDetailView(DetailView):
    model = Morpheme
    context_object_name = 'morpheme'
    last_used_dataset = None

    # Overriding the get method get permissions right

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        # except Http404:
        except:
            # return custom template
            # return render(request, 'dictionary/warning.html', status=404)
            raise Http404()

        if request.user.is_authenticated():
            if self.object.dataset not in get_objects_for_user(request.user, 'view_dataset', Dataset, accept_global_perms=False):
                if self.object.inWeb:
                    return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
                else:
                    messages.add_message(request, messages.WARNING, 'You are not allowed to see this morpheme.')
                    return HttpResponseRedirect('/')
        else:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'glossid': self.object.pk}))
            else:
                return HttpResponseRedirect(reverse('registration:auth_login'))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(MorphemeDetailView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['tagform'] = TagUpdateForm()
        context['videoform'] = VideoUploadForGlossForm()
        context['imageform'] = ImageUploadForGlossForm()
        context['definitionform'] = DefinitionForm()
        context['relationform'] = RelationForm()
        context['morphologyform'] = MorphemeMorphologyForm()
        context['othermediaform'] = OtherMediaForm()
        context['navigation'] = context['morpheme'].navigation(True)
        context['interpform'] = InterpreterFeedbackForm()
        context['SIGN_NAVIGATION'] = settings.SIGN_NAVIGATION

        # Get the set of all the Gloss signs that point to me
        other_glosses_that_point_to_morpheme = SimultaneousMorphologyDefinition.objects.filter(morpheme_id__exact=context['morpheme'].id)
        context['appears_in'] = []

        word_class_choices = FieldChoice.objects.filter(field__iexact='WordClass')

        for sim_morph in other_glosses_that_point_to_morpheme:
            parent_gloss = sim_morph.parent_gloss
            if parent_gloss.wordClass:
                translated_word_class = machine_value_to_translated_human_value(parent_gloss.wordClass,word_class_choices,self.request.LANGUAGE_CODE)
            else:
                translated_word_class = ''

            context['appears_in'].append((parent_gloss, translated_word_class))

        try:
            # Note: setting idgloss to context['morpheme'] is not enough; the ".idgloss" needs to be specified
            next_morpheme = Morpheme.objects.get(idgloss=context['morpheme'].idgloss).admin_next_morpheme()
        except:
            next_morpheme = None
        if next_morpheme == None:
            context['nextmorphemeid'] = context['morpheme'].pk
        else:
            context['nextmorphemeid'] = next_morpheme.pk

        if settings.SIGN_NAVIGATION:
            context['glosscount'] = Morpheme.objects.count()
            context['glossposn'] = Morpheme.objects.filter(sn__lt=context['morpheme'].sn).count() + 1

        # Pass info about which fields we want to see
        gl = context['morpheme']
        labels = gl.field_labels()

        # set a session variable to be able to pass the gloss's id to the ajax_complete method
        # the last_used_dataset name is updated to that of this gloss
        # if a sequesce of glosses are being created by hand, this keeps the dataset setting the same
        if gl.dataset:
            self.request.session['datasetid'] = gl.dataset.id
            self.last_used_dataset = gl.dataset.name
        else:
            self.request.session['datasetid'] = get_default_language_id()

        self.request.session['last_used_dataset'] = self.last_used_dataset

        context['choice_lists'] = {}

        # Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['phonology', 'semantics', 'frequency']:
            context[topic + '_fields'] = []

            for field in FIELDS[topic]:

                # Get and save the choice list for this field
                field_category = fieldname_to_category(field)
                choice_list = FieldChoice.objects.filter(field__iexact=field_category)

                if len(choice_list) > 0:
                    context['choice_lists'][field] = choicelist_queryset_to_translated_dict(choice_list,
                                                                                                    self.request.LANGUAGE_CODE)

                # Take the human value in the language we are using
                machine_value = getattr(gl, field)
                human_value = machine_value_to_translated_human_value(machine_value,choice_list,self.request.LANGUAGE_CODE)

                # And add the kind of field
                kind = fieldname_to_kind(field)

                context[topic + '_fields'].append([human_value, field, labels[field], kind])

        # Gather the OtherMedia
        context['other_media'] = []
        other_media_type_choice_list = FieldChoice.objects.filter(field__iexact='OthermediaType')

        for other_media in gl.othermedia_set.all():

            human_value_media_type = machine_value_to_translated_human_value(other_media.type,other_media_type_choice_list,self.request.LANGUAGE_CODE)

            path = settings.STATIC_URL + 'othermedia/' + other_media.path
            context['other_media'].append([other_media.pk, path, human_value_media_type, other_media.alternative_gloss])

            # Save the other_media_type choices (same for every other_media, but necessary because they all have other ids)
            context['choice_lists'][
                'other-media-type_' + str(other_media.pk)] = choicelist_queryset_to_translated_dict(
                other_media_type_choice_list, self.request.LANGUAGE_CODE)

        context['choice_lists']['morph_type'] = choicelist_queryset_to_translated_dict(FieldChoice.objects.filter(field__iexact='MorphemeType'),self.request.LANGUAGE_CODE)

        context['choice_lists'] = json.dumps(context['choice_lists'])

        # make lemma group empty for Morpheme (ask Onno about this)
        # Morpheme Detail View shares the gloss_edit.js code with Gloss Detail View
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

        morph_typ_choices = FieldChoice.objects.filter(field__iexact='MorphemeType')

        if gl.mrpType:
            translated_morph_type = machine_value_to_translated_human_value(gl.mrpType,morph_typ_choices,self.request.LANGUAGE_CODE)
        else:
            translated_morph_type = ''

        context['morpheme_type'] = translated_morph_type


        # Put translations (keywords) per language in the context
        context['translations_per_language'] = {}
        if gl.dataset:
            for language in gl.dataset.translation_languages.all():
                context['translations_per_language'][language] = gl.translation_set.filter(language=language)
        else:
            language = Language.objects.get(id=get_default_language_id())
            context['translations_per_language'][language] = gl.translation_set.filter(language=language)


        context['separate_english_idgloss_field'] = SEPARATE_ENGLISH_IDGLOSS_FIELD

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
            context['dataset_choices'] = {}
            user = self.request.user
            if user.is_authenticated():
                qs = get_objects_for_user(user, 'view_dataset', Dataset, accept_global_perms=False)
                dataset_choices = dict()
                for dataset in qs:
                    dataset_choices[dataset.name] = dataset.name
                context['dataset_choices'] = json.dumps(dataset_choices)

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix
        return context

def gloss_ajax_search_results(request):
    """Returns a JSON list of glosses that match the previous search stored in sessions"""

    if 'search_type' in request.session.keys() and \
            (request.session['search_type'] == 'sign' or request.session['search_type'] == 'morpheme' or request.session['search_type'] == 'sign_or_morpheme'):
        return HttpResponse(json.dumps(request.session['search_results']))
    else:
        return HttpResponse(json.dumps(None))

def handshape_ajax_search_results(request):
    """Returns a JSON list of handshapes that match the previous search stored in sessions"""

    if 'search_type' in request.session.keys() and request.session['search_type'] == 'handshape':
        return HttpResponse(json.dumps(request.session['search_results']))
    else:
        return HttpResponse(json.dumps(None))

def gloss_ajax_complete(request, prefix):
    """Return a list of glosses matching the search term
    as a JSON structure suitable for typeahead."""

    datasetid = request.session['datasetid']
    dataset_id = Dataset.objects.get(id=datasetid)

    query = Q(lemma__lemmaidglosstranslation__text__istartswith=prefix) | \
            Q(annotationidglosstranslation__text__istartswith=prefix) | \
            Q(sn__startswith=prefix)
    qs = Gloss.objects.filter(query).distinct()

    from signbank.tools import convert_language_code_to_2char
    language_code = convert_language_code_to_2char(request.LANGUAGE_CODE)

    result = []
    for g in qs:
        if g.dataset == dataset_id:
            default_annotationidglosstranslation = ""
            annotationidglosstranslation = g.annotationidglosstranslation_set.get(language__language_code_2char=language_code)
            if annotationidglosstranslation:
                default_annotationidglosstranslation = annotationidglosstranslation.text
            else:
                annotationidglosstranslation = g.annotationidglosstranslation_set.get(
                    language__language_code_2char='en')
                if annotationidglosstranslation:
                    default_annotationidglosstranslation = annotationidglosstranslation.text
            result.append({'idgloss': g.idgloss, 'annotation_idgloss': default_annotationidglosstranslation, 'sn': g.sn, 'pk': "%s" % (g.id)})

    return HttpResponse(json.dumps(result), {'content-type': 'application/json'})

def handshape_ajax_complete(request, prefix):
    """Return a list of handshapes matching the search term
    as a JSON structure suitable for typeahead."""

    if request.LANGUAGE_CODE == 'nl':
        query = Q(dutch_name__istartswith=prefix)
    elif request.LANGUAGE_CODE == 'zh-hans':
        query = Q(chinese_name__istartswith=prefix)
    else:
        query = Q(english_name__istartswith=prefix)

    qs = Handshape.objects.filter(query)

    result = []
    for g in qs:
        result.append({'dutch_name': g.dutch_name, 'english_name': g.english_name, 'machine_value': g.machine_value, 'chinese_name': g.chinese_name})

    return HttpResponse(json.dumps(result), {'content-type': 'application/json'})

def morph_ajax_complete(request, prefix):
    """Return a list of morphs matching the search term
    as a JSON structure suitable for typeahead."""

    datasetid = request.session['datasetid']
    dataset_id = Dataset.objects.get(id=datasetid)

    query = Q(idgloss__istartswith=prefix) | \
            Q(annotationidglosstranslation__text__istartswith=prefix) | \
            Q(sn__startswith=prefix)
    qs = Morpheme.objects.filter(query).distinct()

    result = []
    for g in qs:
        if g.dataset == dataset_id:
            default_annotationidglosstranslation = ""
            annotationidglosstranslation = g.annotationidglosstranslation_set.get(language__language_code_2char=request.LANGUAGE_CODE)
            if annotationidglosstranslation:
                default_annotationidglosstranslation = annotationidglosstranslation.text
            else:
                annotationidglosstranslation = g.annotationidglosstranslation_set.get(
                    language__language_code_2char='en')
                if annotationidglosstranslation:
                    default_annotationidglosstranslation = annotationidglosstranslation.text
            result.append({'idgloss': g.idgloss, 'annotation_idgloss': default_annotationidglosstranslation, 'sn': g.sn,
                           'pk': "%s" % (g.id)})

    return HttpResponse(json.dumps(result), {'content-type': 'application/json'})

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

    return HttpResponse(json.dumps(result), {'content-type': 'application/json'})


def lemma_ajax_complete(request, dataset_id, q):
    """Return a list of users matching the search term
    as a JSON structure suitable for typeahead."""

    lemmas = LemmaIdgloss.objects.filter(dataset_id=dataset_id, lemmaidglosstranslation__text__icontains=q)
    lemmas_dict = [{'pk': lemma.pk, 'lemma': str(lemma)} for lemma in lemmas]

    return HttpResponse(json.dumps(lemmas_dict), {'content-type': 'application/json'})

def homonyms_ajax_complete(request, gloss_id):

    language_code = request.LANGUAGE_CODE

    if language_code == "zh-hans":
        language_code = "zh"

    try:
        this_gloss = Gloss.objects.get(id=gloss_id)
        homonym_objects = this_gloss.homonym_objects()
    except:
        homonym_objects = []

    result = []
    for homonym in homonym_objects:
        translation = ""
        translations = homonym.annotationidglosstranslation_set.filter(language__language_code_2char=language_code)
        if translations is not None and len(translations) > 0:
            translation = translations[0].text
        else:
            translations = homonym.annotationidglosstranslation_set.filter(language__language_code_3char='eng')
            if translations is not None and len(translations) > 0:
                translation = translations[0].text

        result.append({ 'id': str(homonym.id), 'gloss': translation })
        # result.append({ 'id': str(homonym.id), 'gloss': str(homonym) })

    homonyms_dict = { str(gloss_id) : result }

    return HttpResponse(json.dumps(homonyms_dict), {'content-type': 'application/json'})

def minimalpairs_ajax_complete(request, gloss_id, gloss_detail=False):

    if 'gloss_detail' in request.GET:
        gloss_detail = request.GET['gloss_detail']

    language_code = request.LANGUAGE_CODE

    if language_code == "zh-hans":
        language_code = "zh"

    this_gloss = Gloss.objects.get(id=gloss_id)

    try:
        minimalpairs_objects = this_gloss.minimal_pairs_dict()
    except:
        minimalpairs_objects = []

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
            # print('values: ', values)
            other_gloss_dict['field'] = field
            other_gloss_dict['field_display'] = values[0]
            other_gloss_dict['field_category'] = values[1]
            # print('field: ', field, ', choice: ', values[2])
            # print('translated_choice_lists_table: ', translated_choice_lists_table[field])
            focus_gloss_choice = values[2]
            other_gloss_choice = values[3]
            field_kind = values[4]
            # print('other gloss ', minimalpairs_object.id, ', field ', field, ': kind and choices: ', field_kind, ', ', focus_gloss_choice, ', ', other_gloss_choice)
            if field_kind == 'list':
                if focus_gloss_choice:
                    try:
                        focus_gloss_value = translated_choice_lists_table[field][int(focus_gloss_choice)][language_code]
                    except:
                        focus_gloss_value = 'ERROR_' + focus_gloss_choice
                        print('Error for gloss ', minimalpairs_object.id, ' on stored choice (field: ', field, ', choice: ', focus_gloss_choice, ')')
                else:
                    focus_gloss_value = '-'
            elif field_kind == 'check':
                if focus_gloss_choice == 'True':
                    focus_gloss_value = _('Yes')
                elif focus_gloss_choice == 'Neutral' and field in ['weakdrop', 'weakprop']:
                    focus_gloss_value = _('Neutral')
                else:
                    focus_gloss_value = _('No')
            else:
                # translate Boolean fields
                focus_gloss_value = focus_gloss_choice
            # print('focus gloss choice: ', focus_gloss_value)
            other_gloss_dict['focus_gloss_value'] = focus_gloss_value
            if field_kind == 'list':
                if other_gloss_choice:
                    try:
                        other_gloss_value = translated_choice_lists_table[field][int(other_gloss_choice)][language_code]
                    except:
                        other_gloss_value = 'ERROR_' + other_gloss_choice
                        print('Error for gloss ', minimalpairs_object.id, ' on stored choice (field: ', field, ', choice: ', other_gloss_choice, ')')
                else:
                    other_gloss_value = '-'
            elif field_kind == 'check':
                if other_gloss_choice == 'True':
                    other_gloss_value = _('Yes')
                elif other_gloss_choice == 'Neutral' and field in ['weakdrop', 'weakprop']:
                    other_gloss_value = _('Neutral')
                else:
                    other_gloss_value = _('No')
            else:
                other_gloss_value = other_gloss_choice
            # print('other gloss choice: ', other_gloss_value)
            other_gloss_dict['other_gloss_value'] = other_gloss_value
            other_gloss_dict['field_kind'] = field_kind

        # print('min pairs other gloss dict: ', other_gloss_dict)
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

class LemmaListView(ListView):
    model = LemmaIdgloss
    template_name = 'dictionary/admin_lemma_list.html'
    paginate_by = 10

    def get_queryset(self, **kwargs):
        queryset = super(LemmaListView, self).get_queryset(**kwargs)
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        return queryset.filter(dataset__in=selected_datasets).annotate(num_gloss=Count('gloss'))

    def get_context_data(self, **kwargs):
        context = super(LemmaListView, self).get_context_data(**kwargs)

        if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS'):
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = settings.SHOW_DATASET_INTERFACE_OPTIONS
        else:
            context['SHOW_DATASET_INTERFACE_OPTIONS'] = False

        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages

        return context


class LemmaCreateView(CreateView):
    model = LemmaIdgloss
    template_name = 'dictionary/add_lemma.html'
    fields = []

    def get_context_data(self, **kwargs):
        context = {}
        selected_datasets = get_selected_datasets_for_user(self.request.user)
        context['selected_datasets'] = selected_datasets
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()
        context['dataset_languages'] = dataset_languages
        context['add_lemma_form'] = LemmaCreateForm(self.request.GET, languages=dataset_languages, user=self.request.user)
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix
        return context

    def post(self, request, *args, **kwargs):
        print(request.POST)
        dataset = None
        if 'dataset' in request.POST and request.POST['dataset'] is not None:
            dataset = Dataset.objects.get(pk=request.POST['dataset'])
            selected_datasets = Dataset.objects.filter(pk=request.POST['dataset'])
        else:
            selected_datasets = get_selected_datasets_for_user(request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

        form = LemmaCreateForm(request.POST, languages=dataset_languages, user=request.user)

        for item, value in request.POST.items():
            if item.startswith(form.lemma_create_field_prefix):
                language_code_2char = item[len(form.lemma_create_field_prefix):]
                language = Language.objects.get(language_code_2char=language_code_2char)
                lemmas_for_this_language_and_annotation_idgloss = LemmaIdgloss.objects.filter(
                    lemmaidglosstranslation__language=language,
                    lemmaidglosstranslation__text__exact=value.upper(),
                    dataset=dataset)
                if len(lemmas_for_this_language_and_annotation_idgloss) != 0:
                    return render(request, 'dictionary/warning.html',
                                  {'warning': language.name + " " + 'lemma ID Gloss not unique.'})

        if form.is_valid():
            try:
                lemma = form.save()
                print("LEMMA " + str(lemma.pk))
            except ValidationError as ve:
                messages.add_message(request, messages.ERROR, ve.message)
                return render(request, 'dictionary/add_lemma.html', {'add_lemma_form': LemmaCreateForm(request.POST, user=request.user),
                                                                     'dataset_languages': dataset_languages,
                                                                     'selected_datasets': get_selected_datasets_for_user(request.user)})

            # return HttpResponseRedirect(reverse('dictionary:admin_lemma_list', kwargs={'pk': lemma.id}))
            return HttpResponseRedirect(reverse('dictionary:admin_lemma_list'))
        else:
            return render(request, 'dictionary/add_gloss.html', {'add_lemma_form': form,
                                                             'dataset_languages': dataset_languages,
                                                             'selected_datasets': get_selected_datasets_for_user(
                                                                 request.user)})


def create_lemma_for_gloss(request, glossid):
    try:
        gloss = Gloss.objects.get(id=glossid)
    except ObjectDoesNotExist:
        try:
            gloss = Morpheme.objects.get(id=glossid).gloss
        except ObjectDoesNotExist:
            messages.add_message(request, messages.ERROR, _("The specified gloss does not exist."))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    dataset = gloss.dataset
    dataset_languages = dataset.translation_languages.all()
    form = LemmaCreateForm(request.POST, languages=dataset_languages, user=request.user)
    for item, value in request.POST.items():
        if item.startswith(form.lemma_create_field_prefix):
            language_code_2char = item[len(form.lemma_create_field_prefix):]
            language = Language.objects.get(language_code_2char=language_code_2char)
            lemmas_for_this_language_and_annotation_idgloss = LemmaIdgloss.objects.filter(
                lemmaidglosstranslation__language=language,
                lemmaidglosstranslation__text__exact=value.upper(),
                dataset=dataset)
            if len(lemmas_for_this_language_and_annotation_idgloss) != 0:
                messages.add_message(request, messages.ERROR, _('Lemma ID Gloss not unique for %(language)s.') % {'language': language.name})
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    if form.is_valid():
        try:
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
    template_name = 'dictionary/update_lemma.html'
    fields = []

    def get_context_data(self, **kwargs):
        context = super(LemmaUpdateView, self).get_context_data(**kwargs)
        dataset = self.object.dataset
        context['dataset'] = dataset
        dataset_languages = Language.objects.filter(dataset=dataset).distinct()
        context['dataset_languages'] = dataset_languages
        context['change_lemma_form'] = LemmaUpdateForm(instance=self.object)
        context['lemma_create_field_prefix'] = LemmaCreateForm.lemma_create_field_prefix
        return context

    def post(self, request, *args, **kwargs):
        print(request.POST)
        instance = self.get_object()
        dataset = instance.dataset

        form = LemmaUpdateForm(request.POST, instance=instance)

        for item, value in request.POST.items():
            if item.startswith(form.lemma_update_field_prefix):
                language_code_2char = item[len(form.lemma_update_field_prefix):]
                language = Language.objects.get(language_code_2char=language_code_2char)
                lemmas_for_this_language_and_annotation_idgloss = LemmaIdgloss.objects.filter(
                    lemmaidglosstranslation__language=language,
                    lemmaidglosstranslation__text__exact=value.upper(),
                    dataset=dataset)
                if len(lemmas_for_this_language_and_annotation_idgloss) != 0:
                    return render(request, 'dictionary/warning.html',
                                  {'warning': language.name + " " + 'lemma ID Gloss not unique.'})

        if form.is_valid():
            try:
                lemma = form.save()
                print("LEMMA " + str(lemma.pk))
            except ValidationError as ve:
                messages.add_message(request, messages.ERROR, ve.message)
                return render(request, 'dictionary/update_lemma.html', {'change_lemma_form': LemmaUpdateForm(instance=self.get_object())})

            # return HttpResponseRedirect(reverse('dictionary:admin_lemma_list', kwargs={'pk': lemma.id}))
            return HttpResponseRedirect(reverse('dictionary:admin_lemma_list'))
        else:
            return HttpResponseRedirect(reverse_lazy('dictionary:change_lemma', kwargs={'pk': instance.id}))


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
