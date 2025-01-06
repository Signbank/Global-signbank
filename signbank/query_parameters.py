import signbank.settings
from signbank.settings.base import WSGI_FILE, WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, LANGUAGE_CODE, EARLIEST_GLOSS_CREATION_DATE
import os
import shutil
from html.parser import HTMLParser
from zipfile import ZipFile
import json
import re
from urllib.parse import quote
import csv
from django.db.models import Q
from django.http import QueryDict

from django.utils.translation import override, gettext_lazy as _

from django.http import HttpResponse, HttpResponseRedirect
from django.utils import html

from signbank.dictionary.models import *
from signbank.video.models import GlossVideo, GlossVideoNME
from django.db.models.functions import Concat
from signbank.dictionary.forms import *
from signbank.dictionary.field_choices import fields_to_fieldcategory_dict
from django.utils.dateformat import format
from django.core.exceptions import ObjectDoesNotExist, EmptyResultSet
from django.db import OperationalError, ProgrammingError
from django.db.models import Q, Count, CharField, TextField, Value as V
from django.db.models.fields import BooleanField, BooleanField

from django.urls import reverse
from tagging.models import TaggedItem, Tag
from django.shortcuts import render, get_object_or_404, redirect
from guardian.shortcuts import get_objects_for_user
from signbank.tools import get_dataset_languages


def list_to_query(query_list):
    # this ANDs together the individual Q elements in the query_list
    if not query_list:
        #query_list argument to list_to_query is empty
        return Q()
    if len(query_list) == 1:
        return query_list[0]

    # here the recursive call is only done if the rest of the list is not empty
    rest_of_query_list = query_list[1:]
    q_exp = list_to_query(rest_of_query_list)
    or_query = query_list[0] & q_exp
    return or_query

def query_parameters_this_gloss(phonology_focus, phonology_matrix):
    # this is used to determine a default query for the case the user showed all glosses and there are no parameters
    # when the user is looking at a specific gloss and no query parameters are active, this determines what to show
    # the function gets parameters for non-empty fields of the gloss
    # it then determines for each field what the relevant field of the Gloss Search Form is

    fields_with_choices = fields_to_fieldcategory_dict()

    query_parameters = dict()
    for field_key in phonology_focus:
        field_value = phonology_matrix[field_key]
        if field_key in fields_with_choices.keys():
            # this assumes the field_key is unique
            # the value the key is mapped to ends up being a list inside a list, as needed by the Gloss Search Form
            # for multiselect values
            field_key = field_key + '[]'
            query_parameters[field_key] = []
            query_parameters[field_key].append(field_value)
        elif field_key in ['weakdrop', 'weakprop', 'domhndsh_letter', 'domhndsh_number',
                           'subhndsh_letter', 'subhndsh_number', 'repeat', 'altern', 'hasRelationToForeignSign',
                           'inWeb', 'isNew', 'isablend', 'ispartofablend']:
            # these mappings match the choices in the Gloss Search Form
            NEUTRALBOOLEANCHOICES = {'None': '1', 'True': '2', 'False': '3'}
            query_parameters[field_key] = NEUTRALBOOLEANCHOICES[field_value]
        elif field_key in ['defspublished', 'hasmultiplesenses']:
            # these mappings match the choices in the Gloss Search Form and get_queryset
            # some of these are legacy mappings
            YESNOCHOICES = {'None': '-', 'True': _('Yes'), 'False': _('No')}
            query_parameters[field_key] = YESNOCHOICES[field_value]
        else:
            query_parameters[field_key] = field_value
    return query_parameters


def apply_language_filters_to_results(model, qs, query_parameters):
    # Evaluate all gloss/language search fields
    # this needs to be done explicitly so the respective filters are applied in sequence
    # [identified during testing:] if the filters are mapped to Q expressions they end up filtering too many results away
    # in the case that more than one field has been filled in
    # Here the expressions and order matches that of get_queryset
    # the function convert_query_parameters_to_filter (below) creates the Q expression for filtering
    gloss_prefix = 'gloss__' if model in ['GlossSense', 'AnnotatedGloss'] else ''

    gloss_search_field_prefix = "glosssearch_"
    len_gloss_search_field_prefix = len(gloss_search_field_prefix)
    keyword_search_field_prefix = "keyword_"
    len_keyword_search_field_prefix = len(keyword_search_field_prefix)
    lemma_search_field_prefix = "lemma_"
    len_lemma_search_field_prefix = len(lemma_search_field_prefix)
    text_filter = 'iregex' if USE_REGULAR_EXPRESSIONS else 'icontains'

    for get_key, get_value in query_parameters.items():
        if get_key.startswith(gloss_search_field_prefix) and get_value != '':
            language_code_2char = get_key[len_gloss_search_field_prefix:]
            language = Language.objects.filter(language_code_2char=language_code_2char).first()
            query_filter_annotation_text = gloss_prefix + 'annotationidglosstranslation__text__' + text_filter
            query_filter_annotation_language = gloss_prefix + 'annotationidglosstranslation__language'
            qs = qs.filter(**{query_filter_annotation_text: get_value,
                              query_filter_annotation_language: language})
        elif get_key.startswith(lemma_search_field_prefix) and get_value != '':
            language_code_2char = get_key[len_lemma_search_field_prefix:]
            language = Language.objects.filter(language_code_2char=language_code_2char).first()
            query_filter_lemma_text = gloss_prefix + 'lemma__lemmaidglosstranslation__text__' + text_filter
            query_filter_lemma_language = gloss_prefix + 'lemma__lemmaidglosstranslation__language'
            qs = qs.filter(**{query_filter_lemma_text: get_value,
                              query_filter_lemma_language: language})
        elif get_key.startswith(keyword_search_field_prefix) and get_value != '':
            language_code_2char = get_key[len_keyword_search_field_prefix:]
            language = Language.objects.filter(language_code_2char=language_code_2char).first()
            query_filter_sense_text = gloss_prefix + 'translation__translation__text__' + text_filter
            query_filter_sense_language = gloss_prefix + 'translation__language'
            qs = qs.filter(**{query_filter_sense_text: get_value,
                              query_filter_sense_language: language})
    return qs


def matching_file_exists(videofile):
    from pathlib import Path
    video_file_full_path = Path(WRITABLE_FOLDER, videofile)
    if video_file_full_path.exists():
        return True
    else:
        return False


def matching_file__does_not_exist(videofile):
    from pathlib import Path
    video_file_full_path = Path(WRITABLE_FOLDER, videofile)
    if video_file_full_path.exists():
        return False
    else:
        return True


def apply_video_filters_to_results(model, qs, query_parameters):
    gloss_prefix = 'gloss__' if model in ['GlossSense', 'AnnotatedGloss'] else ''
    filter_id = gloss_prefix + 'id__in'
    gloss_ids = [gl.id if model == 'Gloss' else gl.gloss.id for gl in qs]
    if 'hasvideo' not in query_parameters.keys():
        return qs
    elif query_parameters['hasvideo'] == '2':
        glossvideo_queryset = GlossVideo.objects.filter(gloss__id__in=gloss_ids, glossvideonme=None, glossvideoperspective=None, version=0)
        queryset_res = glossvideo_queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file_exists(qv['videofile'])]
        glosses_with_videofile = GlossVideo.objects.filter(id__in=results)
        gloss_ids = [gv.gloss.id for gv in glosses_with_videofile]
        return qs.filter(Q(**{filter_id: gloss_ids}))
    else:
        null_videos = qs.filter(Q(**{gloss_prefix + 'glossvideo__isnull': True}))
        gloss_ids_without_video = [gl.id if model == 'Gloss' else gl.gloss.id for gl in null_videos]
        glossvideo_queryset = GlossVideo.objects.filter(gloss__id__in=gloss_ids, glossvideonme=None, glossvideoperspective=None, version=0)
        queryset_res = glossvideo_queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file__does_not_exist(qv['videofile'])]
        glosses_with_missing_videofile = GlossVideo.objects.filter(id__in=results)
        gloss_ids_missing_videos = [gv.gloss.id for gv in glosses_with_missing_videofile]
        filter_no_video = Q(**{filter_id: gloss_ids_without_video}) | Q(**{filter_id: gloss_ids_missing_videos})
        return qs.filter(Q(**{filter_id: filter_no_video}))


