#!/usr/bin/python
#
# This is a rewrite of the perl script
# signCounter.pl


import getopt
import json
import os
import re
import sys
import csv
from lxml import etree
from collections import defaultdict
import flatdict


class SignCounter:
    def __init__(self, metadata_file, files, minimum_overlap=0, gloss_tier_type='gloss', region_metadata_id='Metadata region'):
        self.minimum_overlap = int(minimum_overlap)
        self.gloss_tier_type = gloss_tier_type
        self.region_metadata_id = region_metadata_id
        self.all_files = []
        self.metadata = {}
        self.time_slots = {}

        self.freqs = defaultdict(lambda: 0)
        self.freqsPerPerson = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        self.freqsPerRegion = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        self.freqsPerSomething = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))

        for f in files:
            self.add_file(f)

        self.load_metadata(metadata_file)

    def add_file(self, fname):
        if os.path.isfile(fname):
            if fname.endswith(".eaf"):
                self.all_files.append(fname)
        elif os.path.isdir(fname):
            files_in_dir = os.listdir(fname)
            for f in files_in_dir:
                self.add_file(fname + os.sep + f)
        else:
            sys.stderr.write("No such file of directory: %s\n" % fname)

    def load_metadata(self, metadata_file):
        if not metadata_file:
            self.metadata = {}
        else:
            with open(metadata_file) as meta:
                header = meta.readline().strip().split("\t")  # Skip first row (header)
                for line in meta.readlines():
                    fields = line.strip().split("\t")
                    self.metadata[fields[0]] = dict(zip(header[1:], fields[1:]))

    def run(self):
        """ """
        if len(self.all_files) > 0:
            for f in self.all_files:
                try:
                    self.process_file(f)
                    self.generate_result()
                except KeyError as ke:
                    sys.stderr.write("KeyError in file %s: '%s'\n" % (f, ke.args[0]))
                # except:
                #     sys.stderr.write("Unexpected error: %s %s\n" % (str(sys.exc_info()[0]), str(sys.exc_info()[1])))
        else:
            sys.stderr.write("No EAF files to process.\n")

    def process_file(self, fname):
        file_basename = os.path.basename(fname)
        basename = os.path.splitext(file_basename)[0]
        with open(fname, 'r', encoding="utf-8") as eaf:
            xml = etree.parse(eaf)
            self.extract_time_slots(xml)
            grouped_tiers = self.group_tiers_per_participant(xml)
            extracted_glosses_per_participant = self.extract_glosses_per_participant(grouped_tiers)
            for participant, extracted_glosses in extracted_glosses_per_participant.items():
                if extracted_glosses[1] == 1:
                    list_of_gloss_units = self.to_units(extracted_glosses[0])
                    self.restructure(list_of_gloss_units, basename)
                elif extracted_glosses[1] == 2:
                    list_of_gloss_units = self.to_units_two_handed(extracted_glosses[0])
                    self.restructure(list_of_gloss_units, basename)

    # Helper functions to extract data from the EAF XML
    def extract_time_slots(self, xml):
        for time_slot in xml.findall("//TIME_SLOT"):
            time_slot_id = time_slot.attrib['TIME_SLOT_ID']
            self.time_slots[time_slot_id] = time_slot.attrib['TIME_VALUE']

    def get_tier_id(self, tier):
        return tier.attrib['TIER_ID']

    def get_participant(self, tier):
        if 'PARTICIPANT' in tier.attrib:
            return tier.attrib['PARTICIPANT']
        return ""

    def get_linguistic_type(self, tier):
        if 'LINGUISTIC_TYPE_REF' in tier.attrib:
            return tier.attrib['LINGUISTIC_TYPE_REF']
        return ""
    # End helper functions

    def group_tiers_per_participant(self, xml):
        grouped_tiers = defaultdict(list)
        for tier in xml.findall("//TIER"):
            if self.get_linguistic_type(tier).lower() == self.gloss_tier_type \
                    and ('PARENT_REF' not in tier.attrib or tier.attrib['PARENT_REF'] == ''):
                grouped_tiers[self.get_participant(tier)].append(tier)
        return grouped_tiers

    def extract_glosses_per_participant(self, grouped_tiers):
        extracted_glosses_per_participant = {}
        for participant, tier_list in grouped_tiers.items():
            if len(tier_list) == 1:
                extracted_glosses_per_participant[participant] = self.extract_glosses(participant, tier_list[0]), 1
            elif len(tier_list) == 2:
                extracted_glosses_per_participant[participant] = self.extract_glosses_two_handed(participant, tier_list), 2
            else:
                # No extraction possible because the number of tiers
                # for a specific participant is not 1 or 2
                pass
        return extracted_glosses_per_participant

    def extract_glosses_two_handed(self, participant, tier_list):
        list_of_glosses = {}  # Structure: { $tierID: { "participant":  "...", "annotations": [ { "begin": ..., "end": ..., "id": ..., "participant": ... }, { ... } ] } }
        tier_id_hand = {}
        for tier in tier_list:
            tier_id = self.get_tier_id(tier)
            list_of_glosses[tier_id] = {}

            match_left = re.match(r'(Gloss?L|left\s*hand)', tier_id, re.IGNORECASE)
            match_right = re.match(r'(Gloss?R|right\s*hand)', tier_id, re.IGNORECASE)
            if match_left or match_right:
                hand = 'L' if match_left else 'R'
                tier_id_hand[hand] = tier_id

                list_of_glosses[tier_id]["participant"] = participant

                list_of_glosses[tier_id]["annotations"] = []

                for annotation in tier.findall("ANNOTATION/ALIGNABLE_ANNOTATION"):
                    annotation_id = annotation.attrib['ANNOTATION_ID']
                    cve_ref = None
                    if 'CVE_REF' in annotation.attrib:
                        cve_ref = annotation.attrib['CVE_REF']
                    annotation_data = {
                        "begin": int(self.time_slots[annotation.attrib['TIME_SLOT_REF1']]),
                        "end": int(self.time_slots[annotation.attrib['TIME_SLOT_REF2']]),
                        "id": annotation_id,
                        "value": annotation.find("ANNOTATION_VALUE").text,
                        "cve_ref": cve_ref,
                        "participant": participant,
                        "hand": hand
                    }
                    list_of_glosses[tier_id]["annotations"].append(annotation_data)

        return list_of_glosses, tier_id_hand

    def extract_glosses(self, participant, tier):
        list_of_glosses = {}
        tier_id = self.get_tier_id(tier)
        list_of_glosses[tier_id] = {}
        list_of_glosses[tier_id]["participant"] = participant
        list_of_glosses[tier_id]["annotations"] = self.get_list_of_glosses(tier, participant, None)
        return list_of_glosses

    def get_list_of_glosses(self, tier, participant, hand):
        annotations = []
        for annotation in tier.findall("ANNOTATION/ALIGNABLE_ANNOTATION"):
            annotation_id = annotation.attrib['ANNOTATION_ID']
            cve_ref = None
            if 'CVE_REF' in annotation.attrib:
                cve_ref = annotation.attrib['CVE_REF']
            annotation_data = {
                "begin": int(self.time_slots[annotation.attrib['TIME_SLOT_REF1']]),
                "end": int(self.time_slots[annotation.attrib['TIME_SLOT_REF2']]),
                "id": annotation_id,
                "value": annotation.find("ANNOTATION_VALUE").text,
                "cve_ref": cve_ref,
                "participant": participant,
                "hand": hand
            }
            annotations.append(annotation_data)
        return annotations


    def to_units_two_handed(self, list_of_glosses_and_tier_id_hand):
        """Turns the list of glosses into a list of units of overlapping glosses.
        :rtype: list of gloss units
        """
        list_of_glosses = list_of_glosses_and_tier_id_hand[0]
        tier_id_hand = list_of_glosses_and_tier_id_hand[1]

        list_of_gloss_units = []  # Structure: [ [ { "begin": ..., "end": ..., "id": ..., "participant": ... } ], [ ] ]
        for signer_id in (1, 2):
            unit = []  # Overlapping glosses are put in a unit.
            last_end_on = ''  # The hand (L or R) of the last seen gloss
            last_end = None  # The end timeSlot of the last seen gloss

            right_tier_id = tier_id_hand['R']
            left_tier_id = tier_id_hand['L']
            if right_tier_id in list_of_glosses and left_tier_id in list_of_glosses:
                right_hand_data = list_of_glosses[right_tier_id]
                left_hand_data = list_of_glosses[left_tier_id]

                if "annotations" in right_hand_data and "annotations" in left_hand_data:
                    right_hand_annotations = right_hand_data['annotations']
                    left_hand_annotations = left_hand_data['annotations']
                    while len(right_hand_annotations) > 0 or len(left_hand_annotations) > 0:
                        if len(right_hand_annotations) > 0 and len(left_hand_annotations) > 0:
                            if right_hand_annotations[0]['begin'] <= left_hand_annotations[0]['begin']:
                                last_end_on = 'R'
                            else:
                                last_end_on = 'L'
                        elif len(right_hand_data['annotations']) > 0:
                            last_end_on = 'R'
                        else:
                            last_end_on = 'L'

                        current_hand_data = list_of_glosses[tier_id_hand[last_end_on]]
                        current_hand_begin = current_hand_data['annotations'][0]['begin']
                        if last_end is not None and current_hand_begin > (last_end - self.minimum_overlap):
                            # Begin new unit
                            list_of_gloss_units.append(unit)
                            unit = []

                        unit.append(current_hand_data['annotations'][0])

                        current_hand_end = current_hand_data['annotations'][0]['end']
                        if last_end is None or current_hand_end > last_end:
                            last_end = current_hand_end

                        current_hand_data['annotations'].pop(0)

            list_of_gloss_units.append(unit)

        return list_of_gloss_units

    def to_units(self, list_of_glosses):
        list_of_gloss_units = []  # Structure: [ [ { "begin": ..., "end": ..., "id": ..., "participant": ... } ], [ ] ]
        for tier_name, tier_data in list_of_glosses.items():
            for annotation in tier_data["annotations"]:
                list_of_gloss_units.append([annotation])
        return list_of_gloss_units

    def restructure(self, list_of_glosses, basename):
        for unit in list_of_glosses:
            tmp = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
            for annotation in unit:
                gloss = annotation['value']

                try:
                    re.sub(r'\n', '', gloss)
                    re.sub(r'\t', '', gloss)
                    re.sub(r'\s\s+', ' ', gloss)
                    re.sub(r'^\s+', '', gloss)
                    re.sub(r'\s+$', '', gloss)
                except TypeError:
                    pass

                if gloss is not None and not gloss == '':
                    tmp[gloss]['participants'][annotation['participant']] += 1

            for gloss in tmp.keys():
                self.freqs[gloss] += 1

                for person in tmp[gloss]['participants'].keys():
                    self.freqsPerPerson[person][basename][gloss] += 1

                    try:
                        region = self.metadata[person][self.region_metadata_id]
                        self.freqsPerRegion[region][person][gloss] += 1
                    except:
                        pass

                    try:
                        for something in self.metadata[person].keys():
                            if something != 'self.region_metadata_id':
                                item = self.metadata[person][something]
                                self.freqsPerSomething[something][item][person][gloss] += 1
                    except:
                        pass

    def generate_result(self):
        number_of_tokens = 0
        number_of_types = 0
        number_of_singletons = 0

        self.sign_counts = {}

        for gloss in sorted(self.freqs.keys()):
            number_of_types += 1
            number_of_tokens += self.freqs[gloss]
            if self.freqs[gloss] == 1:
                number_of_singletons += 1

            # Person frequencies
            number_of_signers = 0
            for person in sorted(self.freqsPerPerson.keys()):
                for document in sorted(self.freqsPerPerson[person].keys()):
                    if gloss in self.freqsPerPerson[person][document]:
                        number_of_signers += 1

            # Uncomment the following to pass this in the result
            # signer_frequencies = defaultdict(lambda: defaultdict(int))
            # for person in sorted(self.freqsPerPerson.keys()):
            #     for document in sorted(self.freqsPerPerson[person].keys()):
            #         if gloss in self.freqsPerPerson[person][document].keys():
            #             signer_frequencies[person][document] = self.freqsPerPerson[person][document][gloss]

            # Region frequencies
            region_frequencies = defaultdict(lambda: defaultdict(int))
            for region in sorted(self.freqsPerRegion.keys()):
                # region_frequencies[region]['frequency'] = 0
                for person in sorted(self.freqsPerRegion[region].keys()):
                    if gloss in self.freqsPerRegion[region][person]:
                        region_frequencies[region]['frequency'] += self.freqsPerRegion[region][person][gloss]
                        region_frequencies[region]['numberOfSigners'] += 1

            something_frequencies = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
            for something in sorted(self.freqsPerSomething.keys()):
                for item in sorted(self.freqsPerSomething[something].keys()):
                    for person in sorted(self.freqsPerSomething[something][item].keys()):
                        if gloss in self.freqsPerSomething[something][item][person]:
                            label = 'frequencyPer' + something
                            something_frequencies[label][item]['frequency'] += \
                                self.freqsPerSomething[something][item][person][gloss]
                            something_frequencies[label][item]['numberOfSigners'] += 1

            self.sign_counts[gloss] = {'frequency': self.freqs[gloss], 'numberOfSigners': number_of_signers,
                                    'frequenciesPerRegion': region_frequencies} #, 'frequenciesPerSpeaker': signer_frequencies}
            self.sign_counts[gloss].update(something_frequencies)

    def get_result(self):

        return self.sign_counts


