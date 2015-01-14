from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.db.models import Q
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
    paginate_by = 1000
    
    
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
        fieldnames = ['idgloss', 'annotation_idgloss', 'annotation_idgloss_en', 'useInstr', 'sense', 'morph', 'StemSN', 'compound', 'rmrks', 'handedness', 'domhndsh', 'subhndsh', 'locprim', 'relatArtic', 'absOriPalm', 'absOriFing', 'relOriMov', 'relOriLoc', 'handCh', 'repeat', 'altern', 'movSh', 'movDir', 'movMan', 'contType', 'phonOth', 'mouthG', 'mouthing', 'phonetVar', 'iconImg', 'namEnt', 'tokNo', 'tokNoSgnr', 'tokNoA', 'tokNoV', 'tokNoR', 'tokNoGe', 'tokNoGr', 'tokNoO', 'tokNoSgnrA', 'tokNoSgnrV', 'tokNoSgnrR', 'tokNoSgnrGe', 'tokNoSgnrGr', 'tokNoSgnrO', 'inWeb', 'isNew'];
        fields = [Gloss._meta.get_field(fieldname) for fieldname in fieldnames]

        writer = csv.writer(response)
        header = [f.verbose_name for f in fields]

        for extra_column in ['Languages','Dialects','Keywords','Relations to other signs','Relations to foreign signs',]:
            header.append(extra_column);

        writer.writerow(header)
    
        for gloss in self.get_queryset():
            row = []
            for f in fields:

                #Try the value of the choicelist
                try:
                    row.append(getattr(gloss, 'get_'+f.name+'_display')())

                #If it's not there, try the raw value
                except AttributeError:
                    value = getattr(gloss,f.name)
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
            
    
        ## phonology field filters
        if get.has_key('domhndsh') and get['domhndsh'] != '':
            val = get['domhndsh']
            qs = qs.filter(domhndsh__exact=val)
            
            #print "C :", len(qs)
            
        if get.has_key('subhndsh') and get['subhndsh'] != '':
            val = get['subhndsh']
            qs = qs.filter(subhndsh__exact=val)
            #print "D :", len(qs)
            
        if get.has_key('final_domhndsh') and get['final_domhndsh'] != '':
            val = get['final_domhndsh']
            qs = qs.filter(final_domhndsh__exact=val)
            #print "E :", len(qs)
            
        if get.has_key('final_subhndsh') and get['final_subhndsh'] != '':
            val = get['final_subhndsh']
            qs = qs.filter(final_subhndsh__exact=val)  
           # print "F :", len(qs)   
            
        if get.has_key('locprim') and get['locprim'] != '':
            val = get['locprim']
            qs = qs.filter(locprim__exact=val)
            #print "G :", len(qs)

        if get.has_key('locsecond') and get['locsecond'] != '':
            val = get['locsecond']
            qs = qs.filter(locsecond__exact=val)
            
            #print "H :", len(qs)     

        if get.has_key('final_loc') and get['final_loc'] != '':
            val = get['final_loc']
            qs = qs.filter(final_loc__exact=val)   
            
        
        
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
            
           # print "G :", len(qs)
        # end of phonology filters
        
        
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
                

        
        
        vals = get.getlist('dialect', [])
        if vals != []:
            qs = qs.filter(dialect__in=vals)
            
           # print "H :", len(qs)
         
        vals = get.getlist('language', [])
        if vals != []:
            qs = qs.filter(language__in=vals)
            
            #print "I :", len(qs)
                     
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

	fields['phonology'] = ['handedness','domhndsh','subhndsh','locprim','relatArtic','absOriPalm','absOriFing',
                  'relOriMov','relOriLoc','handCh','repeat', 'altern', 'movSh','movDir','movMan','contType','phonOth', 'mouthG', 
                  'mouthing', 'phonetVar',];

	fields['semantics'] = ['iconImg','namEnt'];

	fields['frequency'] = ['tokNoA','tokNoSgnrA','tokNoV','tokNoSgnrV','tokNoR','tokNoSgnrR','tokNoGe','tokNoSgnrGe',
                               'tokNoGr','tokNoSgnrGr','tokNoO','tokNoSgnrO'];

        for topic in ['phonology','semantics','frequency']:
            context[topic+'_fields'] = [];

            for field in fields[topic]:

                try:
                    value = getattr(gl,'get_'+field+'_display');
                except AttributeError:
                    value = getattr(gl,field);

                if field in ['phonOth','mouthG','mouthing','phonetVar','iconImg']:
                    kind = 'text';
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