def apply_nmevideo_filters_to_results(model, qs, query_parameters):
    gloss_prefix = 'gloss__' if model in ['GlossSense', 'AnnotatedGloss'] else ''
    filter_id = gloss_prefix + 'id__in'
    gloss_ids = [gl.id if model == 'Gloss' else gl.gloss.id for gl in qs]
    if 'hasnmevideo' not in query_parameters.keys():
        return qs
    elif query_parameters['hasnmevideo'] == '2':
        glossvideo_queryset = GlossVideoNME.objects.filter(gloss__id__in=gloss_ids, version=0)
        queryset_res = glossvideo_queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file_exists(qv['videofile'])]
        glosses_with_videofile = GlossVideoNME.objects.filter(id__in=results)
        gloss_ids = [gv.gloss.id for gv in glosses_with_videofile]
        return qs.filter(Q(**{filter_id: gloss_ids}))
    else:
        null_videos = qs.filter(Q(**{gloss_prefix + 'glossvideo__isnull': True}))
        gloss_ids_without_video = [gl.id if model == 'Gloss' else gl.gloss.id for gl in null_videos]
        glossvideo_queryset = GlossVideoNME.objects.filter(gloss__id__in=gloss_ids, version=0)
        queryset_res = glossvideo_queryset.values('id', 'videofile')
        results = [qv['id'] for qv in queryset_res
                   if matching_file__does_not_exist(qv['videofile'])]
        glosses_with_missing_videofile = GlossVideoNME.objects.filter(id__in=results)
        gloss_ids_missing_videos = [gv.gloss.id for gv in glosses_with_missing_videofile]
        filter_no_video = Q(**{filter_id: gloss_ids_without_video}) | Q(**{filter_id: gloss_ids_missing_videos})
        return qs.filter(Q(**{filter_id: filter_no_video}))


