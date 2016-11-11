from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.db.models import Q
from django.db.models.fields import NullBooleanField
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.utils.translation import override

from collections import OrderedDict
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
from signbank.settings.base import ECV_FILE,EARLIEST_GLOSS_CREATION_DATE, OTHER_MEDIA_DIRECTORY, FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD, LANGUAGE_CODE, ECV_SETTINGS


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
    if (get.has_key('sortOrder') and get['sortOrder'] != ''):
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
        ordered = qs.order_by(sOrder)

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

        context['searchform'] = search_form
        context['search_type'] = self.search_type
        if self.search_type == 'sign':
            context['glosscount'] = Gloss.none_morpheme_objects().count()   # Only count the none-morpheme glosses
        else:
            context['glosscount'] = Gloss.objects.count()  # Count the glosses + morphemes

        context['add_gloss_form'] = GlossCreateForm()
        context['ADMIN_RESULT_FIELDS'] = settings.ADMIN_RESULT_FIELDS

        context['input_names_fields_and_labels'] = {}

        for topic in ['main','phonology','semantics']:

            context['input_names_fields_and_labels'][topic] = []

            for fieldname in settings.FIELDS[topic]:
                field = search_form[fieldname]
                label = field.label

                context['input_names_fields_and_labels'][topic].append((fieldname,field,label))

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
        for gloss in Gloss.none_morpheme_objects():
            glossid = str(gloss.pk)
            myattributes = {cve_id: glossid}
            cve_entry_element = ET.SubElement(cv_element, cv_entry_ml, myattributes)

            desc = self.get_ecv_descripion_for_gloss(gloss, ECV_SETTINGS['include_phonology_and_frequencies'])

            for lang in ECV_SETTINGS['languages']:
                cve_value_element = ET.SubElement(cve_entry_element, cve_value, {description:desc, lang_ref:lang['id']})
                cve_value_element.text = self.get_value_for_ecv(gloss, lang['annotation_idgloss_fieldname'])

        xmlstr = minidom.parseString(ET.tostring(top,'utf-8')).toprettyxml(indent="   ")
        with open(ECV_FILE, "w") as f:
            f.write(xmlstr.encode('utf-8'))

