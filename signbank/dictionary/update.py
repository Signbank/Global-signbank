from django.core.exceptions import ObjectDoesNotExist

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.template import Context, RequestContext, loader
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse

from django.contrib.auth.decorators import permission_required
from django.db.models.fields import NullBooleanField

from tagging.models import TaggedItem, Tag
import os, shutil, re
from datetime import datetime
from django.contrib import messages

from signbank.dictionary.models import *
from signbank.dictionary.forms import *
import signbank.settings
from django.conf import settings

from signbank.settings.base import OTHER_MEDIA_DIRECTORY
from signbank.dictionary.translate_choice_list import machine_value_to_translated_human_value
from signbank.tools import get_selected_datasets_for_user, gloss_from_identifier

from django.utils.translation import ugettext_lazy as _

from guardian.shortcuts import get_user_perms, get_group_perms

# this method is called from the GlossListView (Add Gloss button on the page)
@permission_required('dictionary.add_gloss')
def add_gloss(request):
    """Create a new gloss and redirect to the edit view"""

    if request.method == "POST":
        dataset = None
        if 'dataset' in request.POST and request.POST['dataset'] is not None:
            dataset = Dataset.objects.get(pk=request.POST['dataset'])
            selected_datasets = Dataset.objects.filter(pk=request.POST['dataset'])
        else:
            selected_datasets = get_selected_datasets_for_user(request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

        if 'last_used_dataset' in request.session.keys():
            form = GlossCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=request.session['last_used_dataset'])
        else:
            form = GlossCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=None)

        # Lemma handling
        lemmaidgloss = None
        lemma_form = None
        if request.POST['select_or_new_lemma'] == 'new':
            lemma_form = LemmaCreateForm(request.POST, languages=dataset_languages, user=request.user)
        else:
            try:
                lemmaidgloss_id = request.POST['idgloss']
                lemmaidgloss = LemmaIdgloss.objects.get(id=lemmaidgloss_id)
            except:
                messages.add_message(request, messages.ERROR,
                                     _("The given Lemma Idgloss ID is unknown."))
                return render(request, 'dictionary/add_gloss.html', {'add_gloss_form': form})

        # Check for 'change_dataset' permission
        if dataset and ('change_dataset' not in get_user_perms(request.user, dataset)) \
                and ('change_dataset' not in get_group_perms(request.user, dataset))\
                and not request.user.is_staff:
            messages.add_message(request, messages.ERROR, _("You are not authorized to change the selected dataset."))
            return render(request, 'dictionary/add_gloss.html', {'add_gloss_form': form})
        elif not dataset:
            # Dataset is empty, this is an error
            messages.add_message(request, messages.ERROR, _("Please provide a dataset."))
            return render(request, 'dictionary/add_gloss.html', {'add_gloss_form': form})

        # if we get to here a dataset has been chosen for the new gloss

        for item, value in request.POST.items():
            if item.startswith(form.gloss_create_field_prefix):
                language_code_2char = item[len(form.gloss_create_field_prefix):]
                language = Language.objects.get(language_code_2char=language_code_2char)
                glosses_for_this_language_and_annotation_idgloss = Gloss.objects.filter(
                    annotationidglosstranslation__language=language,
                    annotationidglosstranslation__text__exact=value.upper(),
                    lemma__dataset=dataset)
                if len(glosses_for_this_language_and_annotation_idgloss) != 0:
                    return render(request, 'dictionary/warning.html',
                                  {'warning': language.name + " " + 'annotation ID Gloss not unique.'})

        if form.is_valid() and (lemmaidgloss or lemma_form.is_valid()):
            try:
                gloss = form.save()
                gloss.creationDate = datetime.now()
                gloss.excludeFromEcv = False
                if lemma_form:
                    lemmaidgloss = lemma_form.save()
                gloss.lemma = lemmaidgloss
                gloss.save()
                gloss.creator.add(request.user)
            except ValidationError as ve:
                messages.add_message(request, messages.ERROR, ve.message)
                return render(request, 'dictionary/add_gloss.html', {'add_gloss_form': form,
                                                                     'dataset_languages': dataset_languages,
                                                                     'selected_datasets': get_selected_datasets_for_user(request.user)})


            # context variables need to be set before GlossDetailView
            if not ('search_results' in request.session.keys()):
                request.session['search_results'] = None
            request.session['last_used_dataset'] = dataset.name
            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?edit')
        else:
            return render(request,'dictionary/add_gloss.html',{'add_gloss_form': form,
                                                               'dataset_languages': dataset_languages,
                                                               'selected_datasets': get_selected_datasets_for_user(request.user),
                                                               'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})
        
    return HttpResponseRedirect(reverse('dictionary:admin_gloss_list'))


def update_gloss(request, glossid):
    """View to update a gloss model from the jeditable jquery form
    We are sent one field and value at a time, return the new value
    once we've updated it."""

    if not request.user.has_perm('dictionary.change_gloss'):
        return HttpResponseForbidden("Gloss Update Not Allowed")

    if request.method == "POST":

        gloss = get_object_or_404(Gloss, id=glossid)
        gloss.save() # This updates the lastUpdated field

        field = request.POST.get('id', '')
        value = request.POST.get('value', '')
        original_value = '' #will in most cases be set later, but can't be empty in case it is not set
        category_value = ''
        field_category = ''
        lemma_gloss_group = False
        lemma_group_string = gloss.idgloss
        other_glosses_in_lemma_group = Gloss.objects.filter(lemma__lemmaidglosstranslation__text__iexact=lemma_group_string).count()
        if other_glosses_in_lemma_group > 1:
            lemma_gloss_group = True

        if len(value) == 0:
            # this seems a bit dangerous
            value = ' '

        elif value[0] == '_':
            value = value[1:]

        values = request.POST.getlist('value[]')   # in case we need multiple values 

        # validate
        # field is a valid field
        # value is a valid value for field
        
        if field == 'deletegloss':
            if value == 'confirmed':
                # delete the gloss and redirect back to gloss list

                pk = gloss.pk
                gloss.delete()
                gloss.pk = pk

                return HttpResponseRedirect(reverse('dictionary:admin_gloss_list'))
        
        if field.startswith('definition'):
            
            return update_definition(request, gloss, field, value)

        elif field.startswith('keywords'):

            return update_keywords(gloss, field, value)

        elif field.startswith('relationforeign'):
            
            return update_relationtoforeignsign(gloss, field, value)
            
        elif field.startswith('relation'):
            
            return update_relation(gloss, field, value)

        elif field.startswith('morphology-definition'):

            return update_morphology_definition(gloss, field, value, request.LANGUAGE_CODE)

        elif field.startswith('morpheme-definition'):

            return update_morpheme_definition(gloss, field, value)

        elif field.startswith('blend-definition'):

            return update_blend_definition(gloss, field, value)

        elif field.startswith('other-media'):

            return update_other_media(request,gloss, field, value)

        elif field == 'signlanguage':
            # expecting possibly multiple values

            return update_signlanguage(gloss, field, values)

        elif field == 'dialect':
            # expecting possibly multiple values

            return update_dialect(gloss, field, values)

        elif field == 'dataset':
            original_value = getattr(gloss,field)

            # in case somebody tries an empty or non-existent dataset name
            try:
                ds = Dataset.objects.get(name=value)
            except:
                return HttpResponse(str(original_value), {'content-type': 'text/plain'})

            if ds.is_public:
                newvalue = value
                setattr(gloss, field, ds)
                gloss.save()

                request.session['last_used_dataset'] = ds.name

                return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

            import guardian
            if ds in guardian.shortcuts.get_objects_for_user(request.user, 'view_dataset', Dataset):
                newvalue = value
                setattr(gloss, field, ds)
                gloss.save()

                request.session['last_used_dataset'] = ds.name

                return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

            print('no permission for chosen dataset')
            newvalue = original_value
            return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

        elif field == "sn":
            # sign number must be unique, return error message if this SN is 
            # already taken
            
            if value == '':
                gloss.__setattr__(field, None)
                gloss.save()
                newvalue = ''
            else:
                try:
                    value = int(value)
                except:
                    return HttpResponseBadRequest("SN value must be integer", {'content-type': 'text/plain'})
                
                existing_gloss = Gloss.objects.filter(sn__exact=value)
                if existing_gloss.count() > 0:
                    g = existing_gloss[0].idgloss
                    return HttpResponseBadRequest("SN value already taken for gloss %s" % g, {'content-type': 'text/plain'})
                else:
                    gloss.sn = value
                    gloss.save()
                    newvalue = value
            
        
        elif field in 'inWeb':
            # only modify if we have publish permission
            if request.user.has_perm('dictionary.can_publish'):
                gloss.inWeb = value.lower() in [_('Yes').lower(),'true',True,1]
                gloss.save()
            
            if gloss.inWeb:
                newvalue = _('Yes')
            else:
                newvalue = _('No')

        elif field in 'isNew':
            # only modify if we have publish permission
            print(_('yes'))
            gloss.isNew = value.lower() in [_('Yes').lower(),'true',True,1]
            gloss.save()

            if gloss.isNew:
                newvalue = _('Yes')
            else:
                newvalue = _('No')
        elif field in 'excludeFromEcv':
            # only modify if we have publish permission

            gloss.excludeFromEcv = value.lower() in [_('Yes').lower(),'true',True,1]
            gloss.save()

            if gloss.excludeFromEcv:
                newvalue = _('Yes')
            else:
                newvalue = _('No')

        elif field.startswith('annotation_idgloss'):

            return update_annotation_idgloss(gloss, field, value)

        elif field.startswith('lemmaidgloss'):
            # Set new lemmaidgloss for this gloss
            # First check whether the gloss dataset is the same as the lemma dataset
            try:
                dataset = gloss.dataset
                lemma = LemmaIdgloss.objects.get(pk=value)
                if dataset == lemma.dataset:
                    old_video_path = settings.MEDIA_ROOT + gloss.get_video_path()
                    gloss.lemma = lemma
                    gloss.save()
                    new_video_path = settings.MEDIA_ROOT + gloss.get_video_path()

                    # Rename video
                    gloss.rename_video(old_video_path, new_video_path)
                else:
                    messages.add_message(messages.ERROR, _("The dataset of the gloss is not the same as that of the lemma."))
            except ObjectDoesNotExist:
                messages.add_message(messages.ERROR, _("The specified lemma does not exist."))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        else:


            if not field in [f.name for f in Gloss._meta.get_fields()]:
                return HttpResponseBadRequest("Unknown field", {'content-type': 'text/plain'})

            whitespace = tuple(' \n\r\t')
            if value.startswith(whitespace) or value.endswith(whitespace):
                value = value.strip()
            original_value = getattr(gloss,field)

            if field == 'idgloss' and value == '':
                # don't allow user to set Lemma ID Gloss to empty
                # return HttpResponse(str(original_value), {'content-type': 'text/plain'})
                value = str(original_value)

            # special cases
            # - Foreign Key fields (Language, Dialect)
            # - keywords
            # - videos
            # - tags

            #Translate the value if a boolean
            # Language values are needed here!

            if isinstance(gloss._meta.get_field(field),NullBooleanField):
                # value is the html 'value' received during editing
                newvalue = value
                # value gets converted to a Boolean by the following statement
                if field == 'weakdrop' or field == 'weakprop' or field == 'domhndsh_letter' or field == 'domhndsh_number' or \
                                                    field == 'subhndsh_letter' or field == 'subhndsh_number':
                    category_value = 'phonology'
                    if field == 'weakdrop':
                        value = {'1': None, '2': True, '3': False}[value]
                        newvalue = {'1': '&nbsp;', '2': '+WD', '3': '-WD'}[newvalue]

                    elif field == 'weakprop':
                        value = {'1': None, '2': True, '3': False}[value]
                        newvalue = {'1': '&nbsp;', '2': '+WP', '3': '-WP'}[newvalue]

                    else:
                        value = (value in ['letter', 'number'])

                else:
                    value = (value.lower() in [_('Yes').lower(),'true',True,1])

            # special value of 'notset' or -1 means remove the value
            fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew']

            char_fields_not_null = [f.name for f in Gloss._meta.fields
                                    if f.name in fieldnames and f.__class__.__name__ == 'CharField' and not f.null]

            if (value == 'notset' or value == -1 or value == '') and field not in char_fields_not_null:
                gloss.__setattr__(field, None)
                gloss.save()
                newvalue = ''

            #Regular field updating
            else:
                #Remember the old video path if you're changing the name
                if field == 'idgloss':
                    old_video_path = gloss.get_video_path()
                    old_image_path = gloss.get_image_path()

                    try:
                        old_extension = old_image_path.split('.')[-1]
                    except AttributeError:
                        old_extension = ''

                setattr(gloss,field,value)
                gloss.save()

                #Update the video location if you're changing the name
                if field == 'idgloss':
                    new_video_path = gloss.get_video_path()
                    new_image_path = gloss.get_image_path(check_existance=False)

                    try:
                        shutil.move(settings.MEDIA_ROOT+'/'+old_video_path,settings.MEDIA_ROOT+'/'+new_video_path)

                    #You don't have to do this if there's no video
                    except IOError:
                        pass

                    try:
                        shutil.move(settings.MEDIA_ROOT+'/'+old_image_path,settings.MEDIA_ROOT+'/'+new_image_path+'.'+old_extension)

                    #You don't have to do this if there's no image
                    except (IOError,TypeError):
                        pass

                if field == 'idgloss':
                    # new value has already been saved to gloss
                    lemma_group_string = gloss.idgloss
                    other_glosses_in_lemma_group = Gloss.objects.filter(idgloss__iexact=lemma_group_string).count()
                    if other_glosses_in_lemma_group > 1:
                        lemma_gloss_group = True
                    else:
                        lemma_gloss_group = False

                #If the value is not a Boolean, return the new value
                if not isinstance(value,bool):

                    field_category = fieldname_to_category(field)

                    choice_list = FieldChoice.objects.filter(field__iexact=field_category)
                    newvalue = machine_value_to_translated_human_value(value,choice_list,request.LANGUAGE_CODE)

                if field_category in FIELDS['phonology']:

                     category_value = 'phonology'

        # if field == 'domhndsh':
            # value should be the machine_value representation, please confirm if modifying the above code
            # print("Strong Hand: ", newvalue, ", ", value)

        #This is because you cannot concat none to a string in py3
        if original_value == None:
            original_value = ''

        # The machine_value (value) representation is also returned to accommodate Hyperlinks to Handshapes in gloss_edit.js
        return HttpResponse(
            str(original_value) + str('\t') + str(newvalue) + str('\t') +  str(value) + str('\t') + str(category_value) + str('\t') + str(lemma_gloss_group),
            {'content-type': 'text/plain'})

def update_keywords(gloss, field, value):
    """Update the keyword field"""

    # Determine the language of the keywords
    language = Language.objects.get(id=get_default_language_id())
    try:
        language_code_2char = field[len('keywords_'):]
        language = Language.objects.filter(language_code_2char=language_code_2char)[0]
    except:
        pass

    kwds = [k.strip() for k in value.split(',')]

    keywords_list = []

    # omit duplicates
    for kwd in kwds:
        if kwd not in keywords_list:
            keywords_list.append(kwd)

    # remove current keywords
    current_trans = gloss.translation_set.filter(language=language)
    current_trans.delete()
    # add new keywords
    for i in range(len(keywords_list)):
        (kobj, created) = Keyword.objects.get_or_create(text=keywords_list[i])
        trans = Translation(gloss=gloss, translation=kobj, index=i, language=language)
        trans.save()
    
    newvalue = ", ".join([t.translation.text for t in gloss.translation_set.filter(language=language)])
    
    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def update_annotation_idgloss(gloss, field, value):
    """Update the AnnotationIdGlossTranslation"""

    # Determine the language of the keywords
    language = Language.objects.get(id=get_default_language_id())
    try:
        language_code_2char = field[len('annotation_idgloss_'):]
        language = Language.objects.filter(language_code_2char=language_code_2char)[0]
    except:
        pass

    # value might be empty string
    whitespace = tuple(' \n\r\t')
    if value.startswith(whitespace) or value.endswith(whitespace):
        value = value.strip()

    annotation_idgloss_translation = AnnotationIdglossTranslation.objects.get(gloss=gloss, language=language)
    original_value = annotation_idgloss_translation.text

    if value == '':
        # don't allow user to set Annotation ID Gloss to empty
        return HttpResponse(str(original_value), {'content-type': 'text/plain'})

    annotation_idgloss_translation.text = value
    annotation_idgloss_translation.save()

    return HttpResponse(str(value), {'content-type': 'text/plain'})

def update_signlanguage(gloss, field, values):
    # expecting possibly multiple values

    # Sign Language and Dialect are interdependent
    # When updated in Gloss Detail View, checks are made to insure consistency
    # Because we use Ajax calls to update the data, two values need to be returned in order to also have a side effect
    # on the other field. I.e., Changing the Sign Language may cause Dialects to be removed, and changing the Dialect
    # may cause the Sign Language to be filled in if not already set, with that of the new Dialect
    # To accommodate this in the interactive user interface for Editting a Gloss, two values are returned

    # The dialects value is set to the current dialects value
    dialects_value = ", ".join([str(d.signlanguage.name) + '/' + str(d.name) for d in gloss.dialect.all()])
    current_signlanguages = gloss.signlanguage.all()
    current_signlanguage_name = ''
    for lang in current_signlanguages:
        # this looks strange, is this a convenience for a singleton set
        current_signlanguage_name = lang.name

    try:
        gloss.signlanguage.clear()
        for value in values:
            lang = SignLanguage.objects.get(name=value)
            gloss.signlanguage.add(lang)
            if value != current_signlanguage_name:
                gloss.dialect.clear()
                # Has a side effect that the Dialects value is cleared, this will be passed back to the user interface
                dialects_value = ''
        gloss.save()
        new_signlanguage_value = ", ".join([str(g) for g in gloss.signlanguage.all()])
    except:
        return HttpResponseBadRequest("Unknown Language %s" % values, {'content-type': 'text/plain'})

    return HttpResponse(str(new_signlanguage_value) + '\t' + str(dialects_value), {'content-type': 'text/plain'})

def update_dialect(gloss, field, values):
    # expecting possibly multiple values

    dialect_choices = json.loads(gloss.dialect_choices())
    numerical_values_converted_to_dialects = [ dialect_choices[int(value)] for value in values ]
    error_string_values = ', '.join(numerical_values_converted_to_dialects)
    new_dialects_to_save = []

    try:
        gloss_signlanguages = gloss.signlanguage.all()
        for value in numerical_values_converted_to_dialects:
            # Gloss Detail View pairs the Dialect with the Language in the update menu
            (sign_lang, dia) = value.split('/')
            lang = SignLanguage.objects.get(name=sign_lang)
            if not lang in gloss_signlanguages:
                if gloss_signlanguages:
                    # There is currently a sign language assigned to this gloss, the new dialect does not match it
                    raise Exception
                else:
                    # currently no sign language has been assigned, assign this one
                    # this value is not returned to the Gloss Detail View, it is a side effect
                    gloss.signlanguage.add(lang)

            dialect_objs = Dialect.objects.filter(name=dia).filter(signlanguage_id=lang)
            for lang in dialect_objs:
                new_dialects_to_save.append(lang)

        # clear the old dialects only after we've parsed and checked the new ones
        gloss.dialect.clear()
        for lang in new_dialects_to_save:
            gloss.dialect.add(lang)
        gloss.save()

        # The signlanguage value is set to the currect sign languages value
        signlanguage_value = ", ".join([str(g) for g in gloss.signlanguage.all()])
        new_dialects_value = ", ".join([str(d.signlanguage.name)+'/'+str(d.name) for d in gloss.dialect.all()])
    except:
        return HttpResponseBadRequest("Dialect %s does not match Sign Language of Gloss" % error_string_values,
                                      {'content-type': 'text/plain'})

    return HttpResponse(str(signlanguage_value) + '\t' + str(new_dialects_value), {'content-type': 'text/plain'})

def update_tags(gloss, field, values):
    # expecting possibly multiple values

    current_tag_ids = [tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    new_tag_ids = [tag.id for tag in Tag.objects.filter(name__in=values)]

    # the existance of the new tag has already been checked
    for tag_id in current_tag_ids:

        if tag_id not in new_tag_ids:
            # delete tag from object
            tagged_obj = TaggedItem.objects.get(object_id=gloss.id,tag_id=tag_id)
            print("DELETE TAGGED OBJECT: ", tagged_obj, ' for gloss: ', tagged_obj.object_id)
            tagged_obj.delete()

    for value in values:
        Tag.objects.add_tag(gloss, value)

    new_tag_ids = [tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    newvalue = ', '.join([str(tag.name).replace('_',' ') for tag in  Tag.objects.filter(id__in=new_tag_ids) ])

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def update_sequential_morphology(gloss, field, values):
    # expecting possibly multiple values

    morphemes = [morpheme.id for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]

    role = 2

    # the existance of the morphemes in parameter values has already been checked
    try:
        for morpheme_def_id in morphemes:
            old_morpheme = MorphologyDefinition.objects.get(id=morpheme_def_id)
            print("DELETE Sequential Morphology: ", old_morpheme)
            old_morpheme.delete()
        for value in values:
            morpheme = Gloss.objects.get(pk=value)
            morph_def = MorphologyDefinition()
            morph_def.parent_gloss = gloss
            morph_def.role = role
            morph_def.morpheme = morpheme
            morph_def.save()
            role = role + 1
    except:
        return HttpResponseBadRequest("Unknown Morpheme %s" % values, {'content-type': 'text/plain'})

    seq_morphemes = [morpheme.morpheme for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]

    newvalue = ", ".join([str(g.idgloss) for g in seq_morphemes])

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def update_simultaneous_morphology(gloss, field, values):
    # expecting possibly multiple values

    existing_sim_ids = [morpheme.id for morpheme in SimultaneousMorphologyDefinition.objects.filter(parent_gloss_id=gloss)]
    new_sim_tuples = []
    for value in values:
        (morpheme_id, role) = value.split(':')
        new_sim_tuples.append((morpheme_id,role))

    # delete any existing simultaneous morphology objects rather than update
    # to allow (re-)insertion in the correct order
    for sim_id in existing_sim_ids:
        sim = SimultaneousMorphologyDefinition.objects.get(id=sim_id)
        print("DELETE Simultaneous Morphology: ", sim)
        sim.delete()

    # the existance of the morphemes has already been checked, but check again anyway
    for (morpheme_id, role) in new_sim_tuples:

        try:
            morpheme_gloss = Gloss.objects.get(pk=morpheme_id)

            # create new morphology
            sim = SimultaneousMorphologyDefinition()
            sim.parent_gloss_id = gloss.id
            sim.morpheme_id = morpheme_gloss.id
            sim.role = role
            sim.save()

        except:
            print("morpheme not found")
            continue


    # Refresh Simultaneous Morphology with newly inserted objects
    morphemes = [(str(morpheme.morpheme.id), morpheme.role)
                 for morpheme in SimultaneousMorphologyDefinition.objects.filter(parent_gloss_id=gloss)]
    sim_morphs = []
    for m in morphemes:
        sim_morphs.append(':'.join(m))
    simultaneous_morphemes = ', '.join(sim_morphs)

    newvalue = simultaneous_morphemes

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})


def update_blend_morphology(gloss, field, values):

    existing_blends = [ ble_morph.id for ble_morph in BlendMorphology.objects.filter(parent_gloss=gloss) ]

    new_blend_tuples = []
    for value in values:
        (gloss_id, role) = value.split(':')
        new_blend_tuples.append((gloss_id,role))

    try:

        # delete any existing blend morphology objects
        for existing_blend in existing_blends:
            blend_object = BlendMorphology.objects.get(id=existing_blend)
            print("DELETE Blend Morphology for gloss ", str(gloss.pk), ": ", blend_object.glosses.pk, " ", blend_object.role)
            blend_object.delete()

        for (gloss_id, role) in new_blend_tuples:

            morpheme_gloss = Gloss.objects.get(pk=gloss_id)

            # create new morphology
            new_blend = BlendMorphology()
            new_blend.parent_gloss = gloss
            new_blend.glosses = morpheme_gloss
            new_blend.role = role
            new_blend.save()

    except:
        return HttpResponseBadRequest("Unknown Morpheme in Blend Morphology %s" % values, {'content-type': 'text/plain'})

    # convert to display format
    blend_morphemes = [ (str(ble_morph.glosses.pk), ble_morph.role) for ble_morph in BlendMorphology.objects.filter(parent_gloss=gloss) ]
    ble_morphs = []
    for m in blend_morphemes:
        ble_morphs.append(':'.join(m))
    blend_morphemes = ', '.join(ble_morphs)

    newvalue = blend_morphemes

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})


