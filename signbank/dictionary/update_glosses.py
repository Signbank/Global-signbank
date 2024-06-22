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
def mapping_toggle_tag(request, glossid, tagid):

    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    try:
        gloss_id = int(glossid)
    except TypeError:
        return {}

    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        return {}

    try:
        tag_id = int(tagid)
    except TypeError:
        return {}

    try:
        new_tag = Tag.objects.get(id=tag_id)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return {}

    current_tags = [tagged_item.tag_id for tagged_item in TaggedItem.objects.filter(object_id=gloss.id)]

    with atomic():
        new_tag_name = new_tag.name.replace(' ', '_')
        if new_tag.id not in current_tags:
            # do not store spaces in tag name
            # the add_tag method of class Tag is inside a package
            # it creates a new tag if it does not exist
            # the second argument is a string that is the tag name
            # make sure we keep using underscores on tag names to avoid creating new names with spaces instead
            Tag.objects.add_tag(gloss, new_tag_name)
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

    try:
        gloss_id = int(glossid)
    except TypeError:
        return {}

    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        return {}

    try:
        semanticfield_machine_value = int(semanticfield)
    except TypeError:
        return {}

    semanticfield = SemanticField.objects.filter(machine_value=semanticfield_machine_value).first()

    if not semanticfield:
        return {}

    current_semanticfields = [semfield.machine_value for semfield in gloss.semField.all()]

    with atomic():
        if semanticfield.machine_value not in current_semanticfields:
            gloss.semField.add(semanticfield)
        else:
            gloss.semField.remove(semanticfield)

    updated_semanticfields = [semfield.name for semfield in gloss.semField.all()]

    result = dict()
    result['glossid'] = str(gloss.id)
    result['semantic_fields_list'] = updated_semanticfields

    return result


@permission_required('dictionary.change_gloss')
def mapping_toggle_wordclass(request, glossid, wordclass):

    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    try:
        gloss_id = int(glossid)
    except TypeError:
        return {}

    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        return {}

    try:
        wordclass_machine_value = int(wordclass)
    except TypeError:
        return {}

    empty_wordclass = FieldChoice.objects.get(field='WordClass', machine_value=0)
    new_wordclass = FieldChoice.objects.filter(field='WordClass', machine_value=wordclass_machine_value).first()

    if not new_wordclass:
        # if the word class does not exist, set it to empty
        wordclass_machine_value = 0
        new_wordclass = empty_wordclass

    with atomic():
        if not gloss.wordClass:
            gloss.wordClass = new_wordclass
        elif gloss.wordClass.machine_value != wordclass_machine_value:
            gloss.wordClass = new_wordclass
        else:
            gloss.wordClass = empty_wordclass
        gloss.save()

    result = dict()
    result['glossid'] = str(gloss.id)
    newvalue = gloss.wordClass.name
    result['wordclass'] = newvalue

    return result


@permission_required('dictionary.change_gloss')
def mapping_toggle_namedentity(request, glossid, namedentity):

    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    try:
        gloss_id = int(glossid)
    except TypeError:
        return {}

    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        return {}

    try:
        namedentity_machine_value = int(namedentity)
    except TypeError:
        return {}

    empty_namedentity = FieldChoice.objects.get(field='NamedEntity', machine_value=0)
    new_namedentity = FieldChoice.objects.filter(field='NamedEntity', machine_value=namedentity_machine_value).first()

    if not new_namedentity:
        # if the word class does not exist, set it to empty
        namedentity_machine_value = 0
        new_namedentity = empty_namedentity

    with atomic():
        if not gloss.namEnt:
            gloss.namEnt = new_namedentity
        elif gloss.namEnt.machine_value != namedentity_machine_value:
            gloss.namEnt = new_namedentity
        else:
            gloss.namEnt = empty_namedentity
        gloss.save()

    result = dict()
    result['glossid'] = str(gloss.id)
    newvalue = gloss.namEnt.name
    result['namedentity'] = newvalue

    return result


@permission_required('dictionary.change_gloss')
def mapping_toggle_handedness(request, glossid, handedness):
    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    try:
        gloss_id = int(glossid)
    except TypeError:
        return {}

    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        return {}

    try:
        handedness_machine_value = int(handedness)
    except TypeError:
        return {}

    empty_handedness = FieldChoice.objects.get(field='Handedness', machine_value=0)
    new_handedness = FieldChoice.objects.filter(field='Handedness', machine_value=handedness_machine_value).first()

    if not new_handedness:
        # if the word class does not exist, set it to empty
        handedness_machine_value = 0
        new_handedness = empty_handedness

    with atomic():
        if not gloss.handedness:
            gloss.handedness = new_handedness
        elif gloss.handedness.machine_value != handedness_machine_value:
            gloss.handedness = new_handedness
        else:
            gloss.handedness = empty_handedness
        gloss.save()

    result = dict()
    result['glossid'] = str(gloss.id)
    newvalue = gloss.handedness.name
    result['handedness'] = newvalue

    return result


@permission_required('dictionary.change_gloss')
def mapping_toggle_domhndsh(request, glossid, domhndsh):
    if not request.user.is_authenticated:
        return {}

    if not request.user.has_perm('dictionary.change_gloss'):
        return {}

    try:
        gloss_id = int(glossid)
    except TypeError:
        return {}

    gloss = Gloss.objects.filter(id=gloss_id).first()

    if not gloss:
        return {}

    try:
        domhndsh_machine_value = int(domhndsh)
    except TypeError:
        return {}

    empty_domhndsh = Handshape.objects.get(machine_value=0)
    new_domhndsh = Handshape.objects.filter(machine_value=domhndsh_machine_value).first()

    if not new_domhndsh:
        # if the word class does not exist, set it to empty
        domhndsh_machine_value = 0
        new_domhndsh = empty_domhndsh

    with atomic():
        if not gloss.domhndsh:
            gloss.domhndsh = new_domhndsh
        elif gloss.domhndsh.machine_value != domhndsh_machine_value:
            gloss.domhndsh = new_domhndsh
        else:
            gloss.domhndsh = empty_domhndsh
        gloss.save()

    result = dict()
    result['glossid'] = str(gloss.id)
    newvalue = gloss.domhndsh.name
    result['domhndsh'] = newvalue

    return result

