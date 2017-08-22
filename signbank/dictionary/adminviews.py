from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.db.models import Q, F, ExpressionWrapper, IntegerField
from django.db.models import CharField, Value as V
from django.db.models.functions import Concat
from django.db.models.fields import NullBooleanField
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.utils.translation import override
from django.forms.fields import TypedChoiceField, ChoiceField
from django.shortcuts import *

import csv
import operator
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import datetime as DT

from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from signbank.feedback.models import *
from signbank.video.forms import VideoUploadForGlossForm
from tagging.models import Tag, TaggedItem
from signbank.settings.base import ECV_FILE,EARLIEST_GLOSS_CREATION_DATE, FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD, LANGUAGE_CODE, ECV_SETTINGS, URL, LANGUAGE_CODE_MAP
from signbank.settings import server_specific
from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value, choicelist_queryset_to_translated_dict


def order_queryset_by_sort_order(get, qs):
    """Change the sort-order of the query set, depending on the form field [sortOrder]

    This function is used both by GlossListView as well as by MorphemeListView.
    The value of [sortOrder] is 'idgloss' by default.
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

    # Set the default sort order
    sOrder = 'idgloss'  # Default sort order if nothing is specified
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

class GlossListView(ListView):
    
    model = Gloss
    template_name = 'dictionary/admin_gloss_list.html'
    paginate_by = 500
    only_export_ecv = False #Used to call the 'export ecv' functionality of this view without the need for an extra GET parameter
    search_type = 'sign'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(GlossListView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books

        # Retrieve the search_type,so that we know whether the search should be restricted to Gloss or not
        if 'search_type' in self.request.GET:
            self.search_type = self.request.GET['search_type']

        search_form = GlossSearchForm(self.request.GET)

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
        if self.search_type == 'sign':
            context['glosscount'] = Gloss.none_morpheme_objects().count()   # Only count the none-morpheme glosses
        else:
            context['glosscount'] = Gloss.objects.count()  # Count the glosses + morphemes

        context['add_gloss_form'] = GlossCreateForm()
        context['ADMIN_RESULT_FIELDS'] = settings.ADMIN_RESULT_FIELDS

        if hasattr(settings, 'SHOW_MORPHEME_SEARCH'):
            context['SHOW_MORPHEME_SEARCH'] = settings.SHOW_MORPHEME_SEARCH
        else:
            context['SHOW_MORPHEME_SEARCH'] = False

        context['input_names_fields_and_labels'] = {}

        for topic in ['main','phonology','semantics']:

            context['input_names_fields_and_labels'][topic] = []

            for fieldname in settings.FIELDS[topic]:
                field = search_form[fieldname]
                label = field.label

                context['input_names_fields_and_labels'][topic].append((fieldname,field,label))

        try:
            context['show_all'] = self.kwargs['show_all']
        except KeyError:
            context['show_all'] = False

        context['paginate_by'] = self.request.GET.get('paginate_by', self.paginate_by)

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
        description  = 'DESCRIPTION'
        language     = 'LANGUAGE'
        lang_ref     = 'LANG_REF'

        cv_entry_ml  = 'CV_ENTRY_ML'
        cve_id       = 'CVE_ID'
        cve_value    = 'CVE_VALUE'

        topattributes = {'xmlns:xsi':"http://www.w3.org/2001/XMLSchema-instance",
                         'DATE':str(DT.date.today())+ 'T'+str(DT.datetime.now().time()),
                         'AUTHOR':'',
                         'VERSION':'0.2',
                         'xsi:noNamespaceSchemaLocation':"http://www.mpi.nl/tools/elan/EAFv2.8.xsd"}
        top = ET.Element('CV_RESOURCE', topattributes)

        for lang in ECV_SETTINGS['languages']:
            ET.SubElement(top, language, lang['attributes'])

        cv_element = ET.SubElement(top, 'CONTROLLED_VOCABULARY', {'CV_ID':ECV_SETTINGS['CV_ID']})

        # description f0r cv_element
        for lang in ECV_SETTINGS['languages']:
            myattributes = {lang_ref: lang['id']}
            desc_element = ET.SubElement(cv_element, description, myattributes)
            desc_element.text = lang['description']

        # Make sure we iterate only over the none-Morpheme glosses
        for gloss in Gloss.none_morpheme_objects().filter(excludeFromEcv=False):
            glossid = str(gloss.pk)
            myattributes = {cve_id: glossid, 'EXT_REF':'signbank-ecv'}
            cve_entry_element = ET.SubElement(cv_element, cv_entry_ml, myattributes)

            for lang in ECV_SETTINGS['languages']:
                langId = lang['id']
                if len(langId) == 3:
                    langId = [c[2] for c in LANGUAGE_CODE_MAP if c[3] == langId][0]
                desc = self.get_ecv_descripion_for_gloss(gloss, langId, ECV_SETTINGS['include_phonology_and_frequencies'])
                cve_value_element = ET.SubElement(cve_entry_element, cve_value, {description:desc, lang_ref:lang['id']})
                cve_value_element.text = self.get_value_for_ecv(gloss, lang['annotation_idgloss_fieldname'])

        ET.SubElement(top, 'EXTERNAL_REF', {'EXT_REF_ID':'signbank-ecv', 'TYPE':'resource_url', 'VALUE':URL + "/dictionary/gloss/"})

        xmlstr = minidom.parseString(ET.tostring(top,'utf-8')).toprettyxml(indent="   ")
        import codecs
        with codecs.open(ECV_FILE, "w", "utf-8") as f:
            f.write(xmlstr)

#        tree = ET.ElementTree(top)
#        tree.write(open(ECV_FILE, 'w'), encoding ="utf-8",xml_declaration=True, method="xml")

        return HttpResponse('OK')

    def get_ecv_descripion_for_gloss(self, gloss, lang, include_phonology_and_frequencies=False):
        desc = ""
        if include_phonology_and_frequencies:
            description_fields = ['handedness','domhndsh', 'subhndsh', 'handCh', 'locprim', 'relOriMov', 'movDir','movSh', 'tokNo',
                          'tokNoSgnr'];

            for f in description_fields:
                if f in FIELDS['phonology']:
                    choice_list = FieldChoice.objects.filter(field__iexact=fieldname_to_category(f))
                    machine_value = getattr(gloss,f)
                    value = machine_value_to_translated_human_value(machine_value,choice_list,lang)
                    if value is None:
                        value = ' '
                else:
                    value = self.get_value_for_ecv(gloss,f)

                if f == 'handedness':
                    desc = value
                elif f == 'domhndsh':
                    desc = desc+ ', ('+ value
                elif f == 'subhndsh':
                    desc = desc+','+value
                elif f == 'handCh':
                    desc = desc+'; '+value+')'
                elif f == 'tokNo':
                    desc = desc+' ['+value
                elif f == 'tokNoSgnr':
                    desc = desc+'/'+value+']'
                else:
                    desc = desc+', '+value

        if desc:
            desc += ", "

        trans = [t.translation.text for t in gloss.translation_set.all()]
        desc += ", ".join(
            # The next line was adapted from an older version of this code,
            # that happened to do nothing. I left this for future usage.
            #map(lambda t: str(t.encode('ascii','xmlcharrefreplace')) if isinstance(t, unicode) else t, trans)
            trans
        )

        return desc

    def get_value_for_ecv(self, gloss, fieldname):
        try:
            value = getattr(gloss, 'get_'+fieldname+'_display')()

        except AttributeError:
            value = getattr(gloss,fieldname)

        # This was disabled with the move to python 3... might not be needed anymore
        # if isinstance(value,unicode):
        #     value = str(value.encode('ascii','xmlcharrefreplace'))

        if value is None:
           value = " "
        elif not isinstance(value,str):
            value = str(value)

        if value == '-':
            value = ' '
        return value


    # noinspection PyInterpreter,PyInterpreter
    def render_to_csv_response(self, context):

        if not self.request.user.has_perm('dictionary.export_csv'):
            raise PermissionDenied

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dictionary-export.csv"'


#        fields = [f.name for f in Gloss._meta.fields]
        #We want to manually set which fields to export here

        fieldnames = ['idgloss', 'annotation_idgloss', 'annotation_idgloss_en', 'useInstr', 'sense', 'StemSN', 'rmrks', 'handedness',
                      'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim', 'locVirtObj', 'relOriMov', 'relOriLoc', 'oriCh', 'contType',
                      'movSh', 'movDir', 'repeat', 'altern', 'phonOth', 'mouthG', 'mouthing', 'phonetVar',
                      'domSF', 'domFlex', 'oriChAbd', 'oriChFlex', 'iconImg', 'iconType',
                      'namEnt', 'semField', 'valence', 'lexCatNotes', 'tokNo', 'tokNoSgnr', 'tokNoA', 'tokNoV', 'tokNoR', 'tokNoGe',
                      'tokNoGr', 'tokNoO', 'tokNoSgnrA', 'tokNoSgnrV', 'tokNoSgnrR', 'tokNoSgnrGe',
                      'tokNoSgnrGr', 'tokNoSgnrO', 'inWeb', 'isNew']

        if hasattr(server_specific, 'SHOW_ENGLISH_ONLY') and server_specific.SHOW_ENGLISH_ONLY:
            fieldnames.pop(1) # Remove Annotation ID Gloss (Dutch) from list

        fields = [Gloss._meta.get_field(fieldname) for fieldname in fieldnames]

        writer = csv.writer(response)

        with override(LANGUAGE_CODE):
            header = ['Signbank ID'] + [f.verbose_name.title().encode('ascii','ignore').decode() for f in fields]

        for extra_column in ['SignLanguages','Dialects','Keywords','Morphology','Relations to other signs','Relations to foreign signs',]:
            header.append(extra_column);

        writer.writerow(header)

        for gloss in self.get_queryset():
            row = [str(gloss.pk)]
            for f in fields:

                #Try the value of the choicelist
                try:
                    row.append(getattr(gloss, 'get_'+f.name+'_display')())

                #If it's not there, try the raw value
                except AttributeError:
                    value = getattr(gloss,f.name)

                    # This was disabled with the move to Python 3... might not be needed anymore?
                    # if isinstance(value,unicode):
                    #     value = str(value.encode('ascii','xmlcharrefreplace'));

                    if not isinstance(value,str):
                        value = str(value);

                    row.append(value)

            # get languages
            signlanguages = [signlanguage.name for signlanguage in gloss.signlanguage.all()]
            row.append(", ".join(signlanguages));

            # get dialects
            dialects = [dialect.name for dialect in gloss.dialect.all()]
            row.append(", ".join(dialects));

            # get translations
            trans = [t.translation.text for t in gloss.translation_set.all()]
            row.append(", ".join(trans))

            # get morphology
            morphemes = [morpheme.morpheme.annotation_idgloss for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]
            row.append(", ".join(morphemes))

            # get relations to other signs
            relations = [relation.target.idgloss for relation in Relation.objects.filter(source=gloss)]
            row.append(", ".join(relations))

            # get relations to foreign signs
            relations = [relation.other_lang_gloss for relation in RelationToForeignSign.objects.filter(gloss=gloss)]
            row.append(", ".join(relations))


            #Make it safe for weird chars
            safe_row = [];
            for column in row:
                try:
                    safe_row.append(column.encode('utf-8').decode())
                except AttributeError:
                    safe_row.append(None);

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

        #Get the initial selection
        if len(get) > 0 or show_all:
            if self.search_type == 'sign':
                # Get all the GLOSS items that are not member of the sub-class Morpheme
                qs = Gloss.none_morpheme_objects().prefetch_related('parent_glosses').prefetch_related('morphemePart').prefetch_related('translation_set')
            else:
                qs = Gloss.objects.all().prefetch_related('parent_glosses').prefetch_related('morphemePart').prefetch_related('translation_set')

        #No filters or 'show_all' specified? show nothing
        else:
            qs = Gloss.objects.none()

        if not self.request.user.has_perm('dictionary.search_gloss'):
            qs = qs.filter(inWeb__exact=True)

        #If we wanted to get everything, we're done now
        if show_all:
            return order_queryset_by_sort_order(self.request.GET, qs)

        #If not, we will go trhough a long list of filters
        if 'search' in get and get['search'] != '':
            val = get['search']
            query = Q(idgloss__iregex=val) | \
                    Q(annotation_idgloss__iregex=val)

            if re.match('^\d+$', val):
                query = query | Q(sn__exact=val)

            qs = qs.filter(query)
            #print "A: ", len(qs)

        if 'englishGloss' in get and get['englishGloss'] != '':
            val = get['englishGloss']
            qs = qs.filter(annotation_idgloss_en__iregex=val)

        if 'keyword' in get and get['keyword'] != '':
            val = get['keyword']
            qs = qs.filter(translation__translation__text__iregex=val)


        if 'inWeb' in get and get['inWeb'] != '0':
            # Don't apply 'inWeb' filter, if it is unspecified ('0' according to the NULLBOOLEANCHOICES)
            val = get['inWeb'] == 'yes'
            qs = qs.filter(inWeb__exact=val)
            #print "B :", len(qs)


        if 'hasvideo' in get and get['hasvideo'] != 'unspecified':
            val = get['hasvideo'] == 'no'

            qs = qs.filter(glossvideo__isnull=val)

        if 'defspublished' in get and get['defspublished'] != 'unspecified':
            val = get['defspublished'] == 'yes'

            qs = qs.filter(definition__published=val)


        fieldnames = ['idgloss', 'annotation_idgloss', 'annotation_idgloss_en', 'useInstr', 'sense', 'morph', 'StemSN', 'compound', 'rmrks', 'handedness',
                      'domhndsh', 'subhndsh', 'locprim', 'locVirtObj', 'relatArtic',  'relOriMov', 'relOriLoc', 'oriCh', 'handCh', 'repeat', 'altern',
                      'movSh', 'movDir', 'contType', 'phonOth', 'mouthG', 'mouthing', 'phonetVar',
                      'domSF', 'domFlex', 'oriChAbd', 'oriChFlex', 'iconImg', 'iconType', 'namEnt', 'semField', 'valence',
                      'lexCatNotes','tokNo', 'tokNoSgnr','tokNoA', 'tokNoV', 'tokNoR', 'tokNoGe', 'tokNoGr', 'tokNoO', 'tokNoSgnrA',
                      'tokNoSgnrV', 'tokNoSgnrR', 'tokNoSgnrGe', 'tokNoSgnrGr', 'tokNoSgnrO', 'inWeb', 'isNew']

        # SignLanguage and basic property filters
        vals = get.getlist('dialect', [])
        if vals != []:
            qs = qs.filter(dialect__in=vals)

        vals = get.getlist('signlanguage', [])
        if vals != []:
            qs = qs.filter(signlanguage__in=vals)

        if 'useInstr' in get and get['useInstr'] != '':
            qs = qs.filter(useInstr__icontains=get['useInstr'])


        ## phonology and semantics field filters
        for fieldname in fieldnames:

            if fieldname in get:
                key = fieldname+'__exact'
                val = get[fieldname]

                if isinstance(Gloss._meta.get_field(fieldname),NullBooleanField):
                    val = {'0':'','1': None, '2': True, '3': False}[val]

                if val != '':
                    kwargs = {key:val}
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

            #print "J :", len(qs)

        qs = qs.distinct()

        if 'nottags' in get and get['nottags'] != '':
            vals = get.getlist('nottags')

           # print "NOT TAGS: ", vals

            tags = []
            for t in vals:
                tags.extend(Tag.objects.filter(name=t))

            # search is an implicit AND so intersection
            tqs = TaggedItem.objects.get_intersection_by_model(Gloss, tags)

           # print "NOT", tags, len(tqs)
            # exclude all of tqs from qs
            qs = [q for q in qs if q not in tqs]

           # print "K :", len(qs)

        if 'relationToForeignSign' in get and get['relationToForeignSign'] != '':

            relations = RelationToForeignSign.objects.filter(other_lang_gloss__icontains=get['relationToForeignSign'])
            potential_pks = [relation.gloss.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if 'hasRelationToForeignSign' in get and get['hasRelationToForeignSign'] != '0':

            pks_for_glosses_with_relations = [relation.gloss.pk for relation in RelationToForeignSign.objects.all()];
            # print('pks_for_glosses',pks_for_glosses_with_relations)

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
                relations_with_this_role = Relation.objects.all();
            else:
                relations_with_this_role = Relation.objects.filter(role__exact=get['hasRelation']);

            #Remember the pk of all glosses that take part in the collected relations
            pks_for_glosses_with_correct_relation = [relation.source.pk for relation in relations_with_this_role];
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_relation)

        if 'id_morpheme' in get and get['id_morpheme'] != '':

            # Filter all glosses that contain a morpheme with the indicated text in its gloss
            # Step 1: get all morphemes containing the indicated text
            potential_morphemes = Morpheme.objects.filter(idgloss__exact=get['id_morpheme']);
            if (potential_morphemes.count() > 0):
                # At least one has been found: take the first one
                selected_morpheme = potential_morphemes[0];
                # Step 2: get all Glosses containing the above morphemes
                potential_pks = [appears.pk for appears in Gloss.objects.filter(morphemePart=selected_morpheme)];
                qs = qs.filter(pk__in=potential_pks)

        if 'hasComponentOfType' in get and get['hasComponentOfType'] != '':

            # Look for "compound-components" of the indicated type. Compound Components are defined in class[MorphologyDefinition]
            morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__exact=get['hasComponentOfType']);
            pks_for_glosses_with_morphdefs_with_correct_role = [morphdef.parent_gloss.pk for morphdef in morphdefs_with_correct_role];
            qs = qs.filter(pk__in=pks_for_glosses_with_morphdefs_with_correct_role)

        if 'hasMorphemeOfType' in get and get['hasMorphemeOfType'] != '':

            # Get all Morphemes of the indicated mrpType
            target_morphemes = Morpheme.objects.filter(mrpType__exact=get['hasMorphemeOfType'])
            # Get all glosses that have one of the morphemes in this set
            glosses_with_correct_mrpType = Gloss.objects.filter(morphemePart__in=target_morphemes)
            # Turn this into a list with pks
            pks_for_glosses_with_correct_mrpType = [glossdef.pk for glossdef in glosses_with_correct_mrpType];
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_mrpType)

        if 'definitionRole' in get and get['definitionRole'] != '':

            #Find all definitions with this role
            if get['definitionRole'] == 'all':
                definitions_with_this_role = Definition.objects.all();
            else:
                definitions_with_this_role = Definition.objects.filter(role__exact=get['definitionRole']);

            #Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role];
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if 'definitionContains' in get and get['definitionContains'] != '':

            definitions_with_this_text = Definition.objects.filter(text__icontains=get['definitionContains']);

            #Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_text];
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
        self.request.session['search_results'] = None

        # Make sure that the QuerySet has filters applied (user is searching for something instead of showing all results [objects.all()])
        if hasattr(qs.query.where, 'children') and len(qs.query.where.children) > 0:

            items = []

            for item in qs:
                items.append(dict(id = item.id, gloss = item.annotation_idgloss))

            self.request.session['search_results'] = items

        # print "Final :", len(qs)
        # Sort the queryset by the parameters given
        qs = order_queryset_by_sort_order(self.request.GET, qs)

        # Return the resulting filtered and sorted queryset
        return qs


class GlossDetailView(DetailView):

    model = Gloss
    context_object_name = 'gloss'

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):

        try:
            self.object = self.get_object()
        except Http404:
            # return custom template
            return render(request, 'dictionary/warning.html', status=404)

        if request.user.is_authenticated():
            if not request.user.has_perm('dictionary.search_gloss'):
                if self.object.inWeb:
                    return HttpResponseRedirect(reverse('dictionary:public_gloss',kwargs={'idgloss':self.object.idgloss}))
                else:
                    return HttpResponse('')
        else:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'idgloss': self.object.idgloss}))
            else:
                return HttpResponseRedirect(reverse('registration:auth_login'))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
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
                                                                   self.request.LANGUAGE_CODE,ordered=False,id_prefix=''))

        context['morphemeform'] = GlossMorphemeForm()
        context['othermediaform'] = OtherMediaForm()
        context['navigation'] = context['gloss'].navigation(True)
        context['interpform'] = InterpreterFeedbackForm()
        context['SIGN_NAVIGATION']  = settings.SIGN_NAVIGATION
        context['handedness'] = (int(self.object.handedness) > 1) if self.object.handedness else 0  # minimal machine value is 2
        context['domhndsh'] = (int(self.object.domhndsh) > 2) if self.object.subhndsh else 0        # minimal machine value -s 3
        context['tokNo'] = self.object.tokNo                 # Number of occurrences of Sign, used to display Stars
        context['StrongHand'] = self.object.domhndsh
        context['WeakHand'] = self.object.subhndsh

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

        context['choice_lists'] = {}

        #Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['main','phonology','semantics','frequency']:
            context[topic+'_fields'] = [];

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
                if field in ['useInstr','phonOth','mouthG','mouthing','phonetVar','iconImg','locVirtObj']:
                    kind = 'text'
                elif field in ['repeat','altern','oriChAbd','oriChFlex']:
                    kind = 'check'
                else:
                    kind = 'list'

                context[topic+'_fields'].append([human_value,field,labels[field],kind]);

        #Add morphology to choice lists
        context['choice_lists']['morphology_role'] = choicelist_queryset_to_translated_dict(FieldChoice.objects.filter(field__iexact='MorphologyType'),
                                                                                       self.request.LANGUAGE_CODE)

        #Collect all morphology definitions for th sequential morphology section, and make some translations in advance
        morphdef_roles = FieldChoice.objects.filter(field__iexact='MorphologyType')
        morphdefs = []

        for morphdef in context['gloss'].parent_glosses.all():

            translated_role = machine_value_to_translated_human_value(morphdef.role,morphdef_roles,self.request.LANGUAGE_CODE)
            morphdefs.append((morphdef,translated_role))

        context['morphdefs'] = morphdefs

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
            # print("path: ", other_media.path)
            other_media_filename = other_media.path.split('/')[1]
            # print("path: ", other_media_filename)
            if other_media_filename.split('.')[-1] == 'mp4':
                file_type = 'video/mp4'
            elif other_media_filename.split('.')[-1] == 'png':
                file_type = 'image/png'
            else:
                file_type = ''

            context['other_media'].append([other_media.pk, path, file_type, human_value_media_type, other_media.alternative_gloss])

            #Save the other_media_type choices (same for every other_media, but necessary because they all have other ids)
            context['choice_lists']['other-media-type_'+str(other_media.pk)] = choicelist_queryset_to_translated_dict(other_media_type_choice_list,self.request.LANGUAGE_CODE)

        #context['choice_lists'] = gl.get_choice_lists()
        context['choice_lists'] = json.dumps(context['choice_lists'])

        context['separate_english_idgloss_field'] = SEPARATE_ENGLISH_IDGLOSS_FIELD

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
            if not request.user.has_perm('dictionary.search_gloss'):
                if self.object.inWeb:
                    return HttpResponseRedirect(reverse('dictionary:public_gloss',kwargs={'idgloss':self.object.idgloss}))
                else:
                    return HttpResponse('')
        else:
            if self.object.inWeb:
                return HttpResponseRedirect(reverse('dictionary:public_gloss', kwargs={'idgloss': self.object.idgloss}))
            else:
                return HttpResponseRedirect(reverse('registration:auth_login'))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
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
                                                                   self.request.LANGUAGE_CODE,ordered=False,id_prefix=''))

        context['morphemeform'] = GlossMorphemeForm()
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
                machine_value = getattr(gl,field);
                human_value = machine_value_to_translated_human_value(machine_value,choice_list,self.request.LANGUAGE_CODE)

                #And add the kind of field
                if field in ['useInstr','phonOth','mouthG','mouthing','phonetVar','iconImg','locVirtObj']:
                    kind = 'text'
                elif field in ['repeat','altern','oriChAbd','oriChFlex']:
                    kind = 'check'
                else:
                    kind = 'list'

                context[topic+'_fields'].append([human_value,field,labels[field],kind])

        #Add morphology to choice lists
        context['choice_lists']['morphology_role'] = choicelist_queryset_to_translated_dict(FieldChoice.objects.filter(field__iexact='MorphologyType'),
                                                                                       self.request.LANGUAGE_CODE)

        #Collect all morphology definitions for th sequential morphology section, and make some translations in advance
        morphdef_roles = FieldChoice.objects.filter(field__iexact='MorphologyType')
        morphdefs = []

        for morphdef in context['gloss'].parent_glosses.all():

            translated_role = machine_value_to_translated_human_value(morphdef.role,morphdef_roles,self.request.LANGUAGE_CODE)
            morphdefs.append((morphdef,translated_role))

        context['morphdefs'] = morphdefs

        context['separate_english_idgloss_field'] = SEPARATE_ENGLISH_IDGLOSS_FIELD

        return context


class MorphemeListView(ListView):
    """The morpheme list view basically copies the gloss list view"""

    model = Morpheme
    template_name = 'dictionary/admin_morpheme_list.html'
    paginate_by = 500


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(MorphemeListView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books

        search_form = MorphemeSearchForm(self.request.GET)

        context['searchform'] = search_form
        context['glosscount'] = Morpheme.objects.all().count()
        context['add_morpheme_form'] = MorphemeCreateForm()
        context['ADMIN_RESULT_FIELDS'] = settings.ADMIN_RESULT_FIELDS

        # make sure that the morpheme-type options are available to the listview
        oChoiceLists = {}
        choice_list = FieldChoice.objects.filter(field__iexact = fieldname_to_category('mrpType'))
        if (len(choice_list) > 0):
            ordered_dict = choicelist_queryset_to_translated_dict(choice_list, self.request.LANGUAGE_CODE)
            oChoiceLists['mrpType'] = ordered_dict

        # Make all choice lists available in the context (currently only mrpType)
        context['choice_lists'] = json.dumps(oChoiceLists)

        context['input_names_fields_and_labels'] = {}

        for topic in ['phonology', 'semantics']:

            context['input_names_fields_and_labels'][topic] = []

            for fieldname in settings.FIELDS[topic]:
                field = search_form[fieldname]
                label = field.label

                context['input_names_fields_and_labels'][topic].append((fieldname, field, label))

        context['paginate_by'] = self.request.GET.get('paginate_by', self.paginate_by)
        
        return context


    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)


    def get_queryset(self):

        # get query terms from self.request
        get = self.request.GET

        if len(get) > 0:
            qs = Morpheme.objects.all()

        #Don't show anything when we're not searching yet
        else:
            qs = Morpheme.objects.none()

        if 'search' in get and get['search'] != '':
            val = get['search']
            query = Q(idgloss__iregex=val) | \
                    Q(annotation_idgloss__iregex=val)

            if re.match('^\d+$', val):
                query = query | Q(sn__exact=val)

            qs = qs.filter(query)
            # print "A: ", len(qs)

        if 'englishGloss' in get and get['englishGloss'] != '':
            val = get['englishGloss']
            qs = qs.filter(annotation_idgloss_en__iregex=val)

        if 'keyword' in get and get['keyword'] != '':
            val = get['keyword']
            qs = qs.filter(translation__translation__text__iregex=val)

        if 'inWeb' in get and get['inWeb'] != '0':
            # Don't apply 'inWeb' filter, if it is unspecified ('0' according to the NULLBOOLEANCHOICES)
            val = get['inWeb'] == 'yes'
            qs = qs.filter(inWeb__exact=val)
            # print "B :", len(qs)

        if 'hasvideo' in get and get['hasvideo'] != 'unspecified':
            val = get['hasvideo'] == 'no'

            qs = qs.filter(glossvideo__isnull=val)

        if 'defspublished' in get and get['defspublished'] != 'unspecified':
            val = get['defspublished'] == 'yes'

            qs = qs.filter(definition__published=val)

        fieldnames = ['idgloss', 'annotation_idgloss', 'annotation_idgloss_en', 'useInstr', 'sense', 'morph', 'StemSN',
                      'compound', 'rmrks', 'handedness',
                      'domhndsh', 'subhndsh', 'locprim', 'locVirtObj', 'relatArtic', 'relOriMov', 'relOriLoc', 'oriCh',
                      'handCh', 'repeat', 'altern',
                      'movSh', 'movDir', 'contType', 'phonOth', 'mouthG', 'mouthing', 'phonetVar', 'iconImg', 'iconType',
                      'namEnt', 'semField', 'valence',
                      'lexCatNotes', 'tokNo', 'tokNoSgnr', 'tokNoA', 'tokNoV', 'tokNoR', 'tokNoGe', 'tokNoGr', 'tokNoO',
                      'tokNoSgnrA',
                      'tokNoSgnrV', 'tokNoSgnrR', 'tokNoSgnrGe', 'tokNoSgnrGr', 'tokNoSgnrO', 'inWeb', 'isNew'];

        # SignLanguage and basic property filters
        vals = get.getlist('dialect', [])
        if vals != []:
            qs = qs.filter(dialect__in=vals)

        vals = get.getlist('signlanguage', [])
        if vals != []:
            qs = qs.filter(signlanguage__in=vals)

        if 'useInstr' in get and get['useInstr'] != '':
            qs = qs.filter(useInstr__icontains=get['useInstr'])

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

            # print "J :", len(qs)

        qs = qs.distinct()

        if 'nottags' in get and get['nottags'] != '':
            vals = get.getlist('nottags')

            # print "NOT TAGS: ", vals

            tags = []
            for t in vals:
                tags.extend(Tag.objects.filter(name=t))

            # search is an implicit AND so intersection
            tqs = TaggedItem.objects.get_intersection_by_model(Gloss, tags)

            # print "NOT", tags, len(tqs)
            # exclude all of tqs from qs
            qs = [q for q in qs if q not in tqs]

            # print "K :", len(qs)

        if 'relationToForeignSign' in get and get['relationToForeignSign'] != '':
            relations = RelationToForeignSign.objects.filter(other_lang_gloss__icontains=get['relationToForeignSign'])
            potential_pks = [relation.gloss.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if 'hasRelationToForeignSign' in get and get['hasRelationToForeignSign'] != '0':

            pks_for_glosses_with_relations = [relation.gloss.pk for relation in RelationToForeignSign.objects.all()]
            # print('pks_for_glosses', pks_for_glosses_with_relations)

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

        if 'hasMorphemeOfType' in get and get['hasMorphemeOfType'] != '':

            # Get all Morphemes of the indicated mrpType
            target_morphemes = Morpheme.objects.filter(mrpType__exact=get['hasMorphemeOfType'])
            # Turn this into a list with pks
            pks_for_glosses_with_correct_mrpType = [glossdef.pk for glossdef in target_morphemes]
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_mrpType)

#        if 'hasMorphemeOfType' in get and get['hasMorphemeOfType'] != '':
#            morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__exact=get['hasMorphemeOfType']);
#            pks_for_glosses_with_morphdefs_with_correct_role = [morphdef.parent_gloss.pk for morphdef in
#                                                                morphdefs_with_correct_role];
#            qs = qs.filter(pk__in=pks_for_glosses_with_morphdefs_with_correct_role)

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
                .filter(created_by__icontains=created_by_search_string)

        # Saving querysets results to sessions, these results can then be used elsewhere (like in gloss_detail)
        # Flush the previous queryset (just in case)
        self.request.session['search_results'] = None

        # Make sure that the QuerySet has filters applied (user is searching for something instead of showing all results [objects.all()])
        if hasattr(qs.query.where, 'children') and len(qs.query.where.children) > 0:

            items = []

            for item in qs:
                items.append(dict(id=item.id, gloss=item.idgloss))

            self.request.session['search_results'] = items

        # print "Final :", len(qs)
        # Sort the queryset by the parameters given
        qs = order_queryset_by_sort_order(self.request.GET, qs)

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

        fieldnames = ['idgloss', 'annotation_idgloss', 'annotation_idgloss_en',
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

        writer = csv.writer(response)

        with override(LANGUAGE_CODE):
            header = ['Signbank ID'] + [f.verbose_name.title().encode('ascii', 'ignore').decode() for f in fields]

        for extra_column in ['SignLanguages', 'Dialects', 'Keywords', 'Morphology', 'Relations to other signs',
                             'Relations to foreign signs', 'Appears in signs', ]:
            header.append(extra_column);

        writer.writerow(header)

        for gloss in self.get_queryset():
            row = [str(gloss.pk)]
            for f in fields:

                # Try the value of the choicelist
                try:
                    row.append(getattr(gloss, 'get_' + f.name + '_display')())

                # If it's not there, try the raw value
                except AttributeError:
                    value = getattr(gloss, f.name)


                    # This was disabled with the move to Python 3... might not be needed anymore?
                    # if isinstance(value, unicode):
                    #     value = str(value.encode('ascii', 'xmlcharrefreplace'));
                    # elif not isinstance(value, str):

                    value = str(value);

                    row.append(value)

            # get languages
            signlanguages = [signlanguage.name for signlanguage in gloss.language.all()]
            row.append(", ".join(signlanguages));

            # get dialects
            dialects = [dialect.name for dialect in gloss.dialect.all()]
            row.append(", ".join(dialects));

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
            appearsin = [appears.idgloss for appears in Gloss.objects.filter(morphemePart=gloss)]
            row.append(", ".join(appearsin))

            # Make it safe for weird chars
            safe_row = [];
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

    class Meta:
        verbose_name_plural = "Handshapes"
        ordering = ['machine_value']

    #Overriding the get method get permissions right
    def get(self, request, *args, **kwargs):

        # print("args: ", kwargs['pk'])
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
                # print('o machine_value: ', o.machine_value)
                if o.machine_value == match_machine_value: # only one match
                    new_id = o.machine_value
                    new_machine_value = o.machine_value
                    new_english_name = o.english_name
                    new_dutch_name = o.dutch_name
                    new_chinese_name = o.chinese_name

                    new_handshape = Handshape(machine_value=new_machine_value, english_name=new_english_name,
                                              dutch_name=new_dutch_name, chinese_name=new_chinese_name)
                    new_handshape.save()
                    # print("New handshape: ", new_id)
                    handshape_not_created = 0
                    self.object = new_handshape
                    break;

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

        labels = hs.field_labels()
        # print('labels: ', labels)
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
            # print('fieldchoice_category', fieldchoice_category)

            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category).order_by('machine_value')

            if len(choice_list) > 0:
                context['choice_lists'][field] = choicelist_queryset_to_translated_dict (choice_list,self.request.LANGUAGE_CODE)

            # print('choice list: ', choice_list)
            #Take the human value in the language we are using
            machine_value = getattr(hs, field)
            human_value = machine_value_to_translated_human_value(machine_value,choice_list,self.request.LANGUAGE_CODE)
            # print("Human value: " + str(human_value))

            #And add the kind of field
            if field in ['fsT', 'fsI', 'fsM', 'fsR', 'fsP',
                         'fs2T', 'fs2I', 'fs2M', 'fs2R', 'fs2P',
                         'ufT', 'ufI', 'ufM', 'ufR', 'ufP']:
                kind = 'check'
            else:
                kind = 'list'

            # print('handshape field', field)
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
        # temp = context['handshape_fields']
        # print('handshape fields: ', temp)
        # temp2 = context['choice_lists']
        # print('choice lists: ', temp2)

        return context


class HandshapeListView(ListView):

    model = Handshape
    template_name = 'dictionary/admin_handshape_list.html'
    paginate_by = 50
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

        context['searchform'] = search_form
        context['search_type'] = self.search_type
        # if self.search_type == 'sign_handshape':
        #     context['glosscount'] = Gloss.none_morpheme_objects().count()   # Only count the none-morpheme glosses
        # else:
        #     context['glosscount'] = Gloss.objects.count()  # Count the glosses + morphemes

        context['handshapefieldchoicecount'] = FieldChoice.objects.filter(field__iexact='Handshape').count()
        context['signscount'] = Gloss.objects.all().count()
        context['HANDSHAPE_RESULT_FIELDS'] = settings.HANDSHAPE_RESULT_FIELDS

        context['handshape_fields_FS1'] = []


        context['choice_lists'] = {}

        for field in FIELDS['handshape']:

            # Get and save the choice list for this field
            fieldchoice_category = fieldname_to_category(field)
            # print('fieldchoice_category', fieldchoice_category)

            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category).order_by('machine_value')

            if len(choice_list) > 0:
                context['choice_lists'][field] = choicelist_queryset_to_translated_dict(choice_list,
                                                                                        self.request.LANGUAGE_CODE, id_prefix='')

        context['choice_lists'] = json.dumps(context['choice_lists'])
        # print('choice lists: ', context['choice_lists'])

        if 'paginate_by' in self.request.GET:
            self.paginate_by = self.request.GET.get('paginate_by', self.paginate_by)
        else:
            self.paginage_by = 50

        context['paginate_by'] = self.paginate_by

        context['handshapescount'] = Handshape.objects.count()

        return context

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """

        return self.request.GET.get('paginate_by', self.paginate_by)

    def get_queryset(self):

        choice_lists = {}

        for field in FIELDS['handshape']:

            # Get and save the choice list for this field
            fieldchoice_category = fieldname_to_category(field)
            # print('fieldchoice_category', fieldchoice_category)

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
                    # print("get_queryset: fieldname: ", fieldname, ", val: ", val, ", fieldlabel: ", fieldlabel)
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
                    # print('get_query: val: ', val)
                    val = {'0': False, '1': True, 'True': True, 'False': False, 'None': '', '': '' }[val]


                if self.request.LANGUAGE_CODE == 'nl' and fieldname == 'dutch_name' and val != '':
                    # print("query dutch")
                    query = Q(dutch_name__icontains=val)
                    qs = qs.filter(query)

                if self.request.LANGUAGE_CODE == 'cn' and fieldname == 'chinese_name' and val != '':
                    # print("query chinese")
                    query = Q(chinese_name__icontains=val)
                    qs = qs.filter(query)

                if fieldname == 'english_name' and val != '':
                    # print("query english")
                    query = Q(english_name__icontains=val)
                    qs = qs.filter(query)


                if val != '' and fieldname != 'hsNumSel' and fieldname != 'dutch_name' and fieldname != 'chinese_name' and fieldname != 'english_name':
                    kwargs = {key: val}
                    qs = qs.filter(**kwargs)

        # Saving querysets results to sessions, these results can then be used elsewhere (like in gloss_detail)
        # Flush the previous queryset (just in case)
        # self.request.session['search_results'] = None
        # Handshape searching of signs relies on using the search_results in order to search signs that have the handshapes
        # The search_results is no longer set to None

        # Make sure that the QuerySet has filters applied (user is searching for something instead of showing all results [objects.all()])

        # print(qs.query)

        if hasattr(qs.query.where, 'children') and len(qs.query.where.children) > 0:

            items = []

            for item in qs:
                if self.request.LANGUAGE_CODE == 'nl':
                    items.append(dict(id = item.machine_value, handshape = item.dutch_name))
                elif self.request.LANGUAGE_CODE == 'cn':
                    items.append(dict(id = item.machine_value, handshape = item.chinese_name))
                else:
                    items.append(dict(id = item.machine_value, handshape = item.english_name))

            self.request.session['search_results'] = items

        qs = order_handshape_queryset_by_sort_order(self.request.GET, qs)

        if self.search_type == 'sign_handshape':

            # search for signs with found hadnshapes
            # find relevant machine values for handshapes
            selected_handshapes = [ h.machine_value for h in qs ]
            # print("selected handshapes: ", selected_handshapes)

            # print("qeury: ", qs.query)
            if len(selected_handshapes) == (Handshape.objects.all().count()):
                # print("searching for all handshapes")

                qs = Gloss.objects.filter(Q(domhndsh__in=selected_handshapes) | Q(domhndsh__isnull=True) | Q(domhndsh__exact='0')
                                          | Q(subhndsh__in=selected_handshapes) | Q(subhndsh__isnull=True) | Q(subhndsh__exact='0'))

            else:
                qs = Gloss.objects.filter(Q(domhndsh__in=selected_handshapes) | Q(subhndsh__in=selected_handshapes))

        return qs

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