def convert_query_parameters_to_filter(query_parameters):
    # this function maps the query parameters to a giant Q expression
    # the code follows that of get_queryset of GlossListView
    # note that only non-empty fields are stored in query_parameters
    # use these to idenfiy language based fields
    glosssearch = "glosssearch_"
    lemmasearch = "lemma_"
    keywordsearch = "keyword_"
    text_filter = 'iregex' if USE_REGULAR_EXPRESSIONS else 'icontains'

    gloss_fields = {}
    for fname in Gloss.get_field_names():
        gloss_fields[fname] = Gloss.get_field(fname)

    fields_with_choices = fields_to_fieldcategory_dict()
    multiple_select_gloss_fields = [fieldname + '[]' for fieldname in Gloss.get_field_names()
                                    if fieldname in fields_with_choices.keys()]

    query_list = []
    for get_key, get_value in query_parameters.items():
        if get_key in ['search_type', 'isRepresentative', 'annotatedSentenceContains']:
            continue
        elif get_key.startswith(glosssearch) or get_key.startswith(lemmasearch) \
                or get_key.startswith(keywordsearch):
            # because of joining tables, these are done in a separate function
            # and directly applied to the query results (see previous function)
            continue
        elif get_key == 'search' and get_value:
            query_filter_annotation_text = 'annotationidglosstranslation__text__' + text_filter
            query = Q(**{query_filter_annotation_text: get_value})
            if re.match(r'^\d+$', get_value):
                query = query | Q(sn__exact=get_value)
            query_list.append(query)

        elif get_key == 'translation' and get_value:
            query_filter_sense_text = 'translation__translation__text__' + text_filter
            query_list.append(Q(**{query_filter_sense_text: get_value}))

        elif get_key == 'inWeb' and get_value != '':
            val = get_value == '2'
            query_list.append(Q(inWeb__exact=val))

        elif get_key == 'excludeFromEcv' and get_value != '':
            val = get_value == '2'
            query_list.append(Q(excludeFromEcv__exact=val))

        elif get_key in ['hasvideo', 'hasnmevideo'] and get_value != '':
            # this is done in a separate function
            continue

        elif get_key in ['hasothermedia'] and get_value != '':

            # Remember the pk of all glosses that have other media
            pks_for_glosses_with_othermedia = [ om.parent_gloss.pk for om in OtherMedia.objects.all() ]
            if get_value == '2':
                # value '1' filters glosses with othermedia
                query_list.append(Q(pk__in=pks_for_glosses_with_othermedia))
            elif get_value == '3':
                # the code for '3' excludes the above glosses from the results
                query_list.append(~Q(pk__in=pks_for_glosses_with_othermedia))

        elif get_key == 'hasRelationToForeignSign':
            pks_for_glosses_with_relations = [relation.gloss.pk
                                              for relation in RelationToForeignSign.objects.filter(gloss__archived__exact=False)]

            if get_value == '2':
                # value '1' filters glosses with a relation to a foreign sign
                query_list.append(Q(pk__in=pks_for_glosses_with_relations))
            elif get_value == '3':
                # the code for "No" excludes the above glosses from the results
                query_list.append(~Q(pk__in=pks_for_glosses_with_relations))

        elif get_key == 'isablend':
            pks_for_gloss_blends = [blemorph.parent_gloss.pk
                                    for blemorph in BlendMorphology.objects.filter(parent_gloss__archived__exact=False,
                                                                                   glosses__archived__exact=False)]

            if get_value == '2':  # glosses that are blends
                query_list.append(Q(pk__in=pks_for_gloss_blends))
            elif get_value == '3':
                # the code for "No" excludes the above glosses from the results
                query_list.append(~Q(pk__in=pks_for_gloss_blends))

        elif get_key == 'ispartofablend':
            pks_for_glosses_of_blends = [blemorph.glosses.pk
                                         for blemorph in BlendMorphology.objects.filter(parent_gloss__archived__exact=False,
                                                                                        glosses__archived__exact=False)]

            if get_value == '2':  # glosses that are part of blends
                query_list.append(Q(pk__in=pks_for_glosses_of_blends))
            elif get_value == '3':
                # the code for "No" excludes the above glosses from the results
                query_list.append(~Q(pk__in=pks_for_glosses_of_blends))

        elif get_key == 'relationToForeignSign':
            relations = RelationToForeignSign.objects.filter(gloss__archived__exact=False,
                                                             other_lang_gloss__icontains=get_value)
            potential_pks = [relation.gloss.pk for relation in relations]
            query_list.append(Q(pk__in=potential_pks))

        elif get_key == 'defspublished' and get_value:
            val = get_value == 'yes'
            query_list.append(Q(definition__published=val))

        elif get_key == 'hasmultiplesenses' and get_value:
            val = get_value == 'yes'
            if val:
                multiple_senses = [gsv['gloss'] for gsv in GlossSense.objects.values(
                    'gloss').annotate(Count('id')).filter(id__count__gt=1)]
            else:
                multiple_senses = [gsv['gloss'] for gsv in GlossSense.objects.values(
                    'gloss').annotate(Count('id')).filter(id__count=1)]
            query_list.append(Q(id__in=multiple_senses))

        elif get_key == 'negative' and get_value:
            sentences_with_negative_type = ExampleSentence.objects.filter(negative__exact=True)
            sentences_with_other_type = ExampleSentence.objects.filter(negative__exact=False)
            if get_value == 'yes':  # only senses with negative sentences
                glosssenses = GlossSense.objects.filter(
                    sense__exampleSentences__in=sentences_with_negative_type).distinct()
            else:  # only senses sentences that are not negative
                glosssenses = GlossSense.objects.filter(
                    sense__exampleSentences__in=sentences_with_other_type).distinct()
            relevant_glosses = [gs.gloss.pk for gs in glosssenses]
            query_list.append(Q(pk__in=relevant_glosses))

        elif get_key == 'sentenceType[]' and get_value:
            sentences_with_this_type = ExampleSentence.objects.filter(sentenceType__machine_value__in=get_value)
            glosssenses = GlossSense.objects.filter(sense__exampleSentences__in=sentences_with_this_type).distinct()
            relevant_glosses = [gs.gloss.pk for gs in glosssenses]
            query_list.append(Q(pk__in=relevant_glosses))

        elif get_key in ['definitionContains']:
            definitions_with_this_text = Definition.objects.filter(text__icontains=get_value)

            # Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_text]
            query_list.append(Q(pk__in=pks_for_glosses_with_these_definitions))

        elif get_key == 'dialect[]':
            query_list.append(Q(dialect__in=get_value))

        elif get_key == 'tags[]':
            values = [int(v) for v in get_value]
            pks_for_glosses_with_tags = list(
                TaggedItem.objects.filter(tag__id__in=values).values_list('object_id', flat=True))
            query_list.append(Q(pk__in=pks_for_glosses_with_tags))

        elif get_key == 'signlanguage[]':
            query_list.append(Q(signlanguage__in=get_value))
        elif get_key == 'definitionRole[]':
            # Find all definitions with this role
            definitions_with_this_role = Definition.objects.filter(role__machine_value__in=get_value)
            # Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role]
            query_list.append(Q(pk__in=pks_for_glosses_with_these_definitions))
        elif get_key == 'hasComponentOfType[]':
            morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__machine_value__in=get_value)
            pks_for_glosses_with_morphdefs_with_correct_role = [morphdef.parent_gloss.pk for morphdef in morphdefs_with_correct_role]
            query_list.append(Q(pk__in=pks_for_glosses_with_morphdefs_with_correct_role))
        elif get_key[:-2] == 'semField':
            q_filter = 'semField__in'
            query_list.append(Q(**{q_filter: get_value}))
        elif get_key[:-2] == 'derivHist':
            q_filter = 'derivHist__in'
            query_list.append(Q(**{q_filter: get_value}))
        elif get_key == 'useInstr':
            query_list.append(Q(useInstr__icontains=get_value))
        elif get_key == 'createdBefore':
            created_before_date = DT.datetime.strptime(get_value, settings.DATE_FORMAT).date()
            query_list.append(Q(creationDate__range=(EARLIEST_GLOSS_CREATION_DATE, created_before_date)))
        elif get_key == 'createdAfter':
            created_after_date = DT.datetime.strptime(get_value, settings.DATE_FORMAT).date()
            query_list.append(Q(creationDate__range=(created_after_date, DT.datetime.now())))
        elif get_key == 'createdBy':
            query_list.append(Q(**{'creator__first_name__icontains': get_value}) |
                              Q(**{'creator__last_name__icontains': get_value}))
        elif get_key in multiple_select_gloss_fields:
            mapped_key = get_key[:-2]
            q_filter = mapped_key + '__machine_value__in'
            query_list.append(Q(** {q_filter: get_value}))
        elif get_key in ['hasRelation[]']:
            relations_with_this_role = Relation.objects.filter(role__in=get_value)
            pks_for_glosses_with_correct_relation = [relation.source.pk for relation in relations_with_this_role]
            query_list.append(Q(pk__in=pks_for_glosses_with_correct_relation))
        elif get_key in ['relation']:
            potential_targets = Gloss.objects.filter(annotationidglosstranslation__text__icontains=get_value)
            relations = Relation.objects.filter(target__in=potential_targets)
            potential_pks = [relation.source.pk for relation in relations]
            query_list.append(Q(pk__in=potential_pks))
        elif get_key in ['morpheme']:
            # Filter all glosses that contain this morpheme in their simultaneous morphology
            try:
                selected_morpheme = Morpheme.objects.get(pk=int(get_value))
                potential_pks = [appears.parent_gloss.pk for appears in SimultaneousMorphologyDefinition.objects.filter(morpheme=selected_morpheme)]
                query_list.append(Q(pk__in=potential_pks))
            except ObjectDoesNotExist:
                # This error should not occur, the input search form requires the selection of a morpheme from a list
                # If the user attempts to input a string, it is ignored by the gloss list search form
                print("convert_query_parameters_to_filter: Morpheme not found: ", get_value)
                continue
        elif get_key in ['hasComponentOfType']:
            # Look for "compound-components" of the indicated type.
            # Compound Components are defined in class[MorphologyDefinition]
            morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__machine_value__in=get_value)
            pks_for_glosses_with_morphdefs_with_correct_role = [morphdef.parent_gloss.pk for morphdef in morphdefs_with_correct_role]
            query_list.append(Q(pk__in=pks_for_glosses_with_morphdefs_with_correct_role))
        elif get_key in ['mrpType[]']:
            # Get all Morphemes of the indicated mrpType
            target_morphemes = [ m.id for m in Morpheme.objects.filter(mrpType__machine_value__in=get_value) ]
            # this only works in the query is Sign or Morpheme
            query_list.append(Q(id__in=target_morphemes))

        elif get_key in gloss_fields.keys():
            # not sure if this is needed, this case is Gloss fields rather than GlossSearchForm fields
            # this should be the fall through for fields not in multiselect and not covered above
            # it could happen that a ForeignKey field falls through which is not included in multiselect
            field_obj = Gloss.get_field(get_key)

            if type(field_obj) in [CharField,TextField]:
                q_filter = get_key + '__icontains'
            elif hasattr(field_obj, 'field_choice_category'):
                # just in case, field choice field that is not multi-select
                q_filter = get_key + '__machine_value'
            else:
                q_filter = get_key + '__exact'

            if isinstance(field_obj,BooleanField):
                q_value = {'0':'','1': None, '2': True, '3': False}[get_value]
            else:
                q_value = get_value
            kwargs = {q_filter:q_value}
            query_list.append(Q(**kwargs))
        else:
            print('convert_query_parameters_to_filter: not implemented for ', get_key)
            pass

    # make a filter from the list of Q elements
    # a singleton is treated differently from more than one
    if not query_list:
        # query_list is empty, this will return everything since nothing was filtered
        query = Q()
    elif len(query_list) == 1:
        query = query_list[0]
    else:
        # length of query_list is greater than 1
        query = list_to_query(query_list)
    return query


def convert_query_parameters_to_annotatedgloss_filter(query_parameters):
    # this function maps the query parameters to a giant Q expression

    query_list = []
    for get_key, get_value in query_parameters.items():
        print(get_key, get_value)
        if get_key in ['isRepresentative'] and get_value:
            if get_value == 'yes':
                annotatedglosses = AnnotatedGloss.objects.filter(isRepresentative__exact=True).distinct()
            else:
                annotatedglosses = AnnotatedGloss.objects.filter(isRepresentative__exact=False).distinct()

            relevant_glosses = [ag.id for ag in annotatedglosses]
            query_list.append(Q(id__in=relevant_glosses))

        elif get_key in ['annotatedSentenceContains'] and get_value:
            sentence_translations_with_this_text = AnnotatedSentenceTranslation.objects.filter(
                text__icontains=get_value)
            sentences_with_this_text = [est.annotatedsentence.id for est in sentence_translations_with_this_text]
            query_list.append(Q(annotatedsentence__id__in=sentences_with_this_text))
        else:
            continue

    # make a filter from the list of Q elements
    # a singleton is treated differently from more than one
    if not query_list:
        # query_list is empty, this will return everything since nothing was filtered
        query = Q()
    elif len(query_list) == 1:
        query = query_list[0]
    else:
        # length of query_list is greater than 1
        query = list_to_query(query_list)
    return query


