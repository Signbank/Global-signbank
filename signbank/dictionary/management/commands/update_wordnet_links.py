"""This script updates the WordNet links in the database."""

import os
import shutil
import requests

from django.core.management import BaseCommand
from signbank.settings.server_specific import WORDNET_USERNAME, WORDNET_PASSWORD, WRITABLE_FOLDER

class Command(BaseCommand):
    help = 'Update the WordNet links in the database.'

    def download_links_csv(self):

        # Replace these with the actual URLs and credentials
        LOGIN_URL = "https://signwordnetannotation.pythonanywhere.com/login.html"
        DOWNLOAD_URL = "https://signwordnetannotation.pythonanywhere.com/generate_csv.html" 
        EXPECTED_LANDING_URL = "https://signwordnetannotation.pythonanywhere.com/"

        with requests.Session() as session:
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

        # Download the links CSV file
        download_payload = {
            "submit": "links" 
        }
        download_response = session.post(DOWNLOAD_URL, data=download_payload)
        if download_response.status_code == 200:
            with open(os.path.join(WRITABLE_FOLDER, "synsets/wordnet_links.csv"), "wb") as f:
                f.write(download_response.content)
            print("Links CSV downloaded successfully.")
        else:
            print("Failed to download Links CSV. Status code:", download_response.status_code)

        # Download the links CSV file
        download_payload = {
            "submit": "signs" 
        }
        download_response = session.post(DOWNLOAD_URL, data=download_payload)
        if download_response.status_code == 200:
            with open(os.path.join(WRITABLE_FOLDER, "synsets/wordnet_signs.csv"), "wb") as f:
                f.write(download_response.content)
            print("Signs CSV downloaded successfully.")
        else:
            print("Failed to download Signs CSV. Status code:", download_response.status_code)


    def get_links_data(self):
        import csv

        signs = {}
        with open(os.path.join(WRITABLE_FOLDER, "synsets/wordnet_signs.csv"), mode='r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                wordnet_sign_id = row[0]
                signbank_sign_id = row[1]
                wordnet_sign_id = wordnet_sign_id.replace("ngt.", "").replace("'", '').replace(" ", "")
                signbank_sign_id = signbank_sign_id.replace("'", '').replace(" ", "")
                signs[wordnet_sign_id] = signbank_sign_id

        links = {}
        link_base = "https://www.sign-lang.uni-hamburg.de/easier/sign-wordnet/synset/"
        with open(os.path.join(WRITABLE_FOLDER, "synsets/wordnet_links.csv"), mode='r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                for r_i, r in enumerate(row):
                    row[r_i] = r.replace("'", '').replace(" ", "")
                wordnet_sign_id = row[0].replace("ngt.", "")

                link = f"{link_base}{row[1]}.html"
                links_list = [row[1], row[2], row[3], link]
                sign_id = wordnet_sign_id
                if wordnet_sign_id in signs:
                    sign_id = signs[wordnet_sign_id]
                
                if signs[wordnet_sign_id] not in links:
                    links[sign_id]=[]

                links[sign_id].append(links_list)
        return links
    

    def get_lemma_definitions(self):
        from nltk.corpus import wordnet as wn

        with open(os.path.join(WRITABLE_FOLDER, 'synsets/sign_wordnet_gloss_dse.tab'), 'r') as file:
            rows = file.readlines()
            
        wn_dict = {}
        for row in rows[1:]:
            row_split = row.split('\t')
            omw_id = row_split[0]
            offset, pos = omw_id.split('-')
            synset = wn.synset_from_pos_and_offset(pos, int(offset))
            if synset:
                wn_dict["omw."+omw_id] = [synset.lemma_names(), synset.definition()]

        return wn_dict

    def find_lemmas_description_in_html(self, html):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        lemmas_paragraph = None
        for p in soup.find_all("p"):
            if "Lemmas:" in p.get_text():
                lemmas_paragraph = p
                lemmas = [lemma.strip() for lemma in lemmas_paragraph.get_text().replace("Lemmas:", "").split(",")]
                lemmas = ", ".join(lemmas)
                break
        if lemmas_paragraph is None:
            lemmas = ""

        definition_paragraph = soup.find("p", class_="synset_def")
        if definition_paragraph:
            definition = definition_paragraph.get_text().replace("Definition:", "").strip()
        else:
            definition = ""
        return lemmas, definition
    
    def update_links_data(self, links, wn_dict):
        from signbank.dictionary.models import Synset, Dataset, Gloss
        from django.core.exceptions import ObjectDoesNotExist
        import requests

        ngt_dataset = Dataset.objects.get(acronym="NGT")
        Synset.objects.filter(dataset = ngt_dataset).delete()
        
        for gloss_id in links.keys():

            if not str(gloss_id).isdigit():
                continue

            gloss = Gloss.objects.filter(id=int(gloss_id)).first()
            if not gloss:
                continue 

            for l in links[gloss_id]:
                synset = Synset.objects.filter(name = l[0], dataset = ngt_dataset).first()
                if not synset:
                    synset = Synset.objects.create(name = l[0], dataset = ngt_dataset)

                    if l[0] in wn_dict:
                        lemmas_string = ', '.join(wn_dict[l[0]][0])
                        synset.lemmas = lemmas_string
                        synset.description = wn_dict[l[0]][1]

                    response = requests.get(l[3])
                    if response.status_code == 200:
                        synset.url = l[3]
                        if not synset.lemmas:
                            lemmas, description = self.find_lemmas_description_in_html(response.text)
                            synset.lemmas = lemmas
                            synset.description = description

                    synset.save()
                gloss.synsets.add(synset)
                gloss.save()          

        print("WordNet links updated successfully.")     


    def handle(self, *args, **options):
        import nltk
        nltk.download('wordnet')
        nltk.download('omw')
        self.download_links_csv()
        links = self.get_links_data()
        wn_dict = self.get_lemma_definitions()
        self.update_links_data(links, wn_dict)