def subst_notes(gloss, field, values):
    # this is called by csv_import to modify the notes for a gloss

    note_role_choices = FieldChoice.objects.filter(field__iexact='NoteType')
    # this is used to speedup matching updates to Notes
    # it allows the type of note to be in either English or Dutch in the CSV file
    note_reverse_translation = {}
    for nrc in note_role_choices:
        note_reverse_translation[nrc.english_name] = nrc.machine_value
        note_reverse_translation[nrc.dutch_name] = nrc.machine_value

    for original_note in gloss.definition_set.all():
        original_note.delete()

    # convert new Notes csv value to proper format
    # the syntax of the new note values has already been checked at a previous stage of csv import
    new_notes_values = []

    split_values = re.findall(r'([^\:]+\:[^\)]*\)),?\s?', values)

    for note_value in split_values:
        take_apart = re.match("([^\:]+)\:\s?\((False|True),(\d),([^\)]*)\)", note_value)
        if take_apart:
            (field, name, count, text) = take_apart.groups()
            new_tuple = (field, name, count, text)
            new_notes_values.append(new_tuple)

    for (role, published, count, text) in new_notes_values:
        is_published = (published == 'True')
        note_role = str(note_reverse_translation[role])
        index_count = int(count)
        defn = Definition(gloss=gloss, count=index_count, role=note_role, text=text, published=is_published)
        defn.save()

    new_notes_refresh = [(note.role, str(note.published), str(note.count), note.text) for note in gloss.definition_set.all()]
    notes_by_role = []
    for note in new_notes_refresh:
        notes_by_role.append(':'.join(note))

    new_gloss_notes = ", ".join(notes_by_role)

    return HttpResponse(str(new_gloss_notes), {'content-type': 'text/plain'})

