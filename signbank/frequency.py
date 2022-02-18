import signbank.settings
from signbank.settings.base import WSGI_FILE, WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, LANGUAGE_CODE
import os
import shutil
from html.parser import HTMLParser
from zipfile import ZipFile
import json
import re
from urllib.parse import quote
import csv
from django.utils.translation import override, ugettext_lazy as _

from django.utils.translation import override

from signbank.dictionary.models import *
from signbank.tools import get_default_annotationidglosstranslation
from django.utils.dateformat import format
from django.core.exceptions import ObjectDoesNotExist, EmptyResultSet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import *
from django.contrib import messages
from django.db import OperationalError, ProgrammingError
from django.core.urlresolvers import reverse
from tagging.models import TaggedItem, Tag

from signbank.settings.base import ECV_FILE,EARLIEST_GLOSS_CREATION_DATE, FIELDS, SEPARATE_ENGLISH_IDGLOSS_FIELD, LANGUAGE_CODE, ECV_SETTINGS, URL, LANGUAGE_CODE_MAP
from signbank.settings.server_specific import *

from CNGT_scripts.python.signCounter import SignCounter
from CNGT_scripts.python.cngt_calculated_metadata import get_creation_time

from guardian.shortcuts import get_objects_for_user

def get_gloss_from_frequency_dict(dataset_acronym, gloss_id_or_value):
    dataset = Dataset.objects.get(acronym=dataset_acronym)
    language = dataset.default_language.id
    try:
        gloss_id = int(gloss_id_or_value)
        gloss = Gloss.objects.get(id=gloss_id)
        if gloss.lemma == None:
            # this is a problem because we don't know what dataset this gloss is in
            print('get_gloss_from_frequency_dict gloss has empty lemma: ', gloss_id_or_value, gloss)
            raise ValueError
        # the dataset has not been restricted to the dataset_acronym
        # if it succeeds to get a gloss with the gloss_id it might be in a different dataset
        # check that the gloss indeed has a dataset
        if gloss.lemma.dataset == None:
            print('get_gloss_from_frequency_dict gloss has no dataset: ', gloss_id_or_value, gloss)
            raise ValueError
        # the caller will check whether the dataset of the gloss matches
        # if we return a gloss, it has a lemma and hence a dataset defined
        return gloss
    except (ValueError, ObjectDoesNotExist, MultipleObjectsReturned, TypeError):
        query = Q(annotationidglosstranslation__text__iexact=gloss_id_or_value,
                  annotationidglosstranslation__language=language)
        qs = Gloss.objects.filter(lemma__dataset=dataset).filter(query)
        if qs.exists():
            if len(qs) > 1:
                # can this happen? how often does this happen?
                print('get_gloss_from_frequency_dict: more than one match found for gloss: ', gloss_id_or_value)
            return qs[0]
        else:
            return None


def get_gloss_tokNo(dataset_acronym, gloss_id):

    gf_objects = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym, gloss__id=gloss_id)
    total_occurrences = 0
    for gf in gf_objects:
        total_occurrences += gf.frequency

    return total_occurrences

def get_gloss_tokNoSgnr(dataset_acronym, gloss_id):

    gf_objects = GlossFrequency.objects.filter(speaker__identifier__endswith='_'+dataset_acronym,
                                               document__corpus__name=dataset_acronym, gloss__id=gloss_id)

    speakers = [ fg.speaker.participant() for fg in gf_objects]
    speakers = sorted(list(set(speakers)))

    total_speakers = len(speakers)
    return total_speakers

def remove_document_from_corpus(dataset_acronym, document_identifier):
    try:
        glosses_to_update = {}
        documents_with_identifier = Document.objects.filter(corpus__name=dataset_acronym, identifier=document_identifier)
        for d_obj in documents_with_identifier:
            gloss_frequency_objects = d_obj.glossfrequency_set.all()
            for gf in gloss_frequency_objects:
                if gf.gloss.id not in glosses_to_update.keys():
                    glosses_to_update[gf.gloss.id] = gf.gloss
                gf.delete()
            d_obj.delete()
        # update frequency counts stored in gloss fields tokNo and tokNoSgnr
        for gid in glosses_to_update.keys():
            glosses_to_update[gid].tokNo = get_gloss_tokNo(dataset_acronym, gid)
            glosses_to_update[gid].tokNoSgnr = get_gloss_tokNoSgnr(dataset_acronym, gid)
            glosses_to_update[gid].save()
        return
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        print('remove_document_from_corpus: not found: ', dataset_acronym, document_identifier)
        return

def speaker_to_glosses(dataset_acronym, speaker_id):
    # maps a speaker id to glosses that occur in frequency data
    # the corpus name is also a parameter because the speaker identifiers are suffixed with it
    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym,
                                                        speaker__identifier__endswith='_'+dataset_acronym)
    glosses_frequencies_filtered_per_speaker_id = glosses_frequencies.filter(speaker__identifier__startswith=speaker_id)
    glosses = [ fg.gloss.id for fg in glosses_frequencies_filtered_per_speaker_id ]
    glosses = sorted(list(set(glosses)))
    return glosses

