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

        # Check if the download was successful and save the file
        if download_response.status_code == 200:
            filepath = os.path.join(WRITABLE_FOLDER, "wordnet_links.csv")
            with open(filepath, "wb") as f:
                f.write(download_response.content)
            print("CSV downloaded successfully!")
        else:
            print("Failed to download CSV. Status code:", download_response.status_code)

    def handle(self, *args, **options):
        
        self.download_links_csv()