def subst_foreignrelations(gloss, field, values):
    # expecting possibly multiple values
    # values is a list of values, where each value is a tuple of the form 'Boolean:String:String'
    # The format of argument values has been checked before calling this function

    existing_relations = [(relation.id, relation.other_lang_gloss) for relation in RelationToForeignSign.objects.filter(gloss=gloss)]

    existing_relation_ids = [r[0] for r in existing_relations]
    existing_relation_other_glosses = [r[1] for r in existing_relations]

    new_relations = []
    new_relation_tuples = []

    for value in values:
        (loan_word, other_lang, other_lang_gloss) = value.split(':')
        new_relation_tuples.append((loan_word,other_lang,other_lang_gloss))

    new_relations = [ t[2] for t in new_relation_tuples]

    # delete any existing relations with obsolete other language gloss
    for rel_id in existing_relation_ids:
        rel = RelationToForeignSign.objects.get(id=rel_id)
        if rel.other_lang_gloss not in new_relations:
            print("DELETE Relation to Foreign Sign: ", rel)
            rel.delete()

    # all remaining existing relations are to be updated
    for (loan_word, other_lang, other_lang_gloss) in new_relation_tuples:
        if other_lang_gloss in existing_relation_other_glosses:
            # update existing relation
            rel = RelationToForeignSign.objects.get(gloss=gloss, other_lang_gloss=other_lang_gloss)
            rel.loan = loan_word in ['Yes', 'yes', 'ja', 'Ja', '是', 'true', 'True', True, 1]
            rel.other_lang = other_lang
            rel.save()
        else:
            # create new relation
            new_relations += [other_lang_gloss]
            rel = RelationToForeignSign(gloss=gloss,loan=loan_word,other_lang=other_lang,other_lang_gloss=other_lang_gloss)
            rel.save()

    new_relations_refresh = [(str(relation.loan), relation.other_lang, relation.other_lang_gloss) for relation in
                 RelationToForeignSign.objects.filter(gloss=gloss)]
    relations_with_categories = []
    for rel_cat in new_relations_refresh:
        relations_with_categories.append(':'.join(rel_cat))

    relations_categories = ", ".join(relations_with_categories)

    newvalue = relations_categories

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def subst_relations(gloss, field, values):
    # expecting possibly multiple values
    # values is a list of values, where each value is a tuple of the form 'Role:String'
    # The format of argument values has been checked before calling this function

    existing_relations = [(relation.id, relation.role, relation.target.id) for relation in Relation.objects.filter(source=gloss)]
    existing_relation_ids = [ r[0] for r in existing_relations ]
    existing_relations_by_role = dict()

    for (rel_id, rel_role, rel_other_gloss) in existing_relations:

        if rel_role in existing_relations_by_role:
            existing_relations_by_role[rel_role].append(rel_other_gloss)
        else:
            existing_relations_by_role[rel_role] = [rel_other_gloss]

    new_tuples_to_add = []
    already_existing_to_keep = []

    for value in values:
        (role, target) = value.split(':')
        role = role.strip()
        target = target.strip()
        if role in existing_relations_by_role and target in existing_relations_by_role[role]:
            already_existing_to_keep.append((role,target))
        else:
            new_tuples_to_add.append((role, target))

    # delete existing relations and reverse relations involving this gloss
    for rel_id in existing_relation_ids:
        rel = Relation.objects.get(id=rel_id)

        if (rel.role, rel.target.id) in already_existing_to_keep:
            continue

        # Also delete the reverse relation
        reverse_relations = Relation.objects.filter(source=rel.target, target=rel.source,
                                                    role=Relation.get_reverse_role(rel.role))
        if reverse_relations.count() > 0:
            print("DELETE reverse relation: target: ", rel.target, ", relation: ", reverse_relations[0])
            reverse_relations[0].delete()

        print("DELETE Relation: ", rel)
        rel.delete()

    # all remaining existing relations are to be updated
    for (role, target) in new_tuples_to_add:
        try:
            target_gloss = Gloss.objects.get(pk=target)
            rel = Relation(source=gloss, role=role, target=target_gloss)
            rel.save()
            # Also add the reverse relation
            reverse_relation = Relation(source=target_gloss, target=gloss, role=Relation.get_reverse_role(role))
            reverse_relation.save()
        except:
            print("target gloss not found")
            continue

    new_relations_refresh = [ (relation.role, relation.target.idgloss) for relation in
                 Relation.objects.filter(source=gloss)]
    relations_with_categories = []
    for rel_cat in new_relations_refresh:
        relations_with_categories.append(':'.join(rel_cat))

    relations_categories = ", ".join(relations_with_categories)

    newvalue = relations_categories

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