def dictionary_speakers_to_glosses(dataset_acronym):

    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym)

    flattened_gfs = [(fg.speaker.participant(), fg.gloss.id) for fg in glosses_frequencies]

    speakers = [ sid for (sid, gid) in flattened_gfs ]
    speakers = sorted(list(set(speakers)))

    speakers_sign_glosses = {}
    for speaker_id in speakers:

        glosses_signed = [ gid for (sid, gid) in flattened_gfs if speaker_id == sid ]
        glosses_signed = sorted(list(set(glosses_signed)))

        if speaker_id not in speakers_sign_glosses.keys():
            speakers_sign_glosses[speaker_id] = glosses_signed
    return speakers_sign_glosses

def speaker_to_documents(dataset_acronym, speaker_id):
    # maps a speaker id to corpus documents that occur in frequency data
    # the corpus name is also a parameter because the speaker identifiers are suffixed with it
    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym,
                                                        speaker__identifier__endswith='_'+dataset_acronym)
    glosses_frequencies_filtered_per_speaker_id = glosses_frequencies.filter(speaker__identifier__startswith=speaker_id)
    documents = [ fg.document.identifier for fg in glosses_frequencies_filtered_per_speaker_id ]
    documents = sorted(list(set(documents)))
    return documents

def dictionary_speakers_to_documents(dataset_acronym):

    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym)

    flattened_gfs = [(fg.speaker.participant(), fg.document.identifier) for fg in glosses_frequencies]

    speakers = [ sid for (sid, did) in flattened_gfs ]
    speakers = sorted(list(set(speakers)))

    speakers_sign_in_documents = {}
    for speaker_id in speakers:

        documents = [ did for (sid, did) in flattened_gfs if speaker_id == sid ]
        documents = sorted(list(set(documents)))

        if speaker_id not in speakers_sign_in_documents.keys():
            speakers_sign_in_documents[speaker_id] = documents
    return speakers_sign_in_documents

def gloss_to_speakers(gloss_id):
    # maps a gloss id to speakers that occur in frequency data for the gloss
    glosses_frequencies = GlossFrequency.objects.filter(gloss__id=gloss_id)
    speakers = [ fg.speaker.participant() for fg in glosses_frequencies]
    speakers = sorted(list(set(speakers)))
    return speakers

def dictionary_glosses_to_speakers(dataset_acronym):
    # maps a corpus name to a dictionary that maps gloss ids to speakers that occur in frequency data for that gloss

    # get all frequency data for this corpus
    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym)

    flattened_gfs = [(fg.speaker.participant(), fg.gloss.id) for fg in glosses_frequencies]

    glosses = [ gid for (sid, gid) in flattened_gfs ]
    # remove duplicates
    glosses = sorted(list(set(glosses)))

    glosses_signed_by_speakers = {}
    for gid in glosses:
        speakers_who_sign = [ speaker_id for (speaker_id, gloss_id) in flattened_gfs if gloss_id == gid ]
        # remove duplicates
        speakers = sorted(list(set(speakers_who_sign)))
        if gid not in glosses_signed_by_speakers.keys():
            glosses_signed_by_speakers[gid] = speakers
    return glosses_signed_by_speakers

def gloss_to_documents(gloss_id):
    # maps a gloss id to documents that occur in frequency data for the gloss
    glosses_frequencies = GlossFrequency.objects.filter(gloss__id=gloss_id)
    documents = [ fg.document.identifier for fg in glosses_frequencies]
    documents = sorted(list(set(documents)))
    return documents

def dictionary_glosses_to_documents(dataset_acronym):

    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym)

    flattened_gfs = [(fg.document.identifier, fg.gloss.id) for fg in glosses_frequencies]

    glosses = [ gid for (did, gid) in flattened_gfs ]
    glosses = sorted(list(set(glosses)))

    glosses_appear_in_documents = {}
    for gloss_id in glosses:

        documents = [ did for (did, gid) in flattened_gfs if gloss_id == gid ]
        documents = sorted(list(set(documents)))

        if gloss_id not in glosses_appear_in_documents.keys():
            glosses_appear_in_documents[gloss_id] = documents
    return glosses_appear_in_documents

def document_to_number_of_glosses(dataset_acronym, document_id):
    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym,
                                                        document__identifier=document_id).values('speaker__identifier', 'gloss__id', 'frequency')
    glosses = [gf['gloss__id'] for gf in glosses_frequencies]
    return len(sorted(list(set(glosses))))

def document_to_glosses(dataset_acronym, document_id):
    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym, document__identifier=document_id)
    glosses = [ fg.gloss.id for fg in glosses_frequencies]
    glosses = sorted(list(set(glosses)))
    return glosses

def dictionary_documents_to_glosses(dataset_acronym):

    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym)

    flattened_gfs = [(fg.document.identifier, fg.gloss.id) for fg in glosses_frequencies]

    document_identifiers = [ did for (did, gid) in flattened_gfs ]
    document_identifiers = sorted(list(set(document_identifiers)))

    documents_contain_glosses = {}
    for did in document_identifiers:

        glosses_signed = [ gloss_id for (document_id, gloss_id) in flattened_gfs if document_id == did ]
        glosses_signed = sorted(list(set(glosses_signed)))

        if did not in documents_contain_glosses.keys():
            documents_contain_glosses[did] = glosses_signed
    return documents_contain_glosses


def document_to_speakers(document_id):
    glosses_frequencies = GlossFrequency.objects.filter(document__identifier=document_id)
    speakers = [ fg.speaker.participant() for fg in glosses_frequencies]
    speakers = sorted(list(set(speakers)))
    return speakers

