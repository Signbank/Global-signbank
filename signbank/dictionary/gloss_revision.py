
from signbank.dictionary.models import Gloss, GlossRevision
import datetime as DT
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect
from signbank.dictionary.update import okay_to_update_gloss
from django.urls import reverse
from django.conf import settings


@permission_required('dictionary.change_gloss')
def cleanup(request, glossid):

    gloss = Gloss.objects.filter(id=glossid, archived=False).first()

    if not okay_to_update_gloss(request, gloss):
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    success_url = '/dictionary/gloss/' + glossid + '/history'

    revisions = GlossRevision.objects.filter(gloss=gloss).order_by('time')

    empty_revisions = []
    duplicate_revisions = dict()
    tuple_updates = []
    tuple_update_already_seen = []
    for revision in revisions:
        if revision.old_value in ['', '-'] and revision.new_value in ['', '-']:
            empty_revisions.append(revision)
        elif revision.old_value == revision.new_value:
            if revision.field_name not in duplicate_revisions.keys():
                # this is the first time the duplicate occurs
                duplicate_revisions[revision.field_name] = []
            else:
                # we have already seen this duplicate, schedule to delete
                duplicate_revisions[revision.field_name].append(revision)
        else:
            if not tuple_updates:
                tuple_updates.append((revision.field_name, revision.old_value, revision.new_value))
            else:
                (last_field, last_old_value, last_new_value) = tuple_updates[-1]
                if last_field == revision.field_name and last_old_value == revision.old_value and last_new_value == revision.new_value:
                    tuple_update_already_seen.append(revision)
                else:
                    tuple_updates.append((revision.field_name, revision.old_value, revision.new_value))
    for empty_revision in empty_revisions:
        empty_revision.delete()

    for field_name, duplicates in duplicate_revisions.items():
        for duplicate in duplicates:
            duplicate.delete()

    for already_seen in tuple_update_already_seen:
        already_seen.delete()

    # because this method updates the database, return such that the template will be redrawn
    return HttpResponseRedirect(settings.PREFIX_URL + success_url)

