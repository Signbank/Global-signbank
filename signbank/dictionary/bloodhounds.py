
from django.http import JsonResponse

from signbank.dictionary.models import (FieldChoice, Gloss, Handshape,
                                        Dialect, SemanticField, DerivationHistory)


def handedness_ajax_complete(request, prefix):
    """Return a list of handedness choices matching the search term"""
    qs = FieldChoice.objects.filter(field='Handedness', name__istartswith=prefix)

    result = []
    for f in qs:
        result.append({'name': f.name, 'machine_value': f.machine_value})

    return JsonResponse(result, safe=False)


def semField_ajax_complete(request, prefix):
    """Return a list of semantic field choices matching the search term"""
    qs = SemanticField.objects.filter(name__istartswith=prefix)

    result = []
    for f in qs:
        result.append({'name': f.name, 'machine_value': f.machine_value})

    return JsonResponse(result, safe=False)


def fieldchoice_ajax_complete(request, field, prefix):
    """Return a list of field choices matching the search term"""
    qs = FieldChoice.objects.filter(field=field, name__istartswith=prefix)

    result = []
    for f in qs:
        result.append({'name': f.name, 'machine_value': f.machine_value})

    return JsonResponse(result, safe=False)


def derivHist_ajax_complete(request, prefix):
    """Return a list of derivation history choices matching the search term"""
    qs = DerivationHistory.objects.filter(name__istartswith=prefix)

    result = []
    for f in qs:
        result.append({'name': f.name, 'machine_value': f.machine_value})

    return JsonResponse(result, safe=False)

def dialect_ajax_complete(request, datasetid, prefix):
    """Return a list of derivation history choices matching the search term"""
    qs = Dialect.objects.filter(signlanguage__dataset__id=datasetid)
    qs = qs.filter(name__istartswith=prefix)

    result = []
    for f in qs:
        result.append({'name': f'{f.signlanguage.name}/{f.name}', 'machine_value': f.pk})

    return JsonResponse(result, safe=False)
