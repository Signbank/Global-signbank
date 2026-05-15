
from django.http import JsonResponse

from signbank.dictionary.models import FieldChoice, Gloss, Handshape, SemanticField


# def handshape_ajax_complete(request, prefix):
#     qs = Handshape.objects.filter(name__istartswith=prefix)
#
#     result = []
#     for g in qs:
#         result.append({'name': g.name, 'machine_value': g.machine_value})
#
#     return JsonResponse(result, safe=False)


def handedness_ajax_complete(request, prefix):
    """Return a list of field choices matching the search term"""
    qs = FieldChoice.objects.filter(field='Handedness', name__istartswith=prefix)

    result = []
    for f in qs:
        result.append({'name': f.name, 'machine_value': f.machine_value})

    return JsonResponse(result, safe=False)


def semField_ajax_complete(request, prefix):
    """Return a list of field choices matching the search term"""
    qs = SemanticField.objects.filter(name__istartswith=prefix)

    result = []
    for f in qs:
        result.append({'name': f.name, 'machine_value': f.machine_value})

    return JsonResponse(result, safe=False)

