from signbank.dictionary.models import GlossFrequency
from json import dumps

def regionality_score(percentages, skip_zeroes = True):

	if skip_zeroes:
		percentages = list(filter(lambda a: a != 0, percentages))        

	expected_score = 1/len(percentages)
	maximum_total_deviation = (len(percentages)-1) * expected_score + abs(1 - expected_score)
	total_deviation_from_expected = sum([abs(perc-expected_score) for perc in percentages])

	try:
		return total_deviation_from_expected/maximum_total_deviation
	except ZeroDivisionError:
		return 0

INTERESTING_GLOSSES = [(57,58),(146,459),(247,712),(344,611),(460,488),(494,495),(639,640),(649,650,651),(657,662)]
PLACE_NORMALIZERS = {'Groningen': 23,'Amsterdam': 9,'St. Michielsgestel': 1,'Voorburg': 2.5}
total_result = []

for variants in INTERESTING_GLOSSES:

	print('--')
	result = {place: {} for place in PLACE_NORMALIZERS.keys()}
	result_swapped = {}

	#Find regionals numbers
	for variant in variants:

		result_swapped[variant] = {place: 0 for place in PLACE_NORMALIZERS.keys()}

		for place in PLACE_NORMALIZERS.keys():
			result[place][variant] = 0

		for freq in GlossFrequency.objects.filter(gloss__pk=variant):

			location = freq.speaker.location

			if location in PLACE_NORMALIZERS.keys():
				result[location][variant] += 1 # / PLACE_NORMALIZERS[location]
				result_swapped[variant][location] += 1 / PLACE_NORMALIZERS[location]

	#Translate to percentages
	perc_result = {}
	for place, freq_per_variant in result.items():

		nr_of_occurrences = sum(freq_per_variant.values())
		if nr_of_occurrences == 0:
			continue

		perc_result[place] = {}

		for variant, freq in freq_per_variant.items():
			perc_result[place][variant] = freq/nr_of_occurrences

	perc_result_swapped = {}
	regionality_scores = {}
	for variant, freq_per_place in result_swapped.items():

		nr_of_occurrences = sum(freq_per_place.values())
		if nr_of_occurrences == 0:
			continue

		perc_result_swapped[variant] = {}

		for place, freq in freq_per_place.items():
			perc_result_swapped[variant][place] = freq/nr_of_occurrences

		regionality_scores[variant] = regionality_score(perc_result_swapped[variant].values())

	print(perc_result)
	print(perc_result_swapped)
	print(regionality_scores)

	total_result.append(regionality_scores)

print(dumps(total_result))