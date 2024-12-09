"""This script updates the WordNet links in the database. This works ONLY for NGT dataset."""

import os
import io
import shutil
import requests
import csv

from django.core.management import BaseCommand

from signbank.dictionary.models import Synset, Dataset, Gloss
from signbank.settings.server_specific import WORDNET_USERNAME, WORDNET_PASSWORD

import nltk
from nltk.corpus import wordnet as wn
from bs4 import BeautifulSoup

LOGIN_URL = "https://signwordnetannotation.pythonanywhere.com/login.html"
DOWNLOAD_SIGNS_LINKS_URL = "https://signwordnetannotation.pythonanywhere.com/generate_csv.html" 
EXPECTED_LANDING_URL = "https://signwordnetannotation.pythonanywhere.com/"
DOWNLOAD_TAB_URL = "https://www.sign-lang.uni-hamburg.de/easier/sign-wordnet/static/tab/sign_wordnet_gloss_dse.tab"
LINK_BASE = "https://www.sign-lang.uni-hamburg.de/easier/sign-wordnet/synset/"

class Command(BaseCommand):
    help = 'Update the WordNet links in the database. This works ONLY for NGT dataset.'

    def download_wordnet_gloss(self):
        """ Download the WordNet gloss file from the server. """
        response = requests.get(DOWNLOAD_TAB_URL)
        if response.status_code == 200:
            glosses_wordnet = response.content
            print("WordNet gloss file downloaded successfully.")
            return glosses_wordnet
        else:
            print("Failed to download WordNet gloss file. Status code:", response.status_code)

    def download_csv(self, session, csv_type):
        """ Download the WordNet links and signs CSV file from the server. """
        download_payload = {
            "submit": csv_type
        }
        download_response = session.post(DOWNLOAD_SIGNS_LINKS_URL, data=download_payload)
        if download_response.status_code == 200:
            csv = download_response.content
            print(f"{csv_type} CSV downloaded successfully.")
            return csv
        else:
            print(f"Failed to download {csv_type} CSV. Status code:", download_response.status_code)

    def download_links_csv(self):
        """ Download the WordNet links CSV file from the server. """

        session = requests.Session() 
        login_payload = {
            "username": WORDNET_USERNAME,      
            "password": WORDNET_PASSWORD      
        }

        # Send the login request
        login_response = session.post(LOGIN_URL, data=login_payload)

        # Check if login was successful by looking at the status code or response content
        if login_response.url != EXPECTED_LANDING_URL:
            print("Login failed or redirected incorrectly.")
            return None
        else:
            print("Login successful!")

        links_csv = self.download_csv(session, "links")
        signs_csv = self.download_csv(session, "signs")

        return links_csv, signs_csv

    def get_links_data(self, links_csv, signs_csv):
        """ Read the WordNet links CSV file and return the data. """

        # Read the signs CSV file
        signs = {}
        decoded_signs_csv = signs_csv.decode('utf-8')
        decoded_signs_csv = io.StringIO(decoded_signs_csv)
        signs_csv_reader = csv.reader(decoded_signs_csv)
        next(signs_csv_reader)
        
        for row in signs_csv_reader:
            wordnet_sign_id = row[0]
            signbank_sign_id = row[1]
            wordnet_sign_id = wordnet_sign_id.replace("ngt.", "").replace("'", '').replace(" ", "")
            signbank_sign_id = signbank_sign_id.replace("'", '').replace(" ", "")
            signs[wordnet_sign_id] = signbank_sign_id

        # Read the links CSV file
        links = {}
        decoded_links_csv = links_csv.decode('utf-8')
        decoded_links_csv = io.StringIO(decoded_links_csv)
        links_csv_reader = csv.reader(decoded_links_csv)
        next(links_csv_reader)

        for row in links_csv_reader:
            for r_i, r in enumerate(row):
                row[r_i] = r.replace("'", '').replace(" ", "")

            # only keep rows with confidence level >= 5
            if int(row[2]) < 5:
                continue

            wordnet_sign_id = row[0].replace("ngt.", "")

            link = f"{LINK_BASE}{row[1]}.html"
            links_list = [row[1], row[2], row[3], link]
            sign_id = wordnet_sign_id
            if wordnet_sign_id in signs:
                sign_id = signs[wordnet_sign_id]
            
            if signs[wordnet_sign_id] not in links:
                links[sign_id]=[]

            links[sign_id].append(links_list)
        return links
    

    def get_lemma_definitions(self, glosses_wordnet):
        """ Get the lemma names and definitions from the WordNet gloss file. """

        rows = glosses_wordnet.decode("utf-8").split('\n')
            
        # Save the lemma names and definitions in a dictionary
        wn_dict = {}
        for row in rows[1:]:
            # check if row is empty
            if not row:
                continue
            row_split = row.split('\t')
            omw_id = row_split[0]
            offset, pos = omw_id.split('-')
            synset = wn.synset_from_pos_and_offset(pos, int(offset))
            if synset:
                wn_dict["omw."+omw_id] = [synset.lemma_names(), synset.definition()]

        return wn_dict

    def find_lemmas_description_in_html(self, html):
        """ Find the lemmas and description in the HTML of the Multilingual Sign Language Wordnet page. """
        
        soup = BeautifulSoup(html, "html.parser")

        # Scrape the lemmas from the HTML
        lemmas_paragraph = None
        for p in soup.find_all("p"):
            if "Lemmas:" in p.get_text():
                lemmas_paragraph = p
                lemmas = [lemma.strip() for lemma in lemmas_paragraph.get_text().replace("Lemmas:", "").split(",")]
                lemmas = ", ".join(lemmas)
                break
        if lemmas_paragraph is None:
            lemmas = ""

        # Scrape the definition from the HTML
        definition_paragraph = soup.find("p", class_="synset_def")
        if definition_paragraph:
            definition = definition_paragraph.get_text().replace("Definition:", "").strip()
        else:
            definition = ""

        return lemmas, definition

    def update_links_data(self, links, wn_dict):
        """ Update the WordNet links in the database. """

        ngt_dataset = Dataset.objects.get(acronym="NGT")

        # unlink all synsets from glosses
        for synset in Synset.objects.filter(glosses__lemma__dataset=ngt_dataset):
            synset.glosses.clear()
        
        for gloss_id in links.keys():

            if not str(gloss_id).isdigit():
                continue

            gloss = Gloss.objects.filter(id=int(gloss_id)).first()
            if not gloss:
                continue 
            
            # Create the Synset objects and add them to the Gloss
            for l in links[gloss_id]:

                synset = Synset.objects.filter(name = l[0], glosses__lemma__dataset = ngt_dataset).first()

                if not synset:
                    synset = Synset.objects.create(name = l[0])

                    # Check if lemma and description are available in the WordNet gloss file
                    if l[0] in wn_dict:
                        synset.lemmas = ', '.join(wn_dict[l[0]][0])
                        synset.description = wn_dict[l[0]][1]

                    # Check if the URL is valid
                    response = requests.get(l[3])
                    if response.status_code == 200:
                        synset.url = l[3]
                        # Lemmas and descriptions are not available in the WordNet gloss file, so scrape them from the HTML
                        if not synset.lemmas:
                            synset.lemmas, synset.description = self.find_lemmas_description_in_html(response.text)
                    synset.save()

                if synset not in gloss.synsets.all():
                    gloss.synsets.add(synset)
                    gloss.save()

        # Delete the Synset objects that are not in the new synsets (outdated)
        Synset.objects.filter(glosses=None).delete()

        print("WordNet links updated successfully.")     


    def handle(self, *args, **options):
        nltk.download('wordnet')
        nltk.download('omw')
        glosses_wordnet = self.download_wordnet_gloss()
        links_csv, signs_csv = self.download_links_csv()
        links = self.get_links_data(links_csv, signs_csv)
        wn_dict = self.get_lemma_definitions(glosses_wordnet)
        self.update_links_data(links, wn_dict)