class MorphemeDetailView(DetailView):
    model = Morpheme
    context_object_name = 'morpheme'

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
        context['glosslinks'] = Gloss.objects.filter(morphemePart__id=context['morpheme'].id)
        # context['glosslinks'] = self.gloss_set.all()

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
        gl = context['morpheme'];
        labels = gl.field_labels();

        context['choice_lists'] = {}

        # Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['phonology', 'semantics', 'frequency']:
            context[topic + '_fields'] = [];

            for field in FIELDS[topic]:

                # Get and save the choice list for this field
                field_category = fieldname_to_category(field)
                choice_list = FieldChoice.objects.filter(field__iexact=field_category)

                if len(choice_list) > 0:
                    context['choice_lists'][field] = choicelist_queryset_to_translated_dict(choice_list,
                                                                                                    self.request.LANGUAGE_CODE)

                # Take the human value in the language we are using
                machine_value = getattr(gl, field);
                human_value = machine_value_to_translated_human_value(machine_value,choice_list,self.request.LANGUAGE_CODE)

                # And add the kind of field
                if field in ['phonOth', 'mouthG', 'mouthing', 'phonetVar', 'iconImg', 'locVirtObj']:
                    kind = 'text'
                elif field in ['repeat', 'altern']:
                    kind = 'check'
                else:
                    kind = 'list'

                context[topic + '_fields'].append([human_value, field, labels[field], kind]);

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

        # context['choice_lists'] = gl.get_choice_lists()
        context['choice_lists'] = json.dumps(context['choice_lists'])

        context['separate_english_idgloss_field'] = SEPARATE_ENGLISH_IDGLOSS_FIELD

        return context