def dictionary_documents_to_speakers(dataset_acronym):

    glosses_frequencies = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym)

    flattened_gfs = [(fg.document.identifier, fg.speaker.participant()) for fg in glosses_frequencies]

    document_identifiers = [ did for (did, sid) in flattened_gfs ]
    document_identifiers = sorted(list(set(document_identifiers)))

    documents_contain_speakers = {}
    for document_id in document_identifiers:

        speakers = [ sid for (did, sid) in flattened_gfs if document_id == did ]

        speakers = sorted(list(set(speakers)))

        if document_id not in documents_contain_speakers.keys():
            documents_contain_speakers[document_id] = speakers
    return documents_contain_speakers

def get_names_of_updated_eaf_files(dataset_acronym, **kwargs):
    # this is a convenience function that determines which documents have been updated and which documents have been removed
    # however, glosses can be added and removed from the database, so whether an eaf file has been changed or not may be irrelevant
    # if glosses have been added the eaf files should be processed again in case the glosses were not found the previous time

    if 'testing' in kwargs.keys():
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.TEST_DATA_DIRECTORY,settings.DATASET_EAF_DIRECTORY, dataset_acronym)
    else:
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.DATASET_EAF_DIRECTORY,dataset_acronym)

    try:
        dataset = Dataset.objects.get(acronym=dataset_acronym)
    except (ObjectDoesNotExist):
        # No dataset corresponding to dataset acronym
        return ([],[],[])

    uploaded_eaf_files = dataset.uploaded_eafs()

    try:
        corpus = Corpus.objects.get(name=dataset_acronym)
    except (ObjectDoesNotExist):
        corpus = None

    eaf_file_paths_small_files = []
    eaf_file_paths_large_files = []
    for filename in uploaded_eaf_files:
        filesize = os.path.getsize(dataset_eaf_folder + os.sep + str(filename))
        if filesize > 50000:
            eaf_file_paths_large_files.append(dataset_eaf_folder + os.sep + str(filename))
        else:
            eaf_file_paths_small_files.append(dataset_eaf_folder + os.sep + str(filename))

    existing_documents_creation_dates = {}
    if corpus:
        existing_documents = Document.objects.filter(corpus=corpus)
        existing_documents_identifiers = [ d.identifier for d in existing_documents ]
        for d in existing_documents:
            existing_documents_creation_dates[d.identifier] = d.creation_time
    else:
        existing_documents_identifiers = []

    all_eaf_files_identifiers = []
    all_eaf_files_creation_dates = {}
    all_eaf_files = eaf_file_paths_small_files + eaf_file_paths_large_files
    for eaf_path in all_eaf_files:
        file_basename = os.path.basename(eaf_path)
        basename = os.path.splitext(file_basename)[0]
        all_eaf_files_identifiers += [basename]
        all_eaf_files_creation_dates[basename] = get_creation_time(eaf_path)

    missing_eaf_files = []
    for d_identier in existing_documents_identifiers:
        if d_identier not in all_eaf_files_identifiers:
            missing_eaf_files += [d_identier]

    eaf_files_to_update = []
    new_eaf_files = []
    for eaf_path in all_eaf_files:
        file_basename = os.path.basename(eaf_path)
        basename = os.path.splitext(file_basename)[0]
        if basename in existing_documents_identifiers:
            if all_eaf_files_creation_dates[basename] > existing_documents_creation_dates[basename]:
                eaf_files_to_update += [ eaf_path ]
            else:
                # file on disk has the same creation date as document in corpus
                continue
        else:
            # a new eaf file has been found
            new_eaf_files += [ eaf_path ]

    return (eaf_files_to_update, new_eaf_files, missing_eaf_files)


def newly_uploaded_documents(dataset_acronym, **kwargs):

    if 'testing' in kwargs.keys():
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.TEST_DATA_DIRECTORY,settings.DATASET_EAF_DIRECTORY, dataset_acronym)
    else:
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.DATASET_EAF_DIRECTORY,dataset_acronym)

    try:
        dataset = Dataset.objects.get(acronym=dataset_acronym)
    except (ObjectDoesNotExist):
        # No dataset corresponding to dataset acronym
        return []

    try:
        corpus = Corpus.objects.get(name=dataset_acronym)
    except (ObjectDoesNotExist):
        corpus = None

    existing_documents = Document.objects.filter(corpus=corpus)
    existing_documents_identifiers = [ d.identifier for d in existing_documents ]
    existing_documents_creation_dates = {}
    for d in existing_documents:
        existing_documents_creation_dates[d.identifier] = d.creation_time

    newly_uploaded_documents = []
    if os.path.isdir(dataset_eaf_folder):
        for filename in os.listdir(dataset_eaf_folder):
            basename = os.path.splitext(filename)[0]
            if basename not in existing_documents_identifiers:
                newly_uploaded_documents.append(filename)
    newly_uploaded_documents.sort()

    return newly_uploaded_documents

