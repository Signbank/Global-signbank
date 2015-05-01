from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.db.models import Q
from django.db.models.fields import NullBooleanField
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
import csv
import re

from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from signbank.feedback.models import *
from signbank.video.forms import VideoUploadForGlossForm
from tagging.models import Tag, TaggedItem

class GlossListView(ListView):
    
    model = Gloss
    template_name = 'dictionary/admin_gloss_list.html'
    paginate_by = 500
    
    
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(GlossListView, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['searchform'] = GlossSearchForm(self.request.GET)
        context['glosscount'] = Gloss.objects.all().count()
        context['add_gloss_form'] = GlossCreateForm()
        context['ADMIN_RESULT_FIELDS'] = settings.ADMIN_RESULT_FIELDS
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
        else:
            return super(GlossListView, self).render_to_response(context)


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
                      'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim', 'locVirtObj', 'absOriPalm', 'absOriFing', 'relOriMov', 'relOriLoc', 'oriCh', 'contType',
                      'movSh', 'movDir', 'movMan', 'repeat', 'altern', 'phonOth', 'mouthG', 'mouthing', 'phonetVar', 'iconImg', 'namEnt', 'semField', 'tokNo',
                      'tokNoSgnr', 'tokNoA', 'tokNoV', 'tokNoR', 'tokNoGe', 'tokNoGr', 'tokNoO', 'tokNoSgnrA', 'tokNoSgnrV', 'tokNoSgnrR', 'tokNoSgnrGe',
                      'tokNoSgnrGr', 'tokNoSgnrO', 'inWeb', 'isNew'];
        fields = [Gloss._meta.get_field(fieldname) for fieldname in fieldnames]

        writer = csv.writer(response)
        header = ['Signbank ID'] + [f.verbose_name for f in fields]

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
            morphemes = [morpheme.role for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]
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

        # get query terms from self.request
        qs = Gloss.objects.all()
        
        #print "QS:", len(qs)
        
        get = self.request.GET
 
        
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
            
          
        if get.has_key('inWeb') and get['inWeb'] != 'unspecified':
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
                      'domhndsh', 'subhndsh', 'locprim', 'locVirtObj', 'relatArtic', 'absOriPalm', 'absOriFing', 'relOriMov', 'relOriLoc', 'oriCh', 'handCh', 'repeat', 'altern',
                      'movSh', 'movDir', 'movMan', 'contType', 'phonOth', 'mouthG', 'mouthing', 'phonetVar', 'iconImg', 'namEnt', 'semField', 'tokNo', 'tokNoSgnr',
                      'tokNoA', 'tokNoV', 'tokNoR', 'tokNoGe', 'tokNoGr', 'tokNoO', 'tokNoSgnrA', 'tokNoSgnrV', 'tokNoSgnrR', 'tokNoSgnrGe',
                      'tokNoSgnrGr', 'tokNoSgnrO', 'inWeb', 'isNew'];

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

        if get.has_key('morpheme') and get['morpheme'] != '':

            potential_morphemes = Gloss.objects.filter(idgloss__icontains=get['morpheme']);
            potential_morphdefs = MorphologyDefinition.objects.filter(morpheme__in=[morpheme.pk for morpheme in potential_morphemes])
            potential_pks = [morphdef.parent_gloss.pk for morphdef in potential_morphdefs];
            qs = qs.filter(pk__in=potential_pks)

        if get.has_key('hasMorphemeOfType') and get['hasMorphemeOfType'] != '':

            morphdefs_with_correct_role = MorphologyDefinition.objects.filter(role__exact=get['hasMorphemeOfType']);
            pks_for_glosses_with_morphdefs_with_correct_role = [morphdef.parent_gloss.pk for morphdef in morphdefs_with_correct_role];
            qs = qs.filter(pk__in=pks_for_glosses_with_morphdefs_with_correct_role)

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

       # print "Final :", len(qs)
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
        context['definitionform'] = DefinitionForm()
        context['relationform'] = RelationForm()
        context['morphologyform'] = MorphologyForm()
        context['navigation'] = context['gloss'].navigation(True)
        context['interpform'] = InterpreterFeedbackForm()
        context['SIGN_NAVIGATION']  = settings.SIGN_NAVIGATION
        if settings.SIGN_NAVIGATION:
            context['glosscount'] = Gloss.objects.count()
            context['glossposn'] =  Gloss.objects.filter(sn__lt=context['gloss'].sn).count()+1

        #Pass info about which fields we want to see
        gl = context['gloss'];
        labels = gl.field_labels();

	fields = {};

	fields['phonology'] = ['handedness','domhndsh','subhndsh','handCh','relatArtic','locprim','locVirtObj','absOriPalm','absOriFing',
                  'relOriMov','relOriLoc','oriCh','contType','movSh','movDir','movMan','repeat','altern','phonOth', 'mouthG',
                  'mouthing', 'phonetVar',];

	fields['semantics'] = ['iconImg','namEnt','semField'];

	fields['frequency'] = ['tokNoA','tokNoSgnrA','tokNoV','tokNoSgnrV','tokNoR','tokNoSgnrR','tokNoGe','tokNoSgnrGe',
                               'tokNoGr','tokNoSgnrGr','tokNoO','tokNoSgnrO'];

        for topic in ['phonology','semantics','frequency']:
            context[topic+'_fields'] = [];

            for field in fields[topic]:

                try:
                    value = getattr(gl,'get_'+field+'_display');
                except AttributeError:
                    value = getattr(gl,field);

                if field in ['phonOth','mouthG','mouthing','phonetVar','iconImg','locVirtObj']:
                    kind = 'text';
                elif field in ['repeat','altern']:
                    kind = 'check';
                else:
                    kind = 'list';

                context[topic+'_fields'].append([value,field,labels[field],kind]);

        return context
        
        
def gloss_ajax_complete(request, prefix):
    """Return a list of glosses matching the search term
    as a JSON structure suitable for typeahead."""
    
    
    query = Q(idgloss__istartswith=prefix) | \
            Q(annotation_idgloss__istartswith=prefix) | \
            Q(sn__startswith=prefix)
    qs = Gloss.objects.filter(query)

    result = []
    for g in qs:
        result.append({'idgloss': g.idgloss, 'annotation_idgloss': g.annotation_idgloss, 'sn': g.sn, 'pk': "%s (%s)" % (g.idgloss, g.pk)})
    
    return HttpResponse(json.dumps(result), {'content-type': 'application/json'})
