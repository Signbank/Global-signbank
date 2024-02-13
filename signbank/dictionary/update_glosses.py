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

    # new_tag_get = request.POST.get('new_tag')
    # new_translation_list = json.loads(new_tag_get) if new_tag_get else []
    # new_tag_names = [s.strip().replace(' ', '_') for s in new_translation_list]

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