## This function is called from the Gloss Detail View template when updating Relations to Other Signs
def update_relation(gloss, field, value):
    """Update one of the relations for this gloss"""
    
    (what, relid) = field.split('_')
    what = what.replace('-','_')

    try:
        rel = Relation.objects.get(id=relid)
    except:
        return HttpResponseBadRequest("Bad Relation ID '%s'" % relid, {'content-type': 'text/plain'})

    if not rel.source == gloss:
        return HttpResponseBadRequest("Relation doesn't match gloss", {'content-type': 'text/plain'})
    
    if what == 'relationdelete':
        print("DELETE relation: ", rel)
        rel.delete()

        # Also delete the reverse relation
        reverse_relations = Relation.objects.filter(source=rel.target, target=rel.source,
                                                    role=Relation.get_reverse_role(rel.role))
        if reverse_relations.count() > 0:
            reverse_relations[0].delete()

        return HttpResponse('', {'content-type': 'text/plain'})
    elif what == 'relationrole':
        rel.role = value
        rel.save()
        newvalue = rel.get_role_display()
    elif what == 'relationtarget':
        
        target = gloss_from_identifier(value)
        if target:
            rel.target = target
            rel.save()
            newvalue = str(target)
        else:
            return HttpResponseBadRequest("Badly formed gloss identifier '%s'" % value, {'content-type': 'text/plain'})
    else:
        
        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})           
    
    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def delete_relation(gloss, field):

    return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})

def update_relationtoforeignsign(gloss, field, value):
    """Update one of the relations for this gloss"""
    
    (what, relid) = field.split('_')
    what = what.replace('-','_')

    try:
        rel = RelationToForeignSign.objects.get(id=relid)
    except:
        return HttpResponseBadRequest("Bad RelationToForeignSign ID '%s'" % relid, {'content-type': 'text/plain'})

    if not rel.gloss == gloss:
        return HttpResponseBadRequest("Relation doesn't match gloss", {'content-type': 'text/plain'})
    
    if what == 'relationforeign_delete':
        print("DELETE Relation to Foreign Sign: ", rel)
        rel.delete()
        # return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editrelforeign')
        return HttpResponse('', {'content-type': 'text/plain'})
    elif what == 'relationforeign_loan':
        rel.loan = value == 'YES'
        rel.save()

    elif what == 'relationforeign_other_lang':
        rel.other_lang = value
        rel.save()

    elif what == 'relationforeign_other_lang_gloss':
        rel.other_lang_gloss = value
        rel.save()

    else:
        
        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})           
    
    return HttpResponse(str(value), {'content-type': 'text/plain'})


def morph_from_identifier(value):
    """Given an id of the form idgloss (pk) return the
    relevant Morpheme or None if none is found
    BUT: first check if a unique hit can be found by the string alone (if it is not empty)
    """

    match = re.match('(.*) \((\d+)\)', value)
    if match:
        print("MATCH: ", match)
        idgloss = match.group(1)
        pk = match.group(2)
        print("INFO: ", idgloss, pk)

        target = Morpheme.objects.get(pk=int(pk))
        print("TARGET: ", target)
        return target
    elif value != '':
        idgloss = value
        target = Morpheme.objects.get(idgloss=idgloss)
        return target
    else:
        return None


def update_definition(request, gloss, field, value):
    """Update one of the definition fields"""

    newvalue = ''
    (what, defid) = field.split('_')
    try:
        defn = Definition.objects.get(id=defid)
    except:
        return HttpResponseBadRequest("Bad Definition ID '%s'" % defid, {'content-type': 'text/plain'})

    if not defn.gloss == gloss:
        return HttpResponseBadRequest("Definition doesn't match gloss", {'content-type': 'text/plain'})
    
    if what == 'definitiondelete':
        defn.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editdef')
    
    if what == 'definition':
        # update the definition
        defn.text = value
        defn.save()
        newvalue = defn.text
    elif what == 'definitioncount':
        defn.count = int(value)
        defn.save()
        newvalue = defn.count
    elif what == 'definitionpub':
        
        if request.user.has_perm('dictionary.can_publish'):
            defn.published = value == 'Yes'
            defn.save()
        
        if defn.published:
            newvalue = 'Yes'
        else:
            newvalue = 'No'
    elif what == 'definitionrole':
        defn.role = value
        defn.save()
        choice_list = FieldChoice.objects.filter(field__iexact='NoteType')
        newvalue = machine_value_to_translated_human_value(value, choice_list, request.LANGUAGE_CODE)

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