def document_has_been_updated(dataset_acronym, document_identifier, **kwargs):

    if 'testing' in kwargs.keys():
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.TEST_DATA_DIRECTORY,settings.DATASET_EAF_DIRECTORY, dataset_acronym)
    else:
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.DATASET_EAF_DIRECTORY,dataset_acronym)

    try:
        existing_document = Document.objects.get(corpus__name=dataset_acronym, identifier=document_identifier)
    except ObjectDoesNotExist:
        return False

    document_eaf_path = os.path.join(dataset_eaf_folder, document_identifier + '.eaf')
    if not os.path.exists(document_eaf_path):
        return False
    date_of_file = get_creation_time(document_eaf_path)
    return date_of_file > existing_document.creation_time


def import_corpus_speakers(dataset_acronym):
    errors = []

    original_speaker_identifiers = [ s.identifier for s in Speaker.objects.filter(identifier__endswith='_'+dataset_acronym) ]
    metadata_location = settings.WRITABLE_FOLDER + settings.DATASET_METADATA_DIRECTORY + os.sep + dataset_acronym + '_metadata.csv'
    #First do some checks
    if not os.path.isfile(metadata_location):
        errors.append('The required metadata file ' + metadata_location + ' is not present')
        return errors

    processed_speaker_identifiers = []
    csvfile = open(metadata_location)
    dialect = csv.Sniffer().sniff(csvfile.readline())
    csvfile.seek(0)
    reader = csv.reader(csvfile, dialect=dialect)
    for n,row in enumerate(reader):

        #Skip the header
        if n == 0:
            if row == ['Participant','Metadata region','Age at time of recording','Gender','Preference hand']:
                continue
            elif row == ['Participant','Region','Age','Gender','Handedness']:
                continue
            else:
                errors.append('The header of '+ settings.METADATA_LOCATION + ' is not Participant,Metadata region,Age at time of recording,Gender,Preference hand')
                continue

        try:
            participant, location, age, gender, hand = row
        except (ValueError):
            errors.append('Line '+str(n)+' does not seem to have the correct amount of items')
            continue

        # we use this syntax because we process the fields one at a time
        try:
            # if the speaker exists with the original participant as identifier (i.e., CNGT eaf files), add the dataset acronym
            speaker = Speaker.objects.get(identifier=participant)
            speaker.identifier = speaker.identifier+'_'+dataset_acronym
        except (ObjectDoesNotExist):
            try:
                speaker = Speaker.objects.get(identifier=participant+'_'+dataset_acronym)
            except (ObjectDoesNotExist):
                speaker = Speaker()
                speaker.identifier = participant+'_'+dataset_acronym
        speaker.location = location
        gender_lower = gender.lower()
        if gender_lower in ['female', 'f', 'v']:
            speaker.gender = 'f'
        elif gender_lower in ['male', 'm']:
            speaker.gender = 'm'
        elif gender_lower in ['other', 'o']:
            speaker.gender = 'o'
        else:
            speaker.gender = None
        hand_lower = hand.lower()
        if hand_lower in ['right', 'r']:
            speaker.handedness = 'r'
        elif hand_lower in ['left', 'l']:
            speaker.handedness = 'l'
        elif hand_lower in ['ambidextrous', 'a', 'both']:
            speaker.handedness = 'a'
        elif hand_lower in ['unknown']:
            speaker.handedness = ''
        else:
            speaker.handedness = ''
        try:
            speaker.age = int(age)
        except (ValueError):
            # might need to do some checking here if other data has been found
            errors.append('Line '+str(n)+' has an incorrect age format')
            pass
        # field Preference hand is ignored
        speaker.save()
        processed_speaker_identifiers.append(speaker.identifier)
    # if there are speaker objects in the database for this corpus that are no longer in the metafile, delete them.
    for original_speaker in original_speaker_identifiers:
        if original_speaker not in processed_speaker_identifiers:
            try:
                original_speaker_object = Speaker.objects.get(identifier=original_speaker)
                original_speaker_object.delete()
            except ObjectDoesNotExist:
                continue
    return errors


def get_corpus_speakers(dataset_acronym):

    try:
        corpus = Corpus.objects.get(name=dataset_acronym)
    except ObjectDoesNotExist:
        return []

    # Get all frequencies mentioning this corpus
    frequencies = GlossFrequency.objects.filter(document__corpus=corpus)

    # Get all speaker identifiers
    speaker_indentifiers = [ speaker['speaker__identifier'] for speaker in frequencies.values('speaker__identifier').distinct() ]

    # Return the list of speakers correspoonding to those identifiers
    return Speaker.objects.filter(identifier__in=speaker_indentifiers).order_by('identifier')


def speaker_identifiers_contain_dataset_acronym(dataset_acronym):

    speakers_in_corpus = Speaker.objects.filter(identifier__endswith='_'+dataset_acronym)
    # return a Boolean
    return len(speakers_in_corpus) > 0


def dictionary_speakerIdentifiers_to_speakerObjects(dataset_acronym):
    dictionary_speakerIds_to_speakerObjs = {}
    speaker_identifiers = []
    for speaker in Speaker.objects.filter(identifier__endswith='_'+dataset_acronym):
        speaker_identifier = speaker.participant()
        # to speed up processing later, speaker objects are stored in a dict by their identifier
        dictionary_speakerIds_to_speakerObjs[speaker_identifier] = speaker
        speaker_identifiers += [speaker_identifier]
    return (speaker_identifiers, dictionary_speakerIds_to_speakerObjs)