def pretty_print_query_fields(dataset_languages,query_parameters):
    # this function determines what to show when a Query Parameters table is shown
    # some of the fields do not match those in the Gloss Search Form
    # the code checks whether the field exists in the Gloss model or in the Gloss Search Form
    # print statements are shown in the log in cases where no appropriate description was found
    # it is expected that as the functionality of Query Parameters is extended that the descriptions will evolve
    # depending on what the user wants to be able to do
    gloss_fields = Gloss.get_field_names()
    form_fields = GlossSearchForm.get_field_names()
    gloss_search_field_prefix = "glosssearch_"
    keyword_search_field_prefix = "keyword_"
    lemma_search_field_prefix = "lemma_"
    query_dict = dict()
    for key in query_parameters:
        if key.startswith(gloss_search_field_prefix) or key.startswith(keyword_search_field_prefix) \
                or key.startswith(lemma_search_field_prefix) or key == 'translation':
            # language-based fields are done later
            continue
        elif key == 'search_type':
            query_dict[key] = gettext("Search Type")
        elif key == 'dialect[]':
            query_dict[key] = gettext("Dialect")
        elif key == 'signlanguage[]':
            query_dict[key] = gettext("Sign Language")
        elif key == 'definitionRole[]':
            query_dict[key] = gettext("Note Type")
        elif key[-2:] == '[]':
            if key[:-2] in gloss_fields:
                query_dict[key] = Gloss.get_field(key[:-2]).verbose_name.encode('utf-8').decode()
            elif key[:-2] in form_fields:
                query_dict[key] = GlossSearchForm.get_field(key[:-2]).label.encode('utf-8').decode()
            elif key[:-2] in ['sentenceType']:
                query_dict[key] = SentenceForm.get_field('sentenceType').label.encode('utf-8').decode()
            else:
                print('pretty_print_query_fields: multiple select field not found in Gloss or GlossSearchForm: ', key)
                query_dict[key] = key
        elif key not in gloss_fields:
            if key == 'negative':
                query_dict[key] = gettext("Negative")
            elif key == 'isRepresentative':
                query_dict[key] = gettext("Is Representative")
            elif key == 'sentenceContains':
                query_dict[key] = gettext("Sentence Contains")
            elif key == 'annotatedSentenceContains':
                query_dict[key] = gettext("Annotated Sentence Contains")
            elif key in form_fields:
                query_dict[key] = GlossSearchForm.get_field(key).label.encode('utf-8').decode()
            else:
                print('pretty_print_query_fields: key not in gloss_fields, not in form_fields:', key)
                query_dict[key] = key
        else:
            query_dict[key] = Gloss.get_field(key).verbose_name.encode('utf-8').decode()

    for language in dataset_languages:
        glosssearch_field_name = gloss_search_field_prefix + language.language_code_2char
        if glosssearch_field_name in query_parameters:
            query_dict[glosssearch_field_name] = _('Annotation ID Gloss') + " (" + language.name + ")"
        lemma_field_name = lemma_search_field_prefix + language.language_code_2char
        if lemma_field_name in query_parameters:
            query_dict[lemma_field_name] = _('Lemma ID Gloss') + " (" + language.name + ")"
        keyword_field_name = keyword_search_field_prefix + language.language_code_2char
        if keyword_field_name in query_parameters:
            query_dict[keyword_field_name] = _('Senses') + " (" + language.name + ")"
        if 'translation' in query_parameters:
            query_dict['translation'] = _('Search Senses')
    return query_dict


def pretty_print_query_values(dataset_languages,query_parameters):
    # this function maps the Gloss Search Form field values back to a human readable value
    # for display in Query Parameters

    # set up some mappings
    # if Query Parameters is made into a model, these will eventually become coded elsewhere
    # right now, they're localised here
    gloss_search_field_prefix = "glosssearch_"
    keyword_search_field_prefix = "keyword_"
    lemma_search_field_prefix = "lemma_"
    NEUTRALBOOLEANCHOICES = {'0': _('Neutral'), '1': _('Neutral'), '2': _('Yes'), '3': _('No')}
    UNKNOWNBOOLEANCHOICES = {'0': _('-'), '2': _('True'), '3': _('False')}
    NULLBOOLEANCHOICES = {'0': _('-'), '2': _('True'), '3': _('False')}
    YESNOCHOICES = {'0': '-', 'yes': _('Yes'), 'no': _('No'), '2': _('Yes'), '3': _('No')}
    RELATION_ROLE_CHOICES = {'homonym': _('Homonym'),
                             'synonym': _('Synonym'),
                             'variant': _('Variant'),
                             'antonym': _('Antonym'),
                             'hyponym': _('Hyponym'),
                             'hypernym': _('Hypernym'),
                             'seealso': _('See Also'),
                             'paradigm': _('Handshape Paradigm')}
    SEARCH_TYPE_CHOICES = {
        'sign': _("Search Sign"),
        'sense': _("Search Senses"),
        'sign_or_morpheme': _("Search Sign or Morpheme"),
        'morpheme': _("Search Morpheme"),
        'sign_handshape': _("Search Sign by Handshape"),
        'handshape': _("Search Handshape"),
        'lemma': _("Search Lemma"),
        'annotatedsentence': _("Annotated Gloss Sentence")
    }
    query_dict = dict()
    for key in query_parameters:
        if key == 'search_type':
            query_dict[key] = SEARCH_TYPE_CHOICES[query_parameters[key]]
        elif key == 'dialect[]':
            choices_for_category = Dialect.objects.filter(id__in=query_parameters[key])
            query_dict[key] = [ choice.signlanguage.name + "/" + choice.name for choice in choices_for_category ]
        elif key == 'signlanguage[]':
            choices_for_category = SignLanguage.objects.filter(id__in=query_parameters[key])
            query_dict[key] = [ choice.name for choice in choices_for_category ]
        elif key == 'definitionRole[]':
            # this is a Note
            choices_for_category = FieldChoice.objects.filter(field__iexact='NoteType', machine_value__in=query_parameters[key])
            query_dict[key] = [choice.name for choice in choices_for_category]
        elif key == 'hasComponentOfType[]':
            choices_for_category = FieldChoice.objects.filter(field__iexact='MorphologyType', machine_value__in=query_parameters[key])
            query_dict[key] = [choice.name for choice in choices_for_category]
        elif key == 'tags[]':
            tag_objects = Tag.objects.filter(id__in=query_parameters[key])
            tag_names = [t.name for t in tag_objects]
            query_dict[key] = tag_names
        elif key[-2:] == '[]':
            if key in ['hasRelation[]']:
                choices_for_category = [RELATION_ROLE_CHOICES[val] for val in query_parameters[key]]
                query_dict[key] = choices_for_category
                continue
            # in the Gloss Search Form, multiple choice fields have a list of values
            # these are all displayed in the Query Parameters display (as non-selectable buttons in the template)
            if key[:-2] in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
                choices_for_category = Handshape.objects.filter(machine_value__in=query_parameters[key])
            elif key[:-2] in ['semField']:
                choices_for_category = SemanticField.objects.filter(machine_value__in=query_parameters[key])
            elif key[:-2] in ['derivHist']:
                choices_for_category = DerivationHistory.objects.filter(machine_value__in=query_parameters[key])
            else:
                field = key[:-2]
                if field in ['sentenceType']:
                    field_category = 'SentenceType'
                elif field in ['mrpType']:
                    # this is a field of Morpheme
                    field_category = 'MorphemeType'
                else:
                    field_category = Gloss.get_field(field).field_choice_category
                choices_for_category = FieldChoice.objects.filter(field__iexact=field_category, machine_value__in=query_parameters[key])
            query_dict[key] = [choice.name for choice in choices_for_category]
        elif key.startswith(gloss_search_field_prefix) or key.startswith(keyword_search_field_prefix) or key.startswith(lemma_search_field_prefix):
            continue
        elif key in ['weakdrop', 'weakprop']:
            query_dict[key] = NEUTRALBOOLEANCHOICES[query_parameters[key]]
        elif key in ['domhndsh_letter', 'domhndsh_number', 'subhndsh_letter', 'subhndsh_number']:
            query_dict[key] = UNKNOWNBOOLEANCHOICES[query_parameters[key]]
        elif key in ['repeat', 'altern']:
            query_dict[key] = UNKNOWNBOOLEANCHOICES[query_parameters[key]]
        elif key in ['hasRelationToForeignSign', 'isablend', 'ispartofablend']:
            if query_parameters[key] in ['2']:
                query_dict[key] = _('Yes')
            elif query_parameters[key] in ['3']:
                query_dict[key] = _('No')
        elif key in ['inWeb', 'isNew', 'excludeFromEcv', 'hasvideo', 'hasnmevideo', 'hasothermedia']:
            query_dict[key] = NULLBOOLEANCHOICES[query_parameters[key]]
        elif key in ['defspublished', 'hasmultiplesenses', 'negative']:
            query_dict[key] = YESNOCHOICES[query_parameters[key]]
        elif key in ['hasRelation']:
            choices_for_category = [RELATION_ROLE_CHOICES[val] for val in query_parameters[key]]
            query_dict[key] = choices_for_category
        elif key in ['hasComponentOfType']:
            choices_for_category = FieldChoice.objects.filter(field__iexact='MorphologyType', machine_value__in=query_parameters[key])
            query_dict[key] = [choice.name for choice in choices_for_category][0]
        elif key in ['mrpType']:
            choices_for_category = FieldChoice.objects.filter(field__iexact='MorphemeType', machine_value__in=query_parameters[key])
            query_dict[key] = [choice.name for choice in choices_for_category][0]
        elif key in ['morpheme']:
            try:
                morpheme_object = Gloss.objects.get(pk=int(query_parameters[key]))
                query_dict[key] = morpheme_object.idgloss
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                query_dict[key] = query_parameters[key]
        elif key in ['createdBefore', 'createdAfter']:
            created_date = DT.datetime.strptime(query_parameters[key], settings.DATE_FORMAT).date()
            query_dict[key] = created_date.strftime(settings.DATE_FORMAT)
        else:
            # key can be keyword, just print the value
            # includes relationToForeignSign, relation
            query_dict[key] = query_parameters[key]

    for language in dataset_languages:
        glosssearch_field_name = gloss_search_field_prefix + language.language_code_2char
        if glosssearch_field_name in query_parameters:
            query_dict[glosssearch_field_name] = query_parameters[glosssearch_field_name]
        lemma_field_name = lemma_search_field_prefix + language.language_code_2char
        if lemma_field_name in query_parameters:
            query_dict[lemma_field_name] = query_parameters[lemma_field_name]
        keyword_field_name = keyword_search_field_prefix + language.language_code_2char
        if keyword_field_name in query_parameters:
            query_dict[keyword_field_name] = query_parameters[keyword_field_name]

    return query_dict