def update_other_media(request,gloss,field,value):

    action_or_fieldname, other_media_id = field.split('_')

    other_media = None
    try:
        other_media = OtherMedia.objects.get(id=other_media_id)
    except:
        return HttpResponseBadRequest("Bad OtherMedia ID '%s'" % other_media, {'content-type': 'text/plain'})

    if not other_media.parent_gloss == gloss:
        return HttpResponseBadRequest("OtherMedia doesn't match gloss", {'content-type': 'text/plain'})

    if action_or_fieldname == 'other-media-delete':
        other_media.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.pk})+'?editothermedia')

    elif action_or_fieldname == 'other-media-type':
        other_media.type = value
        choice_list = FieldChoice.objects.filter(field__iexact='OtherMediaType')
        value = machine_value_to_translated_human_value(value,choice_list,request.LANGUAGE_CODE)

    elif action_or_fieldname == 'other-media-alternative-gloss':
        other_media.alternative_gloss = value

    other_media.save()

    return HttpResponse(str(value), {'content-type': 'text/plain'})

def add_relation(request):
    """Add a new relation instance"""
    
    if request.method == "POST":
        
        form = RelationForm(request.POST)
        
        if form.is_valid():
            
            role = form.cleaned_data['role']
            sourceid = form.cleaned_data['sourceid']
            targetid = form.cleaned_data['targetid'] # This is a gloss ID now
            
            try:
                source = Gloss.objects.get(pk=int(sourceid))
            except:
                print("source gloss not found")
                return HttpResponseBadRequest("Source gloss not found.", {'content-type': 'text/plain'})
            
            target = Gloss.objects.get(id=targetid)
            if target:
                rel = Relation(source=source, target=target, role=role)
                rel.save()

                # Also add the reverse relation
                reverse_relation = Relation(source=target, target=source, role=Relation.get_reverse_role(role))
                reverse_relation.save()

                return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': source.id})+'?editrel')

            else:
                print("target gloss not found")
                return HttpResponseBadRequest("Target gloss not found.", {'content-type': 'text/plain'})
        else:
            print(form)

    # fallback to redirecting to the requesting page
    return HttpResponseRedirect('/')


@permission_required('dictionary.change_gloss')
def variants_of_gloss(request):

#    thisgloss = get_object_or_404(Gloss, id=glossid)

    if request.method == "POST":

        form = VariantsForm(request.POST)

        if form.is_valid():
            role = 'variant'
            sourceid = form.cleaned_data['sourceid']
            targetid = form.cleaned_data['targetid']

            source = str(sourceid)
            target = str(targetid)

            source_object = Gloss.objects.get(pk=int(source))
            target_object = Gloss.objects.get(pk=int(target))

            rel = Relation(source=source_object, target=target_object, role=role)
            rel.save()

            return HttpResponse(json.dumps(rel), content_type="application/json")
        else:
#            print('invalid form')
            print(form)

    return HttpResponseRedirect('/')

def add_relationtoforeignsign(request):
    """Add a new relationtoforeignsign instance"""
    
    if request.method == "POST":
        
        form = RelationToForeignSignForm(request.POST)
        
        if form.is_valid():
            
            sourceid = form.cleaned_data['sourceid']
            loan = form.cleaned_data['loan']
            other_lang = form.cleaned_data['other_lang']
            other_lang_gloss = form.cleaned_data['other_lang_gloss']
            
            try:
                gloss = Gloss.objects.get(pk=int(sourceid))
            except:
                return HttpResponseBadRequest("Source gloss not found.", {'content-type': 'text/plain'})
            
            rel = RelationToForeignSign(gloss=gloss,loan=loan,other_lang=other_lang,other_lang_gloss=other_lang_gloss)
            rel.save()
                
            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editrelforeign')

        else:
            print(form)
            return HttpResponseBadRequest("Form not valid", {'content-type': 'text/plain'})

    # fallback to redirecting to the requesting page
    return HttpResponseRedirect('/')

def add_definition(request, glossid):
    """Add a new definition for this gloss"""
    
    
    thisgloss = get_object_or_404(Gloss, id=glossid)
    
    if request.method == "POST":
        form = DefinitionForm(request.POST)
        
        if form.is_valid():
            
            published = form.cleaned_data['published']
            count = form.cleaned_data['count']
            role = form.cleaned_data['role']
            text = form.cleaned_data['text']
            
            # create definition, default to not published
            defn = Definition(gloss=thisgloss, count=count, role=role, text=text, published=published)
            defn.save()

    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editdef')


def add_morphology_definition(request):

    if request.method == "POST":
        form = GlossMorphologyForm(request.POST)

        if form.is_valid():

            parent_gloss = form.cleaned_data['parent_gloss_id']
            role = form.cleaned_data['role']
            morpheme_id = form.cleaned_data['morpheme_id'] # This is now a gloss ID
            morpheme = Gloss.objects.get(id=morpheme_id)

            thisgloss = get_object_or_404(Gloss, pk=parent_gloss)

            # create definition, default to not published
            morphdef = MorphologyDefinition(parent_gloss=thisgloss, role=role, morpheme=morpheme)
            morphdef.save()

            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

    raise Http404('Incorrect request')

# Add a 'morpheme' (according to the Morpheme model)
def add_morpheme_definition(request, glossid):

    if request.method == "POST":
        form = GlossMorphemeForm(request.POST)

        # Get the glossid at any rate
        thisgloss = get_object_or_404(Gloss, pk=glossid)

        # check availability of morpheme before continuing
        if form.data['morph_id'] == "":
            # The user has not selected a morpheme
            # Check if there are morphemes available for this dataset
            if 'datasetid' in request.session.keys():
                datasetid = request.session['datasetid']
                dataset_id = Dataset.objects.get(name=datasetid)
                count_morphemes_in_dataset = Morpheme.objects.filter(lemma__dataset=dataset_id).count()
                if count_morphemes_in_dataset < 1:
                    messages.add_message(request, messages.INFO, ('Edit Simultaneuous Morphology: The dataset of this gloss has no morphemes.'))
                    return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

            messages.add_message(request, messages.INFO, ('Edit Simultaneuous Morphology: No morpheme selected.'))
            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

        if form.is_valid():

            morph_id = form.cleaned_data['morph_id'] ## This is a morpheme ID now

            try:
                morph = Morpheme.objects.get(id=morph_id)
            except:

                # The user has tryed to type in a name themself rather than select from the list.
                messages.add_message(request, messages.INFO, ('Simultaneuous morphology: no morpheme found with identifier ' + morph_id + '.'))

                return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

            definition = SimultaneousMorphologyDefinition()
            definition.parent_gloss = thisgloss
            definition.morpheme = morph
            definition.role = form.cleaned_data['description']
            definition.save()
            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

    # If we get here the request method has apparently been changed to get instead of post, can this happen?
    raise Http404('Incorrect request')

def add_morphemeappearance(request):

    if request.method == "POST":
        form = GlossMorphologyForm(request.POST)

        if form.is_valid():

            parent_gloss = form.cleaned_data['parent_gloss_id']
            role = form.cleaned_data['role']
            morpheme_id = form.cleaned_data['morpheme_id']
            morpheme = gloss_from_identifier(morpheme_id)

            thisgloss = get_object_or_404(Gloss, pk=parent_gloss)

            # create definition, default to not published
            morphdef = MorphologyDefinition(parent_gloss=thisgloss, role=role, morpheme=morpheme)
            morphdef.save()

            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

    raise Http404('Incorrect request')

# Add a 'blend' (according to the Blend model)
def add_blend_definition(request, glossid):

    if request.method == "POST":
        form = GlossBlendForm(request.POST)

        # Get the glossid at any rate
        thisgloss = get_object_or_404(Gloss, pk=glossid)

        # check availability of morpheme before continuing
        if form.data['blend_id'] == "":
            # The user has obviously not selected a morpheme
            # Desired action (Issue #199): nothing happens
            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

        if form.is_valid():

            blend_id = form.cleaned_data['blend_id'] # This is a gloss ID now
            blend = Gloss.objects.get(id=blend_id)

            if blend != None:
                definition = BlendMorphology()
                definition.parent_gloss = thisgloss
                definition.glosses = blend
                definition.role = form.cleaned_data['role']
                definition.save()

            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': thisgloss.id})+'?editmorphdef')

    raise Http404('Incorrect request')