def gloss_ajax_search_results(request):
    """Returns a JSON list of glosses that match the previous search stored in sessions"""

    return HttpResponse(json.dumps(request.session['search_results']))

def gloss_ajax_complete(request, prefix):
    """Return a list of glosses matching the search term
    as a JSON structure suitable for typeahead."""


    query = Q(idgloss__istartswith=prefix) | \
            Q(annotation_idgloss__istartswith=prefix) | \
            Q(sn__startswith=prefix)
    # TODO: possibly reduce the possibilities of [Gloss.objects] to exclude Morphemes??
    # Suggestion: qs = Gloss.none_morpheme_objects.filter(query) -- if that works
    qs = Gloss.objects.filter(query)

    result = []
    for g in qs:
        result.append({'idgloss': g.idgloss, 'annotation_idgloss': g.annotation_idgloss, 'sn': g.sn, 'pk': "%s" % (g.idgloss)})

    return HttpResponse(json.dumps(result), {'content-type': 'application/json'})

def handshape_ajax_complete(request, prefix):
    """Return a list of handshapes matching the search term
    as a JSON structure suitable for typeahead."""

    if request.LANGUAGE_CODE == 'nl':
        query = Q(dutch_name__istartswith=prefix)
    elif request.LANGUAGE_CODE == 'cn':
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

    query = Q(idgloss__istartswith=prefix) | \
            Q(annotation_idgloss__istartswith=prefix) | \
            Q(sn__startswith=prefix)
    qs = Morpheme.objects.filter(query)

    result = []
    for g in qs:
        result.append({'idgloss': g.idgloss, 'annotation_idgloss': g.annotation_idgloss, 'sn': g.sn,
                       'pk': "%s" % (g.idgloss)})

    return HttpResponse(json.dumps(result), {'content-type': 'application/json'})
