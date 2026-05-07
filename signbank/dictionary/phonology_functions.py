

from signbank.settings.server_specific import FIELDS

from signbank.dictionary.models import FieldChoiceForeignKey, PhonologicalVariation

def show_fields_rows(gloss):
    show_field = {}
    for field in FIELDS['phonology']:
        field_value = getattr(gloss, field)
        if field_value is None or field_value in ['', 0, '-']:
            show_field[field] = [False]
            continue
        internal_field = PhonologicalVariation.get_field(field)
        if isinstance(internal_field, FieldChoiceForeignKey):
            show_field[field] = [field_value.machine_value not in [0]]
            continue
        if field in ['weakdrop', 'weakprop']:
            show_field[field] = [field_value not in [None]]
            continue
        show_field[field] = [field_value not in [None, 0, '-', '', False]]
    for gv in PhonologicalVariation.objects.filter(gloss=gloss).order_by('variation'):
        for field in FIELDS['phonology']:
            field_value = getattr(gv, field)
            if field_value is None or field_value in ['', 0, '-']:
                show_field[field].append(False)
                continue
            internal_field = PhonologicalVariation.get_field(field)
            if isinstance(internal_field, FieldChoiceForeignKey):
                show_field[field].append(field_value.machine_value not in [0])
                continue
            if field in ['weakdrop', 'weakprop']:
                show_field[field].append(field_value not in [None])
                continue
            show_field[field].append(field_value not in [None, 0, '-', '', False])
    show_field_row = {}
    for field in FIELDS['phonology']:
        show_field_row[field] = any(show_field[field])
    return show_field_row