def update_handshape(request, handshapeid):

    if request.method == "POST":

        hs = get_object_or_404(Handshape, machine_value=handshapeid)
        hs.save() # This updates the lastUpdated field

        field = request.POST.get('id', '')
        value = request.POST.get('value', '')
        original_value = ''
        value = str(value)
        newPattern = ''

        if len(value) == 0:
            value = ' '

        elif value[0] == '_':
            value = value[1:]

        values = request.POST.getlist('value[]')  # in case we need multiple values

        if value == '':
            hs.__setattr__(field, None)
            hs.save()
            newvalue = ''
        else:
            original_value = getattr(hs, field)
            hs.__setattr__(field, value)
            hs.save()
            newvalue = value

            if not isinstance(value, bool):
                field_category = fieldname_to_category(field)
                choice_list = FieldChoice.objects.filter(field__iexact=field_category)
                newvalue = machine_value_to_translated_human_value(value, choice_list, request.LANGUAGE_CODE)

        # Finger selections are saved as both boolean values per finger and as patterns that include the fingers
        # The patterns, such as TIM, are stored as choice lists in FieldChoice.
        # This is done automatically for display and sorting purposes.
        # A user always modifies the selected fingers data per finger.

        if field in ['fsT', 'fsI', 'fsM', 'fsR', 'fsP']:
            category_value = 'fingerSelection1'

            if newvalue != original_value:
                hs_mod = get_object_or_404(Handshape, machine_value=handshapeid)
                newPattern = hs_mod.get_fingerSelection_display()
                object_fingSelection = FieldChoice.objects.filter(field__iexact='FingerSelection', english_name__iexact=newPattern)
                if object_fingSelection:
                    mv = object_fingSelection[0].machine_value
                    hs_mod.__setattr__('hsFingSel', mv)
                    hs_mod.save()
                else:
                    print("finger selection not found: ", newPattern)
        elif field in ['fs2T', 'fs2I', 'fs2M', 'fs2R', 'fs2P']:
            category_value = 'fingerSelection2'

            if newvalue != original_value:
                hs_mod = get_object_or_404(Handshape, machine_value=handshapeid)
                newPattern = hs_mod.get_fingerSelection2_display()
                object_fingSelection = FieldChoice.objects.filter(field__iexact='FingerSelection',
                                                                  english_name__iexact=newPattern)
                if object_fingSelection:
                    mv = object_fingSelection[0].machine_value
                    hs_mod.__setattr__('hsFingSel2', mv)
                    hs_mod.save()
                else:
                    print("finger selection not found: ", newPattern)
        elif field in ['ufT', 'ufI', 'ufM', 'ufR', 'ufP']:
            category_value = 'unselectedFingers'

            if newvalue != original_value:
                hs_mod = get_object_or_404(Handshape, machine_value=handshapeid)
                newPattern = hs_mod.get_unselectedFingers_display()
                object_fingSelection = FieldChoice.objects.filter(field__iexact='FingerSelection',
                                                                  english_name__iexact=newPattern)
                if object_fingSelection:
                    mv = object_fingSelection[0].machine_value
                    hs_mod.__setattr__('hsFingUnsel', mv)
                    hs_mod.save()
        else:
            category_value = 'fieldChoice'

        return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' + str(category_value) + '\t' + str(newPattern), {'content-type': 'text/plain'})

def add_othermedia(request):

    if request.method == "POST":

        form = OtherMediaForm(request.POST,request.FILES)

        if form.is_valid():

            #Create the folder if needed
            goal_directory = OTHER_MEDIA_DIRECTORY+request.POST['gloss'] + '/'
            goal_path = goal_directory + request.FILES['file'].name

            if not os.path.isdir(goal_directory):
                os.mkdir(goal_directory)

            with open(goal_path, 'wb+') as destination:

                #Save the file
                for chunk in request.FILES['file'].chunks():
                        destination.write(chunk)

                #Save the database record
                parent_gloss = Gloss.objects.filter(pk=request.POST['gloss'])[0]
                OtherMedia(path=request.POST['gloss']+'/'+request.FILES['file'].name,alternative_gloss=request.POST['alternative_gloss'],type=request.POST['type'],parent_gloss=parent_gloss).save()

            return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': request.POST['gloss']})+'?editothermedia')

    raise Http404('Incorrect request')

def update_morphology_definition(gloss, field, value, language_code = 'en'):
    """Update one of the relations for this gloss"""

    (what, morph_def_id) = field.split('_')
    what = what.replace('-','_')

    try:
        morph_def = MorphologyDefinition.objects.get(id=morph_def_id)
    except:
        return HttpResponseBadRequest("Bad Morphology Definition ID '%s'" % morph_def_id, {'content-type': 'text/plain'})

    if not morph_def.parent_gloss == gloss:
        return HttpResponseBadRequest("Morphology Definition doesn't match gloss", {'content-type': 'text/plain'})

    if what == 'morphology_definition_delete':
        print("DELETE morphology definition: ", morph_def)
        morph_def.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editmorphdef')
    elif what == 'morphology_definition_role':
        morph_def.role = value
        morph_def.save()

        choice_list = FieldChoice.objects.filter(field__iexact='MorphologyType')
        newvalue = machine_value_to_translated_human_value(value, choice_list, language_code)


    elif what == 'morphology_definition_morpheme':

        morpheme = gloss_from_identifier(value)
        if morpheme:
            morph_def.morpheme = morpheme
            morph_def.save()
            newvalue = str(morpheme)
        else:
            return HttpResponseBadRequest("Badly formed gloss identifier '%s'" % value, {'content-type': 'text/plain'})
    else:

        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})

    return HttpResponse(str(newvalue), {'content-type': 'text/plain'})