def dictionary_documentIdentifiers_to_documentObjects(corpus, document_identifiers_of_eaf_files, document_creation_dates_of_eaf_files):
    dictionary_documentIds_to_documentObjs = {}
    for document_id in document_identifiers_of_eaf_files:
        try:
            document = Document.objects.get(corpus=corpus, identifier=document_id)
        except ObjectDoesNotExist:
            document = Document()
            document.identifier = document_id
            document.corpus = corpus
            document.creation_time = document_creation_dates_of_eaf_files[document_id]
            document.save()
        # to speed up processing later, document objects are already looked up
        dictionary_documentIds_to_documentObjs[document_id] = document
    return dictionary_documentIds_to_documentObjs

def process_frequencies_per_speaker(dataset_acronym, speaker_objects, document_objects, frequencies_per_speaker):

    if not frequencies_per_speaker:
        return ([],{},[])
    glosses_not_in_signbank = []
    updated_glosses = {}
    glosses_in_other_dataset = []
    for pers in frequencies_per_speaker.keys():
        for doc in frequencies_per_speaker[pers].keys():
            gloss_frequency_list = sorted(frequencies_per_speaker[pers][doc].items())
            for gloss_id_or_value, cnt in gloss_frequency_list:
                gloss = get_gloss_from_frequency_dict(dataset_acronym, gloss_id_or_value)
                if gloss:
                    # the gloss returned has a lemma and a dataset
                    if gloss.dataset.acronym == dataset_acronym:
                        if gloss.id not in updated_glosses.keys():
                            updated_glosses[gloss.id] = gloss
                        try:
                            gloss_frequency = GlossFrequency.objects.get(speaker=speaker_objects[pers],
                                                                         document=document_objects[doc], gloss=gloss)
                            gloss_frequency.frequency = cnt
                        except (ObjectDoesNotExist):
                            gloss_frequency = GlossFrequency()
                            gloss_frequency.speaker = speaker_objects[pers]
                            gloss_frequency.document = document_objects[doc]
                            gloss_frequency.gloss = gloss
                            gloss_frequency.frequency = cnt
                        gloss_frequency.save()
                    else:
                        # found a matching gloss in a different dataset
                        annotation_matching_gloss_id = get_default_annotationidglosstranslation(gloss)
                        if annotation_matching_gloss_id not in glosses_in_other_dataset:
                            glosses_in_other_dataset += [ annotation_matching_gloss_id ]
                else:
                    # no match for gloss_id_or_value
                    if gloss_id_or_value not in glosses_not_in_signbank:
                        glosses_not_in_signbank += [gloss_id_or_value]

    # print('glosses not in signbank: ', glosses_not_in_signbank)
    return (glosses_not_in_signbank, updated_glosses, glosses_in_other_dataset)


