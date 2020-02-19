from signbank.dictionary.models import GlossFrequency

INTERESTING_GLOSSES = [(57,58),(146,459),(247,712),(344,611),(460,488),(494,495),(639,640),(649,650,651),(657,662)]
AGE_GROUPS = [1,2,3,4]

for variants in INTERESTING_GLOSSES:

    print('--')
    result = {1: {}, 2: {}, 3: {}, 4: {}}

    #Find regionals numbers
    for variant in variants:

        result[1][variant] = 0
        result[2][variant] = 0
        result[3][variant] = 0
        result[4][variant] = 0

        for freq in GlossFrequency.objects.filter(gloss__pk=variant):

            age = freq.speaker.age

            if age < 25:
                age_group = 1
            elif age < 36:
                age_group = 2
            elif age < 66:
                age_group = 3
            else:
                age_group = 4

            result[age_group][variant] += 1

    #Translate to percentages
    perc_result = {}
    for age_group, freq_per_variant in result.items():

        nr_of_occurrences = sum(freq_per_variant.values())
        if nr_of_occurrences == 0:
            continue

        perc_result[age_group] = {}

        for variant, freq in freq_per_variant.items():
            perc_result[age_group][variant] = freq/nr_of_occurrences

    print(perc_result)