def add_morpheme(request):
    """Create a new morpheme and redirect to the edit view"""

    if request.method == "POST":
        dataset = None
        if 'dataset' in request.POST and request.POST['dataset'] is not None:
            dataset = Dataset.objects.get(pk=request.POST['dataset'])
            selected_datasets = Dataset.objects.filter(pk=request.POST['dataset'])
        else:
            selected_datasets = get_selected_datasets_for_user(request.user)
        dataset_languages = Language.objects.filter(dataset__in=selected_datasets).distinct()

        if 'last_used_dataset' in request.session.keys():
            form = MorphemeCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=request.session['last_used_dataset'])
        else:
            form = MorphemeCreateForm(request.POST, languages=dataset_languages, user=request.user, last_used_dataset=None)

        # Check for 'change_dataset' permission
        if dataset and ('change_dataset' not in get_user_perms(request.user, dataset)) \
                and ('change_dataset' not in get_group_perms(request.user, dataset))\
                and not request.user.is_staff:
            messages.add_message(request, messages.ERROR, _("You are not authorized to change the selected dataset."))
            return render(request, 'dictionary/add_morpheme.html', {'add_morpheme_form': form})
        elif not dataset:
            # Dataset is empty, this is an error
            messages.add_message(request, messages.ERROR, _("Please provide a dataset."))
            return render(request, 'dictionary/add_morpheme.html', {'add_morpheme_form': form})

        # if we get to here a dataset has been chosen for the new gloss

        # Lemma handling
        lemmaidgloss = None
        lemma_form = None
        if request.POST['select_or_new_lemma'] == 'new':
            lemma_form = LemmaCreateForm(request.POST, languages=dataset_languages, user=request.user)
        else:
            try:
                lemmaidgloss_id = request.POST['idgloss']
                lemmaidgloss = LemmaIdgloss.objects.get(id=lemmaidgloss_id)
            except:
                messages.add_message(request, messages.ERROR,
                                     _("The given Lemma Idgloss ID is unknown."))
                return render(request, 'dictionary/add_gloss.html', {'add_gloss_form': form})

        # Check for 'change_dataset' permission
        if dataset and ('change_dataset' not in get_user_perms(request.user, dataset)) and ('change_dataset' not in get_group_perms(request.user, dataset)):
            messages.add_message(request, messages.ERROR, _("You are not authorized to change the selected dataset."))
            return render(request, 'dictionary/add_gloss.html', {'add_gloss_form': form})
        elif not dataset:
            # Dataset is empty, this is an error
            messages.add_message(request, messages.ERROR, _("Please provide a dataset."))
            return render(request, 'dictionary/add_gloss.html', {'add_gloss_form': form})


        for item, value in request.POST.items():
            if item.startswith(form.morpheme_create_field_prefix):
                language_code_2char = item[len(form.morpheme_create_field_prefix):]
                language = Language.objects.get(language_code_2char=language_code_2char)
                morphemes_for_this_language_and_annotation_idgloss = Gloss.objects.filter(
                    annotationidglosstranslation__language=language,
                    annotationidglosstranslation__text__exact=value.upper())
                if len(morphemes_for_this_language_and_annotation_idgloss) != 0:
                    return render(request, 'dictionary/warning.html',
                                  {'warning': language.name + " " + 'annotation ID Gloss not unique.'})

        if form.is_valid() and (lemmaidgloss or lemma_form.is_valid()):
            try:
                morpheme = form.save()
                morpheme.creationDate = datetime.now()
                morpheme.creator.add(request.user)
                if lemma_form:
                    lemmaidgloss = lemma_form.save()
                morpheme.lemma = lemmaidgloss
                morpheme.save()
            except ValidationError as ve:
                messages.add_message(request, messages.ERROR, ve.message)
                return render(request, 'dictionary/add_morpheme.html', {'add_morpheme_form': form,
                                                     'dataset_languages': dataset_languages,
                                                     'selected_datasets': get_selected_datasets_for_user(request.user)})

            if not ('search_results' in request.session.keys()):
                request.session['search_results'] = None
            if not ('search_type' in request.session.keys()):
                request.session['search_type'] = None
            request.session['last_used_dataset'] = dataset.name

            return HttpResponseRedirect(reverse('dictionary:admin_morpheme_view', kwargs={'pk': morpheme.id})+'?edit')
        else:
            return render(request,'dictionary/add_morpheme.html', {'add_morpheme_form': form,
                                                                    'dataset_languages': dataset_languages,
                                                                    'selected_datasets': get_selected_datasets_for_user(request.user),
                                                                   'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS})

    return HttpResponseRedirect(reverse('dictionary:admin_morpheme_list'))


def update_morpheme(request, morphemeid):
    """View to update a morpheme model from the jeditable jquery form
    We are sent one field and value at a time, return the new value
    once we've updated it."""

    if not request.user.has_perm('dictionary.change_morpheme'):
        return HttpResponseForbidden("Morpheme Update Not Allowed")

    if request.method == "POST":

        morpheme = get_object_or_404(Morpheme, id=morphemeid)

        field = request.POST.get('id', '')
        value = request.POST.get('value', '')
        original_value = ''  # will in most cases be set later, but can't be empty in case it is not set
        category_value = ''
        lemma_gloss_group = False

        if len(value) == 0:
            value = ' '

        elif value[0] == '_':
            value = value[1:]

        values = request.POST.getlist('value[]')  # in case we need multiple values

        # validate
        # field is a valid field
        # value is a valid value for field

        if field == 'deletemorpheme':
            if value == 'confirmed':
                # delete the morpheme and redirect back to morpheme list
                morpheme.delete()
                return HttpResponseRedirect(reverse('dictionary:admin_morpheme_list'))

        if field.startswith('definition'):

            return update_definition(request, morpheme, field, value)

        elif field.startswith('keywords'):

            return update_keywords(morpheme, field, value)

        elif field.startswith('relationforeign'):

            return update_relationtoforeignsign(morpheme, field, value)

        elif field.startswith('relation'):

            return update_relation(morpheme, field, value)

        elif field.startswith('morphology-definition'):

            return update_morphology_definition(morpheme, field, value, request.LANGUAGE_CODE)

        elif field.startswith('other-media'):

            return update_other_media(request, morpheme, field, value)

        elif field == 'signlanguage':
            # expecting possibly multiple values

            return update_signlanguage(morpheme, field, values)

        elif field == 'dialect':
            # expecting possibly multiple values

            return update_dialect(morpheme, field, values)

        elif field == 'dataset':

            original_value = getattr(morpheme,field)

            # in case somebody tries an empty or non-existent dataset name
            try:
                ds = Dataset.objects.get(name=value)
            except:
                return HttpResponse(str(original_value), {'content-type': 'text/plain'})

            if ds.is_public:
                newvalue = value
                setattr(morpheme, field, ds)
                morpheme.save()

                request.session['last_used_dataset'] = ds.name

                return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

            import guardian
            if ds in guardian.shortcuts.get_objects_for_user(request.user, 'view_dataset', Dataset):
                newvalue = value
                setattr(morpheme, field, ds)
                morpheme.save()

                request.session['last_used_dataset'] = ds.name

                return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

            print('no permission for chosen dataset')
            newvalue = original_value
            return HttpResponse(str(newvalue), {'content-type': 'text/plain'})

        elif field == "sn":
            # sign number must be unique, return error message if this SN is
            # already taken

            if value == '':
                morpheme.__setattr__(field, None)
                morpheme.save()
                newvalue = ''
            else:
                try:
                    value = int(value)
                except:
                    return HttpResponseBadRequest("SN value must be integer", {'content-type': 'text/plain'})

                existing_morpheme = Morpheme.objects.filter(sn__exact=value)
                if existing_morpheme.count() > 0:
                    g = existing_morpheme[0].idgloss
                    return HttpResponseBadRequest("SN value already taken for morpheme %s" % g,
                                                  {'content-type': 'text/plain'})
                else:
                    morpheme.sn = value
                    morpheme.save()
                    newvalue = value


        elif field == 'inWeb':
            # only modify if we have publish permission
            if request.user.has_perm('dictionary.can_publish'):
                morpheme.inWeb = (value == 'Yes')
                morpheme.save()

            if morpheme.inWeb:
                newvalue = 'Yes'
            else:
                newvalue = 'No'

        elif field.startswith('annotation_idgloss'):

            return update_annotation_idgloss(morpheme, field, value)

        elif field.startswith('lemmaidgloss'):
            # Set new lemmaidgloss for this gloss
            # First check whether the morpheme dataset is the same as the lemma dataset
            try:
                dataset = morpheme.dataset
                lemma = LemmaIdgloss.objects.get(pk=value)
                if dataset == lemma.dataset:
                    old_video_path = settings.MEDIA_ROOT + morpheme.get_video_path()
                    morpheme.lemma = lemma
                    morpheme.save()
                    new_video_path = settings.MEDIA_ROOT + morpheme.get_video_path()

                    # Rename video
                    morpheme.rename_video(old_video_path, new_video_path)
                else:
                    messages.add_message(messages.ERROR, _("The dataset of the morpheme is not the same as that of the lemma."))
            except ObjectDoesNotExist:
                messages.add_message(messages.ERROR, _("The specified lemma does not exist."))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        else:

            if not field in [f.name for f in Morpheme._meta.get_fields()]:
                return HttpResponseBadRequest("Unknown field", {'content-type': 'text/plain'})

            whitespace = tuple(' \n\r\t')
            if value.startswith(whitespace) or value.endswith(whitespace):
                value = value.strip()
            original_value = getattr(morpheme,field)

            if field == 'idgloss' and value == '':
                # don't allow user to set Lemma ID Gloss to empty
                return HttpResponse(str(original_value), {'content-type': 'text/plain'})
            # special cases
            # - Foreign Key fields (Language, Dialect)
            # - keywords
            # - videos
            # - tags

            # Translate the value if a boolean
            if isinstance(morpheme._meta.get_field(field), NullBooleanField):
                newvalue = value
                value = (value == 'Yes')

            # special value of 'notset' or -1 means remove the value
            fieldnames = FIELDS['main'] + FIELDS['phonology'] + FIELDS['semantics'] + ['inWeb', 'isNew']

            char_fields_not_null = [f.name for f in Morpheme._meta.fields
                                    if f.name in fieldnames and f.__class__.__name__ == 'CharField' and not f.null]

            if (value == 'notset' or value == -1 or value == '') and field not in char_fields_not_null:
                morpheme.__setattr__(field, None)
                morpheme.save()
                newvalue = ''

            # Regular field updating
            else:

                # Remember the old video path if you're changing the name
                if field == 'idgloss':
                    old_video_path = morpheme.get_video_path()

                morpheme.__setattr__(field, value)
                morpheme.save()

                # Update the video location if you're changing the name
                if field == 'idgloss':
                    new_video_path = morpheme.get_video_path()

                    try:
                        shutil.move(settings.MEDIA_ROOT + '/' + old_video_path,
                                    settings.MEDIA_ROOT + '/' + new_video_path)

                    # You don't have to do this if there's no video
                    except IOError:
                        pass

                # If the value is not a Boolean, return the new value
                if not isinstance(value, bool):
                    field_category = fieldname_to_category(field)
                    choice_list = FieldChoice.objects.filter(field__iexact=field_category)
                    newvalue = machine_value_to_translated_human_value(value, choice_list, request.LANGUAGE_CODE)
                    category_value = 'phonology'

        return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' + str(value) + str('\t') + str(category_value) + str('\t') + str(lemma_gloss_group), {'content-type': 'text/plain'})


def update_morpheme_definition(gloss, field, value):
    """Update the morpheme definition for this gloss"""

    newvalue = value
    original_value = ''
    category_value = 'simultaneous_morphology'
    (what, morph_def_id) = field.split('_')
    what = what.replace('-','_')

    if what == 'morpheme_definition_delete':
        definition = SimultaneousMorphologyDefinition.objects.get(id=morph_def_id)
        definition.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editmorphdef')
    elif what == 'morpheme_definition_meaning':
        definition = SimultaneousMorphologyDefinition.objects.get(id=morph_def_id)
        original_value = getattr(definition, 'role')
        definition.__setattr__('role', value)
        definition.save()
        return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' +  str(value) + str('\t') + str(category_value), {'content-type': 'text/plain'})
    else:
        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})