#        tree = ET.ElementTree(top)
#        tree.write(open(ECV_FILE, 'w'), encoding ="utf-8",xml_declaration=True, method="xml")

        return HttpResponse('OK')

    def get_ecv_descripion_for_gloss(self, gloss, include_phonology_and_frequencies=False):
        desc = ""
        if include_phonology_and_frequencies:
            description_fields = ['handedness','domhndsh', 'subhndsh', 'handCh', 'locprim', 'relOriMov', 'movDir','movSh', 'tokNo',
                          'tokNoSgnr'];

            for f in description_fields:
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

        if isinstance(value,unicode):
            value = str(value.encode('ascii','xmlcharrefreplace'))
        elif value is None:
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
        fields = [Gloss._meta.get_field(fieldname) for fieldname in fieldnames]

        writer = csv.writer(response)

        with override(LANGUAGE_CODE):
            header = ['Signbank ID'] + [f.verbose_name.title().encode('ascii','ignore') for f in fields]

        for extra_column in ['Languages','Dialects','Keywords','Morphology','Relations to other signs','Relations to foreign signs',]:
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

                    if isinstance(value,unicode):
                        value = str(value.encode('ascii','xmlcharrefreplace'));
                    elif not isinstance(value,str):
                        value = str(value);

                    row.append(value)

            # get languages
            languages = [language.name for language in gloss.language.all()]
            row.append(", ".join(languages));

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
                    safe_row.append(column.encode('utf-8'))
                except AttributeError:
                    safe_row.append(None);

            writer.writerow(safe_row)
    
        return response


    def get_queryset(self):

        get = self.request.GET

        if 'search_type' in get:
            self.search_type = get['search_type']
        else:
            self.search_type = 'sign'

        setattr(self.request, 'search_type', self.search_type)


        if self.search_type == 'sign':
            # Get all the GLOSS items that are not member of the sub-class Morpheme
            qs = Gloss.none_morpheme_objects()
        else:
            qs = Gloss.objects.all()

        #print "QS:", len(qs)
        

        if get.has_key('search') and get['search'] != '':
            val = get['search']
            query = Q(idgloss__istartswith=val) | \
                    Q(annotation_idgloss__istartswith=val)

            if re.match('^\d+$', val):
                query = query | Q(sn__exact=val)
                    
            qs = qs.filter(query)
            #print "A: ", len(qs)

        if get.has_key('englishGloss') and get['englishGloss'] != '':
            val = get['englishGloss']
            qs = qs.filter(annotation_idgloss_en__istartswith=val)

        if get.has_key('keyword') and get['keyword'] != '':
            val = get['keyword']
            qs = qs.filter(translation__translation__text__istartswith=val)
            
          
        if get.has_key('inWeb') and get['inWeb'] != '0':
            # Don't apply 'inWeb' filter, if it is unspecified ('0' according to the NULLBOOLEANCHOICES)
            val = get['inWeb'] == 'yes'
            qs = qs.filter(inWeb__exact=val)
            #print "B :", len(qs)
            
            
        if get.has_key('hasvideo') and get['hasvideo'] != 'unspecified':
            val = get['hasvideo'] == 'no'

            qs = qs.filter(glossvideo__isnull=val)

        if get.has_key('defspublished') and get['defspublished'] != 'unspecified':
            val = get['defspublished'] == 'yes'

            qs = qs.filter(definition__published=val)


        fieldnames = ['idgloss', 'annotation_idgloss', 'annotation_idgloss_en', 'useInstr', 'sense', 'morph', 'StemSN', 'compound', 'rmrks', 'handedness',
                      'domhndsh', 'subhndsh', 'locprim', 'locVirtObj', 'relatArtic',  'relOriMov', 'relOriLoc', 'oriCh', 'handCh', 'repeat', 'altern',
                      'movSh', 'movDir', 'contType', 'phonOth', 'mouthG', 'mouthing', 'phonetVar',
                      'domSF', 'domFlex', 'oriChAbd', 'oriChFlex', 'iconImg', 'iconType', 'namEnt', 'semField', 'valence',
                      'lexCatNotes','tokNo', 'tokNoSgnr','tokNoA', 'tokNoV', 'tokNoR', 'tokNoGe', 'tokNoGr', 'tokNoO', 'tokNoSgnrA',
                      'tokNoSgnrV', 'tokNoSgnrR', 'tokNoSgnrGe', 'tokNoSgnrGr', 'tokNoSgnrO', 'inWeb', 'isNew'];

        #Language and basic property filters
        vals = get.getlist('dialect', [])
        if vals != []:
            qs = qs.filter(dialect__in=vals)

        vals = get.getlist('language', [])
        if vals != []:
            qs = qs.filter(language__in=vals)

        if get.has_key('useInstr') and get['useInstr'] != '':
            qs = qs.filter(useInstr__icontains=get['useInstr'])


        ## phonology and semantics field filters
        for fieldname in fieldnames:

            if get.has_key(fieldname):
                key = fieldname+'__exact';
                val = get[fieldname];

                if isinstance(Gloss._meta.get_field(fieldname),NullBooleanField):
                    val = {'0':'','1': None, '2': True, '3': False}[val];

                if val != '':
                    kwargs = {key:val};
                    qs = qs.filter(**kwargs);
        
        
        if get.has_key('initial_relative_orientation') and get['initial_relative_orientation'] != '':
            val = get['initial_relative_orientation']
            qs = qs.filter(initial_relative_orientation__exact=val)               

        if get.has_key('final_relative_orientation') and get['final_relative_orientation'] != '':
            val = get['final_relative_orientation']
            qs = qs.filter(final_relative_orientation__exact=val)   

        if get.has_key('initial_palm_orientation') and get['initial_palm_orientation'] != '':
            val = get['initial_palm_orientation']
            qs = qs.filter(initial_palm_orientation__exact=val)               

        if get.has_key('final_palm_orientation') and get['final_palm_orientation'] != '':
            val = get['final_palm_orientation']
            qs = qs.filter(final_palm_orientation__exact=val)  

        if get.has_key('initial_secondary_loc') and get['initial_secondary_loc'] != '':
            val = get['initial_secondary_loc']
            qs = qs.filter(initial_secondary_loc__exact=val)  

        if get.has_key('final_secondary_loc') and get['final_secondary_loc'] != '':
            val = get['final_secondary_loc']
            qs = qs.filter(final_secondary_loc__exact=val) 
            
        if get.has_key('final_secondary_loc') and get['final_secondary_loc'] != '':
            val = get['final_secondary_loc']
            qs = qs.filter(final_secondary_loc__exact=val)
        
        if get.has_key('defsearch') and get['defsearch'] != '':
            
            val = get['defsearch']
            
            if get.has_key('defrole'):
                role = get['defrole']
            else:
                role = 'all'
            
            if role == 'all':
                qs = qs.filter(definition__text__icontains=val)
            else:
                qs = qs.filter(definition__text__icontains=val, definition__role__exact=role)

        if get.has_key('tags') and get['tags'] != '':
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
        
        if get.has_key('nottags') and get['nottags'] != '':
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

        if get.has_key('relationToForeignSign') and get['relationToForeignSign'] != '':

            relations = RelationToForeignSign.objects.filter(other_lang_gloss__icontains=get['relationToForeignSign'])
            potential_pks = [relation.gloss.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if get.has_key('hasRelationToForeignSign') and get['hasRelationToForeignSign'] != '0':

            pks_for_glosses_with_relations = [relation.gloss.pk for relation in RelationToForeignSign.objects.all()];
            print('pks_for_glosses',pks_for_glosses_with_relations)

            if get['hasRelationToForeignSign'] == '1': #We only want glosses with a relation to a foreign sign
                qs = qs.filter(pk__in=pks_for_glosses_with_relations)
            elif get['hasRelationToForeignSign'] == '2': #We only want glosses without a relation to a foreign sign
                qs = qs.exclude(pk__in=pks_for_glosses_with_relations)

        if get.has_key('relation') and get['relation'] != '':

            potential_targets = Gloss.objects.filter(idgloss__icontains=get['relation'])
            relations = Relation.objects.filter(target__in=potential_targets)
            potential_pks = [relation.source.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if get.has_key('hasRelation') and get['hasRelation'] != '':

            #Find all relations with this role
            if get['hasRelation'] == 'all':
                relations_with_this_role = Relation.objects.all();
            else:
                relations_with_this_role = Relation.objects.filter(role__exact=get['hasRelation']);

            #Remember the pk of all glosses that take part in the collected relations
            pks_for_glosses_with_correct_relation = [relation.source.pk for relation in relations_with_this_role];
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_relation)

        if get.has_key('id_morpheme') and get['id_morpheme'] != '':

            # Filter all glosses that contain a morpheme with the indicated text in its gloss
            # Step 1: get all morphemes containing the indicated text
            potential_morphemes = Morpheme.objects.filter(idgloss__exact=get['id_morpheme']);
            if (potential_morphemes.count() > 0):
                # At least one has been found: take the first one
                selected_morpheme = potential_morphemes[0];
                # Step 2: get all Glosses containing the above morphemes
                potential_pks = [appears.pk for appears in Gloss.objects.filter(morphemePart=selected_morpheme)];
                qs = qs.filter(pk__in=potential_pks)

        if get.has_key('hasComponentOfType') and get['hasComponentOfType'] != '':

            # Look for "compound-components" of the indicated type. Compound Components are defined in class[MorphologyDefinition]
            morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__exact=get['hasComponentOfType']);
            pks_for_glosses_with_morphdefs_with_correct_role = [morphdef.parent_gloss.pk for morphdef in morphdefs_with_correct_role];
            qs = qs.filter(pk__in=pks_for_glosses_with_morphdefs_with_correct_role)

        if get.has_key('hasMorphemeOfType') and get['hasMorphemeOfType'] != '':

            # Get all Morphemes of the indicated mrpType
            target_morphemes = Morpheme.objects.filter(mrpType__exact=get['hasMorphemeOfType'])
            # Get all glosses that have one of the morphemes in this set
            glosses_with_correct_mrpType = Gloss.objects.filter(morphemePart__in=target_morphemes)
            # Turn this into a list with pks
            pks_for_glosses_with_correct_mrpType = [glossdef.pk for glossdef in glosses_with_correct_mrpType];
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_mrpType)

        if get.has_key('definitionRole') and get['definitionRole'] != '':

            #Find all definitions with this role
            if get['definitionRole'] == 'all':
                definitions_with_this_role = Definition.objects.all();
            else:
                definitions_with_this_role = Definition.objects.filter(role__exact=get['definitionRole']);

            #Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role];
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if get.has_key('definitionContains') and get['definitionContains'] != '':

            definitions_with_this_text = Definition.objects.filter(text__icontains=get['definitionContains']);

            #Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_text];
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if get.has_key('createdBefore') and get['createdBefore'] != '':

            created_before_date = DT.datetime.strptime(get['createdBefore'], "%m/%d/%Y").date()
            qs = qs.filter(creationDate__range=(EARLIEST_GLOSS_CREATION_DATE,created_before_date))

        if get.has_key('createdAfter') and get['createdAfter'] != '':

            created_after_date = DT.datetime.strptime(get['createdAfter'], "%m/%d/%Y").date()
            qs = qs.filter(creationDate__range=(created_after_date,DT.datetime.now()))

        # Saving querysets results to sessions, these results can then be used elsewhere (like in gloss_detail)
        # Flush the previous queryset (just in case)
        self.request.session['search_results'] = None

        # Make sure that the QuerySet has filters applied (user is searching for something instead of showing all results [objects.all()])
        if hasattr(qs.query.where, 'children') and len(qs.query.where.children) > 0:

            items = []

            for item in qs:
                items.append(dict(id = item.id, gloss = item.idgloss))

            self.request.session['search_results'] = items

        # print "Final :", len(qs)
        # Sort the queryset by the parameters given
        qs = order_queryset_by_sort_order(self.request.GET, qs)

        # Return the resulting filtered and sorted queryset
        return qs


