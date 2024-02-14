from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import permission_required
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag

from signbank.dictionary.models import *
from signbank.dictionary.forms import *

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse


@permission_required('dictionary.change_gloss')
def mapping_toggle_tag(request, glossid, tagname):

    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    gloss = get_object_or_404(Gloss, id=glossid)

    current_tags = [tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    change_tag = Tag.objects.get_or_create(name=tagname)
    (new_tag, created) = change_tag

    if new_tag.id not in current_tags:
        Tag.objects.add_tag(gloss, tagname)
    else:
        # delete tag from object
        tagged_obj = TaggedItem.objects.get(object_id=gloss.id, tag_id=new_tag.id)
        tagged_obj.delete()

    new_tag_ids = [tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    result = dict()
    result['glossid'] = str(gloss.id)
    newvalue = [tag.name.replace('_', ' ') for tag in Tag.objects.filter(id__in=new_tag_ids)]
    result['tags_list'] = newvalue

    return result


@permission_required('dictionary.change_gloss')
def mapping_toggle_semanticfield(request, glossid, semanticfield):

    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    gloss = get_object_or_404(Gloss, id=glossid)

    current_semanticfields = [semfield.machine_value for semfield in gloss.semField.all()]

    semanticfield = SemanticField.objects.get_or_create(name=semanticfield)
    (new_semanticfield, created) = semanticfield

    if new_semanticfield.machine_value not in current_semanticfields:
        gloss.semField.add(new_semanticfield)
    else:
        # delete semantic field from gloss
        gloss.semField.remove(new_semanticfield)

    updated_semanticfields = [semfield.machine_value for semfield in gloss.semField.all()]

    result = dict()
    result['glossid'] = str(gloss.id)
    newvalue = [semfield.name for semfield in SemanticField.objects.filter(machine_value__in=updated_semanticfields)]
    result['semantic_fields_list'] = newvalue

    return result


@permission_required('dictionary.change_gloss')
def mapping_toggle_wordclass(request, glossid, wordclass):

    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    gloss = get_object_or_404(Gloss, id=glossid)

    new_wordclass = FieldChoice.objects.filter(field='WordClass', name=wordclass).first()

    if not new_wordclass:
        # if the word class does not exist, set it to empty
        new_wordclass = FieldChoice.objects.get(field='WordClass', machine_value=0)

    gloss.wordClass = new_wordclass

    result = dict()
    result['glossid'] = str(gloss.id)
    newvalue = new_wordclass.name
    result['wordclass'] = newvalue

    return result
