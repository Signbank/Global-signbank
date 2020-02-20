from signbank.dictionary.models import GlossFrequency

INTERESTING_GLOSSES = [(57,58),(146,459),(247,712),(344,611),(460,488),(494,495),(639,640),(649,650,651),(657,662)]
GENDERS = ['m','f']

for variants in INTERESTING_GLOSSES:

    print('--')
    result = {'m': {}, 'f': {}}

    #Find regionals numbers
    for variant in variants:

        result['m'][variant] = 0
        result['f'][variant] = 0

        for freq in GlossFrequency.objects.filter(gloss__pk=variant):
            result[freq.speaker.gender][variant] += 1

    #Translate to percentages
    perc_result = {}
    for gender, freq_per_variant in result.items():

        nr_of_occurrences = sum(freq_per_variant.values())
        if nr_of_occurrences == 0:
            continue

        perc_result[gender] = {}

        for variant, freq in freq_per_variant.items():
            perc_result[gender][variant] = freq/nr_of_occurrences

    print(perc_result)