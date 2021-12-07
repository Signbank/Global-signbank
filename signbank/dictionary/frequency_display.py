
import json
from signbank.dictionary.models import *

from signbank.settings.server_specific import *

# these are the categories that are displayed in chartjs in the GlossFrequencyView template
SEX_CATEGORIES = ['Female', 'Male']
AGE_CATEGORIES = ['< 25', '25 - 35', '36 - 65', '> 65']

def collect_speaker_age_data(speakers_summary, age_range):
    # the following collects the speakers distributed over a range of ages to display on the x axis
    # for display in chartjs, the age labels are stored separately from the number of speakers having that age
    # ages to display data for across the x axis
    speaker_age_data = []
    for i in range(0, 100):
        # the age is a string for javascript
        i_key = str(i)
        if i_key in speakers_summary.keys():
            # some speakers have this age
            # set the number of speakers with this age
            speaker_age_data.append(speakers_summary[i_key])
            age_range[i] = True
        else:
            # no speakers have this age
            # only show labels for ages that have speakers of that age
            speaker_age_data.append(0)

    return (speaker_age_data, age_range)


def collect_variants_data(variants):
    # parameter is a list of variants objects
    # returns a tuple
    #   variants data quick access: dictionary mapping variant annotation to speaker data for variant
    #   sorted variants with keys: sorted list of pairs ( variant annotation, variant object )
    if not variants:
        return ({}, [])
    variants_with_keys = []
    if len(variants) > 1:
        for v in variants:
            # get the annotation explicitly
            # do not use the __str__ property idgloss
            try:
                v_idgloss = v.annotationidglosstranslation_set.get(language=v.lemma.dataset.default_language).text
            except ObjectDoesNotExist:
                # no translation found for annotation of gloss, display gloss id instead
                v_idgloss = str(v_idgloss.id)
            variants_with_keys.append((v_idgloss, v))
    sorted_variants_with_keys = sorted(variants_with_keys, key=lambda tup: tup[0])
    variants_data_quick_access = {}
    for (og_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        variants_speaker_data = variant_of_gloss.speaker_data()
        variants_data_quick_access[og_idgloss] = variants_speaker_data
    return (variants_data_quick_access, sorted_variants_with_keys)


def collect_variants_age_range_data(sorted_variants_with_keys, age_range):

    variants_age_range_distribution_data = {}
    for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        variant_speaker_age_data_v = variant_of_gloss.speaker_age_data()
        speaker_age_data_v = []
        for i in range(0, 100):
            i_key = str(i)
            if i_key in variant_speaker_age_data_v.keys():
                speaker_age_data_v.append(variant_speaker_age_data_v[i_key])
                age_range[i] = True
            else:
                speaker_age_data_v.append(0)
        variants_age_range_distribution_data[variant_idgloss] = speaker_age_data_v

    return (variants_age_range_distribution_data, age_range)


def collect_variants_age_sex_raw_percentage(sorted_variants_with_keys, variants_data_quick_access):
    variants_sex_distribution_data_raw = {}
    variants_sex_distribution_data_percentage = {}
    variants_sex_distribution_data_totals = {}
    for i_key in SEX_CATEGORIES:
        variants_sex_distribution_data_raw[i_key] = {}
        variants_sex_distribution_data_percentage[i_key] = {}
        variants_sex_distribution_data_totals[i_key] = 0
    variants_age_distribution_data_raw = {}
    variants_age_distribution_data_percentage = {}
    variants_age_distribution_data_totals = {}
    for i_key in AGE_CATEGORIES:
        variants_age_distribution_data_raw[i_key] = {}
        variants_age_distribution_data_percentage[i_key] = {}
        variants_age_distribution_data_totals[i_key] = 0

    for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
        for i_key in SEX_CATEGORIES:
            variants_sex_distribution_data_totals[i_key] += variants_data_quick_access[variant_idgloss][i_key]
        for i_key in AGE_CATEGORIES:
            variants_age_distribution_data_totals[i_key] += variants_data_quick_access[variant_idgloss][i_key]

    for i_key in SEX_CATEGORIES:
        total_gender_across_variants = variants_sex_distribution_data_totals[i_key]
        for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
            variant_speaker_data_v = variants_data_quick_access[variant_idgloss]
            i_value = variant_speaker_data_v[i_key]
            speaker_data_v = i_value
            if total_gender_across_variants > 0:
                speaker_data_p = i_value / total_gender_across_variants
            else:
                speaker_data_p = 0
            variants_sex_distribution_data_raw[i_key][variant_idgloss] = speaker_data_v
            variants_sex_distribution_data_percentage[i_key][variant_idgloss] = speaker_data_p

    for i_key in AGE_CATEGORIES:
        total_age_across_variants = variants_age_distribution_data_totals[i_key]
        for (variant_idgloss, variant_of_gloss) in sorted_variants_with_keys:
            variant_speaker_data_v = variants_data_quick_access[variant_idgloss]
            i_value = variant_speaker_data_v[i_key]
            speaker_data_v = i_value
            if total_age_across_variants > 0:
                speaker_data_p = i_value / total_age_across_variants
            else:
                speaker_data_p = 0
            variants_age_distribution_data_raw[i_key][variant_idgloss] = speaker_data_v
            variants_age_distribution_data_percentage[i_key][variant_idgloss] = speaker_data_p

    return (variants_sex_distribution_data_raw, variants_sex_distribution_data_percentage,
            variants_age_distribution_data_raw, variants_age_distribution_data_percentage)

