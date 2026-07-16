
from django.utils.translation import gettext_noop, gettext_lazy as _, gettext, activate

from signbank.settings.server_specific import FIELDS

from signbank.dictionary.models import FieldChoiceForeignKey, PhonologicalVariation, Phonology, Gloss, FieldChoice, Handshape

def display_phonology_matrix(matrix):
    display_matrix = {}
    for field in matrix.keys():
        gloss_field = Gloss._meta.get_field(field)
        field_label = gettext_noop(gloss_field.verbose_name)
        display_matrix[field_label] = {}
        if hasattr(gloss_field, 'field_choice_category'):
            for variation_num in matrix[field]:
                field_value = matrix[field][variation_num]
                if field_value is not None:
                    field_value_display = FieldChoice.objects.get(id=int(field_value)).name
                else:
                    field_value_display = '-'
                display_matrix[field_label][variation_num] = field_value_display
        elif field in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
            for variation_num in matrix[field]:
                field_value = matrix[field][variation_num]
                if field_value is not None:
                    field_value_display = Handshape.objects.get(machine_value=int(field_value)).name
                else:
                    field_value_display = '-'
                display_matrix[field_label][variation_num] = field_value_display
        else:
            for variation_num in matrix[field]:
                field_value = matrix[field][variation_num]
                display_matrix[field_label][variation_num] = field_value
    return display_matrix


def phonological_variations_matrix(gloss):
    gloss_phonology = gloss.phonology_matrix(use_machine_value=False)
    phonology_variations = PhonologicalVariation.objects.filter(gloss=gloss).order_by('variation')
    variations = {}
    for variation in phonology_variations:
        variations[variation.variation] = variation.phonology_matrix(use_machine_value=False)
    for field in FIELDS['phonology']:
        if field in gloss_phonology.keys():
            continue
        gloss_phonology[field] = getattr(gloss, field)
        for variation in phonology_variations:
            variations[variation.variation][field] = getattr(variation, field)
    phonology_differences = {}
    for field in FIELDS['phonology']:
        primary_value = gloss_phonology[field]
        for variation in variations.keys():
            if variations[variation][field] == primary_value:
                continue
            if field not in phonology_differences.keys():
                phonology_differences[field] = {}
    for field in phonology_differences.keys():
        for variation_num in variations.keys():
            phonology_differences[field][1] = gloss_phonology[field]
            phonology_differences[field][variation_num] = variations[variation_num][field]

    return phonology_differences