def query_parameters_toggle_fields(query_parameters):
    query_fields_focus = []
    query_fields_parameters = []
    for qp_key in query_parameters.keys():
        if qp_key in ['search_type', 'isRepresentative', 'annotatedSentenceContains']:
            continue
        if qp_key.startswith(GlossSearchForm.gloss_search_field_prefix) or \
                qp_key.startswith(GlossSearchForm.lemma_search_field_prefix) or \
                qp_key.startswith(GlossSearchForm.keyword_search_field_prefix):
            continue
        if qp_key[:-2] in settings.GLOSS_LIST_DISPLAY_FIELDS:
            continue
        if qp_key == 'hasRelation[]':
            query_fields_parameters.append(query_parameters[qp_key])
        if qp_key[-2:] == '[]':
            query_fields_focus.append(qp_key[:-2])
        else:
            query_fields_focus.append(qp_key)

    if 'hasRelationToForeignSign' in query_fields_focus and 'relationToForeignSign' not in query_fields_focus:
        if query_parameters['hasRelationToForeignSign'] == '2':
            # If hasRelationToForeignSign is True, show the relations in the result table
            query_fields_focus.append('relationToForeignSign')

    gloss_list_display_fields = getattr(settings, 'GLOSS_LIST_DISPLAY_FIELDS', [])
    toggle_gloss_list_display_fields = [(gloss_list_field,
                                         GlossSearchForm.get_field(gloss_list_field).label.encode(
                                             'utf-8').decode()) for gloss_list_field in gloss_list_display_fields]

    toggle_query_parameter_fields = []
    for query_field in query_fields_focus:
        if query_field == 'search_type':
            # don't show a button for this
            continue
        if query_field in GlossSearchForm.get_field_names():
            toggle_query_parameter = (query_field,
                                      GlossSearchForm.get_field(query_field).label.encode('utf-8').decode())
        elif query_field == 'dialect':
            toggle_query_parameter = (query_field, _("Dialect"))
        elif query_field == 'sentenceType':
            toggle_query_parameter = (query_field, _("Sentence Type"))
        elif query_field == 'negative':
            toggle_query_parameter = (query_field, _("Negative"))
        elif query_field == 'isRepresentative':
            toggle_query_parameter = (query_field, _("Is Representative"))
        elif query_field == 'sentenceContains':
            toggle_query_parameter = (query_field, _("Sentence Contains"))
        elif query_field == 'annotatedSentenceContains':
            toggle_query_parameter = (query_field, _("Annotated Sentence Contains"))
        else:
            print('toggle drop through: ', query_field)
            toggle_query_parameter = (query_field, query_field.capitalize())
        toggle_query_parameter_fields.append(toggle_query_parameter)

    toggle_publication_fields = []
    if hasattr(settings, 'SEARCH_BY') and 'publication' in settings.SEARCH_BY.keys():
        for publication_field in settings.SEARCH_BY['publication']:
            toggle_publication_fields.append((publication_field,
                                              GlossSearchForm.get_field(publication_field).label.encode(
                                                  'utf-8').decode()))

    return query_fields_focus, query_fields_parameters, \
        toggle_gloss_list_display_fields, toggle_query_parameter_fields, toggle_publication_fields


def search_fields_from_get(searchform, GET):
    """
    Collect non-empty search fields from GET into dictionary
    Called from get_context_data
    :form: MorphemeSearchForm, FocusGlossSearchForm, LemmaSearchForm
    :view: MorphemeListView, MinimalPairsListView, LemmaListView
    :model: Morpheme, Gloss, LemmaIdgloss
    """
    search_keys = []
    search_fields_to_populate = dict()
    if not searchform:
        return search_keys, search_fields_to_populate
    search_form_fields = searchform.fields.keys()
    for get_key, get_value in GET.items():
        if get_key in ['filter']:
            continue
        if get_value in ['', '0']:
            continue
        if get_key.endswith('[]'):
            vals = GET.getlist(get_key)
            search_fields_to_populate[get_key] = vals
            search_keys.append(get_key)
        elif get_key in ['translation', 'search']:
            print(get_key, html.escape(get_value))
            search_fields_to_populate[get_key] = html.escape(get_value)
        elif get_key not in search_form_fields:
            # skip csrf_token and page
            continue
        else:
            search_fields_to_populate[get_key] = get_value
            search_keys.append(get_key)

    return search_keys, search_fields_to_populate