def configure_corpus_documents(dataset_acronym, **kwargs):

    if 'testing' in kwargs.keys():
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER, settings.TEST_DATA_DIRECTORY, settings.DATASET_EAF_DIRECTORY,dataset_acronym)
        metadata_location = os.path.join(settings.WRITABLE_FOLDER, settings.TEST_DATA_DIRECTORY, settings.DATASET_METADATA_DIRECTORY, dataset_acronym + '_metadata.csv')
    else:
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER, settings.DATASET_EAF_DIRECTORY, dataset_acronym)
        metadata_location = os.path.join(settings.WRITABLE_FOLDER, settings.DATASET_METADATA_DIRECTORY, dataset_acronym + '_metadata.csv')

    # create a Corpus object if it does not exist
    try:
        corpus = Corpus.objects.get(name=dataset_acronym)
    except (ObjectDoesNotExist):
        print('configure_corpus_documents: create a new corpus: ', dataset_acronym)
        corpus = Corpus()
        corpus.name = dataset_acronym
        corpus.description = 'Corpus ' + dataset_acronym
        corpus.speakers_are_cross_referenced = True
        corpus.save()

    (speaker_identifiers, dictionary_speakerIds_to_speakerObjs) = dictionary_speakerIdentifiers_to_speakerObjects(dataset_acronym)

    if not speaker_identifiers:
        print('configure_corpus_documents: No speaker objects found for corpus ', dataset_acronym)
        return

    # create Document objects for the EAF files
    eaf_file_paths_small_files = []
    eaf_file_paths_large_files = []
    for filename in os.listdir(dataset_eaf_folder):
        filesize = os.path.getsize(dataset_eaf_folder + os.sep + str(filename))
        if filesize > 50000:
            eaf_file_paths_large_files.append(dataset_eaf_folder + os.sep + str(filename))
        else:
            eaf_file_paths_small_files.append(dataset_eaf_folder + os.sep + str(filename))

    # fetch document identifiers and creation dates for all eaf files
    # get filenames out of paths to use as document identifiers
    document_identifiers = []
    document_creation_dates = {}
    for eaf_path in eaf_file_paths_small_files + eaf_file_paths_large_files:
        file_basename = os.path.basename(eaf_path)
        basename = os.path.splitext(file_basename)[0]
        document_identifiers += [basename]
        document_creation_dates[basename] = get_creation_time(eaf_path)

    # create document objects for all document identifiers, if don't already exist
    dictionary_documentIds_to_documentObjs = dictionary_documentIdentifiers_to_documentObjects(corpus,
                                                                                               document_identifiers,
                                                                                               document_creation_dates)

    updated_glosses = {}
    glosses_not_in_signbank = []
    glosses_in_other_dataset = []
    if eaf_file_paths_small_files:
        sign_counter = SignCounter(metadata_location,
                                   eaf_file_paths_small_files,
                                   settings.MINIMUM_OVERLAP_BETWEEN_SIGNING_HANDS)

        try:
            sign_counter.run()
        except KeyError:
            # the counter scripts generate a key error if a speaker is not found
            print('configure_corpus_documents: Speakers not found for corpus ', eaf_file_paths_small_files)
            return

        # we get the frequencies from the sign_counter object
        try:
            frequencies_per_speaker = sign_counter.freqsPerPerson
        except KeyError:
            print('configure_corpus_documents: No frequency data calculated for ', eaf_file_paths_small_files)
            frequencies_per_speaker = {}

        (glosses_not_in_signbank, updated_glosses, glosses_in_other_dataset) = process_frequencies_per_speaker(dataset_acronym,
                                                                                     dictionary_speakerIds_to_speakerObjs,
                                                                                     dictionary_documentIds_to_documentObjs,
                                                                                     frequencies_per_speaker)

    # process big files
    for large_eaf_file in eaf_file_paths_large_files:
        sign_counter = SignCounter(metadata_location,
                                   [large_eaf_file],
                                   settings.MINIMUM_OVERLAP_BETWEEN_SIGNING_HANDS)

        try:
            sign_counter.run()
        except KeyError:
            # KeyError is raised if the participants in the eaf file are not found in the metadata file
            print('configure_corpus_documents: Speakers not found for document: ', large_eaf_file)
            continue

        # we get the frequencies from the sign_counter object
        try:
            frequencies_per_speaker_sub = sign_counter.freqsPerPerson
        except KeyError:
            frequencies_per_speaker_sub = {}

        (glosses_not_in_signbank_sub, updated_glosses_sub, glosses_in_other_dataset_sub) = process_frequencies_per_speaker(dataset_acronym,
                                                                                             dictionary_speakerIds_to_speakerObjs,
                                                                                             dictionary_documentIds_to_documentObjs,
                                                                                             frequencies_per_speaker_sub)
        for gloss_id_or_value in glosses_not_in_signbank_sub:
            if gloss_id_or_value not in glosses_not_in_signbank:
                glosses_not_in_signbank.append(gloss_id_or_value)

        for gloss_id in updated_glosses_sub.keys():
            if gloss_id not in updated_glosses.keys():
                updated_glosses[gloss_id] = updated_glosses_sub[gloss_id]

        for gloss_id_or_value in glosses_in_other_dataset_sub:
            if gloss_id_or_value not in glosses_in_other_dataset:
                glosses_in_other_dataset.append(gloss_id_or_value)

    # after processing GlossFreqyency data for all glosses in the EAF files, calculate the relevant info per gloss
    for gid in updated_glosses.keys():
        updated_glosses[gid].tokNo = get_gloss_tokNo(dataset_acronym, gid)
        updated_glosses[gid].tokNoSgnr = get_gloss_tokNoSgnr(dataset_acronym, gid)
        updated_glosses[gid].save()


