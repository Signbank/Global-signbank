
from signbank.dictionary.models import *
from tagging.models import Tag, TaggedItem
from signbank.dictionary.forms import *
from django.utils.translation import override, gettext_lazy as _, activate
from signbank.settings.server_specific import LANGUAGES, LEFT_DOUBLE_QUOTE_PATTERNS, RIGHT_DOUBLE_QUOTE_PATTERNS

from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import permission_required
from django.db import DatabaseError, IntegrityError
from django.db.transaction import TransactionManagementError

from tagging.models import TaggedItem, Tag
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse


def get_gloss_data_json(request, datasetid, glossid):

    try:
        dataset_id = int(datasetid)
    except TypeError:
        return JsonResponse({})

    dataset = Dataset.objects.filter(id=dataset_id).first()
    if not dataset or not request.user.is_authenticated:
        # ignore the database in the url if necessary
        dataset = Dataset.objects.get(id=settings.DEFAULT_DATASET_PK)

    try:
        gloss_id = int(glossid)
    except TypeError:
        return JsonResponse({})

    gloss = Gloss.objects.filter(lemma__dataset=dataset, id=gloss_id).first()

    if not gloss:
        return JsonResponse({})

    # settings.API_FIELDS
    api_fields_2023 = []
    if not dataset:
        dataset = Dataset.objects.get(acronym=settings.DEFAULT_DATASET_ACRONYM)
    for language in dataset.translation_languages.all():
        language_field = _("Annotation ID Gloss") + ": %s" % language.name
        api_fields_2023.append(language_field)
    for language in dataset.translation_languages.all():
        language_field = _("Senses") + ": %s" % language.name
        api_fields_2023.append(language_field)
    api_fields_2023.append("Handedness")
    api_fields_2023.append("Strong Hand")
    api_fields_2023.append("Weak Hand")
    api_fields_2023.append("Location")
    api_fields_2023.append("Semantic Field")
    api_fields_2023.append("Link")

    gloss_fields = [Gloss.get_field(fname) for fname in Gloss.get_field_names()]
    verbose_field_names = []
    if request.user.has_perm('dictionary.change_gloss'):
        # show advanced properties
        for field in gloss_fields:
            verbose_field_names.append(field.verbose_name.title())
    for advanced_property in verbose_field_names:
        api_fields_2023.append(advanced_property)

    gloss_data = dict()
    gloss_data[str(gloss.pk)] = gloss.get_fields_dict(api_fields_2023)

    return JsonResponse(gloss_data)