def queryset_from_get(formclass, searchform, GET, qs):
    """
    Function used by MorphemeListView
    Called from get_queryset
    :form: MorphemeSearchForm
    :view: MorphemeListView
    :model: Morpheme
    """
    text_filter = 'iregex' if USE_REGULAR_EXPRESSIONS else 'icontains'
    for get_key, get_value in GET.items():
        if get_key.endswith('[]'):
            if not get_value:
                continue
            # multiple select
            vals = GET.getlist(get_key)
            field = get_key[:-2]
            if not vals:
                continue
            if field in ['dialect', 'signlanguage', 'semField', 'derivHist']:
                query_filter = field + '__in'
                qs = qs.filter(**{query_filter: get_value})
            elif field in ['definitionRole']:
                definitions_with_this_role = Definition.objects.filter(role__machine_value__in=vals)
                pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role]
                qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)
            elif field in ['tags']:
                values = [int(v) for v in vals]
                morphemes_with_tag = list(
                    TaggedItem.objects.filter(tag__id__in=values).values_list('object_id', flat=True))
                qs = qs.filter(id__in=morphemes_with_tag)
            else:
                query_filter = field + '__machine_value__in'
                qs = qs.filter(**{query_filter: vals})
        elif get_key not in searchform.fields.keys() \
                or get_value in ['', '0']:
            continue
        elif searchform.fields[get_key].widget.input_type in ['text']:
            if get_key in ['search', 'translation', 'sortOrder']:
                continue
            elif get_key in ['definitionContains']:
                definitions_with_this_text = Definition.objects.filter(text__icontains=get_value)
                pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in
                                                          definitions_with_this_text]
                qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)
            elif get_key in ['createdBy']:
                created_by_search_string = ' '.join(get_value.strip().split())  # remove redundant spaces
                qs = qs.annotate(
                    created_by=Concat('creator__first_name', V(' '), 'creator__last_name', output_field=CharField())) \
                    .filter(created_by__icontains=created_by_search_string)
            elif hasattr(searchform, 'gloss_search_field_prefix') and \
                    get_key.startswith(formclass.gloss_search_field_prefix):
                language_code_2char = get_key[len(formclass.gloss_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                query_filter_annotation_text = 'annotationidglosstranslation__text__' + text_filter
                qs = qs.filter(**{query_filter_annotation_text: get_value,
                                  'annotationidglosstranslation__language': language})
            elif hasattr(searchform, 'lemma_search_field_prefix') and \
                    get_key.startswith(formclass.lemma_search_field_prefix):
                language_code_2char = get_key[len(formclass.lemma_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                query_filter_lemma_text = 'lemma__lemmaidglosstranslation__text__' + text_filter
                qs = qs.filter(**{query_filter_lemma_text: get_value,
                                  'lemma__lemmaidglosstranslation__language': language})
            elif hasattr(searchform, 'keyword_search_field_prefix') and \
                    get_key.startswith(formclass.keyword_search_field_prefix):
                language_code_2char = get_key[len(formclass.keyword_search_field_prefix):]
                language = Language.objects.filter(language_code_2char=language_code_2char).first()
                query_filter_sense_text = 'translation__translation__text__' + text_filter
                qs = qs.filter(**{query_filter_sense_text: get_value,
                                  'translation__language': language})
            else:
                # normal text field
                query_filter = get_key + '__icontains'
                qs = qs.filter(**{query_filter: get_value})
                continue

        elif searchform.fields[get_key].widget.input_type in ['date']:
            if get_key == 'createdBefore':
                created_before_date = DT.datetime.strptime(get_value, settings.DATE_FORMAT).date()
                qs = qs.filter(creationDate__range=(EARLIEST_GLOSS_CREATION_DATE, created_before_date))
            elif get_key == 'createdAfter':
                created_after_date = DT.datetime.strptime(get_value, settings.DATE_FORMAT).date()
                qs = qs.filter(creationDate__range=(created_after_date, DT.datetime.now()))
        elif searchform.fields[get_key].widget.input_type in ['select']:
            if get_key in ['inWeb', 'repeat', 'altern', 'isNew']:
                val = get_value == '2'
                key = get_key + '__exact'
            elif get_key in ['hasvideo', 'hasnmevideo']:
                # this is done in a separate function
                continue
            elif get_key in ['defspublished']:
                val = get_value == '2'
                key = 'definition__published'
            else:
                print('Morpheme Search input type select fall through: ', get_key, get_value)
                continue

            kwargs = {key: val}
            qs = qs.filter(**kwargs)
        else:
            # everything should already be taken care of
            print('Morpheme Search input type fall through: ', get_key, get_value,
                  searchform.fields[get_key].widget.input_type)

    return qs


def set_up_fieldchoice_translations(form, fields_with_choices):
    """
    Set up field choice choices in the form.
    This is done dynamically to make the choices language dependent (model translations).
    Called from __init__ method of the view
    :form: GlossSearchForm, MorphemeSearchForm, SentenceForm, FocusGlossSearchForm
    :view: GlossListView, MorphemeListView, SenseListView, MinimalPairsListView
    """
    for (fieldname, field_category) in fields_with_choices.items():
        if fieldname not in form.fields.keys():
            continue
        if fieldname == 'hasRelation':
            # non-fieldchoice field, allow translations
            relations = [('homonym', _('Homonym')),
                         ('synonym', _('Synonym')),
                         ('variant', _('Variant')),
                         ('antonym', _('Antonym')),
                         ('hyponym', _('Hyponym')),
                         ('hypernym', _('Hypernym')),
                         ('seealso', _('See Also')),
                         ('paradigm', _('Handshape Paradigm'))]
            form.fields[fieldname].choices = relations
            continue
        elif fieldname.startswith('semField'):
            field_choices = SemanticField.objects.all().order_by('name')
        elif fieldname.startswith('derivHist'):
            field_choices = DerivationHistory.objects.all().order_by('name')
        else:
            field_choices = FieldChoice.objects.filter(field__iexact=field_category).order_by('name')
        translated_choices = choicelist_queryset_to_translated_dict(field_choices, ordered=False,
                                                                    id_prefix='',
                                                                    shortlist=True)
        form.fields[fieldname].choices = translated_choices


def set_up_language_fields(model, view, form):
    """
    Set up the language fields of the form.
    This is done dynamically since they depend on the selected datasets.
    Called from get_context_data method of the view
    If only one translation language is used, the name of the language is omitted from the field label.
    :model: Gloss, Morpheme, GlossSense, LemmaIdgloss, AnnotatedSentence
    :form: GlossSearchForm, MorphemeSearchForm, FocusGlossSearchForm, LemmaSearchForm, AnnotatedSentenceForm
    :view: GlossListView, MorphemeListView, SenseListView, MinimalPairsListView, LemmaListView, AnnotatedSentenceListView
    """
    from signbank.dictionary.context_data import get_selected_datasets
    selected_datasets = get_selected_datasets(view.request)
    dataset_languages = get_dataset_languages(selected_datasets)
    interface_language = [view.request.LANGUAGE_CODE]
    count_languages = len(dataset_languages)
    for language in dataset_languages:
        if hasattr(form, 'gloss_search_field_prefix'):
            annotation_field_name = form.gloss_search_field_prefix + language.language_code_2char
            if model in [Morpheme]:
                annotation_field_label = _("Annotation")
            else:
                annotation_field_label = _("Gloss")
            if count_languages > 1 or language.language_code_2char not in interface_language:
                annotation_field_label += (" (%s)" % language.name)
            form.fields[annotation_field_name] = forms.CharField(label=annotation_field_label)

        if hasattr(form, 'keyword_search_field_prefix'):
            keyword_field_name = form.keyword_search_field_prefix + language.language_code_2char
            if model in [Morpheme]:
                # Morphemes have translations not senses
                keyword_field_label = _("Translations")
            else:
                keyword_field_label = _("Senses")
            if count_languages > 1 or language.language_code_2char not in interface_language:
                keyword_field_label += (" (%s)" % language.name)
            form.fields[keyword_field_name] = forms.CharField(label=keyword_field_label)

        if hasattr(form, 'lemma_search_field_prefix'):
            lemma_field_name = form.lemma_search_field_prefix + language.language_code_2char
            lemma_field_label = _("Lemma")
            if count_languages > 1 or language.language_code_2char not in interface_language:
                lemma_field_label += (" (%s)" % language.name)
            form.fields[lemma_field_name] = forms.CharField(label=lemma_field_label)

        if hasattr(form, 'annotatedsentence_search_field_prefix'):
            annotatedsentence_field_name = form.annotatedsentence_search_field_prefix + language.language_code_2char
            annotatedsentence_field_label = _("Sentence")
            if count_languages > 1 or language.language_code_2char not in interface_language:
                annotatedsentence_field_label += (" (%s)" % language.name)
            form.fields[annotatedsentence_field_name] = forms.CharField(label=annotatedsentence_field_label)


def set_up_signlanguage_dialects_fields(view, form):
    """
    Set up the sign language and dialect fields of the form.
    This is done dynamically since they depend on the selected datasets.
    Called from get_context_data method of the view
    :form: GlossSearchForm
    :view: GlossListView, SenseListView
    """
    from signbank.dictionary.context_data import get_selected_datasets
    selected_datasets = get_selected_datasets(view.request)
    field_label_signlanguage = gettext("Sign Language")
    field_label_dialects = gettext("Dialect")
    form.fields['signLanguage'] = forms.ModelMultipleChoiceField(label=field_label_signlanguage,
                                                                 widget=Select2,
                                                                 queryset=SignLanguage.objects.filter(
                                                                     dataset__in=selected_datasets).distinct())

    form.fields['dialects'] = forms.ModelMultipleChoiceField(label=field_label_dialects,
                                                             widget=Select2,
                                                             queryset=Dialect.objects.filter(
                                                                 signlanguage__dataset__in=selected_datasets))


def legitimate_search_form_url_parameter(searchform, get_key):

    if not searchform:
        return False

    if get_key in searchform.fields.keys():
        return True

    return False


def queryset_glosssense_from_get(model, formclass, searchform, GET, qs):
    """
    Function used by both GlossListView and SenseListView
    Called from get_queryset
    The gloss_prefix is used for SenseListView to access the gloss since it queries over GlossSense
    :form: GlossSearchForm, FocusGlossSearchForm
    :view: GlossListView, SenseListView, MinimalPairsListView
    :model: Gloss, GlossSense
    """
    if not searchform:
        return qs
    gloss_prefix = 'gloss__' if model in ['GlossSense', 'AnnotatedGloss'] else ''
    text_filter = 'iregex' if USE_REGULAR_EXPRESSIONS else 'icontains'
    for get_key, get_value in GET.items():
        if get_value in ['', '0']:
            continue
        if get_key.endswith('[]'):
            if not get_value:
                continue
            # multiple select
            vals = GET.getlist(get_key)
            if not vals:
                continue
            field = get_key[:-2]
            if field in ['sentenceType']:
                continue
            if field in ['dialect', 'signlanguage', 'semField', 'derivHist']:
                query_filter = gloss_prefix + field + '__in'
                qs = qs.filter(**{query_filter: vals}).distinct()
            elif field in ['definitionRole']:
                definitions_with_this_role = Definition.objects.filter(role__machine_value__in=vals)
                pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role]
                query_filter = gloss_prefix + 'pk__in'
                qs = qs.filter(**{query_filter: pks_for_glosses_with_these_definitions})
            elif field in ['hasComponentOfType']:
                morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__machine_value__in=vals)
                pks_for_glosses_with_morphdefs = [morphdef.parent_gloss.pk for morphdef in morphdefs_with_correct_role]
                query_filter = gloss_prefix + 'pk__in'
                qs = qs.filter(**{query_filter: pks_for_glosses_with_morphdefs})
            elif field in ['mrpType']:
                target_morphemes = [m.id for m in Morpheme.objects.filter(mrpType__machine_value__in=vals)]
                query_filter = gloss_prefix + 'id__in'
                qs = qs.filter(**{query_filter: target_morphemes})
            elif field in ['hasRelation']:
                relations_with_this_role = Relation.objects.filter(role__in=vals)
                pks_for_glosses_with_correct_relation = [relation.source.pk for relation in relations_with_this_role]
                query_filter = gloss_prefix + 'pk__in'
                qs = qs.filter(**{query_filter: pks_for_glosses_with_correct_relation})
            elif field in ['tags']:
                values = [int(v) for v in vals]
                morphemes_with_tag = list(
                    TaggedItem.objects.filter(tag__id__in=values).values_list('object_id', flat=True))
                query_filter = gloss_prefix + 'id__in'
                qs = qs.filter(**{query_filter: morphemes_with_tag})
            else:
                query_filter = gloss_prefix + field + '__machine_value__in'
                qs = qs.filter(**{query_filter: vals})
        elif not legitimate_search_form_url_parameter(searchform, get_key):
            continue
        elif get_key.startswith(formclass.gloss_search_field_prefix):
            language_code_2char = get_key[len(formclass.gloss_search_field_prefix):]
            language = Language.objects.filter(language_code_2char=language_code_2char).first()
            query_filter_annotation_text = gloss_prefix + 'annotationidglosstranslation__text__' + text_filter
            query_filter_language = gloss_prefix + 'annotationidglosstranslation__language'
            qs = qs.filter(**{query_filter_annotation_text: get_value,
                              query_filter_language: language})
            continue
        elif get_key.startswith(formclass.lemma_search_field_prefix):
            language_code_2char = get_key[len(formclass.lemma_search_field_prefix):]
            language = Language.objects.filter(language_code_2char=language_code_2char).first()
            query_filter_lemma_text = gloss_prefix + 'lemma__lemmaidglosstranslation__text__' + text_filter
            query_filter_language = gloss_prefix + 'lemma__lemmaidglosstranslation__language'
            qs = qs.filter(**{query_filter_lemma_text: get_value,
                              query_filter_language: language})
            continue
        elif get_key.startswith(formclass.keyword_search_field_prefix):
            language_code_2char = get_key[len(formclass.keyword_search_field_prefix):]
            language = Language.objects.filter(language_code_2char=language_code_2char).first()
            query_filter_sense_text = gloss_prefix + 'translation__translation__text__' + text_filter
            query_filter_language = gloss_prefix + 'translation__language'
            # for some reason, distinct is needed here
            qs = qs.filter(**{query_filter_sense_text: get_value,
                              query_filter_language: language}).distinct()
            continue
        elif searchform.fields[get_key].widget.input_type in ['text']:
            if get_key in ['search', 'sortOrder', 'translation']:
                continue
            elif get_key in ['morpheme']:
                # Filter all glosses that contain this morpheme in their simultaneous morphology
                try:
                    selected_morpheme = Morpheme.objects.get(pk=int(get_value))
                except (ObjectDoesNotExist, ValueError):
                    continue
                potential_pks = [appears.parent_gloss.pk for appears
                                 in SimultaneousMorphologyDefinition.objects.filter(morpheme=selected_morpheme)]
                query_filter = gloss_prefix + 'pk__in'
                qs = qs.filter(**{query_filter: potential_pks})
            elif get_key in ['definitionContains']:
                definitions_with_this_text = Definition.objects.filter(text__icontains=get_value)
                pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in
                                                          definitions_with_this_text]
                query_filter = gloss_prefix + 'pk__in'
                qs = qs.filter(**{query_filter: pks_for_glosses_with_these_definitions})
            elif get_key in ['relation']:
                potential_targets = Gloss.objects.filter(annotationidglosstranslation__text__icontains=get_value)
                relations = Relation.objects.filter(target__in=potential_targets)
                potential_pks = [relation.source.pk for relation in relations]
                query_filter = gloss_prefix + 'pk__in'
                qs = qs.filter(**{query_filter: potential_pks})
            elif get_key in ['relationToForeignSign']:
                relations = RelationToForeignSign.objects.filter(gloss__archived__exact=False,
                                                                 other_lang_gloss__icontains=get_value)
                potential_pks = [relation.gloss.pk for relation in relations]
                qs = qs.filter(pk__in=potential_pks)
                query_filter = gloss_prefix + 'pk__in'
                qs = qs.filter(**{query_filter: potential_pks})
            elif get_key in ['createdBy']:
                first_name = gloss_prefix + 'creator__first_name__icontains'
                last_name = gloss_prefix + 'creator__last_name__icontains'
                qs = qs.filter(Q(**{first_name:get_value}) | Q(**{last_name:get_value}))
            else:
                # normal text field
                query_filter = gloss_prefix + get_key + '__icontains'
                qs = qs.filter(**{query_filter: get_value})
                continue

        elif searchform.fields[get_key].widget.input_type in ['date']:
            query_filter = gloss_prefix + 'creationDate__range'
            if get_key == 'createdBefore':
                created_before_date = DT.datetime.strptime(get_value, settings.DATE_FORMAT).date()
                qs = qs.filter(**{query_filter: (EARLIEST_GLOSS_CREATION_DATE, created_before_date)})
            elif get_key == 'createdAfter':
                created_after_date = DT.datetime.strptime(get_value, settings.DATE_FORMAT).date()
                qs = qs.filter(**{query_filter: (created_after_date, DT.datetime.now())})
        elif searchform.fields[get_key].widget.input_type in ['select']:
            if get_key in ['hasmultiplesenses']:
                if get_value == '2':
                    multiple_senses = [gsv['gloss'] for gsv in GlossSense.objects.values(
                        'gloss').annotate(Count('id')).filter(id__count__gt=1)]
                else:
                    multiple_senses = [gsv['gloss'] for gsv in GlossSense.objects.values(
                        'gloss').annotate(Count('id')).filter(id__count=1)]
                query_filter = gloss_prefix + 'id__in'
                qs = qs.filter(**{query_filter: multiple_senses})
                continue
            elif get_key in ['hasothermedia']:
                pks_for_glosses_with_othermedia = [om.parent_gloss.pk for om in OtherMedia.objects.all()]
                query_filter = gloss_prefix + 'pk__in'
                if get_value == '2':  # We only want glosses with other media
                    qs = qs.filter(**{query_filter: pks_for_glosses_with_othermedia})
                else:  # We only want glosses without other media
                    qs = qs.exclude(**{query_filter: pks_for_glosses_with_othermedia})
                continue
            elif get_key in ['hasRelationToForeignSign']:
                pks_for_glosses_with_relations = [relation.gloss.pk
                                                  for relation in RelationToForeignSign.objects.filter(gloss__archived__exact=False)]
                query_filter = gloss_prefix + 'pk__in'
                if get_value == '2':  # glosses with a relation to a foreign sign
                    qs = qs.filter(**{query_filter: pks_for_glosses_with_relations})
                else:  # glosses without a relation to a foreign sign
                    qs = qs.exclude(**{query_filter: pks_for_glosses_with_relations})
                continue
            elif get_key in ['isablend']:
                pks_for_gloss_blends = [blemorph.parent_gloss.pk
                                        for blemorph in BlendMorphology.objects.filter(parent_gloss__archived__exact=False,
                                                                                       glosses__archived__exact=False)]
                query_filter = gloss_prefix + 'pk__in'
                if get_value == '2':  # glosses that are blends
                    qs = qs.filter(**{query_filter: pks_for_gloss_blends})
                else:  # glosses that are not blends
                    qs = qs.exclude(**{query_filter: pks_for_gloss_blends})
                continue
            elif get_key in ['ispartofablend']:
                pks_for_glosses_of_blends = [blemorph.glosses.pk
                                             for blemorph in BlendMorphology.objects.filter(parent_gloss__archived__exact=False,
                                                                                            glosses__archived__exact=False)]
                query_filter = gloss_prefix + 'pk__in'
                if get_value == '2':  # glosses that are part of blends
                    qs = qs.filter(**{query_filter: pks_for_glosses_of_blends})
                else:  # glosses that are not part of blends
                    qs = qs.exclude(**{query_filter: pks_for_glosses_of_blends})
                continue
            elif get_key in ['inWeb', 'repeat', 'altern', 'isNew', 'excludeFromEcv']:
                val = get_value == '2'
                key = gloss_prefix + get_key + '__exact'
            elif get_key in ['hasvideo', 'hasnmevideo']:
                # this is done in a separate function
                continue
            elif get_key in ['defspublished']:
                val = get_value == '2'
                key = gloss_prefix + 'definition__published'
            elif get_key in ['weakdrop', 'weakprop',
                             'domhndsh_letter', 'domhndsh_number', 'subhndsh_letter', 'subhndsh_number']:
                key = gloss_prefix + get_key + '__exact'
                val = {'0': '', '1': None, '2': True, '3': False}[get_value]
            else:
                print('1102. Gloss/GlossSense Search input type select fall through: ', get_key, get_value)
                continue

            kwargs = {key: val}
            qs = qs.filter(**kwargs)
        else:
            # everything should already be taken care of
            print('1109. Gloss/GlossSense Search input type fall through: ', get_key, get_value,
                  searchform.fields[get_key].widget.input_type)

    return qs


def queryset_sentences_from_get(searchform, GET, qs):
    # this function is used by SenseListView get_queryset
    """
    Function used by SenseListView
    Called from get_queryset
    :form: SentenceForm
    :view: SenseListView
    :model: GlossSense
    """
    if not searchform:
        return qs
    for get_key, get_value in GET.items():
        if get_key.endswith('[]'):
            if not get_value:
                continue
            # multiple select
            vals = GET.getlist(get_key)
            if not vals:
                continue
            if get_key in ['sentenceType[]']:
                sentences_with_this_type = ExampleSentence.objects.filter(sentenceType__machine_value__in=vals)
                qs = qs.filter(sense__exampleSentences__in=sentences_with_this_type).distinct()
        elif get_key not in searchform.fields.keys() \
                or get_value in ['', '0']:
            continue
        elif searchform.fields[get_key].widget.input_type in ['text']:
            if get_key in ['sentenceContains']:
                sentence_translations_with_this_text = ExampleSentenceTranslation.objects.filter(
                    text__icontains=get_value)
                sentences_with_this_text = [est.examplesentence for est in sentence_translations_with_this_text]
                qs = qs.filter(sense__exampleSentences__in=sentences_with_this_text).distinct()
        elif searchform.fields[get_key].widget.input_type in ['select']:
            if get_key in ['negative']:
                sentences_with_negative_type = ExampleSentence.objects.filter(negative__exact=True)
                sentences_with_other_type = ExampleSentence.objects.filter(negative__exact=False)
                if get_value == 'yes':  # only senses with negative sentences
                    qs = qs.filter(sense__exampleSentences__in=sentences_with_negative_type).distinct()
                else:  # only senses sentences that are not negative
                    qs = qs.filter(sense__exampleSentences__in=sentences_with_other_type).distinct()
    return qs


def queryset_annotatedgloss_from_get(searchform, GET, qs):
    # this function is used by AnnotatedGlossListView get_queryset
    """
    Function used by AnnotatedGlossListView
    Called from get_queryset
    :form: AnnotatedGlossForm
    :view: AnnotatedGlossListView
    :model: AnnotatedGloss
    """
    if not searchform:
        return qs
    for get_key, get_value in GET.items():
        if get_key.endswith('[]'):
            # no multi-select search fields
            continue
        elif get_key not in searchform.fields.keys() \
                or get_value in ['', '0']:
            continue
        elif searchform.fields[get_key].widget.input_type in ['text']:
            if get_key in ['annotatedSentenceContains']:
                sentence_translations_with_this_text = AnnotatedSentenceTranslation.objects.filter(
                    text__icontains=get_value)
                sentences_with_this_text = [est.annotatedsentence.id for est in sentence_translations_with_this_text]
                qs = qs.filter(annotatedsentence__id__in=sentences_with_this_text).distinct()
        elif searchform.fields[get_key].widget.input_type in ['select']:
            if get_key in ['isRepresentative']:
                sentences_with_negative_type = AnnotatedGloss.objects.filter(isRepresentative__exact=True)
                sentences_with_other_type = AnnotatedGloss.objects.filter(isRepresentative__exact=False)
                if get_value == 'yes':  # only annotated glosses that are representative
                    qs = qs.filter(id__in=sentences_with_negative_type).distinct()
                else:  # only annotated glosses that are not representative
                    qs = qs.filter(id__in=sentences_with_other_type).distinct()
    return qs


def query_parameters_from_get(searchform, GET, query_parameters):
    """
    Function to collect non-empty search fields from GET
    Called from get_queryset
    :form: GlossSearchForm, SentenceForm
    :view: GlossListView, SenseListView
    :model: Gloss, GlossSense
    """
    if not searchform:
        return query_parameters
    search_form_fields = searchform.fields.keys()
    for get_key, get_value in GET.items():
        if get_value in ['', '0']:
            continue
        if get_key.endswith('[]'):
            vals = GET.getlist(get_key)
            if not vals:
                continue
            query_parameters[get_key] = vals
        elif get_key not in search_form_fields:
            # skip csrf_token and page
            continue
        else:
            query_parameters[get_key] = get_value
    return query_parameters