class GlossDetailView(DetailView):
    
    model = Gloss
    context_object_name = 'gloss'

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
        context['morphemeform'] = GlossMorphemeForm()
        context['othermediaform'] = OtherMediaForm()
        context['navigation'] = context['gloss'].navigation(True)
        context['interpform'] = InterpreterFeedbackForm()
        context['SIGN_NAVIGATION']  = settings.SIGN_NAVIGATION

        next_gloss = Gloss.objects.get(pk=context['gloss'].pk).admin_next_gloss()
        if next_gloss == None:
            context['nextglossid'] = context['gloss'].pk #context['gloss']
        else:
            context['nextglossid'] = next_gloss.pk

        if settings.SIGN_NAVIGATION:
            context['glosscount'] = Gloss.objects.count()
            context['glossposn'] =  Gloss.objects.filter(sn__lt=context['gloss'].sn).count()+1

        #Pass info about which fields we want to see
        gl = context['gloss'];
        labels = gl.field_labels();

        context['choice_lists'] = {}

        #Translate the machine values to human values in the correct language, and save the choice lists along the way
        for topic in ['main','phonology','semantics','frequency']:
            context[topic+'_fields'] = [];

            for field in FIELDS[topic]:

                #Get and save the choice list for this field
                field_category = fieldname_to_category(field)
                choice_list = FieldChoice.objects.filter(field__iexact=field_category)

                if len(choice_list) > 0:
                    context['choice_lists'][field] = choicelist_queryset_to_translated_ordered_dict (choice_list,self.request.LANGUAGE_CODE)

                #Take the human value in the language we are using
                machine_value = getattr(gl,field);

                if machine_value == '0':
                    human_value = '-'
                elif machine_value == '1':
                    human_value = 'N/A'
                else:

                    try:
                        selected_field_choice = choice_list.filter(machine_value=machine_value)[0]

                        if self.request.LANGUAGE_CODE == 'nl':
                            human_value = selected_field_choice.dutch_name
                        else:
                            human_value = selected_field_choice.english_name

                    except (IndexError, ValueError):
                        human_value = machine_value

                #And add the kind of field
                if field in ['useInstr','phonOth','mouthG','mouthing','phonetVar','iconImg','locVirtObj']:
                    kind = 'text';
                elif field in ['repeat','altern','oriChAbd','oriChFlex']:
                    kind = 'check';
                else:
                    kind = 'list';

                context[topic+'_fields'].append([human_value,field,labels[field],kind]);

        #Gather the OtherMedia
        context['other_media'] = []
        other_media_type_choice_list = FieldChoice.objects.filter(field__iexact='OthermediaType')

        for other_media in gl.othermedia_set.all():

            if int(other_media.type) == 0:
                human_value_media_type = '-'
            elif int(other_media.type) == 1:
                human_value_media_type = 'N/A'
            else:

                selected_field_choice = other_media_type_choice_list.filter(machine_value=other_media.type)[0]

                codes_to_adjectives = dict(settings.LANGUAGES)

                if self.request.LANGUAGE_CODE not in codes_to_adjectives.keys():
                    adjective = 'english'
                else:
                    adjective = codes_to_adjectives[self.request.LANGUAGE_CODE].lower()

                try:
                    human_value_media_type = getattr(selected_field_choice,adjective+'_name')
                except AttributeError:
                    human_value_media_type = getattr(selected_field_choice,'english_name')

            path = settings.STATIC_URL+'othermedia/'+other_media.path
            context['other_media'].append([other_media.pk, path, human_value_media_type, other_media.alternative_gloss])

            #Save the other_media_type choices (same for every other_media, but necessary because they all have other ids)
            context['choice_lists']['other-media-type_'+str(other_media.pk)] = choicelist_queryset_to_translated_ordered_dict(other_media_type_choice_list,self.request.LANGUAGE_CODE)

        #context['choice_lists'] = gl.get_choice_lists()
        context['choice_lists'] = json.dumps(context['choice_lists'])

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
            ordered_dict = choicelist_queryset_to_translated_ordered_dict(choice_list, self.request.LANGUAGE_CODE)
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

        return context


    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class property value.
        """
        return self.request.GET.get('paginate_by', self.paginate_by)


    def get_queryset(self):
        # get query terms from self.request
        qs = Morpheme.objects.all()

        # print "QS:", len(qs)

        get = self.request.GET

        if get.has_key('search') and get['search'] != '':
            val = get['search']
            query = Q(idgloss__istartswith=val) | \
                    Q(annotation_idgloss__istartswith=val)

            if re.match('^\d+$', val):
                query = query | Q(sn__exact=val)

            qs = qs.filter(query)
            # print "A: ", len(qs)

        if get.has_key('englishGloss') and get['englishGloss'] != '':
            val = get['englishGloss']
            qs = qs.filter(annotation_idgloss_en__istartswith=val)

        if get.has_key('keyword') and get['keyword'] != '':
            val = get['keyword']
            qs = qs.filter(translation__translation__text__istartswith=val)

        if get.has_key('inWeb') and get['inWeb'] != '0':
            # Don't apply 'inWeb' filter, if it is unspecified ('0' according to the NULLBOOLEANCHOICES)
            val = get['inWeb'] == 'yes'
            qs = qs.filter(inWeb__exact=val)
            # print "B :", len(qs)

        if get.has_key('hasvideo') and get['hasvideo'] != 'unspecified':
            val = get['hasvideo'] == 'no'

            qs = qs.filter(glossvideo__isnull=val)

        if get.has_key('defspublished') and get['defspublished'] != 'unspecified':
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

        # Language and basic property filters
        vals = get.getlist('dialect', [])
        if vals != []:
            qs = qs.filter(dialect__in=vals)

        vals = get.getlist('language', [])
        if vals != []:
            qs = qs.filter(language__in=vals)

        if get.has_key('useInstr') and get['useInstr'] != '':
            qs = qs.filter(useInstr__icontains=get['useInstr'])

        ## phonology and semantics field filters
        for fieldname in fieldnames:

            if get.has_key(fieldname):
                key = fieldname + '__exact';
                val = get[fieldname];

                if isinstance(Gloss._meta.get_field(fieldname), NullBooleanField):
                    val = {'0': '', '1': None, '2': True, '3': False}[val];

                if val != '':
                    kwargs = {key: val};
                    qs = qs.filter(**kwargs);

        if get.has_key('initial_relative_orientation') and get['initial_relative_orientation'] != '':
            val = get['initial_relative_orientation']
            qs = qs.filter(initial_relative_orientation__exact=val)

        if get.has_key('final_relative_orientation') and get['final_relative_orientation'] != '':
            val = get['final_relative_orientation']
            qs = qs.filter(final_relative_orientation__exact=val)

        if get.has_key('initial_palm_orientation') and get['initial_palm_orientation'] != '':
            val = get['initial_palm_orientation']
            qs = qs.filter(initial_palm_orientation__exact=val)

        if get.has_key('final_palm_orientation') and get['final_palm_orientation'] != '':
            val = get['final_palm_orientation']
            qs = qs.filter(final_palm_orientation__exact=val)

        if get.has_key('initial_secondary_loc') and get['initial_secondary_loc'] != '':
            val = get['initial_secondary_loc']
            qs = qs.filter(initial_secondary_loc__exact=val)

        if get.has_key('final_secondary_loc') and get['final_secondary_loc'] != '':
            val = get['final_secondary_loc']
            qs = qs.filter(final_secondary_loc__exact=val)

        if get.has_key('final_secondary_loc') and get['final_secondary_loc'] != '':
            val = get['final_secondary_loc']
            qs = qs.filter(final_secondary_loc__exact=val)

        if get.has_key('defsearch') and get['defsearch'] != '':

            val = get['defsearch']

            if get.has_key('defrole'):
                role = get['defrole']
            else:
                role = 'all'

            if role == 'all':
                qs = qs.filter(definition__text__icontains=val)
            else:
                qs = qs.filter(definition__text__icontains=val, definition__role__exact=role)

        if get.has_key('tags') and get['tags'] != '':
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

        if get.has_key('nottags') and get['nottags'] != '':
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

        if get.has_key('relationToForeignSign') and get['relationToForeignSign'] != '':
            relations = RelationToForeignSign.objects.filter(other_lang_gloss__icontains=get['relationToForeignSign'])
            potential_pks = [relation.gloss.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if get.has_key('hasRelationToForeignSign') and get['hasRelationToForeignSign'] != '0':

            pks_for_glosses_with_relations = [relation.gloss.pk for relation in RelationToForeignSign.objects.all()];
            print('pks_for_glosses', pks_for_glosses_with_relations)

            if get['hasRelationToForeignSign'] == '1':  # We only want glosses with a relation to a foreign sign
                qs = qs.filter(pk__in=pks_for_glosses_with_relations)
            elif get['hasRelationToForeignSign'] == '2':  # We only want glosses without a relation to a foreign sign
                qs = qs.exclude(pk__in=pks_for_glosses_with_relations)

        if get.has_key('relation') and get['relation'] != '':
            potential_targets = Gloss.objects.filter(idgloss__icontains=get['relation'])
            relations = Relation.objects.filter(target__in=potential_targets)
            potential_pks = [relation.source.pk for relation in relations]
            qs = qs.filter(pk__in=potential_pks)

        if get.has_key('hasRelation') and get['hasRelation'] != '':

            # Find all relations with this role
            if get['hasRelation'] == 'all':
                relations_with_this_role = Relation.objects.all();
            else:
                relations_with_this_role = Relation.objects.filter(role__exact=get['hasRelation']);

            # Remember the pk of all glosses that take part in the collected relations
            pks_for_glosses_with_correct_relation = [relation.source.pk for relation in relations_with_this_role];
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_relation)

        if get.has_key('morpheme') and get['morpheme'] != '':
            potential_morphemes = Gloss.objects.filter(idgloss__icontains=get['morpheme']);
            potential_morphdefs = MorphologyDefinition.objects.filter(
                morpheme__in=[morpheme.pk for morpheme in potential_morphemes])
            potential_pks = [morphdef.parent_gloss.pk for morphdef in potential_morphdefs];
            qs = qs.filter(pk__in=potential_pks)

        if get.has_key('hasMorphemeOfType') and get['hasMorphemeOfType'] != '':

            # Get all Morphemes of the indicated mrpType
            target_morphemes = Morpheme.objects.filter(mrpType__exact=get['hasMorphemeOfType'])
            # Turn this into a list with pks
            pks_for_glosses_with_correct_mrpType = [glossdef.pk for glossdef in target_morphemes];
            qs = qs.filter(pk__in=pks_for_glosses_with_correct_mrpType)

#        if get.has_key('hasMorphemeOfType') and get['hasMorphemeOfType'] != '':
#            morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__exact=get['hasMorphemeOfType']);
#            pks_for_glosses_with_morphdefs_with_correct_role = [morphdef.parent_gloss.pk for morphdef in
#                                                                morphdefs_with_correct_role];
#            qs = qs.filter(pk__in=pks_for_glosses_with_morphdefs_with_correct_role)

        if get.has_key('definitionRole') and get['definitionRole'] != '':

            # Find all definitions with this role
            if get['definitionRole'] == 'all':
                definitions_with_this_role = Definition.objects.all();
            else:
                definitions_with_this_role = Definition.objects.filter(role__exact=get['definitionRole']);

            # Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_role];
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if get.has_key('definitionContains') and get['definitionContains'] != '':
            definitions_with_this_text = Definition.objects.filter(text__icontains=get['definitionContains']);

            # Remember the pk of all glosses that are referenced in the collection definitions
            pks_for_glosses_with_these_definitions = [definition.gloss.pk for definition in definitions_with_this_text];
            qs = qs.filter(pk__in=pks_for_glosses_with_these_definitions)

        if get.has_key('createdBefore') and get['createdBefore'] != '':
            created_before_date = DT.datetime.strptime(get['createdBefore'], "%m/%d/%Y").date()
            qs = qs.filter(creationDate__range=(EARLIEST_GLOSS_CREATION_DATE, created_before_date))

        if get.has_key('createdAfter') and get['createdAfter'] != '':
            created_after_date = DT.datetime.strptime(get['createdAfter'], "%m/%d/%Y").date()
            qs = qs.filter(creationDate__range=(created_after_date, DT.datetime.now()))

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
            header = ['Signbank ID'] + [f.verbose_name.title().encode('ascii', 'ignore') for f in fields]

        for extra_column in ['Languages', 'Dialects', 'Keywords', 'Morphology', 'Relations to other signs',
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

                    if isinstance(value, unicode):
                        value = str(value.encode('ascii', 'xmlcharrefreplace'));
                    elif not isinstance(value, str):
                        value = str(value);

                    row.append(value)

            # get languages
            languages = [language.name for language in gloss.language.all()]
            row.append(", ".join(languages));

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
                    safe_row.append(column.encode('utf-8'))
                except AttributeError:
                    safe_row.append(None);

            writer.writerow(safe_row)

        return response


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
                    context['choice_lists'][field] = choicelist_queryset_to_translated_ordered_dict(choice_list,
                                                                                                    self.request.LANGUAGE_CODE)

                # Take the human value in the language we are using
                machine_value = getattr(gl, field);

                if machine_value == '0':
                    human_value = '-'
                elif machine_value == '1':
                    human_value = 'N/A'
                else:

                    try:
                        selected_field_choice = choice_list.filter(machine_value=machine_value)[0]

                        if self.request.LANGUAGE_CODE == 'nl':
                            human_value = selected_field_choice.dutch_name
                        else:
                            human_value = selected_field_choice.english_name

                    except (IndexError, ValueError):
                        human_value = machine_value

                # And add the kind of field
                if field in ['phonOth', 'mouthG', 'mouthing', 'phonetVar', 'iconImg', 'locVirtObj']:
                    kind = 'text';
                elif field in ['repeat', 'altern']:
                    kind = 'check';
                else:
                    kind = 'list';

                context[topic + '_fields'].append([human_value, field, labels[field], kind]);

        # Gather the OtherMedia
        context['other_media'] = []
        other_media_type_choice_list = FieldChoice.objects.filter(field__iexact='OthermediaType')

        for other_media in gl.othermedia_set.all():

            if int(other_media.type) == 0:
                human_value_media_type = '-'
            elif int(other_media.type) == 1:
                human_value_media_type = 'N/A'
            else:

                selected_field_choice = other_media_type_choice_list.filter(machine_value=other_media.type)[0]

                codes_to_adjectives = dict(settings.LANGUAGES)

                if self.request.LANGUAGE_CODE not in codes_to_adjectives.keys():
                    adjective = 'english'
                else:
                    adjective = codes_to_adjectives[self.request.LANGUAGE_CODE].lower()

                try:
                    human_value_media_type = getattr(selected_field_choice, adjective + '_name')
                except AttributeError:
                    human_value_media_type = getattr(selected_field_choice, 'english_name')

            path = settings.STATIC_URL + 'othermedia/' + other_media.path
            context['other_media'].append([other_media.pk, path, human_value_media_type, other_media.alternative_gloss])

            # Save the other_media_type choices (same for every other_media, but necessary because they all have other ids)
            context['choice_lists'][
                'other-media-type_' + str(other_media.pk)] = choicelist_queryset_to_translated_ordered_dict(
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


def choicelist_queryset_to_translated_ordered_dict(queryset,language_code):

    codes_to_adjectives = dict(settings.LANGUAGES)

    if language_code not in codes_to_adjectives.keys():
        adjective = 'english'
    else:
        adjective = codes_to_adjectives[language_code].lower()

    try:
        raw_choice_list = [('_'+str(choice.machine_value),unicode(getattr(choice,adjective+'_name'))) for choice in queryset]
    except AttributeError:
        raw_choice_list = [('_'+str(choice.machine_value),unicode(getattr(choice,'english_name'))) for choice in queryset]

    sorted_choice_list = [('_0','-'),('_1','N/A')]+sorted(raw_choice_list,key = lambda x: x[1])

    return OrderedDict(sorted_choice_list)
