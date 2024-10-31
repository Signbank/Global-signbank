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
            with open(os.path.join(WRITABLE_FOLDER, "wordnet_links.csv"), "wb") as f:
                f.write(download_response.content)
            print("Links CSV downloaded successfully!")
        else:
            print("Failed to download Links CSV. Status code:", download_response.status_code)

        # Download the links CSV file
        download_payload = {
            "submit": "signs" 
        }
        download_response = session.post(DOWNLOAD_URL, data=download_payload)
        if download_response.status_code == 200:
            with open(os.path.join(WRITABLE_FOLDER, "wordnet_signs.csv"), "wb") as f:
                f.write(download_response.content)
            print("Signs CSV downloaded successfully!")
        else:
            print("Failed to download Signs CSV. Status code:", download_response.status_code)


    def get_links_data(self):
        import csv

        signs = {}
        with open(os.path.join(WRITABLE_FOLDER, "wordnet_signs.csv"), mode='r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                wordnet_sign_id = row[0]
                signbank_sign_id = row[1]
                wordnet_sign_id = wordnet_sign_id.replace("ngt.", "").replace("'", '').replace(" ", "")
                signbank_sign_id = signbank_sign_id.replace("'", '').replace(" ", "")
                signs[wordnet_sign_id] = signbank_sign_id

        links = {}
        link_base = "https://www.sign-lang.uni-hamburg.de/easier/sign-wordnet/synset/"
        with open(os.path.join(WRITABLE_FOLDER, "wordnet_links.csv"), mode='r') as file:
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
                
                # add info to links
                if signs[wordnet_sign_id] not in links:
                    links[sign_id]=[]
                links[sign_id].append(links_list)
        
        return links


    def handle(self, *args, **options):
        self.download_links_csv()
        links = self.get_links_data()