def update_corpus_counts(dataset_acronym, **kwargs):

    if 'testing' in kwargs.keys():
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.TEST_DATA_DIRECTORY,settings.DATASET_EAF_DIRECTORY, dataset_acronym)
        metadata_location = os.path.join(settings.WRITABLE_FOLDER,settings.TEST_DATA_DIRECTORY, settings.DATASET_METADATA_DIRECTORY,dataset_acronym + '_metadata.csv')
    else:
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.DATASET_EAF_DIRECTORY,dataset_acronym)
        metadata_location = os.path.join(settings.WRITABLE_FOLDER,settings.DATASET_METADATA_DIRECTORY,dataset_acronym + '_metadata.csv')

    try:
        corpus = Corpus.objects.get(name=dataset_acronym)
    except (ObjectDoesNotExist):
        print('update_corpus_counts: corpus does not exist: ', dataset_acronym)
        return

    (speaker_identifiers, dictionary_speakerIds_to_speakerObjs) = dictionary_speakerIdentifiers_to_speakerObjects(dataset_acronym)

    if not speaker_identifiers:
        # this would be very weird if this error happened
        print('update_corpus_counts: No speaker objects found for corpus ', dataset_acronym)
        return

    eaf_file_paths_small_files = []
    eaf_file_paths_large_files = []
    for filename in os.listdir(dataset_eaf_folder):
        filesize = os.path.getsize(dataset_eaf_folder + os.sep + str(filename))
        if filesize > 50000:
            eaf_file_paths_large_files.append(dataset_eaf_folder + os.sep + str(filename))
        else:
            eaf_file_paths_small_files.append(dataset_eaf_folder + os.sep + str(filename))

    existing_documents = Document.objects.filter(corpus__name=dataset_acronym)
    existing_documents_creation_dates = {}
    for d in existing_documents:
        existing_documents_creation_dates[d.identifier] = d.creation_time

    document_identifiers_of_eaf_files = []
    document_creation_dates_of_eaf_files = {}
    all_eaf_files = eaf_file_paths_small_files + eaf_file_paths_large_files
    for eaf_path in all_eaf_files:
        file_basename = os.path.basename(eaf_path)
        basename = os.path.splitext(file_basename)[0]
        document_identifiers_of_eaf_files += [basename]
        document_creation_dates_of_eaf_files[basename] = get_creation_time(eaf_path)

    # the initial idea what to only update modified documents
    # however, glosses in the eaf files previously not found in the corpus may have been added since last processing
    # this ends up just storing all the document ids of eaf files
    documents_to_update = []

    # create document objects for all document identifiers, if don't already exist
    dictionary_documentIds_to_documentObjs = dictionary_documentIdentifiers_to_documentObjects(corpus,
                                                                                               document_identifiers_of_eaf_files,
                                                                                               document_creation_dates_of_eaf_files)

    update_small_eaf_files = []
    for eaf_path in eaf_file_paths_small_files:
        file_basename = os.path.basename(eaf_path)
        basename = os.path.splitext(file_basename)[0]
        update_small_eaf_files += [ eaf_path ]
        documents_to_update += [ basename ]

    update_large_eaf_files = []
    for eaf_path in eaf_file_paths_large_files:
        file_basename = os.path.basename(eaf_path)
        basename = os.path.splitext(file_basename)[0]
        update_large_eaf_files += [ eaf_path ]
        documents_to_update += [basename]

    glosses_not_in_signbank = []
    updated_glosses = {}
    glosses_in_other_dataset = []
    if update_small_eaf_files:
        sign_counter = SignCounter(metadata_location,
                                   update_small_eaf_files,
                                   settings.MINIMUM_OVERLAP_BETWEEN_SIGNING_HANDS)
        try:
            sign_counter.run()
        except KeyError:
            # the counter scripts generate a key error if a speaker is not found
            print('update_corpus_counts: Speakers not found for corpus ', eaf_file_paths_small_files)
            return

        try:
            frequencies_per_speaker = sign_counter.freqsPerPerson
        except KeyError:
            frequencies_per_speaker = {}

        (glosses_not_in_signbank, updated_glosses, glosses_in_other_dataset) = process_frequencies_per_speaker(dataset_acronym,
                                                                                     dictionary_speakerIds_to_speakerObjs,
                                                                                     dictionary_documentIds_to_documentObjs,
                                                                                     frequencies_per_speaker)


    # this is used in testing on large data sets to skip the large eaf files
    # more processing is done after the large files for loop
    # if update_large_eaf_files:
    #     update_large_eaf_files = []

    # process big files
    for large_eaf_file in update_large_eaf_files:
        sign_counter = SignCounter(metadata_location,
                                   [large_eaf_file],
                                   settings.MINIMUM_OVERLAP_BETWEEN_SIGNING_HANDS)
        try:
            sign_counter.run()
        except KeyError:
            # KeyError is raised if the participants in the eaf file are not found in the metadata file
            print('update_corpus_counts: Speakers not found for document: ', large_eaf_file)
            continue

        # we get the frequencies from the sign_counter object
        try:
            frequencies_per_speaker_sub = sign_counter.freqsPerPerson
        except (KeyError, ObjectDoesNotExist):
            frequencies_per_speaker_sub = {}
            print('update_corpus_counts: No frequency data calculated for ', large_eaf_file)

        (glosses_not_in_signbank_sub, updated_glosses_sub, glosses_in_other_dataset_sub) = process_frequencies_per_speaker(dataset_acronym,
                                                                                             dictionary_speakerIds_to_speakerObjs,
                                                                                             dictionary_documentIds_to_documentObjs,
                                                                                             frequencies_per_speaker_sub)

        for gloss_id_or_value in glosses_not_in_signbank_sub:
            if gloss_id_or_value not in glosses_not_in_signbank:
                glosses_not_in_signbank.append(gloss_id_or_value)

        for gloss_id in updated_glosses_sub.keys():
            if gloss_id not in updated_glosses.keys():
                updated_glosses[gloss_id] = updated_glosses_sub[gloss_id]

        for gloss_id_or_value in glosses_in_other_dataset_sub:
            if gloss_id_or_value not in glosses_in_other_dataset:
                glosses_in_other_dataset.append(gloss_id_or_value)

    for did in documents_to_update:
        # update the creation_date to that of the eaf files that were updated
        dictionary_documentIds_to_documentObjs[did].creation_time = document_creation_dates_of_eaf_files[did]
        dictionary_documentIds_to_documentObjs[did].save()

    # revise the hard coded frequency fields tokNo and tokNoSgnr
    for gid in updated_glosses.keys():
        updated_glosses[gid].tokNo = get_gloss_tokNo(dataset_acronym, gid)
        updated_glosses[gid].tokNoSgnr = get_gloss_tokNoSgnr(dataset_acronym, gid)
        updated_glosses[gid].save()

    # for the purposes of debugging, this is the data that is accumulated during processing
    # these could be incorporated into a return tuple and used elsewhere in the template for the corpus
    # print('update_corpus_counts: updated glosses: ', updated_glosses)
    # print('update_corpus_counts: glosses not in signbank: ', glosses_not_in_signbank)
    # print('update_corpus_counts: glosses_in_other_dataset: ', glosses_in_other_dataset)