def output_results(result, csv_file=False):
    if csv_file:
        # Flatten result dict
        flat_dicts = {}
        columns = set()
        for gloss, data in result.items():
            flat_data = flatdict.FlatDict(data, delimiter='/')
            flat_dicts[gloss] = flat_data
            columns.update(flat_data.keys())

        # Write to csv file
        with open(csv_file, 'w') as f:
            freqs_writer = csv.writer(f)
            columns_list = sorted(columns)
            freqs_writer.writerow(['gloss'] + columns_list)
            for gloss, flat_dict in flat_dicts.items():
                data_field = [flat_dict.get(name, '') for name in columns_list]
                freqs_writer.writerow([gloss] + data_field)
    else:
        print(json.dumps(result, sort_keys=True, indent=4))


if __name__ == "__main__":
    usage = "Usage: \n" + sys.argv[0] + " -m <metadata file> -o <mimimum overlap> <file|directory ...>"
    errors = []
    optlist, file_list = getopt.getopt(sys.argv[1:], 'm:o:', ['csv='])
    metadata_fname = ''
    min_overlap = None
    csv_file = None
    for opt in optlist:
        if opt[0] == '-m':
            metadata_fname = opt[1]
        if opt[0] == '-o':
            min_overlap = opt[1]
        if opt[0] == '--csv':
            csv_file = opt[1]

    if min_overlap is None or min_overlap == '':
        errors.append("No minimum overlap file given.")

    if file_list is None or len(file_list) == 0:
        errors.append("No files or directories given.")

    if len(errors) != 0:
        print("Errors:")
        print("\n".join(errors))
        print(usage)
        exit(1)

    signCounter = SignCounter(metadata_fname, file_list, min_overlap)
    signCounter.run()
    result = signCounter.get_result()
    output_results(result, csv_file)
