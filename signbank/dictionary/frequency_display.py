
import json
from signbank.dictionary.models import *

from signbank.settings.server_specific import *

def collect_speaker_age_data(speakers_summary):
    # the following collects the speakers distributed over a range of ages to display on the x axis
    # for display in chartjs, the age labels are stored separately from the number of speakers having that age
    # ages to display data for across the x axis
    age_range_labels = []
    speaker_age_data = []
    for i in range(0, 100):
        # the age is a string for javascript
        i_key = str(i)
        if i_key in speakers_summary.keys():
            # some speakers have this age
            # tet the number of speakers with this age
            i_value = speakers_summary[i_key]
            speaker_age_data.append(i_value)
            age_range_labels.append(i_key)
        else:
            # no speakers have this age
            # only show labels for ages that have speakers of that age
            speaker_age_data.append(0)

    return (age_range_labels, speaker_age_data)


def collect_variants_data(variants):
    variants_with_keys = []
    if len(variants) > 1:
        for v in variants:
            # get the annotation explicitly
            # do not use the __str__ property idgloss
            v_idgloss = v.annotationidglosstranslation_set.get(language=v.lemma.dataset.default_language).text
            variants_with_keys.append((v_idgloss, v))
    sorted_variants_with_keys = sorted(variants_with_keys, key=lambda tup: tup[0])
    sorted_variant_keys = sorted([og_idgloss for (og_idgloss, og) in variants_with_keys])
    variants_data_quick_access = {}
    variants_data = []
    for (og_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        variants_speaker_data = variant_of_gloss.speaker_data()
        variants_data.append((og_idgloss, variants_speaker_data))
        variants_data_quick_access[og_idgloss] = variants_speaker_data

    return (variants_data, variants_data_quick_access, sorted_variant_keys, sorted_variants_with_keys)


def collect_variants_age_range_data(sorted_variants_with_keys, age_range_labels):

    variants_age_range_distribution_data = {}
    for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        variant_speaker_age_data_v = variant_of_gloss.speaker_age_data()
        speaker_age_data_v = []
        for i in range(0, 100):
            i_key = str(i)
            if i_key in variant_speaker_age_data_v.keys():
                i_value = variant_speaker_age_data_v[i_key]
                speaker_age_data_v.append(i_value)
                if i_key not in age_range_labels:
                    age_range_labels.append(i_key)
            else:
                speaker_age_data_v.append(0)
        variants_age_range_distribution_data[variant_idgloss] = speaker_age_data_v

    return (variants_age_range_distribution_data, age_range_labels)


def collect_variants_age_sex_raw_percentage(sorted_variants_with_keys, variants_data_quick_access):
    variants_sex_distribution_data = {}
    variants_sex_distribution_data_percentage = {}
    variants_sex_distribution_data_totals = {}
    variants_sex_distribution_data_totals['Female'] = 0
    variants_sex_distribution_data_totals['Male'] = 0
    variants_age_distribution_data = {}
    variants_age_distribution_data_percentage = {}
    variants_age_distribution_data_totals = {}
    variants_age_distribution_data_totals['< 25'] = 0
    variants_age_distribution_data_totals['25 - 35'] = 0
    variants_age_distribution_data_totals['36 - 65'] = 0
    variants_age_distribution_data_totals['> 65'] = 0

    for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        for i_key in ['Female', 'Male']:
            variants_sex_distribution_data_totals[i_key] += variants_data_quick_access[variant_idgloss][i_key]
            variants_sex_distribution_data[i_key] = {}
            variants_sex_distribution_data_percentage[i_key] = {}
        for i_key in ['< 25', '25 - 35', '36 - 65', '> 65']:
            variants_age_distribution_data_totals[i_key] += variants_data_quick_access[variant_idgloss][i_key]
            variants_age_distribution_data[i_key] = {}
            variants_age_distribution_data_percentage[i_key] = {}

    for i_key in ['Female', 'Male']:
        total_gender_across_variants = variants_sex_distribution_data_totals[i_key]
        for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
            variant_speaker_data_v = variants_data_quick_access[variant_idgloss]
            i_value = variant_speaker_data_v[i_key]
            speaker_data_v = i_value
            if total_gender_across_variants > 0:
                speaker_data_p = i_value / total_gender_across_variants
            else:
                speaker_data_p = 0
            variants_sex_distribution_data[i_key][variant_idgloss] = speaker_data_v
            variants_sex_distribution_data_percentage[i_key][variant_idgloss] = speaker_data_p

    for i_key in ['< 25', '25 - 35', '36 - 65', '> 65']:
        total_age_across_variants = variants_age_distribution_data_totals[i_key]
        for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
            variant_speaker_data_v = variants_data_quick_access[variant_idgloss]
            i_value = variant_speaker_data_v[i_key]
            speaker_data_v = i_value
            if total_age_across_variants > 0:
                speaker_data_p = i_value / total_age_across_variants
            else:
                speaker_data_p = 0
            variants_age_distribution_data[i_key][variant_idgloss] = speaker_data_v
            variants_age_distribution_data_percentage[i_key][variant_idgloss] = speaker_data_p

    return (variants_sex_distribution_data, variants_sex_distribution_data_percentage,
            variants_age_distribution_data, variants_age_distribution_data_percentage)


def collect_variants_age_cat_data(sorted_variants_with_keys, variants_data_quick_access):
    variants_age_distribution_cat_data = {}
    variants_age_distribution_cat_percentage = {}
    variants_age_distribution_cat_totals = {}
    variants_age_distribution_cat_totals['< 25'] = 0
    variants_age_distribution_cat_totals['25 - 35'] = 0
    variants_age_distribution_cat_totals['36 - 65'] = 0
    variants_age_distribution_cat_totals['> 65'] = 0

    for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        for i_key in ['< 25', '25 - 35', '36 - 65', '> 65']:
            variants_age_distribution_cat_totals[i_key] += variants_data_quick_access[variant_idgloss][i_key]
            variants_age_distribution_cat_data[i_key] = {}
            variants_age_distribution_cat_percentage[i_key] = {}

    for i_key in ['< 25', '25 - 35', '36 - 65', '> 65']:
        total_age_across_variants = variants_age_distribution_cat_totals[i_key]
        for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
            variant_age_data_v = variants_data_quick_access[variant_idgloss]
            i_value = variant_age_data_v[i_key]

            speaker_data_v = i_value
            if total_age_across_variants > 0:
                speaker_data_p = i_value / total_age_across_variants
            else:
                speaker_data_p = i_value
            variants_age_distribution_cat_data[i_key][variant_idgloss] = speaker_data_v
            variants_age_distribution_cat_percentage[i_key][variant_idgloss] = speaker_data_p

    return (variants_age_distribution_cat_data, variants_age_distribution_cat_percentage)