def update_corpus_document_counts(dataset_acronym, document_id, **kwargs):
    if 'testing' in kwargs.keys():
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.TEST_DATA_DIRECTORY,settings.DATASET_EAF_DIRECTORY, dataset_acronym)
        metadata_location = os.path.join(settings.WRITABLE_FOLDER,settings.TEST_DATA_DIRECTORY, settings.DATASET_METADATA_DIRECTORY,dataset_acronym + '_metadata.csv')
    else:
        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER,settings.DATASET_EAF_DIRECTORY,dataset_acronym)
        metadata_location = os.path.join(settings.WRITABLE_FOLDER,settings.DATASET_METADATA_DIRECTORY,dataset_acronym + '_metadata.csv')

    try:
        corpus = Corpus.objects.get(name=dataset_acronym)
    except (ObjectDoesNotExist):
        print('update_corpus_document_counts: corpus does not exist: ', dataset_acronym)
        return []

    (speaker_identifiers, dictionary_speakerIds_to_speakerObjs) = dictionary_speakerIdentifiers_to_speakerObjects(dataset_acronym)
    if not speaker_identifiers:
        # this would be very weird if this error happened
        print('update_corpus_document_counts: No speaker objects found for corpus ', dataset_acronym)
        return []

    document_identifiers_of_eaf_files = [ document_id ]
    eaf_path = dataset_eaf_folder + os.sep + document_id + '.eaf'
    document_creation_dates_of_eaf_files = [ get_creation_time(eaf_path) ]

    dictionary_documentIds_to_documentObjs = dictionary_documentIdentifiers_to_documentObjects(corpus,
                                                                                               document_identifiers_of_eaf_files,
                                                                                               document_creation_dates_of_eaf_files)
    sign_counter = SignCounter(metadata_location,
                               [ eaf_path ],
                               settings.MINIMUM_OVERLAP_BETWEEN_SIGNING_HANDS)
    try:
        sign_counter.run()
    except KeyError:
        # the counter scripts generate a key error if a speaker is not found
        print('update_corpus_document_counts: Speakers not found for corpus document ', eaf_path)
        return []

    try:
        frequencies_per_speaker = sign_counter.freqsPerPerson
    except (KeyError, ObjectDoesNotExist):
        frequencies_per_speaker = {}
        print('update_corpus_document_counts: No frequency data calculated for ', eaf_path)
    (glosses_not_in_signbank, updated_glosses, glosses_in_other_dataset) = process_frequencies_per_speaker(dataset_acronym,
                                                                                 dictionary_speakerIds_to_speakerObjs,
                                                                                 dictionary_documentIds_to_documentObjs,
                                                                                 frequencies_per_speaker)

    # revise the hard coded frequency fields tokNo and tokNoSgnr
    for gid in updated_glosses.keys():
        updated_glosses[gid].tokNo = get_gloss_tokNo(dataset_acronym, gid)
        updated_glosses[gid].tokNoSgnr = get_gloss_tokNoSgnr(dataset_acronym, gid)
        updated_glosses[gid].save()

    # for the purposes of debugging, this is the data that is accumulated during processing
    # these could be incorporated into a return tuple and used elsewhere in the template for the corpus
    # print('update_corpus_document_counts: updated glosses: ', updated_glosses.keys())
    # print('update_corpus_document_counts: glosses not in signbank: ', glosses_not_in_signbank)
    # print('update_corpus_document_counts: glosses in other dataset: ', glosses_in_other_dataset)
    return updated_glosses.keys()

def update_document_counts(request, dataset_id, document_id):

    try:
        dataset = get_object_or_404(Dataset, pk=dataset_id)
    except ObjectDoesNotExist:
        return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/available/')

    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR, _('Please login to use this functionality.'))
        return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/frequency/' + dataset_id)
    if not request.user.has_perm('dictionary.change_gloss'):
        messages.add_message(request, messages.ERROR, _('No permission to update corpus.'))
        return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/frequency/' + dataset_id)

    if not request.method == "POST":
        print('update_document_counts: not POST')
        return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/frequency/' + dataset_id)

    try:
        document = Document.objects.get(corpus__name=dataset.acronym, identifier=document_id)
    except ObjectDoesNotExist:
        messages.add_message(request, messages.ERROR, _('Document does not exist: ') + document_id)
        return HttpResponseRedirect(URL + settings.PREFIX_URL + '/datasets/frequency/' + dataset_id)

    try:
        updated_glosses = update_corpus_document_counts(dataset.acronym, document_id)
    except Exception as e:
        print(e)
        exception_value = [ 'Failed']
        return HttpResponse(json.dumps(exception_value), {'content-type': 'application/json'})

    glosses_in_documents_at_start = [ gf['gloss__id'] for gf in
                                            GlossFrequency.objects.filter(document__identifier=document_id).values('gloss__id').distinct() ]

    for gl in glosses_in_documents_at_start:
        if gl not in updated_glosses:
            # GlossFrequency object already exists for Gloss but not in updated glosses
            try:
                missing_gloss_has_glossfrequency = GlossFrequency.objects.filter(document=document, gloss__id=gl)
                for glossfrequency_not_in_document in missing_gloss_has_glossfrequency:
                    print('GlossFrequency object, Gloss not in Document: ', glossfrequency_not_in_document)
                    glossfrequency_not_in_document.delete()
            except (ObjectDoesNotExist):
                print('GlossFrequency exists for Gloss but  not in updated glosses, but not retrieved properly: ', gl)
                continue
    if updated_glosses:
        original_value = [ 'Glosses updated']
    else:
        original_value = [ 'No annotations']
    # messages.add_message(request, messages.INFO, ('Corpus document ' + document_id + ' successfully updated.'))

    return HttpResponse(json.dumps(original_value), {'content-type': 'application/json'})