def update_blend_definition(gloss, field, value):
    """Update the morpheme definition for this gloss"""

    newvalue = value
    original_value = ''
    category_value = 'blend_morphology'
    (what, blend_id) = field.split('_')
    what = what.replace('-','_')

    if what == 'blend_definition_delete':
        definition = BlendMorphology.objects.get(id=blend_id)
        definition.delete()
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': gloss.id})+'?editmorphdef')
    elif what == 'blend_definition_role':
        definition = BlendMorphology.objects.get(id=blend_id)
        original_value = getattr(definition, 'role')
        definition.__setattr__('role', value)
        definition.save()
        return HttpResponse(str(original_value) + '\t' + str(newvalue) + '\t' +  str(value) + str('\t') + str(category_value), {'content-type': 'text/plain'})
    else:
        return HttpResponseBadRequest("Unknown form field '%s'" % field, {'content-type': 'text/plain'})


@permission_required('dictionary.change_gloss')
def add_tag(request, glossid):
    """View to add a tag to a gloss"""

    # default response
    response = HttpResponse('invalid', {'content-type': 'text/plain'})

    if request.method == "POST":
        thisgloss = get_object_or_404(Gloss, id=glossid)

        form = TagUpdateForm(request.POST)
        if form.is_valid():

            tag = form.cleaned_data['tag']

            if form.cleaned_data['delete']:
                # get the relevant TaggedItem
                ti = get_object_or_404(TaggedItem, object_id=thisgloss.id, tag__name=tag)
                ti.delete()
                response = HttpResponse('deleted', {'content-type': 'text/plain'})
            else:
                # we need to wrap the tag name in quotes since it might contain spaces
                Tag.objects.add_tag(thisgloss, '"%s"' % tag)
                # response is new HTML for the tag list and form
                response = render(request,'dictionary/glosstags.html',
                                              {'gloss': thisgloss,
                                               'tagform': TagUpdateForm()})
        else:
            print("invalid form")
            print(form.as_table())
            
    return response


def add_morphemetag(request, morphemeid):
    """View to add a tag to a morpheme"""

    # default response
    response = HttpResponse('invalid', {'content-type': 'text/plain'})

    if request.method == "POST":
        thismorpheme= get_object_or_404(Morpheme, id=morphemeid)

        form = TagUpdateForm(request.POST)
        if form.is_valid():

            tag = form.cleaned_data['tag']

            if form.cleaned_data['delete']:
                # get the relevant TaggedItem
                ti = get_object_or_404(TaggedItem, object_id=thismorpheme.id, tag__name=tag)
                ti.delete()
                response = HttpResponse('deleted', {'content-type': 'text/plain'})
            else:
                # we need to wrap the tag name in quotes since it might contain spaces
                Tag.objects.add_morphemetag(thismorpheme, '"%s"' % tag)
                # response is new HTML for the tag list and form
                response = render(request,'dictionary/morphemetags.html',
                                              {'morpheme': thismorpheme,
                                               'tagform': TagUpdateForm()})
        else:
            print("invalid form")
            print(form.as_table())

    return response

def change_dataset_selection(request):
    """View to change dataset selection"""
    dataset_prefix = 'dataset_'

    if request.method == "POST":
        user = request.user
        user_profile = UserProfile.objects.get(user=user)

        user_profile.selected_datasets.clear()
        selected_datasets = []
        for attribute in request.POST:
            if attribute[:len(dataset_prefix)] == dataset_prefix:
                dataset_name = attribute[len(dataset_prefix):]
                selected_datasets.append(dataset_name)

        if selected_datasets:
            user_profile = UserProfile.objects.get(user=user)
            for dataset_name in selected_datasets:
                try:
                    dataset = Dataset.objects.get(name=dataset_name)
                    user_profile.selected_datasets.add(dataset)
                except:
                    print('exception to updating selected datasets')
                    pass
            user_profile.save()

        # check whether the last used dataset is still in the selected datasets
        if 'last_used_dataset' in request.session.keys():
            if not (request.session['last_used_dataset'] in selected_datasets):
                request.session['last_used_dataset'] = None
        else:
            # set the last_used_dataset?
            pass
    return HttpResponseRedirect(reverse('admin_dataset_select'))

def update_dataset(request, datasetid):
    """View to update a dataset model from the jeditable jquery form
    We are sent one field and value at a time, return the new value
    once we've updated it."""

    if request.method == "POST":

        dataset = get_object_or_404(Dataset, id=datasetid)
        dataset.save() # This updates the lastUpdated field

        import guardian
        user_change_datasets = guardian.shortcuts.get_objects_for_user(request.user, 'change_dataset', Dataset, accept_global_perms=False)
        if not dataset in user_change_datasets:
            return HttpResponseForbidden("Dataset Update Not Allowed")

        field = request.POST.get('id', '')
        value = request.POST.get('value', '')
        original_value = ''

        if field == 'description':
            original_value = getattr(dataset,field)
            setattr(dataset, field, value)
            dataset.save()
            return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'copyright':
                original_value = getattr(dataset, field)
                setattr(dataset, field, value)
                dataset.save()
                return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'reference':
                original_value = getattr(dataset, field)
                setattr(dataset, field, value)
                dataset.save()
                return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'conditions_of_use':
                original_value = getattr(dataset, field)
                setattr(dataset, field, value)
                dataset.save()
                return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'acronym':
                original_value = getattr(dataset, field)
                setattr(dataset, field, value)
                dataset.save()
                return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        elif field == 'is_public':
                original_value = getattr(dataset, field)
                dataset.is_public = value == 'True'
                dataset.save()
                if dataset.is_public:
                    newvalue = True
                else:
                    newvalue = False
                return HttpResponse(str(original_value) + str('\t') + str(newvalue), {'content-type': 'text/plain'})
        elif field == 'add_owner':
            update_owner(dataset, field, value)
        elif field == 'default_language':
            original_value = getattr(dataset, field)
            # variable original_value is used for feedback to the interface
            if original_value:
                original_value = original_value.name
            else:
                original_value = '-'
            if value == '-':
                # this option is not offered by the interface, value must be one of the translation languages (not empty '-')
                # this code is here if we want to user to be able to "unset" the default language in the interface
                setattr(dataset, field, None)
                dataset.save()
            else:
                try:
                    new_default_language = Language.objects.get(name=value)
                    setattr(dataset, field, new_default_language)
                    dataset.save()
                except:
                    value = original_value
            return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})
        else:

            if not field in [f.name for f in Dataset._meta.get_fields()]:
                return HttpResponseBadRequest("Unknown field", {'content-type': 'text/plain'})

            # unknown if we need this code yet for the above fields
            whitespace = tuple(' \n\r\t')
            if value.startswith(whitespace) or value.endswith(whitespace):
                value = value.strip()
            original_value = getattr(dataset,field)

        #This is because you cannot concat none to a string in py3
        if original_value == None:
            original_value = ''

        # The machine_value (value) representation is also returned to accommodate Hyperlinks to Handshapes in gloss_edit.js
        return HttpResponse(str(original_value) + str('\t') + str(value), {'content-type': 'text/plain'})

    else:
        print('update dataset is not POST')

def update_owner(dataset, field, values):
    # expecting possibly multiple values

    # The owners value is set to the current owners value
    owners_value = ", ".join([str(o.username) for o in dataset.owners.all()])
    current_owners = dataset.owners.all()
    current_owners_name = ''
    for co in current_owners:
        current_owners_name = co.name

    try:
        # dataset.owners.clear()
        for value in values:
            user = User.objects.get(username=value)
            # dataset.owners.add(user)
            print('add owner ', value, ' to dataset')
            if value != current_owners_name:
                print('clear owners field')
                # dataset.owners.clear()
                # Has a side effect that the Dialects value is cleared, this will be passed back to the user interface
                owners_value = ''
        # dataset.save()
        print('save dataset')
        new_owners_value = ", ".join([str(o.username) for o in dataset.owners.all()])
    except:
        return HttpResponseBadRequest("Unknown Language %s" % values, {'content-type': 'text/plain'})

    return HttpResponse(str(new_owners_value) + '\t' + str(owners_value), {'content-type': 'text/plain'})

def update_excluded_choices(request):

    #We start with the assumption that everything is excluded
    excluded_choices = {dataset.name: [field_choice.pk for field_choice in FieldChoice.objects.all()] for dataset in Dataset.objects.all()}

    #And then remove from this list everything which was checked
    for key in request.POST.keys():

        if key == 'csrfmiddlewaretoken':
            continue

        dataset, choice_pk = key.split('|')
        choice_pk = int(choice_pk)

        excluded_choices[dataset].remove(choice_pk)

    #Now update all datasets
    for dataset_name, choice_pks in excluded_choices.items():

        dataset = Dataset.objects.get(name=dataset_name)
        dataset.exclude_choices = [FieldChoice.objects.get(pk=choice_pk) for choice_pk in choice_pks]
        dataset.save()

    return HttpResponseRedirect(reverse('admin_dataset_field_choices'))