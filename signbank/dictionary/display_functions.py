from django.db.models import ForeignKey

from signbank.settings.server_specific import FIELDS

from signbank.dictionary.models import FieldChoiceForeignKey, Gloss, Handshape

def show_fields_rows(gloss):
    show_field = {}
    for field in FIELDS['phonology'] + ['domhndsh_letter_or_number', 'subhndsh_letter_or_number', 'semField', 'derivHist']:
        if field in ['semField']:
            semantic_fields = gloss.semField.all()
            show_field[field] = [semantic_fields.count() > 0]
            continue
        if field in ['derivHist']:
            derivation_history_fields = gloss.derivHist.all()
            show_field[field] = [derivation_history_fields.count() > 0]
            continue
        if field in ['domhndsh_letter_or_number']:
            letter_value = getattr(gloss, 'domhndsh_letter')
            number_value = getattr(gloss, 'domhndsh_number')
            show_field[field] = [not letter_value and not number_value]
            continue
        if field in ['subhndsh_letter_or_number']:
            letter_value = getattr(gloss, 'subhndsh_letter')
            number_value = getattr(gloss, 'subhndsh_number')
            show_field[field] = [not letter_value and not number_value]
            continue
        field_value = getattr(gloss, field)
        if field_value is None or field_value in ['', 0, '-']:
            show_field[field] = [False]
            continue
        internal_field = Gloss.get_field(field)
        if isinstance(internal_field, FieldChoiceForeignKey):
            show_field[field] = [field_value.machine_value not in [0]]
            continue
        if isinstance(internal_field, ForeignKey) and internal_field.related_model == Handshape:
            show_field[field] = [field_value.machine_value not in [0]]
            continue
        if field in ['weakdrop', 'weakprop']:
            show_field[field] = [field_value not in [None]]
            continue
        show_field[field] = [field_value not in [None, 0, '-', '', False]]
    show_field_row = {}
    for field in FIELDS['phonology'] + ['domhndsh_letter_or_number', 'subhndsh_letter_or_number', 'semField', 'derivHist']:
        show_field_row[field] = any(show_field[field])
    return show_field_row
