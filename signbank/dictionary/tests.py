from itertools import zip_longest
from collections import OrderedDict

from signbank.dictionary.adminviews import *
from signbank.dictionary.forms import GlossCreateForm, FieldChoiceForm
from signbank.dictionary.models import *
from signbank.tools import get_selected_datasets_for_user
from signbank.settings.base import *

from django.contrib.auth.models import User, Permission, Group
from django.test import TestCase, RequestFactory
from django.test.client import RequestFactory, encode_multipart
import json
from django.test import Client
from django.contrib.messages.storage.cookie import MessageDecoder
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.messages.storage.cookie import CookieStorage
from itertools import *
from pathlib import Path
from os import path

from guardian.shortcuts import assign_perm

from signbank.video.models import GlossVideo
from signbank.dictionary.views import gloss_api_get_sign_name_and_media_info

class BasicCRUDTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        self.user.save()

        self.handedness_fieldchoice_1 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).first()
        self.handedness_fieldchoice_2 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).last()

        self.locprim_fieldchoice_1 = FieldChoice.objects.filter(field='Location', machine_value__gt=1).first()
        self.locprim_fieldchoice_2 = FieldChoice.objects.filter(field='Location', machine_value__gt=1).last()

    def test_CRUD(self):

        #Is the gloss there before?
        found = 0
        total_nr_of_glosses = 0
        for gloss in Gloss.objects.filter(handedness=self.handedness_fieldchoice_1):
            if gloss.idgloss == 'thisisatemporarytestlemmaidglosstranslation':
                found += 1
            total_nr_of_glosses += 1

        self.assertEqual(found,0)
        #self.assertGreater(total_nr_of_glosses,0) #Verify that the database is not empty

        # Create the glosses
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create lemma idgloss translations for all languages
        for language in test_dataset.translation_languages.all():
            new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                                  lemma=new_lemma, language=language)
            new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.handedness = self.handedness_fieldchoice_1
        new_gloss.lemma = new_lemma
        new_gloss.save()

        #Is the gloss there now?
        found = 0
        for gloss in Gloss.objects.filter(handedness=self.handedness_fieldchoice_1):
            if gloss.idgloss == 'thisisatemporarytestlemmaidglosstranslation':
                found += 1

        self.assertEqual(found, 1)

        #The handedness before was 4
        self.assertEqual(new_gloss.handedness,self.handedness_fieldchoice_1)

        #If you run an update post request, you can change the gloss
        new_value_handedness = '_'+str(self.handedness_fieldchoice_2.machine_value)
        client = Client()
        client.login(username='test-user', password='test-user')
        client.post('/dictionary/update/gloss/'+str(new_gloss.pk),{'id':'handedness','value':new_value_handedness})

        changed_gloss = Gloss.objects.get(pk = new_gloss.pk)
        self.assertEqual(changed_gloss.handedness, self.handedness_fieldchoice_2)

        # set up keyword search parameter for default language
        default_language = Language.objects.get(id=get_default_language_id())
        keyword_search_field_prefix = "keyword_"
        keyword_field_name = keyword_search_field_prefix + default_language.language_code_2char

        #We can even add and remove stuff to the keyword table

        # to start with, both tables are empty in the test database
        self.assertEqual(Keyword.objects.all().count(), 0)
        self.assertEqual(Translation.objects.all().count(), 0)

        # add five keywords to the translations of this gloss
        client.post('/dictionary/update/gloss/'+str(new_gloss.pk),{'id': keyword_field_name,'value':'a, b, c, d, e'})

        all_keywords = Keyword.objects.all()
        for k in all_keywords:
            print('test_CRUD update1 keyword: ', k)
        all_translations = Translation.objects.all()
        for t in all_translations:
            print('test_CRUD update1 gloss translation: ', t)

        self.assertEqual(Keyword.objects.all().count(), 5)
        self.assertEqual(Translation.objects.all().count(), 5)

        # update the gloss to only have three of the translations
        # the keyword table still has the same data, but only three translations are associated with the gloss

        client.post('/dictionary/update/gloss/'+str(new_gloss.pk),{'id': keyword_field_name,'value':'a, b, c'})

        all_keywords = Keyword.objects.all()
        for k in all_keywords:
            print('test_CRUD update2 keyword: ', k)
        all_translations = Translation.objects.all()
        for t in all_translations:
            print('test_CRUD update2 gloss translation: ', t)

        self.assertEqual(Keyword.objects.all().count(), 5)
        self.assertEqual(Translation.objects.all().count(), 3)

        #Throwing stuff away with the update functionality
        client.post(settings.PREFIX_URL + '/dictionary/update/gloss/'+str(new_gloss.pk),{'id':'deletegloss','value':'confirmed'})
        found = 0
        for gloss in Gloss.objects.filter(handedness=self.handedness_fieldchoice_1):
            if gloss.idgloss == 'thisisatemporarytestgloss':
                found += 1

        self.assertEqual(found, 0)

    def test_createGloss(self):
        # Create Client and log in
        client = Client()
        logged_in = client.login(username='test-user', password='test-user')
        assign_perm('dictionary.add_gloss', self.user)
        self.user.save()

        # Check whether the user is logged in
        response = client.get('/')
        self.assertContains(response, 'href="/logout.html">Logout')

        # Get the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Construct the Create Gloss form data
        create_gloss_form_data = {'dataset': test_dataset.id, 'select_or_new_lemma': "new"}
        for language in test_dataset.translation_languages.all():
            create_gloss_form_data[GlossCreateForm.gloss_create_field_prefix + language.language_code_2char] = \
                "annotationidglosstranslation_test_" + language.language_code_2char
            create_gloss_form_data[LemmaCreateForm.lemma_create_field_prefix + language.language_code_2char] = \
                "lemmaidglosstranslation_test_" + language.language_code_2char

        # User does not have permission to change dataset. Creating a gloss should fail.
        response = client.post('/dictionary/update/gloss/', create_gloss_form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You are not authorized to change the selected dataset.")

        # Give the test user permission to change a dataset
        assign_perm('change_dataset', self.user, test_dataset)
        response = client.post('/dictionary/update/gloss/', create_gloss_form_data)

        glosses = Gloss.objects.filter(lemma__dataset=test_dataset)
        for language in test_dataset.translation_languages.all():
            glosses = glosses.filter(annotationidglosstranslation__language=language,
                                     annotationidglosstranslation__text__exact="annotationidglosstranslation_test_"
                                                                               + language.language_code_2char)
            glosses = glosses.filter(lemma__lemmaidglosstranslation__language=language,
                                     lemma__lemmaidglosstranslation__text__exact="lemmaidglosstranslation_test_"
                                                                                 + language.language_code_2char)

        self.assertEqual(len(glosses), 1)

        self.assertRedirects(response, reverse('dictionary:admin_gloss_view', kwargs={'pk': glosses[0].id})+'?edit')

    def testSearchForGlosses(self):

        #Create a client and log in
        client = Client()
        client.login(username='test-user', password='test-user')

        # Give the test user permission to search glosses
        assign_perm('dictionary.search_gloss', self.user)

        #Create the glosses
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create lemma idgloss translations
        for language in test_dataset.translation_languages.all():
            new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation_"+language.language_code_2char,
                                                                  lemma=new_lemma, language=language)
            new_lemmaidglosstranslation.save()

        new_gloss = Gloss()
        new_gloss.handedness = self.handedness_fieldchoice_1
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # make some annotations for the new gloss
        test_annotation_translation_index = '1'
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss' + test_annotation_translation_index
            annotationIdgloss.save()

        new_gloss = Gloss()
        new_gloss.handedness = self.handedness_fieldchoice_1
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # make some annotations for the new gloss
        test_annotation_translation_index = '2'
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss' + test_annotation_translation_index
            annotationIdgloss.save()

        new_gloss = Gloss()
        new_gloss.handedness = self.handedness_fieldchoice_2
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # make some annotations for the new gloss
        test_annotation_translation_index = '3'
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss' + test_annotation_translation_index
            annotationIdgloss.save()

        all_glosses = Gloss.objects.all()
        for ag in all_glosses:
            try:
                print('testSearchForGlosses created gloss: ', ag.annotationidglosstranslation_set.get(language=default_language).text)
            except:
                print('testSearchForGlosses created gloss has empty annotation translation')
        #Search
        search_value_handedness = str(self.handedness_fieldchoice_1.machine_value)

        response = client.get('/signs/search/',{'handedness[]':search_value_handedness})
        self.assertEqual(len(response.context['object_list']), 0) #Nothing without dataset permission

        assign_perm('view_dataset', self.user, test_dataset)
        response = client.get('/signs/search/',{'handedness[]':search_value_handedness})
        self.assertEqual(len(response.context['object_list']), 2)

        other_search_value_handedness = str(self.handedness_fieldchoice_2.machine_value)
        response = client.get('/signs/search/',{'handedness[]':other_search_value_handedness})
        for gl in response.context['object_list']:
            try:
                print('testSearchForGlosses response 3: ', gl.annotationidglosstranslation_set.get(language=default_language).text)
            except:
                print('testSearchForGlosses response 3: returned gloss has empty annotation translation')
        self.assertEqual(len(response.context['object_list']), 1)

    def test_package_function(self):
        #Create a client and log in
        client = Client()
        client.login(username='test-user', password='test-user')

        #Get a dataset
        dataset_name = settings.DEFAULT_DATASET

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('view_dataset', self.user, test_dataset)
        assign_perm('change_dataset', self.user, test_dataset)
        assign_perm('dictionary.search_gloss', self.user)
        assign_perm('dictionary.add_gloss', self.user)
        assign_perm('dictionary.change_gloss', self.user)
        self.user.save()

        # Create a lemma in order to store the dataset with the new gloss
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        default_language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=default_language)
        new_lemmaidglosstranslation.save()

        # #Create the gloss
        new_gloss = Gloss()
        # to test the package functionality of phonology fields, add some to settings.API_FIELDS
        # for this test, the local settings file has added these two fields
        # they are visible in the result if they appear in API_FIELDS
        new_gloss.handedness = self.handedness_fieldchoice_1
        new_gloss.locprim = self.locprim_fieldchoice_1

        new_gloss.lemma = new_lemma
        new_gloss.save()
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss'
            annotationIdgloss.save()

        # set up keyword search parameter for default language
        keyword_search_field_prefix = "keyword_"
        keyword_field_name = keyword_search_field_prefix + default_language.language_code_2char

        # keywords: this is merely part of the setup for the test
        # add five keywords to the translations of this gloss
        client.post('/dictionary/update/gloss/'+str(new_gloss.pk),{'id': keyword_field_name,'value':'a, b, c, d, e'})

        changed_gloss = Gloss.objects.get(pk = new_gloss.pk)

        # this calculates the data retrieved by get_gloss_data for packages
        # it shows the format/display of the returned gloss fields
        # note that the value of the phonology fields are numerical rather than human readable
        result = changed_gloss.get_fields_dict()
        print('test_package_function: settings.API_FIELDS: ', settings.API_FIELDS)
        print('test_package_function: get_fields_dict: ', result)

#Deprecated?
class BasicQueryTests(TestCase):

    # Search with a search string

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        self.user.save()

        self.handedness_fieldchoice_1 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).first()
        self.handedness_fieldchoice_2 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).last()

    def testSearchForGlosses(self):

        #Create a client and log in
        # client = Client()
        client = Client(enforce_csrf_checks=True)
        client.login(username='test-user', password='test-user')

        #Get a dataset
        dataset_name = settings.DEFAULT_DATASET

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('view_dataset', self.user, test_dataset)
        assign_perm('change_dataset', self.user, test_dataset)
        assign_perm('dictionary.search_gloss', self.user)
        self.user.save()

        # Create a lemma in order to store the dataset with the new gloss
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        default_language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=default_language)
        new_lemmaidglosstranslation.save()

        # #Create the gloss
        new_gloss = Gloss()
        new_gloss.handedness = self.handedness_fieldchoice_1
        new_gloss.lemma = new_lemma
        new_gloss.save()
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss'
            annotationIdgloss.save()

        # set the language for glosssearch field name
        gloss_search_field_prefix = "glosssearch_"
        glosssearch_field_name = gloss_search_field_prefix + default_language.language_code_2char

        #Search
        search_handedness_value = str(self.handedness_fieldchoice_1.machine_value)
        response = client.get('/signs/search/?handedness='+search_handedness_value+'&'+glosssearch_field_name+'=test', follow=True)
        self.assertEqual(len(response.context['object_list']), 1)


class ECVsNonEmptyTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')

    def test_ECV_files_nonempty(self):

        # test to see if there are glosses in all ecv files
        # note: only the files in the ecv folder are checked for non-emptiness
        # it is not checked whether there is an ecv file for all datasets
        # ecv files for non-existing datasets are reported if empty

        location_ecv_files = ECV_FOLDER
        found_errors = False

        from xml.etree import ElementTree

        for filename in os.listdir(location_ecv_files):
            fname, ext = os.path.splitext(os.path.basename(filename))
            filetree = ElementTree.parse(location_ecv_files + os.sep + filename)
            filetreeroot = filetree.getroot()
            entry_nodes = filetreeroot.findall("./CONTROLLED_VOCABULARY/CV_ENTRY_ML")
            # get the dataset using filter (returns a list)
            try:
                dataset_of_filename = Dataset.objects.get(acronym__iexact=fname)
            except ObjectDoesNotExist:
                uppercase_fname = fname.upper()
                try:
                    fname_nounderscore = uppercase_fname.replace("_"," ")
                    dataset_of_filename = Dataset.objects.get(acronym__iexact=fname_nounderscore)
                except ObjectDoesNotExist:
                    print('WARNING: ECV FILENAME DOES NOT MATCH DATASET ACRONYM: ', filename)
                    continue
            if not len(entry_nodes):
                # no glosses in the ecv
                print('EMPTY ECV FILE FOUND: ', filename)
                found_errors = True

        self.assertEqual(found_errors, False)

class ImportExportTests(TestCase):

    # Three test case scenario's for exporting ECV via the DatasetListView with DEFAULT_DATASET
    #       /datasets/available/?dataset_name=DEFAULT_DATASET&export_ecv=ECV
    # 1. The user is logged in and has permission to change dataset
    # 2. The user is logged in but does not have permission to change dataset
    # 3. The user is not logged in

    def setUp(self):

        # create a new temp dataset with fields fetched from default dataset
        default_dataset = Dataset.objects.get(acronym=settings.DEFAULT_DATASET_ACRONYM)
        signlanguage = SignLanguage.objects.get(name=default_dataset.signlanguage.name)
        translation_languages = default_dataset.translation_languages.all()
        # the id is computed because datasets exist in the test database and we want an unused one
        # this also ignores any datasets created during tests
        used_dataset_ids = [ds.id for ds in Dataset.objects.all()]
        max_used_dataset_id = max(used_dataset_ids)
        #Create a temporary dataset that resembles the default dataset
        new_dataset = Dataset(id=max_used_dataset_id+1,
                              acronym = settings.TEST_DATASET_ACRONYM,
                              name=settings.TEST_DATASET_ACRONYM,
                              default_language=default_dataset.default_language,
                              signlanguage = signlanguage)
        new_dataset.save()
        for language in translation_languages:
            new_dataset.translation_languages.add(language)
        # save the newly created dataset for the tests of this class
        self.test_dataset = new_dataset

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')

    def test_DatasetListView_ECV_export_empty_dataset(self):

        print('Test DatasetListView export_ecv with empty dataset')

        # Give the test user permission to change a dataset
        assign_perm('change_dataset', self.user, self.test_dataset)
        print('User has permmission to change dataset.')

        client = Client()

        logged_in = client.login(username='test-user', password='test-user')

        url = '/datasets/available?dataset_name='+ self.test_dataset.name + '&export_ecv=ECV'

        response = client.get(url)

        loaded_cookies = response.cookies.get('messages').value
        decoded_cookies = decode_messages(loaded_cookies)
        json_decoded_cookies = json.loads(decoded_cookies, cls=MessageDecoder)
        json_message = json_decoded_cookies[0]
        print('Message ONE: ', json_message)

        # the Dataset is Empty at this point, so export is not offered.

        self.assertEqual(str(json_message), 'The dataset is empty, export ECV is not available.')


    def test_DatasetListView_ECV_export_permission_change_dataset(self):

        print('Test DatasetListView export_ecv with permission change_dataset')
        print('Test Dataset is: ', self.test_dataset.acronym)

        # Give the test user permission to change a dataset
        assign_perm('change_dataset', self.user, self.test_dataset)
        print('User has permmission to change dataset.')

        client = Client()

        logged_in = client.login(username='test-user', password='test-user')

        # create a gloss and put it in the dataset so we can export it.
        # this has many steps

        # Create a lemma first
        new_lemma = LemmaIdgloss(dataset=self.test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        language = self.test_dataset.default_language
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # fill in the annotation translations for the new gloss
        for language in self.test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss'
            annotationIdgloss.save()

        url = '/datasets/available?dataset_name=' + self.test_dataset.acronym + '&export_ecv=ECV'

        response = client.get(url)

        loaded_cookies = response.cookies.get('messages').value
        decoded_cookies = decode_messages(loaded_cookies)
        json_decoded_cookies = json.loads(decoded_cookies, cls=MessageDecoder)
        json_message = json_decoded_cookies[0]
        print('Message TWO: ', json_message)

        self.assertEqual(str(json_message), 'ECV successfully updated.')

        location_ecv_files = ECV_FOLDER
        for filename in os.listdir(location_ecv_files):
            if filename == self.test_dataset.acronym.lower() + '.ecv':
                filename_path = os.path.join(location_ecv_files,filename)
                os.remove(filename_path)
                print('Temp ecv file removed.')

    def test_DatasetListView_ECV_export_no_permission_change_dataset(self):

        print('Test DatasetListView export_ecv without permission')

        print('Test Dataset is: ', self.test_dataset.acronym)

        client = Client()

        logged_in = client.login(username='test-user', password='test-user')

        url = '/datasets/available?dataset_name='+ self.test_dataset.acronym + '&export_ecv=ECV'

        response = client.get(url)

        loaded_cookies = response.cookies.get('messages').value
        decoded_cookies = decode_messages(loaded_cookies)
        json_decoded_cookies = json.loads(decoded_cookies, cls=MessageDecoder)
        json_message = json_decoded_cookies[0]
        print('Message: ', json_message)

        self.assertEqual(str(json_message), 'No permission to export dataset.')

    def test_DatasetListView_not_logged_in_ECV_export(self):

        print('Test DatasetListView export_ecv anonymous user not logged in')

        print('Test Dataset is: ', self.test_dataset.acronym)

        client = Client()

        url = '/datasets/available?dataset_name=' + self.test_dataset.acronym + '&export_ecv=ECV'

        response = client.get(url, follow=True)
        self.assertTrue("Please login to use this functionality." in str(response.content))

    def test_Export_csv(self):
        client = Client()
        logged_in = client.login(username=self.user.username, password='test-user')
        print(str(logged_in))

        print('Test Dataset is: ', self.test_dataset.acronym)

        # Give the test user permission to change a dataset
        assign_perm('change_dataset', self.user, self.test_dataset)
        print('User has permmission to change dataset.')

        assign_perm('dictionary.export_csv', self.user)
        print('User has permmission to export csv.')

        # set the language for glosssearch field name
        default_language = self.test_dataset.default_language
        gloss_search_field_prefix = "glosssearch_"
        glosssearch_field_name = gloss_search_field_prefix + default_language.language_code_2char

        response = client.get('/signs/search/', {"search_type": "sign", glosssearch_field_name : "wesseltest6", "format": "CSV"})

        self.assertEqual(response['Content-Type'], "text/csv")
        self.assertContains(response, b'Signbank ID,')
        # self.assertContains(response, b',Lemma ID Gloss')  # For an empty database this wil not work
        self.assertContains(response, b',Dataset')

    def test_Import_csv_update_gloss_for_lemma(self):
        """
        This method will test the last stage (#2) importing of a csv with changes to Lemma Idgloss Translations
        :return: 
        """
        client = Client()
        logged_in = client.login(username=self.user.username, password='test-user')
        print(str(logged_in))

        print('Test Dataset is: ', self.test_dataset.acronym)

        # Give the test user permission to change a dataset
        assign_perm('change_dataset', self.user, self.test_dataset)
        print('User has permmission to change dataset.')

        # Create test lemma idgloss
        lemma = LemmaIdgloss(dataset=self.test_dataset)
        lemma.save()

        # Create test lemma idgloss translations
        lemma_idgloss_translation_prefix = 'test_lemma_translation_'
        test_translation_index = 1
        for language in self.test_dataset.translation_languages.all():
            lemma_translation = LemmaIdglossTranslation(lemma=lemma, language=language,
                                    text='{}{}_{}'.format(lemma_idgloss_translation_prefix,
                                                          language.language_code_2char, test_translation_index))
            lemma_translation.save()

        # Create test gloss
        gloss = Gloss(lemma=lemma)
        gloss.save()

        # Prepare form data for making A NEW LemmaIdgloss + LemmaIdglossTranslations
        test_translation_index = 2
        form_data = {'update_or_create': 'update'}
        for language in self.test_dataset.translation_languages.all():
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            form_name = '{}.Lemma ID Gloss ({})'.format(gloss.id, language_name)
            form_data[form_name] = '{}{}_{}'.format(lemma_idgloss_translation_prefix, language.language_code_2char,
                                                    test_translation_index)
        print('Form data test 1 of test_Import_csv_update_gloss_for_lemma: \n', form_data)

        response = client.post(reverse_lazy('import_csv_update'), form_data, follow=True)
        self.assertContains(response, 'Attempt to update Lemma ID Gloss translations')

        # Prepare form data for linking to AN EXISTING LemmaIdgloss + LemmaIdglossTranslations
        test_translation_index = 1
        form_data = {'update_or_create': 'update'}
        for language in self.test_dataset.translation_languages.all():
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            form_name = '{}.Lemma ID Gloss ({})'.format(gloss.id, language_name)
            form_data[form_name] = '{}{}_{}'.format(lemma_idgloss_translation_prefix, language.language_code_2char,
                                                    test_translation_index)
        print('Form data test 2 of test_Import_csv_update_gloss_for_lemma: \n', form_data)

        response = client.post(reverse_lazy('import_csv_update'), form_data, follow=True)
        self.assertEqual(response.status_code, 200)

        count_dataset_translation_languages = self.test_dataset.translation_languages.all().count()
        print('Number of translation languages for the test dataset: ', count_dataset_translation_languages)

        # Prepare form data for linking to SEVERAL EXISTING LemmaIdgloss + LemmaIdglossTranslations
        form_data = {'update_or_create': 'update'}
        for index, language in enumerate(self.test_dataset.translation_languages.all()):
            if index == 0:
                test_translation_index = 1
            else:
                test_translation_index = 2
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            form_name = '{}.Lemma ID Gloss ({})'.format(gloss.id, language_name)
            form_data[form_name] = '{}{}_{}'.format(lemma_idgloss_translation_prefix, language.language_code_2char,
                                                    test_translation_index)
        print('Form data test 3 of test_Import_csv_update_gloss_for_lemma: \n', form_data)

        response = client.post(reverse_lazy('import_csv_update'), form_data, follow=True)
        if count_dataset_translation_languages > 1:
            print('More than one translation language, attempt to update a lemma translation')
            self.assertContains(response, 'Attempt to update Lemma ID Gloss translations')
        else:
            print('Only one translation language, no changes found')
            self.assertContains(response, 'No changes were found.')


        # Prepare form data for linking to SEVERAL EXISTING LemmaIdgloss + LemmaIdglossTranslations

        form_data = {'update_or_create': 'update'}
        for index, language in enumerate(self.test_dataset.translation_languages.all()):
            if index == 0:
                test_translation_index = 1
            else:
                test_translation_index = 3
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            form_name = '{}.Lemma ID Gloss ({})'.format(gloss.id, language_name)
            form_data[form_name] = '{}{}_{}'.format(lemma_idgloss_translation_prefix, language.language_code_2char,
                                                    test_translation_index)
        print('Form data test 4 of test_Import_csv_update_gloss_for_lemma: \n', form_data)

        response = client.post(reverse_lazy('import_csv_update'), form_data, follow=True)

        if count_dataset_translation_languages > 1:
            print('More than one translation language, attempt to update a lemma translation')
            self.assertContains(response, 'Attempt to update Lemma ID Gloss translations')
        else:
            print('Only one translation language, no changes found')
            self.assertContains(response, 'No changes were found.')


    def test_Import_csv_new_gloss_for_lemma(self):
        """
        This method will test the last stage (#2) importing of a csv with a new gloss with Lemma Idgloss Translations
        :return: 
        """
        client = Client()
        logged_in = client.login(username=self.user.username, password='test-user')
        print(str(logged_in))

        print('Test Dataset is: ', self.test_dataset.acronym)

        # Give the test user permission to change a dataset
        assign_perm('change_dataset', self.user, self.test_dataset)
        print('User has permmission to change dataset.')

        gloss_id = 1
        lemma_idgloss_translation_prefix = 'test_lemma_translation_'
        annotation_idgloss_translation_prefix = 'test_annotation_translation_'

        # Prepare form data for making A NEW LemmaIdgloss + LemmaIdglossTranslations
        test_lemma_translation_index = 1
        test_annotation_translation_index = 1
        form_data = {'update_or_create': 'create', '{}.dataset'.format(gloss_id): self.test_dataset.acronym}
        for language in self.test_dataset.translation_languages.all():
            form_name = '{}.lemma_id_gloss_{}'.format(gloss_id, language.language_code_2char)
            form_data[form_name] = '{}{}_{}'.format(lemma_idgloss_translation_prefix, language.language_code_2char,
                                                    test_lemma_translation_index)
            form_name = '{}.annotation_id_gloss_{}'.format(gloss_id, language.language_code_2char)
            form_data[form_name] = '{}{}_{}'.format(annotation_idgloss_translation_prefix, language.language_code_2char,
                                                    test_annotation_translation_index)

        print('Form data test 1 of test_Import_csv_new_gloss_for_lemma: \n', form_data)
        response = client.post(reverse_lazy('import_csv_create'), form_data)
        self.assertContains(response, 'Changes are live.')

        # Prepare form data for linking to AN EXISTING LemmaIdgloss + LemmaIdglossTranslations
        test_annotation_translation_index = 2
        form_data = {'update_or_create': 'create', '{}.dataset'.format(gloss_id): self.test_dataset.acronym}
        for language in self.test_dataset.translation_languages.all():
            form_name = '{}.lemma_id_gloss_{}'.format(gloss_id, language.language_code_2char)
            form_data[form_name] = '{}{}_{}'.format(lemma_idgloss_translation_prefix, language.language_code_2char,
                                                    test_lemma_translation_index)
            form_name = '{}.annotation_id_gloss_{}'.format(gloss_id, language.language_code_2char)
            form_data[form_name] = '{}{}_{}'.format(annotation_idgloss_translation_prefix, language.language_code_2char,
                                                    test_annotation_translation_index)

        print('Form data test 2 of test_Import_csv_new_gloss_for_lemma: \n', form_data)
        response = client.post(reverse_lazy('import_csv_create'), form_data)
        self.assertContains(response, 'Changes are live.')

        count_dataset_translation_languages = self.test_dataset.translation_languages.all().count()
        print('Number of translation languages for the test dataset: ', count_dataset_translation_languages)

        # Prepare form data for linking to SEVERAL EXISTING LemmaIdgloss + LemmaIdglossTranslations
        test_annotation_translation_index = 3
        form_data = {'update_or_create': 'create', '{}.dataset'.format(gloss_id): self.test_dataset.acronym}
        for index, language in enumerate(self.test_dataset.translation_languages.all()):
            if index == 0:
                test_lemma_translation_index = 1
            else:
                test_lemma_translation_index = 2
            form_name = '{}.lemma_id_gloss_{}'.format(gloss_id, language.language_code_2char)
            form_data[form_name] = '{}{}_{}'.format(lemma_idgloss_translation_prefix, language.language_code_2char,
                                                    test_lemma_translation_index)
            form_name = '{}.annotation_id_gloss_{}'.format(gloss_id, language.language_code_2char)
            form_data[form_name] = '{}{}_{}'.format(annotation_idgloss_translation_prefix, language.language_code_2char,
                                                    test_annotation_translation_index)

        print('Form data test 3 of test_Import_csv_new_gloss_for_lemma: \n', form_data)
        response = client.post(reverse_lazy('import_csv_create'), form_data, follow=True)

        if count_dataset_translation_languages > 1:
            print('More than one translation language, attempt to update to combination of existing and new lemma translations')
            self.assertContains(response, "the combination of Lemma ID Gloss translations should either refer")
        else:
            print('Only one translation language, only the annotation translation is changed.')
            self.assertContains(response, 'Changes are live.')

class VideoTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')

        self.handedness_fieldchoice_1 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).first()
        self.handedness_fieldchoice_2 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).last()

    def test_create_and_delete_video(self):

        client = Client()

        logged_in = client.login(username='test-user', password='test-user')
        print(str(logged_in))

        NAME = 'thisisatemporarytestlemmaidglosstranslation'

        # Create the glosses
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)
        default_language = Language.objects.get(id=settings.DEFAULT_DATASET_LANGUAGE_ID)

        assign_perm('change_dataset', self.user, test_dataset)
        print('User granted permmission to change dataset.')

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=default_language)
        new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.handedness = self.handedness_fieldchoice_1
        new_gloss.lemma = new_lemma
        new_gloss.save()

        client = Client()
        client.login(username='test-user', password='test-user')

        video_url = '/dictionary/protected_media/glossvideo/'+test_dataset.acronym+'/'+NAME[0:2]+'/'+NAME+'-'+str(new_gloss.pk)+'.mp4'
        #We expect no video before
        response = client.get(video_url)
        if response.status_code == 200:
            print('The test video already exists in the archive: ', video_url)
            self.assertEqual(response.status_code,200)
        else:
            print('The test video does not exist in the archive: ', video_url)
            self.assertEqual(response.status_code,302)

            #Upload the video
            print('Uploading the test video.')
            videofile = open(settings.WRITABLE_FOLDER+'test_data/video.mp4','rb')
            response = client.post('/video/upload/',{'gloss_id':new_gloss.pk,
                                                     'videofile': videofile,
                                                     'redirect':'/dictionary/gloss/'+str(new_gloss.pk)+'/?edit'}, follow=True)
            self.assertEqual(response.status_code,200)

        #We expect a video now
        response = client.get(video_url, follow=True)
        self.assertEqual(response.status_code,200)

        #You can't see it if you log out
        client.logout()
        print('User has logged out.')
        print('Attempt to see video. Must log in.')
        response = client.get(video_url)
        self.assertEqual(response.status_code,401)

        #Remove the video
        client.login(username='test-user',password='test-user')
        print('User has logged back in.')
        print('Delete the uploaded video.')
        response = client.post('/video/delete/'+str(new_gloss.pk))

        #We expect no video anymore
        print('Attempt to see video. It is not found.')
        response = client.get(video_url)
        self.assertEqual(response.status_code,302)

    def test_create_and_delete_utf8_video(self):

        client = Client()

        logged_in = client.login(username='test-user', password='test-user')

        NAME = 'XXtéstlemmä%20~山脉%20'  # %20 is an url encoded space

        # Create the glosses
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)
        default_language = Language.objects.get(id=settings.DEFAULT_DATASET_LANGUAGE_ID)

        assign_perm('change_dataset', self.user, test_dataset)
        print('User granted permmission to change dataset.')

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text=NAME,
                                                              lemma=new_lemma, language=default_language)
        new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.handedness = self.handedness_fieldchoice_1
        new_gloss.lemma = new_lemma
        new_gloss.save()

        client = Client()
        client.login(username='test-user', password='test-user')

        video_url = '/dictionary/protected_media/glossvideo/'+test_dataset.acronym+'/'+NAME[0:2]+'/'+NAME+'-'+str(new_gloss.pk)+'.mp4'

        if hasattr(settings, 'ESCAPE_UPLOADED_VIDEO_FILE_PATH') and settings.ESCAPE_UPLOADED_VIDEO_FILE_PATH:
            # If the file name is escaped, the url should be escaped twice:
            # the file may contain percent encodings,
            # so in the path the percent should be encoded
            from django.utils.encoding import escape_uri_path
            video_url = escape_uri_path(video_url)
        video_url = video_url.replace('%', '%25')

        #We expect no video before
        response = client.get(video_url)
        if response.status_code == 200:
            print('The test video already exists in the archive: ', video_url, ' (', type(video_url), ')')
            self.assertEqual(response.status_code,200)
        else:
            print('The test video does not exist in the archive: ', video_url, ' (', type(video_url), ')')
            self.assertEqual(response.status_code,302)

            #Upload the video
            videofile = open(settings.WRITABLE_FOLDER+'test_data/video.mp4','rb')

            response = client.post('/video/upload/',{'gloss_id':new_gloss.pk,
                                                     'videofile': videofile,
                                                     'redirect':'/dictionary/gloss/'+str(new_gloss.pk)+'/?edit'}, follow=True)
            self.assertEqual(response.status_code,200)

        #We expect a video now
        response = client.get(video_url, follow=True)
        print("Video url second test: {}".format(video_url))
        print("Video upload response second test: {}".format(response))
        self.assertEqual(response.status_code,200)

        #You can't see it if you log out
        client.logout()
        print('User has logged out.')
        print('Attempt to see video. Must log in.')
        response = client.get(video_url)
        self.assertEqual(response.status_code,401)

        #Remove the video
        client.login(username='test-user',password='test-user')
        print('User has logged back in.')
        print('Delete the uploaded video.')
        response = client.post('/video/delete/'+str(new_gloss.pk))

        #We expect no video anymore
        print('Attempt to see video. It is not found.')
        response = client.get(video_url)
        self.assertEqual(response.status_code,302)

class AjaxTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')


    def test_GlossSuggestion(self):

        NAME = 'thisisatemporarytestgloss'

        #Create the dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        #Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        #Add a gloss to this dataset
        new_gloss = Gloss()
        new_gloss.annotation_idgloss = NAME
        new_gloss.lemma = new_lemma
        new_gloss.save()

        #Add a translation to be shown with ajax (in the language of the dataset)
        annotationidglosstranslation = AnnotationIdglossTranslation(text=NAME)
        annotationidglosstranslation.gloss = new_gloss
        annotationidglosstranslation.language = test_dataset.translation_languages.get(id=1)
        annotationidglosstranslation.save()

        #Log in
        client = Client()
        client.login(username='test-user', password='test-user')

        #Add info of the dataset to the session (normally done in the details)
        session = client.session
        session['datasetid'] = test_dataset.pk
        session.save()

        #The actual test
        response = client.get('/dictionary/ajax/gloss/we')
        self.assertNotContains(response,NAME)

        response = client.get('/dictionary/ajax/gloss/th')
        print(response.content)
        self.assertContains(response,NAME)

class FrontEndTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')

        NAME = 'thisisatemporarytestgloss'

        #Create the dataset
        dataset_name = settings.DEFAULT_DATASET
        self.test_dataset = Dataset.objects.get(name=dataset_name)

        #Create lemma
        self.new_lemma = LemmaIdgloss(dataset=self.test_dataset)
        self.new_lemma.save()

        language = Language.objects.get(id=get_default_language_id())
        hidden_lemmaidglosstranslation = LemmaIdglossTranslation(text=NAME, lemma=self.new_lemma,
                                                                 language=language)
        hidden_lemmaidglosstranslation.save()

        #Add a hidden gloss to this dataset

        self.hidden_gloss = Gloss(lemma=self.new_lemma)
        self.hidden_gloss.save()

        hidden_annotationidglosstranslation = AnnotationIdglossTranslation(text=NAME + 'hidden', gloss=self.hidden_gloss,
                                                                        language=language)
        hidden_annotationidglosstranslation.save()

        # Add a public gloss to this dataset
        self.public_gloss = Gloss(lemma=self.new_lemma)
        self.public_gloss.inWeb = True
        self.public_gloss.save()

        public_annotationidglosstranslation = AnnotationIdglossTranslation(text=NAME + 'public', gloss=self.public_gloss,
                                                                        language=language)
        public_annotationidglosstranslation.save()

    def test_DetailViewRenders(self):

        #You can get information in the public view of the public gloss
        response = self.client.get('/dictionary/gloss/'+str(self.public_gloss.pk)+'.html')
        self.assertEqual(response.status_code,200)
        self.assertTrue('Annotation ID Gloss' in str(response.content))

        #But not of the hidden gloss
        response = self.client.get('/dictionary/gloss/'+str(self.hidden_gloss.pk)+'.html')
        self.assertEqual(response.status_code,200)
        self.assertFalse('Annotation ID Gloss' in str(response.content))

        #And we get a 302 for both details
        response = self.client.get('/dictionary/gloss/'+str(self.public_gloss.pk))
        self.assertEqual(response.status_code,302)

        response = self.client.get('/dictionary/gloss/'+str(self.hidden_gloss.pk))
        self.assertEqual(response.status_code,302)

        #Log in
        self.client = Client()
        self.client.login(username='test-user', password='test-user')

        #We can now request a details
        response = self.client.get('/dictionary/gloss/'+str(self.hidden_gloss.pk))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,
                            'The gloss you are trying to view is not in your selected datasets.'
                            .format(self.hidden_gloss.pk))

        #With permissions you also see something
        assign_perm('view_dataset', self.user, self.test_dataset)
        response = self.client.get('/dictionary/gloss/'+str(self.hidden_gloss.pk))
        self.assertNotEqual(len(response.content),0)

    def test_JavaScriptIsValid(self):

        #Log in
        self.client = Client()
        self.client.login(username='test-user', password='test-user')

        assign_perm('view_dataset', self.user, self.test_dataset)
        response = self.client.get('/dictionary/gloss/'+str(self.hidden_gloss.pk))

        invalid_patterns = ['= ;','= var']

        everything_okay = True

        for script in re.findall('(?si)<script type=.{1,2}text\/javascript.{1,2}>(.*)<\/script>', str(response.content)):
            for invalid_pattern in invalid_patterns:
                if invalid_pattern in script:
                    everything_okay = False
                    print('Found',invalid_pattern)
                    break

        self.assertTrue(everything_okay)


class ManageDatasetTests(TestCase):
    """
    These tests test things a user can do on the Manage Datasets page
    """

    def setUp(self):
        """
        Set up a user, dataset, lemma, , gloss
        :return: 
        """

        # a new test user is created for use during the tests
        self.user_password = 'test-user'
        self.user = User.objects.create_user('test-user', 'example@example.com', self.user_password)

        LEMMA_PREFIX = 'thisisatemporarytestlemma'
        ANNOTATION_PREFIX = 'thisisatemporarytestannotation'

        # Create the dataset
        dataset_name = settings.DEFAULT_DATASET
        self.test_dataset = Dataset.objects.get(name=dataset_name)

        # Create a lemma
        self.new_lemma = LemmaIdgloss(dataset=self.test_dataset)
        self.new_lemma.save()
        
        # Create lemma translations
        for language in self.test_dataset.translation_languages.all():
            language_code_2char = language.language_code_2char
            lemmaidglosstranslation = LemmaIdglossTranslation(text=LEMMA_PREFIX+'_'+language_code_2char,
                                                              language=language, lemma=self.new_lemma)
            lemmaidglosstranslation.save()

        # Add a gloss to this dataset
        self.new_gloss = Gloss()
        self.new_gloss.lemma = self.new_lemma
        self.new_gloss.save()

        # Create annotation translations
        for language in self.test_dataset.translation_languages.all():
            language_code_2char = language.language_code_2char
            annotationidglosstranslation = AnnotationIdglossTranslation(text=ANNOTATION_PREFIX + '_' + language_code_2char,
                                                              language=language, gloss=self.new_gloss)
            annotationidglosstranslation.save()

        # Create client
        self.client = Client()

        # Create a user to Grant and Revoke view and change permissions
        self.user2 = User.objects.create_user('test-user2', 'example@example.com', 'test-user2')

    def test_User_is_not_logged_in(self):
        """
        Tests whether managing datasets is blocked when not logged in
        :return: 
        """

        # The next bit is to solve the problem that a redirect url to the login page contains PREFIX_URL
        # while in tests a redirect url without PREFIX_URL is expected. See also issue #505
        from django.conf import settings
        settings.LOGIN_URL = settings.LOGIN_URL[len(settings.PREFIX_URL):]

        # Grant view permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_view_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'Sign In'.format(self.user2.username))

        # Revoke view permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'delete_view_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'Sign In'.format(self.user2.username))

        # Grant change permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'Sign In'.format(self.user2.username))

        # Revoke change permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'delete_change_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'Sign In'.format(self.user2.username))

    def test_User_is_not_dataset_manager(self):
        """
        Tests whether managing datasets is blocked if the user is not a dataset manager
        :return: 
        """

        logged_in = self.client.login(username=self.user.username, password=self.user_password)
        self.assertTrue(logged_in)

        assign_perm('dictionary.change_dataset', self.user, self.test_dataset)

        # Grant view permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_view_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'You must be in group Dataset Manager to modify dataset permissions.'
                            .format(self.user2.username))

        # Revoke view permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'delete_view_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'You must be in group Dataset Manager to modify dataset permissions.'
                            .format(self.user2.username))

        # Grant change permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'You must be in group Dataset Manager to modify dataset permissions.'
                            .format(self.user2.username))

        # Revoke change permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'delete_change_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'You must be in group Dataset Manager to modify dataset permissions.'
                            .format(self.user2.username))

    def test_User_has_no_dataset_change_permission(self):
        """
        Tests whether managing datasets is possible if the user is a dataset manager but does not have 
        permission to change the dataset
        :return: 
        """

        logged_in = self.client.login(username=self.user.username, password=self.user_password)
        self.assertTrue(logged_in)

        # Make the user member of the group dataset managers
        dataset_manager_group = Group.objects.get(name='Dataset_Manager')
        dataset_manager_group.user_set.add(self.user)

        # Grant view permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_view_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'No permission to modify dataset permissions.'.format(self.user2.username))

        # Revoke view permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                    'delete_view_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'No permission to modify dataset permissions.'.format(self.user2.username))

        # Grant change permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'No permission to modify dataset permissions.'.format(self.user2.username))

        # Revoke change permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                    'delete_change_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'No permission to modify dataset permissions.'.format(self.user2.username))

    def test_User_is_dataset_manager(self):
        """
        Tests whether managing datasets is possible if the user is a dataset manager and has permission
        to change the dataset
        :return: 
        """

        logged_in = self.client.login(username=self.user.username, password=self.user_password)
        self.assertTrue(logged_in)

        # Make the user member of the group dataset managers
        dataset_manager_group = Group.objects.get(name='Dataset_Manager')
        dataset_manager_group.user_set.add(self.user)
        assign_perm('dictionary.change_dataset', self.user, self.test_dataset)

        # Grant view permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_view_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'View permission for user successfully granted.'
                            .format(self.user2.username, self.user2.first_name, self.user2.last_name))

        # Revoke view permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                    'delete_view_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'View (and change) permission for user successfully revoked.'
                            .format(self.user2.username))

        # Grant change permission without view permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'User does not have view permission for this dataset. Please grant view permission first.'
                            .format(self.user2.username, self.user2.first_name, self.user2.last_name))

        # Grant change permission with view permission
        # Grant view permission first
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_view_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # Grant change permission second
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'Change permission for user successfully granted.'
                            .format(self.user2.username))

        # Revoke change permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                    'delete_change_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'Change permission for user successfully revoked.'
                            .format(self.user2.username))


    def test_Set_default_language(self):
        """
        Tests
        :return: 
        """
        logged_in = self.client.login(username='test-user', password='test-user')
        self.assertTrue(logged_in)

        language = self.test_dataset.translation_languages.first()
        form_data = {'dataset_name': self.test_dataset.name, 'default_language': language.id}

        # Not a member of the group dataset managers
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'You must be in group Dataset Manager to modify dataset permissions.')

        # Make the user member of the group dataset managers
        dataset_manager_group = Group.objects.get(name='Dataset_Manager')
        dataset_manager_group.user_set.add(self.user)
        assign_perm('dictionary.change_dataset', self.user, self.test_dataset)
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, 'The default language of')

        # Try to add a language that is not in the translation language set of the test dataset
        language = Language(name="nonexistingtestlanguage", language_code_2char="ts", language_code_3char='tst')
        language.save()
        form_data = {'dataset_name': self.test_dataset.name, 'default_language': language.id}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        self.assertContains(response, '{} is not in the set of languages of dataset {}.'.format(
                                                            language.name, self.test_dataset.acronym))

class LemmaTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        assign_perm('dictionary.search_gloss', self.user)
        self.user.save()

        #Create the glosses
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        default_language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="lemma_with_gloss",
                                                              lemma=new_lemma, language=default_language)
        new_lemmaidglosstranslation.save()


        # Create a second lemma
        new_lemma2 = LemmaIdgloss(dataset=test_dataset)
        new_lemma2.save()

        # Create a lemma idgloss translation
        new_lemmaidglosstranslation2 = LemmaIdglossTranslation(text="lemma_without_gloss",
                                                              lemma=new_lemma2, language=default_language)
        new_lemmaidglosstranslation2.save()

        # Create a second lemma
        new_lemma3 = LemmaIdgloss(dataset=test_dataset)
        new_lemma3.save()

        # Create a lemma idgloss translation
        new_lemmaidglosstranslation3 = LemmaIdglossTranslation(text="lemma_that_does_not_match",
                                                              lemma=new_lemma3, language=default_language)
        new_lemmaidglosstranslation3.save()

        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # make some annotations for the new gloss
        test_annotation_translation_index = '1'
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss' + test_annotation_translation_index
            annotationIdgloss.save()

    def test_QueryLemmasWithoutGlosses(self):
        all_glosses = Gloss.objects.all()
        print('LemmaTests glosses: ', all_glosses)

        all_lemmas = LemmaIdgloss.objects.all()
        print('LemmaTests lemmas: ', all_lemmas)

        all_lemma_translations = LemmaIdglossTranslation.objects.all()
        print('LemmaTests translations: ', all_lemma_translations)

        client = Client(enforce_csrf_checks=False)
        client.login(username='test-user', password='test-user')

        #Get a dataset
        dataset_name = settings.DEFAULT_DATASET

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('view_dataset', self.user, test_dataset)
        self.user.save()

        # search for the lemma without glosses: test_lemma_without_gloss
        response = client.get('/dictionary/lemma/?lemma_en=without', follow=True)
        self.assertEqual(len(response.context['search_results']), 1)

        #Search lemmas with no glosses (no_glosses=1 is set to true aka 1), there are 2
        response = client.get('/dictionary/lemma/?no_glosses=1', follow=True)
        self.assertEqual(len(response.context['search_results']), 2)

        #Search lemmas that have glosses, there is only one
        response = client.get('/dictionary/lemma/?has_glosses=1', follow=True)
        self.assertEqual(len(response.context['search_results']), 1)

        response = client.post('/dictionary/lemma/', {'delete_lemmas': 'confirmed'}, follow=True)

        self.assertContains(response, 'You have no permission to delete lemmas.')

        assign_perm('dictionary.delete_lemmaidgloss', self.user)
        self.user.save()

        response = client.post('/dictionary/lemma/', {'delete_lemmas': 'confirmed'}, follow=True)
        self.assertContains(response, 'Incorrect deletion code.')

        response = client.post('/dictionary/lemma/', {'delete_lemmas': 'delete_lemmas'}, follow=True)
        self.assertContains(response, 'You do not have change permission on the dataset of the lemma you are atteempting to delete.')

        assign_perm('change_dataset', self.user, test_dataset)
        self.user.save()

        response = client.post('/dictionary/lemma/?lemma_en=without', {'delete_lemmas': 'delete_lemmas'}, follow=True)
        self.assertEqual(response.status_code,200)

        response = client.get('/dictionary/lemma/?lemma_en=without', follow=True)
        self.assertEqual(len(response.context['search_results']), 0)

        response = client.get('/dictionary/lemma/?lemma_en=does_not_match', follow=True)
        self.assertEqual(len(response.context['search_results']), 1)

        # delete the remaining lemma without glosses
        response = client.post('/dictionary/lemma/', {'delete_lemmas': 'delete_lemmas'}, follow=True)
        self.assertEqual(response.status_code,200)

        response = client.get('/dictionary/lemma/?no_glosses=1', follow=True)
        self.assertEqual(len(response.context['search_results']), 0)

        all_lemmas = LemmaIdgloss.objects.all()
        print('LemmaTests lemmas after delete: ', all_lemmas)

        all_lemma_translations = LemmaIdglossTranslation.objects.all()
        print('LemmaTests translations after delete: ', all_lemma_translations)

class HandshapeTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        assign_perm('dictionary.search_gloss', self.user)
        assign_perm('dictionary.add_gloss', self.user)
        assign_perm('dictionary.change_gloss', self.user)
        self.user.save()

        self.field_choice_handedness_1 = FieldChoice.objects.filter(field='Handeness', machine_value__gt=1).first()
        self.field_choice_handedness_2 = FieldChoice.objects.filter(field='Handeness', machine_value__gt=1).last()

        print('HandshapeTests setUp.')
        used_machine_values = [ h.machine_value for h in Handshape.objects.filter(machine_value__gt=1) ]
        max_used_machine_value = max(used_machine_values)

        # create two arbitrary new Handshapes

        self.test_handshape1 = Handshape(machine_value=max_used_machine_value+1, name='thisisatemporarytesthandshape1')
        self.test_handshape1.save()

        self.test_handshape2 = Handshape(machine_value=max_used_machine_value+2, name='thisisatemporarytesthandshape2')
        self.test_handshape2.save()

        print('New handshape ', self.test_handshape1.machine_value, ' created: ', self.test_handshape1.name)
        print('New handshape ', self.test_handshape2.machine_value, ' created: ', self.test_handshape2.name)

        from signbank.dictionary.admin import HandshapeAdmin

        self.factory = RequestFactory()

        self.handshape_admin = HandshapeAdmin(model=Handshape, admin_site=signbank)

    def create_handshape(self):

        used_machine_values = [h.machine_value for h in Handshape.objects.filter(machine_value__gt=1)]
        max_used_machine_value = max(used_machine_values)
        print('create_handshape: max_used_machine_value: ', max_used_machine_value)
        new_machine_value = max_used_machine_value + 1
        new_name = 'thisisanewtesthandshape_en'

        new_handshape = Handshape(machine_value=new_machine_value, name=new_name)
        new_handshape.save()

        print('New handshape ', new_handshape.machine_value, ' created: ', new_handshape.name)

        return new_handshape

    def test_create_handshape(self):

        print('HandshapeTests test_create_handshape')
        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('view_dataset', self.user, test_dataset)
        assign_perm('change_dataset', self.user, test_dataset)

        self.client.login(username='test-user', password='test-user')

        #Add info of the dataset to the session (normally done in the details)
        self.client.session['datasetid'] = test_dataset.pk
        self.client.session['search_results'] = None
        self.client.session.save()

        new_handshape = self.create_handshape()
        #We can now request a details
        print('Test HandshapeDetailView for new handshape.')
        response = self.client.get('/dictionary/handshape/'+str(new_handshape.machine_value), follow=True)
        self.assertEqual(response.status_code,200)


    def test_handshape_choices(self):

        print('HandshapeTests test_handshape_choices')

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('view_dataset', self.user, test_dataset)
        assign_perm('change_dataset', self.user, test_dataset)

        # Create 10 lemmas for use in testing
        language = Language.objects.get(id=get_default_language_id())
        lemmas = {}
        for lemma_id in range(1,4):
            new_lemma = LemmaIdgloss(dataset=test_dataset)
            new_lemma.save()
            new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation" + str(lemma_id),
                                                                  lemma=new_lemma, language=language)
            new_lemmaidglosstranslation.save()
            lemmas[lemma_id] = new_lemma

        # Create 10 glosses that start out being the same
        glosses = {}
        for gloss_id in range(1,4):
            gloss_data = {
                'lemma' : lemmas[gloss_id],
                'handedness': self.field_choice_handedness_1,
                'domhndsh': self.test_handshape1,
                'subhndsh': self.test_handshape2,
            }
            new_gloss = Gloss(**gloss_data)
            new_gloss.save()
            for language in test_dataset.translation_languages.all():
                language_code_2char = language.language_code_2char
                annotationIdgloss = AnnotationIdglossTranslation()
                annotationIdgloss.gloss = new_gloss
                annotationIdgloss.language = language
                annotationIdgloss.text = 'thisisatemporarytestgloss_' + language_code_2char + str(gloss_id)
                annotationIdgloss.save()
            glosses[gloss_id] = new_gloss

        # Set up the fields of the new glosses to differ by one phonology field to glosses[1]
        # gloss 1 doesn't set the repeat or altern fields, they are left as whatever the default is

        self.client.login(username='test-user', password='test-user')

        new_handshape = self.create_handshape()

        #We can now request a details
        print('Test HandshapeDetailView for new handshape.')
        response = self.client.get('/dictionary/handshape/'+str(new_handshape.machine_value), follow=True)
        self.assertEqual(response.status_code,200)

        new_handshape_value_string = '_' + str(new_handshape.machine_value)
        # Find out if the new handshape appears in the Handshape Choice menus
        print("Update a gloss to use the new handshape, using the choice list")
        self.client.post('/dictionary/update/gloss/'+str(glosses[1].pk),{'id':'domhndsh','value':new_handshape_value_string})

        changed_gloss = Gloss.objects.get(pk = glosses[1].pk)
        print('Confirm the gloss was updated to the new handshape.')
        self.assertEqual(changed_gloss.domhndsh.machine_value, new_handshape.machine_value)

    def test_delete_handshape(self):

        from signbank.tools import gloss_handshape_fields
        gloss_handshape_fields = gloss_handshape_fields()
        # create a gloss with and without handshape choices

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # now set all the choice fields of the gloss to the first choice of FieldChoice
        # it doesn't matter exactly which one, as long as the same one is used to check existence later

        request = self.factory.get('/'+settings.ADMIN_URL+'/dictionary/handshape/')
        request.user = self.user

        # give the test user permission to delete handshapes
        handshape_options = Handshape.objects.filter(machine_value__gt=1)
        for fc in handshape_options:
            assign_perm('delete_handshape', self.user, fc)
        self.user.save()

        for handshape_field in gloss_handshape_fields:
            # get the first choice for the field
            if handshape_options:
                handshape_in_use = handshape_options.first()
                setattr(new_gloss, handshape_field, handshape_in_use)
        new_gloss.save()

        if handshape_options:
            handshape_in_use = handshape_options.first()
            print('Handshape in use: ', handshape_in_use.name)
            print('Test cannot delete Handshape: ', handshape_in_use.name)
            self.assertEqual(self.handshape_admin.has_delete_permission(request=request, obj=handshape_in_use), False)

        # now do the same with the second choice
        # this time, there are no glosses with that choice
        # the test makes sure it can be deleted in admin
        if handshape_options:
            # a different field choice is chosen than that of the test gloss
            handshape_not_in_use = handshape_options.last()  # This assumes there is more than one
            print('Handshape not in use: ', handshape_not_in_use.name)
            print('Test can delete Handshape: ', handshape_not_in_use.name)
            self.assertEqual(self.handshape_admin.has_delete_permission(request=request, obj=handshape_not_in_use), True)


class MultipleSelectTests(TestCase):

    def setUp(self):
        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        assign_perm('dictionary.search_gloss', self.user)
        assign_perm('dictionary.add_gloss', self.user)
        assign_perm('dictionary.change_gloss', self.user)
        self.user.save()

        self.handedness_fieldchoice_1 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).first()
        self.handedness_fieldchoice_2 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).last()

    def create_semanticfield(self):

        used_machine_values = [s.machine_value for s in SemanticField.objects.all()]
        max_used_machine_value = max(used_machine_values)
        print('create_semanticfield: max_used_machine_value: ', max_used_machine_value)
        new_machine_value = max_used_machine_value + 1
        new_english_name = 'thisisanewtestsemanticfield_'+str(new_machine_value)+'_en'
        dutch_language = Language.objects.get(language_code_2char='nl')
        new_dutch_name = 'thisisanewtestsemanticfield_'+str(new_machine_value)+'_nl'

        # English is the default language, included in the SemanticField object as 'name'
        # Under the FieldChoice model, this used to be english_name
        new_semanticfield = SemanticField(machine_value=new_machine_value, name=new_english_name)
        new_semanticfield.save()

        # Make a translation for Dutch since it is the other language of the test dataset
        new_semanticfield_translation = SemanticFieldTranslation(semField=new_semanticfield, language=dutch_language, name=new_dutch_name)
        new_semanticfield_translation.save()

        print('New semantic field ', new_semanticfield.machine_value, ' created: ', new_semanticfield.name)

        return new_semanticfield

    def test_SemanticField(self):

        # Create the glosses
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        #Create a client and log in
        client = Client(enforce_csrf_checks=False)
        client.login(username='test-user', password='test-user')
        assign_perm('view_dataset', self.user, test_dataset)

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporaryidgloss_"+ language.language_code_2char,
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        new_semanticfield = self.create_semanticfield()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.handedness = self.handedness_fieldchoice_1
        # save the gloss so it can be used in the ManyToMany relation of SemanticField added to the gloss below
        new_gloss.save()

        # make some annotations for the new gloss
        # This is necessary to test Searching, which does a sort on the annotation for the gloss, it can't be non-existent or empty
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporaryannotationidgloss_' + language.language_code_2char
            annotationIdgloss.save()

        new_gloss.semField.clear()
        new_gloss.semField.add(new_semanticfield)
        new_gloss.save()

        print('New gloss ', new_gloss.idgloss, ' created with semantic field ', new_semanticfield.name)
        #Search on the new field
        #It is multi-select so the semField parameter has [] after it
        response = client.get('/signs/search/', {'semField[]':new_semanticfield.machine_value}, follow=True)

        # check that the new gloss is found when searching on the new semantic field
        print('Search for the gloss on semantic field.')
        self.assertEqual(len(response.context['object_list']), 1)

        # Add another semantic field to the gloss
        new_semanticfield_2 = self.create_semanticfield()

        new_gloss.semField.add(new_semanticfield_2)
        new_gloss.save()
        print('Semantic field ', new_semanticfield_2.name, ' added to gloss.')

        #Search on the new field
        #It is multi-select so the semField parameter has [] after it
        response = client.get('/signs/search/', {'semField[]':[ new_semanticfield.machine_value, new_semanticfield_2.machine_value] }, follow=True)

        # check that the new gloss is found when searching on the new semantic field
        print('Search for the gloss on both semantic fields.')
        self.assertEqual(len(response.context['object_list']), 1)


class FieldChoiceTests(TestCase):

    from reversion.admin import VersionAdmin

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user(username='test-user',
                                             email='example@example.com',
                                             password='test-user',
                                             is_superuser=True,
                                             is_staff=True)

        self.user_password = 'test_user'

        # set the test dataset
        self.dataset_name = settings.DEFAULT_DATASET
        self.test_dataset = Dataset.objects.get(name=self.dataset_name)

        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        self.user.user_permissions.add(Permission.objects.get(name='Can add gloss'))
        self.user.user_permissions.add(Permission.objects.get(name='Can add field choice'))
        self.user.user_permissions.add(Permission.objects.get(name='Can change field choice'))
        self.user.user_permissions.add(Permission.objects.get(name='Can delete field choice'))

        self.client = Client()
        self.client.login(username=self.user.username, password=self.user_password)

        from signbank.dictionary.admin import FieldChoiceAdmin

        self.factory = RequestFactory()

        self.fieldchoice_admin = FieldChoiceAdmin(model=FieldChoice, admin_site=signbank)

    def test_update_field_choice(self):
        from signbank.tools import fields_with_choices_glosses
        fields_with_choices = fields_with_choices_glosses()

        client = Client(enforce_csrf_checks=False)
        client.login(username='test-user', password='test-user')

        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options.count() == 0:
                # skip testing field choices with no data
                continue
            first_field_choice_option = field_options.first()
            admin_url_change_suffix_1 = str(first_field_choice_option.id)+\
                                      '/change/?_changelist_filters=field__exact%3D'+first_field_choice_option.field

            initial_data = dict()
            initial_data['field'] = first_field_choice_option.field
            initial_data['machine_value'] = first_field_choice_option.machine_value
            initial_data['name'] = first_field_choice_option.name
            initial_data['field_color'] = first_field_choice_option.field_color
            for language in MODELTRANSLATION_LANGUAGES:
                name_languagecode = 'name_' + language.replace('-', '_')
                try:
                    field_value = getattr(first_field_choice_option,name_languagecode)
                except KeyError:
                    continue
                if not field_value:
                    initial_data[name_languagecode] = 'Default value'
                else:
                    initial_data[name_languagecode] = field_value

            # data to be given to the form
            # English is used as the language to be updated
            LANGUAGE_FIELD_TO_UPDATE = 'name_en'

            update_data = dict()
            update_data['field'] = first_field_choice_option.field
            update_data['machine_value'] = first_field_choice_option.machine_value
            update_data['name'] = first_field_choice_option.name
            # the hash tag is needed in the form interface for display
            update_data['field_color'] = '#' + first_field_choice_option.field_color
            for language in MODELTRANSLATION_LANGUAGES:
                name_languagecode = 'name_' + language.replace('-', '_')
                try:
                    field_value = getattr(first_field_choice_option,name_languagecode)
                except KeyError:
                    continue
                if name_languagecode == LANGUAGE_FIELD_TO_UPDATE:
                    update_data[LANGUAGE_FIELD_TO_UPDATE] = 'Test Update Field Choice'
                elif not field_value:
                    update_data[name_languagecode] = 'Default value'
                else:
                    update_data[name_languagecode] = field_value

            url_of_field_choice_change = '/'+settings.ADMIN_URL + '/dictionary/fieldchoice/'+admin_url_change_suffix_1
            print('Attempt to change fieldchoice url: ', url_of_field_choice_change)
            print('With data: ', update_data)

            response = self.client.get(url_of_field_choice_change, update_data)
            self.assertEqual(response.status_code, 302)

            fieldchoice_form = FieldChoiceForm(instance=first_field_choice_option, data=update_data)

            cleaned = fieldchoice_form.is_valid()
            self.assertTrue(cleaned)

            self.fieldchoice_admin.save_model(obj=first_field_choice_option,
                                              request=response.__dict__['request'],
                                              form=fieldchoice_form,
                                              change=True)

            first_field_choice_option.refresh_from_db()

            # check that the updated field is indeed updated
            # check that none of the other fields were updated
            self.assertEqual(first_field_choice_option.field, initial_data['field'])
            self.assertEqual(first_field_choice_option.machine_value, initial_data['machine_value'])
            self.assertEqual(first_field_choice_option.field_color, initial_data['field_color'])
            for language in MODELTRANSLATION_LANGUAGES:
                name_languagecode = 'name_' + language.replace('-', '_')
                if name_languagecode not in update_data.keys():
                    continue
                if name_languagecode == LANGUAGE_FIELD_TO_UPDATE:
                    self.assertEqual(getattr(first_field_choice_option,LANGUAGE_FIELD_TO_UPDATE), update_data[LANGUAGE_FIELD_TO_UPDATE])
                else:
                    self.assertEqual(getattr(first_field_choice_option,name_languagecode), initial_data[name_languagecode])

            # the following is true if the override language is en, then name has also been updated
            # self.assertEqual(first_field_choice_option.name, update_data['name'])




    def test_delete_fieldchoice_gloss(self):

        from signbank.tools import fields_with_choices_glosses
        fields_with_choices = fields_with_choices_glosses()
        # create a gloss with and without field choices

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # now set all the choice fields of the gloss to the first choice of FieldChoice
        # it doesn't matter exactly which one, as long as the same one is used to check existence later

        request = self.factory.get('/'+settings.ADMIN_URL + '/dictionary/fieldchoice/')
        request.user = self.user

        # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        for fieldchoice in fields_with_choices.keys():
            # get the first choice for the field
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                for fieldname in fields_with_choices[fieldchoice]:
                    setattr(new_gloss, fieldname, field_choice_in_use)
        new_gloss.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no glosses with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                # a different field choice is chosen than that of the test gloss
                field_choice_not_in_use = field_options.last()  # This assumes there is more than one
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_not_in_use), True)

    def test_delete_fieldchoice_handshape(self):

        from signbank.tools import fields_with_choices_handshapes
        fields_with_choices_handshapes = fields_with_choices_handshapes()

        #Create the handshape
        new_handshape = Handshape(name="thisisatemporarytesthandshape")
        new_handshape.save()

        new_handshape.machine_value = new_handshape.pk
        new_handshape.save()

        # now set all the choice fields of the gloss to the first choice of FieldChoice
        # it doesn't matter exactly which one, as long as the same one is used to check existence later

        request = self.factory.get('/'+settings.ADMIN_URL + '/dictionary/fieldchoice/')
        request.user = self.user

        # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices_handshapes.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        for fieldchoice in fields_with_choices_handshapes.keys():
            # get the first choice for the field
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                for fieldname in fields_with_choices_handshapes[fieldchoice]:
                    setattr(new_handshape, fieldname, field_choice_in_use)
                # for FingerSelection, set the Boolean fields of the fingers
                if fieldchoice == 'FingerSelection':
                    new_handshape.set_fingerSelection_display()
                    new_handshape.set_fingerSelection2_display()
                    new_handshape.set_unselectedFingers_display()
        new_handshape.save()

        print('TEST: new handshape created: ', new_handshape.__dict__)
        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices_handshapes.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no glosses with that choice
        # the test makes sure it can be deleted in admin
        for field_value in fields_with_choices_handshapes.keys():

            field_options = FieldChoice.objects.filter(field=field_value, machine_value__gt=1)
            for opt in field_options:
                if field_value in ['FingerSelection']:
                    print('TEST: test whether has_change_permission is False for FingerSelection choice ', opt.name)
                    self.assertEqual(self.fieldchoice_admin.has_change_permission(request=request, obj=opt), False)
                queries_h = [Q(**{ field_name + '__machine_value' : opt.machine_value })
                             for field_name in fields_with_choices_handshapes[field_value]]
                query_h = queries_h.pop()
                for item in queries_h:
                    query_h |= item
                field_is_in_use = Handshape.objects.filter(query_h).count()
                if field_is_in_use > 0:
                    print('TEST: test whether has_delete_permission is False for ', field_value, ' choice ', str(opt.name), ' (in use)')
                    self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=opt), False)
                else:
                    print('TEST: test whether has_delete_permission is True for ', field_value, ' choice ', str(opt.name), ' (not used)')
                    self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=opt), True)

    def test_delete_fieldchoice_definition(self):

        # delete fieldchoice for NoteType

        from signbank.tools import fields_with_choices_definition
        fields_with_choices = fields_with_choices_definition()
        # create a gloss with and without field choices

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # now set all the choice field of the role to the first choice of FieldChoice

        #Create a definition
        new_definition = Definition(gloss=new_gloss, text="thisisatemporarytestnote", count=1, published=True)

        # set the role to the first choice
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                for field in fields_with_choices[fieldchoice]:
                    setattr(new_definition, field, field_choice_in_use)
        new_definition.save()

        print('TEST new definition created: ', new_definition.__dict__)

        request = self.factory.get('/'+settings.ADMIN_URL + '/dictionary/fieldchoice/')
        request.user = self.user

        # # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                print('TEST: test whether has_delete_permission is False for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.name), ' (in use)')
                count_fields_with_same_machine_value = FieldChoice.objects.filter(
                                field=fieldchoice, machine_value=field_choice_in_use.machine_value).count()
                if count_fields_with_same_machine_value > 1:
                    # the user is allowed to delete duplicate machine values in the Admin
                    self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), True)
                else:
                    self.assertEqual(
                        self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no notes with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_not_in_use = field_options.last()  # This assumes there is more than one
                print('TEST: test whether has_delete_permission is True for ', fieldchoice, ' choice ',
                      str(field_choice_not_in_use.name), ' (not used)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_not_in_use), True)

    def test_delete_fieldchoice_morphology_definition(self):

        # delete fieldchoice for morphology definition

        from signbank.tools import fields_with_choices_morphology_definition
        fields_with_choices = fields_with_choices_morphology_definition()

        # create a gloss with and without field choices
        # a second gloss is created to be the morpheme of the new morphology definition

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create two lemmas
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        new_lemma2 = LemmaIdgloss(dataset=test_dataset)
        new_lemma2.save()

        # Create a two lemma idgloss translations
        language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        # Create a lemma idgloss translation
        new_lemmaidglosstranslation2 = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation2",
                                                              lemma=new_lemma2, language=language)
        new_lemmaidglosstranslation2.save()

        #Create two glosses
        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.save()

        new_gloss2 = Gloss()
        new_gloss2.lemma = new_lemma2
        new_gloss2.save()

        # now set all the choice field of the role to the first choice of FieldChoice

        #Create a definition
        new_morphology_definition = MorphologyDefinition(parent_gloss=new_gloss, morpheme=new_gloss2)

        # set the morphology definition role to the first choice
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                for field in fields_with_choices[fieldchoice]:
                    setattr(new_morphology_definition, field, field_choice_in_use)
        new_morphology_definition.save()

        print('TEST new morphology definition created: ', new_morphology_definition.__dict__)

        request = self.factory.get('/'+settings.ADMIN_URL + '/dictionary/fieldchoice/')
        request.user = self.user

        # # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                print('TEST: test whether has_delete_permission is False for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.name), ' (in use)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no notes with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_not_in_use = field_options.last()
                print('TEST: test whether has_delete_permission is True for ', fieldchoice, ' choice ',
                      str(field_choice_not_in_use.name), ' (not used)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_not_in_use), True)

    def test_delete_fieldchoice_othermediatype(self):

        # delete fieldchoice for OtherMediaType

        from signbank.tools import fields_with_choices_other_media_type
        fields_with_choices = fields_with_choices_other_media_type()

        # create a gloss with and without field choices

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # now set all the choice field of the role to the first choice of FieldChoice

        #Create a definition
        new_othermedia = OtherMedia(parent_gloss=new_gloss,
                                    alternative_gloss="thisisatemporaryalternativegloss",
                                    path=str(new_gloss.id)+'/'+new_gloss.idgloss+'.mp4')

        # set the other media type to the first choice
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                for field in fields_with_choices[fieldchoice]:
                    setattr(new_othermedia, field, field_choice_in_use)
        new_othermedia.save()

        print('TEST new othermedia created: ', new_othermedia.__dict__)

        request = self.factory.get('/'+settings.ADMIN_URL + '/dictionary/fieldchoice/')
        request.user = self.user

        # # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                print('TEST: test whether has_delete_permission is False for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.name), ' (in use)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no notes with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_not_in_use = field_options.last()
                print('TEST: test whether has_delete_permission is True for ', fieldchoice, ' choice ',
                      str(field_choice_not_in_use.name), ' (not used)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_not_in_use), True)

    def test_delete_fieldchoice_morpheme_type(self):

        # delete fieldchoice for morpheme type

        from signbank.tools import fields_with_choices_morpheme_type
        fields_with_choices = fields_with_choices_morpheme_type()
        # create a gloss with and without field choices

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create a lemma
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.save()

        # create a morpheme object for the gloss
        new_morpheme = Morpheme(gloss_ptr_id=new_gloss.id)

        # now set all the choice field of the role to the first choice of FieldChoice

        # set the morpheme type to the first choice
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                for field in fields_with_choices[fieldchoice]:
                    setattr(new_gloss, field, field_choice_in_use)
                    setattr(new_morpheme, field, field_choice_in_use)
        new_gloss.save()
        new_morpheme.save()

        print('TEST new morpheme created: ', new_morpheme.__dict__)

        request = self.factory.get('/'+settings.ADMIN_URL + '/dictionary/fieldchoice/')
        request.user = self.user

        # # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                field_choice_in_use = field_options.first()
                print('TEST: test whether has_delete_permission is False for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.name), ' (in use)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no notes with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice, machine_value__gt=1)
            if field_options:
                # a different field choice is chosen than that of the test morpheme
                field_choice_not_in_use = field_options.last()
                print('TEST: test whether has_delete_permission is True for ', fieldchoice, ' choice ',
                          str(field_choice_not_in_use.name), ' (not used)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_not_in_use), True)

class testFrequencyAnalysis(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.save()

        self.client = Client()

        used_machine_values = [ h.machine_value for h in Handshape.objects.all() ]
        max_used_machine_value = max(used_machine_values)

        # create two arbitrary new Handshapes

        self.test_handshape1 = Handshape(machine_value=max_used_machine_value+1, name='thisisatemporarytesthandshape1')
        self.test_handshape1.save()

        self.test_handshape2 = Handshape(machine_value=max_used_machine_value+2, name='thisisatemporarytesthandshape2')
        self.test_handshape2.save()

        self.test_handshape_fieldchoice_1 = FieldChoice(field='Handshape', machine_value=max_used_machine_value + 1,
                                         name='thisisatemporarytesthandshape1')
        self.test_handshape_fieldchoice_1.save()

        self.test_handshape_fieldchoice_2 = FieldChoice(field='Handshape', machine_value=max_used_machine_value + 2,
                                         name='thisisatemporarytesthandshape2')
        self.test_handshape_fieldchoice_2.save()

        self.locprim_fieldchoice_1 = FieldChoice.objects.filter(field='Location', machine_value__gt=1).first()
        self.locprim_fieldchoice_2 = FieldChoice.objects.filter(field='Location', machine_value__gt=1).last()

        self.handedness_fieldchoice_1 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).first()
        self.handedness_fieldchoice_2 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).last()

        self.handch_fieldchoice_1 = FieldChoice.objects.filter(field='HandshapeChange', machine_value__gt=1).first()
        self.handch_fieldchoice_2 = FieldChoice.objects.filter(field='HandshapeChange', machine_value__gt=1).last()

        self.nament_fieldchoice_1 = FieldChoice.objects.filter(field='NamedEntity', machine_value__gt=1).first()
        self.nament_fieldchoice_2 = FieldChoice.objects.filter(field='NamedEntity', machine_value__gt=1).last()

    def test_analysis_frequency(self):

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        language = Language.objects.get(id=get_default_language_id())
        lemmas = {}
        for lemma_id in range(1,10):
            new_lemma = LemmaIdgloss(dataset=test_dataset)
            new_lemma.save()
            new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation" + str(lemma_id),
                                                                  lemma=new_lemma, language=language)
            new_lemmaidglosstranslation.save()
            lemmas[lemma_id] = new_lemma

        glosses = {}
        for gloss_id in range(1,10):
            gloss_data = {
                'lemma' : lemmas[gloss_id],
                'handedness': self.handedness_fieldchoice_1,
                'domhndsh': self.test_handshape1,
                'subhndsh': self.test_handshape2,
                'locprim': self.locprim_fieldchoice_1,
            }
            new_gloss = Gloss(**gloss_data)
            new_gloss.save()
            for language in test_dataset.translation_languages.all():
                language_code_2char = language.language_code_2char
                annotationIdgloss = AnnotationIdglossTranslation()
                annotationIdgloss.gloss = new_gloss
                annotationIdgloss.language = language
                annotationIdgloss.text = 'thisisatemporarytestgloss_' + language_code_2char + str(gloss_id)
                annotationIdgloss.save()
            glosses[gloss_id] = new_gloss

        glosses[2].locprim = self.locprim_fieldchoice_2
        glosses[2].save()

        glosses[3].handedness = self.handedness_fieldchoice_2
        glosses[3].save()

        glosses[4].handCh = self.handch_fieldchoice_1
        glosses[4].save()

        glosses[5].domhndsh = self.test_handshape2
        glosses[5].save()

        glosses[6].handedness = self.handedness_fieldchoice_1
        glosses[6].save()

        glosses[7].domhndsh = self.test_handshape2
        glosses[7].save()

        glosses[8].namEnt = self.nament_fieldchoice_1
        glosses[8].save()

        glosses[9].handedness = self.handedness_fieldchoice_2
        glosses[9].save()

        self.client.login(username='test-user', password='test-user')

        assign_perm('view_dataset', self.user, test_dataset)

        response = self.client.get('/analysis/frequencies/', follow=True)
        self.assertEqual(response.status_code,200)

        table_code = str(test_dataset.id) + '_results_'

        frequency_dict = test_dataset.generate_frequency_dict()
        for fieldname in frequency_dict.keys():
            self.assertContains(response, table_code + fieldname)

        table_code_empty_prefix = str(test_dataset.id) + '_field_'
        table_code_empty_suffix = '_empty_frequency'
        # empty frequencies are displayed in the Frequency Analysis with the suffix _empty_frequency as an id
        # this enables hiding empty frequencies
        # this test makes use of that encoding to determine if the suffix should appear in the table
        for (k,d) in frequency_dict.items():
            for (c,v) in d.items():
                datasetId_fieldCategory_FCname_emptySuffix = table_code_empty_prefix + k + '_' + c + table_code_empty_suffix
                if v not in ['-', 'N/A']:
                    self.assertNotContains(response, datasetId_fieldCategory_FCname_emptySuffix, html=True)
                else:
                    self.assertContains(response, datasetId_fieldCategory_FCname_emptySuffix, html=True)


    def test_frequency_sorting(self):

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        from django.utils import translation
        for language_code in settings.MODELTRANSLATION_LANGUAGES:
            translation.activate(language_code)

            frequency_dict = test_dataset.generate_frequency_dict()
            frequency_dict_keys = frequency_dict.keys()

            frequency_fields = FIELDS['phonology'] + FIELDS['semantics']

            fields_data = []
            for field_name in frequency_fields:
                gloss_field = Gloss._meta.get_field(field_name)
                if hasattr(gloss_field, 'field_choice_category'):
                    fields_data.append((field_name, gloss_field.verbose_name.title(), gloss_field.field_choice_category))
                elif isinstance(gloss_field, models.ForeignKey) and gloss_field.related_model == Handshape:
                    fields_data.append(
                        (field_name, gloss_field.verbose_name.title(), 'Handshape'))
                elif field_name == 'semField':
                    fields_data.append(
                        (field_name, gloss_field.verbose_name.title(), 'SemField'))
                elif field_name == 'derivHist':
                    fields_data.append(
                        (field_name, gloss_field.verbose_name.title(), 'derivHist'))
            fields_data_keys = [f_name for (f_name,v_verbose,c_category) in fields_data]

            self.assertNotEqual(len(fields_data),0)
            self.assertEqual(len(frequency_dict_keys), len(fields_data_keys))

            ordered_fields_data = sorted(fields_data, key=lambda x: x[1])
            for (f, field_verbose_name, fieldchoice_category) in ordered_fields_data:
                if fieldchoice_category == 'Handshape':
                    choice_list = list(Handshape.objects.filter(machine_value__lte=1).
                                    order_by('machine_value').distinct()) \
                                + list(Handshape.objects.filter(machine_value__gt=1)
                                        .distinct().order_by('name'))
                elif fieldchoice_category == 'SemField':
                    choice_list = list(SemanticField.objects.filter(machine_value__lte=1).
                                    order_by('machine_value').distinct()) \
                                + list(SemanticField.objects.filter(machine_value__gt=1)
                                        .distinct().order_by('name'))
                elif fieldchoice_category == 'derivHist':
                    choice_list = list(DerivationHistory.objects.filter(machine_value__lte=1).
                                    order_by('machine_value').distinct()) \
                                + list(DerivationHistory.objects.filter(machine_value__gt=1)
                                        .distinct().order_by('name'))
                else:
                    choice_list = list(FieldChoice.objects.filter(field__iexact=fieldchoice_category, machine_value__lte=1).
                                    order_by('machine_value').distinct()) \
                                + list(FieldChoice.objects.filter(field__iexact=fieldchoice_category, machine_value__gt=1)
                                        .distinct().order_by('name'))
                if len(choice_list) > 0:
                    translated_choices = list(OrderedDict([(choice.name, choice.machine_value) for choice in choice_list]).keys())
                else:
                    translated_choices = []

                frequency_choices_f = frequency_dict[f]
                frequency_choices_f_keys = list(frequency_choices_f.keys())

                self.assertEqual(len(translated_choices), len(frequency_choices_f))

                # Make sure the sorted field choices are in the same order
                self.assertEqual(translated_choices, frequency_choices_f_keys)


class testSettings(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.save()

    def test_Settings(self):

        from os.path import isfile, join
        full_root_path = settings.BASE_DIR + 'signbank' + os.sep + 'settings' + os.sep + 'server_specific'
        all_settings = [ f for f in os.listdir(full_root_path) if isfile(join(full_root_path, f))
                                    and f.endswith('.py') and f != '__init__.py' and f != 'server_specific.py']
        print('Checking settings files: ', all_settings)
        # check that one of the files is the default file
        self.assertIn('default.py', all_settings)
        all_settings_strings = {}
        for next_file in all_settings:
            all_settings_strings[next_file] = []
            next_file_path = os.path.join(full_root_path, next_file)
            with open(next_file_path, 'r') as f:
                for line in f:
                    if '#' in line:
                        line = line.split('#')
                        string_before_hash = line[0]
                        line = string_before_hash.strip()
                    if '=' in line:
                        definition_list = line.split('=')
                        right_hand_side = definition_list[1]
                        right_hand_side = right_hand_side.strip()
                        if right_hand_side.startswith('lambda'):
                            # this is a function definition
                            # this is a bit of a hack because a function is used in the global settings
                            continue
                        definition = definition_list[0]
                        definition = definition.strip()
                        all_settings_strings[next_file].append(definition)

        comparison_table_first_not_in_second = {}
        for first_file in all_settings:
            if not first_file in comparison_table_first_not_in_second.keys():
                comparison_table_first_not_in_second[first_file] = {}
            for second_file in all_settings:
                if first_file != second_file:
                    comparison_table_first_not_in_second[first_file][second_file] = []
                    for setting_first_file in all_settings_strings[first_file]:
                        if setting_first_file in ['SECRET_KEY', 'SWITCH_TO_MYSQL', 'FILE_UPLOAD_MAX_MEMORY_SIZE']:
                            # skip these, since server specific
                            continue
                        if setting_first_file not in all_settings_strings[second_file]:
                            comparison_table_first_not_in_second[first_file][second_file].append(setting_first_file)

        second_file = 'default.py'
        for first_file in all_settings:
            # the default.py file is part of the installation (should this filename be a setting?)
            # check that other settings files do not contain settings that are not in the default settings file
            if first_file != second_file:
                self.assertEqual(comparison_table_first_not_in_second[first_file][second_file],[])

    def test_settings_field_choice_category(self):
        # this test checks that fieldnames in settings exist in the models
        # this can catch spelling errors in the settings
        # next, the test checks that for fields with choice lists that the field_choice_category is defined
        # and that there exist field choices for it
        # this test is intended to help find potential errors in templates that use choice lists for fields
        if 'phonology' in settings.FIELDS.keys():
            phonology_fields = settings.FIELDS['phonology']
            gloss_fields_names = { f.name: f for f in Gloss._meta.fields }
            print('Testing phonology fields for declaration in Gloss model with field_choice_category in FieldChoice table.')
            for f in phonology_fields:
                # make sure all phonology fields in settings are defined in Gloss
                try:
                    gloss_field = Gloss._meta.get_field(f)
                    field_exists = True
                except (KeyError, ObjectDoesNotExist):
                    field_exists = False
                self.assertTrue(field_exists)
                if not field_exists:
                    continue
                # make sure the field_choice_category attribute (only) appears on fields we expect to have choice lists
                if isinstance(gloss_field, models.ForeignKey) and gloss_fields_names[f].related_model == Handshape:
                    self.assertEqual(fieldname_to_kind_table[f], 'list')
                elif not isinstance(gloss_field, FieldChoiceForeignKey):
                    # field is instance of: NullBooleanField, IntegerField, TextField, DateField, DateTimeField, ForeignKey, ManyToManyField
                    self.assertFalse(hasattr(gloss_field, 'field_choice_category'))
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                elif not hasattr(gloss_field, 'field_choice_category'):
                    # this is not a choice list field
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                else:
                    # we expect the field to be a choice list field and to have field_choice_category defined
                    self.assertEqual(fieldname_to_kind_table[f], 'list')
                    self.assertTrue(hasattr(gloss_field, 'field_choice_category'))
                    fc_category = gloss_field.field_choice_category
                    # make sure there are fields for the category
                    fields_for_this_category = FieldChoice.objects.filter(field__iexact=fc_category)
                    self.assertGreater(len(fields_for_this_category),0)

        if 'semantics' in settings.FIELDS.keys():
            semantics_fields = settings.FIELDS['semantics']
            print('Testing semantics fields for declaration in Gloss model with field_choice_category in FieldChoice table.')
            for f in semantics_fields:
                # make sure all semantics fields are defined in Gloss
                try:
                    gloss_field = Gloss._meta.get_field(f)
                    field_exists = True
                except (KeyError, ObjectDoesNotExist):
                    field_exists = False
                self.assertTrue(field_exists)
                if not field_exists:
                    continue

                # make sure the field_choice_category attribute (only) appears on fields we expect to have choice lists
                if f in ['semField', 'derivHist']:
                    self.assertEqual(fieldname_to_kind_table[f], 'list')
                elif not isinstance(gloss_field, FieldChoiceForeignKey):
                    # field is instance of: NullBooleanField, IntegerField, TextField, DateField, DateTimeField, ForeignKey, ManyToManyField
                    self.assertFalse(hasattr(gloss_field, 'field_choice_category'))
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                elif not hasattr(gloss_field, 'field_choice_category'):
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                else:
                    # we expect the field to be a choice list field and have field_choice_category defined
                    self.assertEqual(fieldname_to_kind_table[f], 'list')
                    self.assertTrue(hasattr(gloss_field, 'field_choice_category'))
                    fc_category = gloss_field.field_choice_category
                    # make sure there are fields for the category
                    fields_for_this_category = FieldChoice.objects.filter(field__iexact=fc_category, machine_value__gt=1)
                    self.assertGreater(len(fields_for_this_category),0)

        if 'handshape' in settings.FIELDS.keys():
            handshape_fields = settings.FIELDS['handshape']
            print('Testing handshape fields for declaration in Handshape model with field_choice_category in FieldChoice table.')
            for f in handshape_fields:
                # make sure all handshape fields are defined in Gloss
                try:
                    handshape_field = Handshape._meta.get_field(f)
                    field_exists = True
                except (KeyError, ObjectDoesNotExist):
                    field_exists = False
                self.assertTrue(field_exists)
                if not field_exists:
                    continue

                # make sure the field_choice_category attribute (only) appears on fields we expect to have choice lists
                if not isinstance(handshape_field, FieldChoiceForeignKey):
                    # field is instance of: NullBooleanField, IntegerField, TextField, DateField, DateTimeField, ForeignKey, ManyToManyField
                    self.assertFalse(hasattr(handshape_field, 'field_choice_category'))
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                elif not hasattr(handshape_field, 'field_choice_category'):
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                else:
                    # we expect the field to be a choice list field and have field_choice_category defined
                    self.assertEqual(fieldname_to_kind_table[f], 'list')
                    self.assertTrue(hasattr(handshape_field, 'field_choice_category'))
                    fc_category = handshape_field.field_choice_category
                    # make sure there are fields for the category
                    fields_for_this_category = FieldChoice.objects.filter(field__iexact=fc_category, machine_value__gt=1)
                    self.assertGreater(len(fields_for_this_category),0)

    def test_duplicate_machine_values(self):

        field_choice_objects = FieldChoice.objects.all()

        grouped_by_field = dict()
        for fco in field_choice_objects:
            field = fco.field
            if field not in grouped_by_field.keys():
                grouped_by_field[field] = []
            if fco.machine_value in grouped_by_field[field]:
                matches_to_field = field_choice_objects.filter(field=field, machine_value=fco.machine_value)
                matches_to_string = [ ( m.field, str(m.machine_value),m.name) for m in matches_to_field ]
                print('Duplicate machine value for ', field, ': ', matches_to_string)
            else:
                grouped_by_field[field].append(fco.machine_value)

class RevisionHistoryTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        assign_perm('dictionary.can_publish', self.user)
        self.user.save()

    def test_field_types(self):

        # Create a new lemma in the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)
        new_lemma = LemmaIdgloss(dataset=test_dataset)
        new_lemma.save()

        # Create a lemma idgloss translation
        language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        # Create a new gloss
        new_gloss = Gloss()
        new_gloss.lemma = new_lemma
        new_gloss.save()

        gloss_update_phonology_data = []
        gloss_fields = settings.FIELDS['phonology']+settings.FIELDS['semantics']+settings.FIELDS['main']+['inWeb', 'isNew', 'excludeFromEcv']

        mapped_categories = []
        for f in gloss_fields:
            gloss_field = Gloss._meta.get_field(f)

            if f == 'semField':
                mapped_category = 'SemField'
                if mapped_category not in mapped_categories:
                    mapped_categories.append(mapped_category)
            elif f == 'derivHist':
                mapped_category = 'derivHist'
                if mapped_category not in mapped_categories:
                    mapped_categories.append(mapped_category)
            elif isinstance(gloss_field, models.ForeignKey) and gloss_field.related_model == Handshape:
                mapped_category = 'Handshape'
                if mapped_category not in mapped_categories:
                    mapped_categories.append(mapped_category)
            elif hasattr(gloss_field, 'field_choice_category'):
                mapped_category = gloss_field.field_choice_category
                if mapped_category not in mapped_categories:
                    mapped_categories.append(mapped_category)

        # make a bunch of new choices
        for f in mapped_categories:
            # this should be an unused machine value
            if f == 'Handshape':
                new_machine_value = 500
                new_human_value = 'handshape_500'
                this_handshape = Handshape(machine_value=new_machine_value,
                                           name=new_human_value)
                this_handshape.save()
            elif f == 'SemField':
                new_machine_value = 500
                new_human_value = 'semfield_500'
                this_semfield = SemanticField(machine_value=new_machine_value,
                                              name=new_human_value)
                this_semfield.save()
            elif f == 'derivHist':
                new_machine_value = 500
                new_human_value = 'derivhist_500'
                this_derivhist = DerivationHistory(machine_value=new_machine_value,
                                                   name=new_human_value)
                this_derivhist.save()
            else:
                new_machine_value = 500
                new_human_value = 'fieldchoice_' + f + '_500'
                this_field_choice = FieldChoice(machine_value=new_machine_value,
                                                field=f,
                                                name=new_human_value)
                this_field_choice.save()

        # because semantic fields and derivation histories are multiselect, they use different identifiers for update
        # rather than the gloss model field name
        gloss_update_phonology_keys = []
        for f in gloss_fields:
            gloss_field = Gloss._meta.get_field(f)
            if f == 'semField':
                new_machine_value_string = '_500'
                gloss_update_phonology_data.append({'id' : 'semanticfield', 'value' : new_machine_value_string})
                gloss_update_phonology_keys.append(f)
            elif f == 'derivHist':
                new_machine_value_string = '_500'
                gloss_update_phonology_data.append({'id' : 'derivationhistory', 'value' : new_machine_value_string})
                gloss_update_phonology_keys.append(f)
            elif isinstance(gloss_field, models.ForeignKey) and gloss_field.related_model == Handshape:
                new_machine_value_string = '_500'
                gloss_update_phonology_data.append({'id' : f, 'value' : new_machine_value_string})
                gloss_update_phonology_keys.append(f)
            elif hasattr(gloss_field, 'field_choice_category'):
                new_machine_value_string = '_500'
                gloss_update_phonology_data.append({'id' : f, 'value' : new_machine_value_string})
                gloss_update_phonology_keys.append(f)
            elif isinstance(gloss_field, CharField) or isinstance(gloss_field, TextField):
                new_machine_value_string = f + '_string'
                gloss_update_phonology_data.append({'id' : f, 'value' : new_machine_value_string})
                gloss_update_phonology_keys.append(f)
            elif f in settings.HANDSHAPE_ETYMOLOGY_FIELDS:
                new_machine_value_string = 'true'
                gloss_update_phonology_data.append({'id' : f, 'value' : new_machine_value_string})
                gloss_update_phonology_keys.append(f)
            elif f in settings.HANDEDNESS_ARTICULATION_FIELDS:
                new_machine_value_string = '2'
                gloss_update_phonology_data.append({'id': f, 'value': new_machine_value_string})
                gloss_update_phonology_keys.append(f)
            elif isinstance(gloss_field, NullBooleanField):
                new_machine_value_string = 'true'
                gloss_update_phonology_data.append({'id' : f, 'value' : new_machine_value_string})
                gloss_update_phonology_keys.append(f)

        client = Client()
        client.login(username='test-user', password='test-user')

        for update_data in gloss_update_phonology_data:
            client.post('/dictionary/update/gloss/' + str(new_gloss.pk), update_data)

        all_revisions = GlossRevision.objects.filter(gloss=new_gloss.pk, user=self.user)
        updated_fields = [ r.field_name for r in all_revisions ]

        for f in gloss_update_phonology_keys:
            self.assertTrue(f in updated_fields)


class Corpus_Tests(TestCase):

    # corpus speakers are only imported once, importing a metadata file a second time updates speakers
    # importing an eaf file only creates GlossFrequency objects for the designated corpus

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        assign_perm('dictionary.change_gloss', self.user)
        self.user.save()

        dataset_name = settings.DEFAULT_DATASET
        self.test_dataset = Dataset.objects.get(name=dataset_name)
        language = self.test_dataset.default_language

        # Create 10 lemmas for use in testing
        lemmas = {}
        for lemma_id in range(1,128):
            new_lemma = LemmaIdgloss(dataset=self.test_dataset)
            new_lemma.save()
            new_lemmaidglosstranslation = LemmaIdglossTranslation(text="testlemmaidglosstranslation" + str(lemma_id),
                                                                  lemma=new_lemma, language=language)
            new_lemmaidglosstranslation.save()
            lemmas[lemma_id] = new_lemma

        # Create 10 glosses that start out being the same
        gloss_ids_to_create = [2599, 2688, 2086, 2932, 2840, 3729, 1291, 472, 919, 520, 375, 2969, 2442, 2352,
                               1573, 2807, 1876, 2109, 2707, 1879, 2111, 365, 1192, 3459, 2775, 903, 1205, 2549, 2354, 1777, 889,
                               2934, 2954, 1724, 1738, 1150, 41929, 17, 789, 2872, 902, 2654, 1436, 642, 2093, 795, 3354, 826,
                               1861, 1068, 328, 175, 1664, 2676, 2407, 1313, 20, 2487, 2001, 2328, 2780, 2781, 2782, 2783, 2784,
                               2785, 2786, 2787, 2788, 2789, 2790, 2791, 2792, 2793, 2794, 2795, 2796, 2797, 2798, 2799, 2800, 2801,
                               2802, 2803, 2804, 2805, 2806, 2898, 2808, 2809, 2810, 2811, 2812, 2813, 2814, 2815, 2816, 2817, 2818,
                               2819, 2820, 2821, 2822, 2823, 2824, 2825, 2826, 2827, 2828, 2829, 2830, 2831, 2832, 2833, 2834, 2835,
                               2836, 2837, 2838, 2839, 2890, 2891, 2892, 2893, 2894, 2895, 2896, 2897]
        gloss_annotations_to_create = ['AANHALINGSTEKENS', 'GELUKKIG', 'ECHT-A', 'EMOTIE-B', 'ERG-A', 'EVEN', 'FIETSEN', 'GEK-A', 'GOED-B', 'GOOIEN-A', 'GRAAG-B',
                                       'HANDEN-WRIJVEN-B', 'HAREN', 'HEBBEN-A', 'HEE', 'HOND-A', 'HOND-C', 'HOP', 'HOUDEN-VAN', 'INTERNAAT-C',
                                       'JAM-A', 'JONGEN-A', 'KAART-A', 'KAPOT', 'KIJKEN-A', 'KLAAR-A', 'KLAAR-B', 'KLEREN-B', 'KOMEN-A',
                                       'KUNNEN-NIET-A', 'KWAST', 'LAAT-MAAR', 'LAATSTE-A', 'LACHEN-B', 'LICHAAM-B', 'LOPEN-B', 'LOPEN-D', 'MEE',
                                       'MEISJE-A', 'MOETEN-A', 'NAGELBIJTEN', 'NEE-C', 'NETJES-B', 'NOG-NIET',
                                       'VERANDEREN-E', 'WEGGOOIEN-A', 'WEG-C', 'HELPEN-A', 'LICHAAM-A', 'PROBLEEM-A', 'OUDER-B', 'GEBOREN-B', 'STEM-A',
                                       'ANDERS-B', 'VERSTAND', 'SCHRIJVEN-C', 'GELUK-B', 'ZO', 'SCHRIJVEN-D', 'AF-A', 'STRAKS-A', 'SCHOOL-D',
                                       'KLEINDOCHTER', 'SLECHT-B', 'SLECHTHOREND-B', 'ROEPEN-B', 'KLEIN-HORIZONTAAL-A', 'PRATEN-C', 'SOMS-A',
                                       'VERZOEKEN', 'NAAM-C', 'LIEF-B', 'MAAT-HORIZONTAAL-C', 'PERFECT-A', 'GROOT-VERTICAAL-F', 'MENS',
                                       'KLEIN-HORIZONTAAL-C', 'ONDERWIJS-A', 'OOK-A', 'OUD-A', 'KOMEN-B', 'BEGINNEN-A', 'GEHANDICAPT-B',
                                       'OVERDRIJVEN', 'GEBAREN-A', 'GAUW', 'LOGOPEDIE-A', 'VOOR-D', 'ORAAL-B', 'WAT-A', 'ORAAL-A', 'MAMA',
                                       'MOEILIJK-A', 'VROUW-A', 'NEE-A', 'LACHEN-A', 'ZUS-B', 'ROTTERDAM-B', 'SORRY-A', 'JAAR-B',
                                       'LIEGEN', 'PROCENT-A', 'GAAN-NAAR-A', 'PLOTSELING-A', 'PRATEN-E', 'NOG', 'VERLEGEN-A',
                                       'WEG-B', 'NAAMGEBAAR', 'ROEPEN:1', 'GENOEG', 'LANGZAAM', 'TEVREDEN-B', 'PRATEN-D', 'CULTUUR',
                                       'VANDAAR-A', 'BINNEN', 'HALLO', 'TOEVALLIG-B', 'PUNT-A', 'VERTELLEN', 'WAAR-A', 'KLOPT-D',
                                       'BESTEMPELEN-A', 'ALLES-A', 'VERVELEN-A', 'KIJKEN-B', 'VRAGEN-A', 'NIEUW-A', '~ZEGGEN', 'STOK-A',
                                       'VERBAASD-A', 'GOED-B', 'DURVEN', 'GEK-A', 'CANADA', 'CONGRES-A', 'VEEL-A', 'BUITENLAND', 'EUROPA-C',
                                       'ENGELAND-B', 'TAAL-D', 'AFRIKA-B', 'BELGIE-B',
                                       'HELE', 'PRIMA', 'COMMUNICEREN', 'ALLEMAAL-A', 'BEETJE', 'HOEVEEL', 'CONTROLEREN',
                                       'DISCUSSIEREN', 'GROEP-A', 'AL', 'NIET-A', 'EVEN', 'BIJ-D', 'ROLSTOEL-C', 'REGERING-A', 'AANSLUITEN', 'WERKEN-A']

        self.handedness_fieldchoice_1 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).first()
        self.handedness_fieldchoice_2 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).last()

        glosses = {}
        for next_id in range(1, 128):
            glosses[next_id] = gloss_ids_to_create[next_id-1]

        for gloss_id in range(1,128):
            this_id = gloss_id - 1
            gloss_data = {
                'id': glosses[gloss_id],
                'lemma' : lemmas[gloss_id],
                'handedness': self.handedness_fieldchoice_1,
                'tokNo': 0,
                'tokNoSgnr': 0
            }
            new_gloss = Gloss(**gloss_data)
            new_gloss.save()

            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = gloss_annotations_to_create[this_id]
            # The last created objects had their id set manually
            # Start creating objects with a new initial id
            if not AnnotationIdglossTranslation.objects.count():
                annotationIdgloss.id = 50000
            else:
                annotationIdgloss.id = AnnotationIdglossTranslation.objects.last().id + 1
            annotationIdgloss.save()

        # make some speakers
        speaker_1 = Speaker()
        speaker_1.identifier = 'test_speaker' + '_' + 'OtherCorpus'
        speaker_1.location = 'Disneyworld'
        speaker_1.age = 12
        speaker_1.gender = 'o'
        speaker_1.handedness = 'a'
        speaker_1.save()

    def test_metadata_file(self):
        # this imports the Speaker data to the test database
        from signbank.frequency import import_corpus_speakers

        dataset_acronym = self.test_dataset.acronym

        metadata_location = settings.WRITABLE_FOLDER + settings.DATASET_METADATA_DIRECTORY + os.sep + dataset_acronym + '_metadata.csv'

        count_known_speakers0 = Speaker.objects.filter(identifier__endswith='_'+dataset_acronym).count()
        #There are initially no speakers
        self.assertEqual(count_known_speakers0, 0)
        ### CORPUS FUNCTION
        errors1 = import_corpus_speakers(dataset_acronym)
        self.assertEqual(errors1, [])

        count_known_speakers1 = Speaker.objects.filter(identifier__endswith='_'+dataset_acronym).count()

        # find out how many entries are in the meta data file
        get_wc = "wc " + metadata_location

        import subprocess
        wc_output = subprocess.check_output(get_wc, shell=True)
        wc_output_string = wc_output.decode("utf-8").strip()
        wc_output_values = wc_output_string.split()
        if wc_output_values:
            number_of_entries = int(wc_output_values[0]) - 1
        else:
            number_of_entries = 0
        self.assertEqual(count_known_speakers1, number_of_entries)

        # try to read file again, make sure no new entries are created
        ### CORPUS FUNCTION
        errors2 = import_corpus_speakers(dataset_acronym)
        self.assertEqual(errors2, [])
        count_known_speakers2 = Speaker.objects.filter(identifier__endswith='_'+dataset_acronym).count()
        #After importing the metadata file a second time, the same number of speakers exist
        self.assertEqual(count_known_speakers2, count_known_speakers1)


    def test_corpus_creation(self):
        # this imports the Speaker data to the test database
        from signbank.frequency import import_corpus_speakers, configure_corpus_documents_for_dataset, dictionary_glosses_to_speakers, gloss_to_speakers, \
            dictionary_documents_to_glosses, dictionary_documents_to_speakers, dictionary_glosses_to_documents, \
            document_to_speakers, document_to_glosses, \
            gloss_to_documents, speaker_to_glosses, dictionary_speakers_to_glosses, dictionary_speakers_to_documents, speaker_to_documents, \
            get_corpus_speakers, get_gloss_tokNo, get_gloss_tokNoSgnr

        dataset_acronym = self.test_dataset.acronym
        ### CORPUS FUNCTION
        errors = import_corpus_speakers(dataset_acronym)
        self.assertEqual(errors, [])

        count_known_documents0 = Document.objects.all().count()
        #There are initially no documents
        self.assertEqual(count_known_documents0, 0)

        dataset_eaf_folder = os.path.join(settings.WRITABLE_FOLDER, settings.TEST_DATA_DIRECTORY, settings.DATASET_EAF_DIRECTORY,dataset_acronym)
        eaf_file_paths = []
        for filename in os.listdir(dataset_eaf_folder):
            eaf_file_paths.append(dataset_eaf_folder + os.sep + str(filename))
        if not eaf_file_paths:
            print('No EAF files found in eaf folder for test dataset: ', dataset_eaf_folder)
            print('In order to test corpus creation functionality, sample EAF files are needed.')
            return

        ### CORPUS FUNCTION
        print('CONFIGURE CORPUS')
        configure_corpus_documents_for_dataset(dataset_acronym, testing=True)

        try:
            corpus = Corpus.objects.get(name=dataset_acronym)
        except ObjectDoesNotExist:
            corpus = None
        self.assertNotEqual(corpus, None)

        document_objects = Document.objects.filter(corpus=corpus).order_by('identifier')

        gloss_frequency_objects_per_document = {}
        documents_without_data = []
        for d_obj in document_objects:
            frequency_objects_for_document = GlossFrequency.objects.filter(document=d_obj)
            if frequency_objects_for_document:
                gloss_frequency_objects_per_document[d_obj.identifier] = frequency_objects_for_document
            else:
                documents_without_data.append(d_obj.identifier)

        print('Test documents without annotations: ', documents_without_data)

        glosses = Gloss.objects.filter(lemma__dataset=self.test_dataset)
        gloss_ids = [ g.id for g in glosses ]
        speakers = Speaker.objects.all()
        speaker_ids = [ s.identifier for s in speakers ]

        participants = get_corpus_speakers(dataset_acronym)
        for p in participants:
            self.assertIn(p, speakers)

        gloss_frequency = GlossFrequency.objects.filter(document__corpus__name=self.test_dataset.acronym)
        gloss_frequency_table_1 = {}
        for gf in gloss_frequency:
            gloss_frequency_table_1[gf.gloss.id] = gf.frequency
            self.assertIn(gf.gloss.id, gloss_ids)
            self.assertIn(gf.speaker.identifier, speaker_ids)

        # test Gloss fields tokNo and tokNoSgnr that the methods that compute them correspond to the stored values
        glosses_in_dataset = Gloss.objects.filter(lemma__dataset=self.test_dataset)
        for gl in glosses_in_dataset:
            tokNoSgnr = get_gloss_tokNoSgnr(dataset_acronym, gl.id)
            self.assertEqual(tokNoSgnr, gl.tokNoSgnr)

            tokNo = get_gloss_tokNo(dataset_acronym, gl.id)
            self.assertEqual(tokNo, gl.tokNo)

        # check helper functions that retrieve data from GlossFrequency objects

        gl_signed_by_speakers = dictionary_glosses_to_speakers(self.test_dataset.acronym)

        for gid in gl_signed_by_speakers.keys():
            speakers = gloss_to_speakers(gid)
            self.assertEqual(gl_signed_by_speakers[gid], speakers)

        gl_per_document = dictionary_documents_to_glosses(self.test_dataset.acronym)

        for did in gl_per_document.keys():
            glosses = document_to_glosses(self.test_dataset.acronym, did)
            self.assertEqual(gl_per_document[did], glosses)

        sp_per_document = dictionary_documents_to_speakers(self.test_dataset.acronym)

        for did in sp_per_document.keys():
            speakers = document_to_speakers(self.test_dataset.acronym, did)
            self.assertEqual(sp_per_document[did], speakers)

        gl_appear_in_documents = dictionary_glosses_to_documents(self.test_dataset.acronym)

        for gid in gl_appear_in_documents.keys():
            documents = gloss_to_documents(gid)
            self.assertEqual(gl_appear_in_documents[gid], documents)

        sp_signs_glosses = dictionary_speakers_to_glosses(self.test_dataset.acronym)

        for sid in sp_signs_glosses.keys():
            glosses = speaker_to_glosses(self.test_dataset.acronym, sid)
            self.assertEqual(sp_signs_glosses[sid], glosses)

        sp_signs_documents = dictionary_speakers_to_documents(self.test_dataset.acronym)

        for sid in sp_signs_documents.keys():
            documents = speaker_to_documents(self.test_dataset.acronym, sid)
            self.assertEqual(sp_signs_documents[sid], documents)

        # test that the number of speakers for the corpus corresponds to those stored in the GlossFrequency objects
        # the speaker identifiers inside the corpus have the Dataset postfixed on the participant identifier of the eaf files
        glosses_frequenciesXdataset = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym)

        glosses_frequenciesXspeaker = GlossFrequency.objects.filter(speaker__identifier__endswith='_' + dataset_acronym)

        glosses_frequenciesXdatasetXspeaker = GlossFrequency.objects.filter(document__corpus__name=dataset_acronym,
                                                            speaker__identifier__endswith='_' + dataset_acronym)

        self.assertEqual(len(glosses_frequenciesXdataset), len(glosses_frequenciesXdatasetXspeaker))

        self.assertEqual(len(glosses_frequenciesXspeaker), len(glosses_frequenciesXdatasetXspeaker))

        # modify a creation time of a document in order to update it
        try:
            document_to_update = Document.objects.get(corpus__name=self.test_dataset.acronym, identifier='CNGT1008')
            print('document to update: ', document_to_update.identifier)
            from datetime import datetime
            from django.utils.timezone import get_current_timezone
            document_to_update.creation_time = datetime(2000, 8, 23, tzinfo=get_current_timezone())
            document_to_update.save()
        except ObjectDoesNotExist:
            print('update_corpus_counts: Update corpus not tested, needs EAF file CNGT1008.')
            return

        print('UPDATE CORPUS')
        update_corpus_document_counts(dataset_acronym, 'CNGT1008', testing=True)

        gloss_frequency_2 = GlossFrequency.objects.filter(document__corpus__name=self.test_dataset.acronym)
        gloss_frequency_table_2 = {}
        for gf in gloss_frequency_2:
            gloss_frequency_table_2[gf.gloss.id] = gf.frequency
            self.assertIn(gf.gloss.id, gloss_ids)
            self.assertIn(gf.speaker.identifier, speaker_ids)

        self.assertEqual(gloss_frequency_table_1.keys(), gloss_frequency_table_2.keys())

        for gid in gloss_frequency_table_2.keys():
            self.assertEqual(gloss_frequency_table_1[gid], gloss_frequency_table_2[gid])

        glosses_in_dataset = Gloss.objects.filter(lemma__dataset=self.test_dataset)
        for gl in glosses_in_dataset:
            tokNoSgnr = get_gloss_tokNoSgnr(dataset_acronym, gl.id)
            self.assertEqual(tokNoSgnr, gl.tokNoSgnr)

            tokNo = get_gloss_tokNo(dataset_acronym, gl.id)
            self.assertEqual(tokNo, gl.tokNo)


class MinimalPairsTests(TestCase):

    # This test exists because a bug had previously been found with the display of the repeat phonology field
    # repeat is a Boolean field that should be either True or False (the default if not set)
    # This should be displayed as Yes or No

    # MINIMAL_PAIRS_FIELDS = ['handedness', 'domhndsh', 'subhndsh', 'handCh', 'relatArtic', 'locprim',
    #                         'relOriMov', 'relOriLoc', 'oriCh', 'contType', 'movSh', 'movDir', 'repeat', 'altern']

    # This test currently checks minimal pairs involving the following phonology fields,
    # based on type of the field:

    # handedness
    # domhndsh
    # subhndsh
    # locprim
    # repeat, altern
    # handCh

    def setUp(self):
        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.save()

        self.client = Client()

        used_machine_values = [ h.machine_value for h in Handshape.objects.all() ]
        max_used_machine_value = max(used_machine_values)

        name_1 = 'testhandshape1'
        name_2 = 'testhandshape2'

        # create two arbitrary new Handshapes and store the data in FieldChoice table

        self.test_handshape1 = Handshape(machine_value=max_used_machine_value+1, name='thisisatemporarytesthandshape1')
        self.test_handshape1.save()

        self.test_handshape2 = Handshape(machine_value=max_used_machine_value+2, name='thisisatemporarytesthandshape2')
        self.test_handshape2.save()

        self.handedness_fieldchoice_1 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).first()
        self.handedness_fieldchoice_2 = FieldChoice.objects.filter(field='Handedness', machine_value__gt=1).last()

        self.locprim_fieldchoice_1 = FieldChoice.objects.filter(field='Location', machine_value__gt=1).first()
        self.locprim_fieldchoice_2 = FieldChoice.objects.filter(field='Location', machine_value__gt=1).last()

        self.handch_fieldchoice_1 = FieldChoice.objects.filter(field='HandshapeChange', machine_value__gt=1).first()
        self.handch_fieldchoice_2 = FieldChoice.objects.filter(field='HandshapeChange', machine_value__gt=1).last()

    def test_analysis_minimalpairs(self):

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create 10 lemmas for use in testing
        language = Language.objects.get(id=get_default_language_id())
        lemmas = {}
        for lemma_id in range(1,15):
            new_lemma = LemmaIdgloss(dataset=test_dataset)
            new_lemma.save()
            new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation" + str(lemma_id),
                                                                  lemma=new_lemma, language=language)
            new_lemmaidglosstranslation.save()
            lemmas[lemma_id] = new_lemma

        # Create 10 glosses that start out being the same
        glosses = {}
        for gloss_id in range(1,15):
            gloss_data = {
                'lemma' : lemmas[gloss_id],
                'handedness': self.handedness_fieldchoice_1,
                'domhndsh' : self.test_handshape1,
                'locprim': self.locprim_fieldchoice_1,
            }
            new_gloss = Gloss(**gloss_data)
            new_gloss.save()
            for language in test_dataset.translation_languages.all():
                language_code_2char = language.language_code_2char
                annotationIdgloss = AnnotationIdglossTranslation()
                annotationIdgloss.gloss = new_gloss
                annotationIdgloss.language = language
                annotationIdgloss.text = 'thisisatemporarytestgloss_' + language_code_2char + str(gloss_id)
                annotationIdgloss.save()
            glosses[gloss_id] = new_gloss

        # Set up the fields of the new glosses to differ by one phonology field to glosses[1]
        # gloss 1 doesn't set the repeat or altern fields, they are left as whatever the default is

        glosses[2].locprim = self.locprim_fieldchoice_2
        glosses[2].save()

        glosses[3].repeat = True
        glosses[3].save()

        glosses[4].handedness = self.handedness_fieldchoice_2
        glosses[4].save()

        glosses[5].domhndsh_letter = True
        glosses[5].save()

        glosses[6].weakdrop = True
        glosses[6].save()

        glosses[7].weakdrop = False
        glosses[7].save()

        glosses[8].altern = True
        glosses[8].save()

        glosses[9].handCh = self.handch_fieldchoice_1
        glosses[9].save()

        glosses[10].domhndsh = self.test_handshape2
        glosses[10].domhndsh_letter = True
        glosses[10].save()

        glosses[11].handedness = self.handedness_fieldchoice_2
        glosses[11].weakdrop = False
        glosses[11].save()

        glosses[12].handedness = self.handedness_fieldchoice_2
        glosses[12].weakdrop = True
        glosses[12].save()

        glosses[13].handedness = self.handedness_fieldchoice_2
        glosses[13].save()

        glosses[14].domhndsh = self.test_handshape2
        glosses[14].domhndsh_letter = False
        glosses[14].save()

        self.client.login(username='test-user', password='test-user')

        assign_perm('view_dataset', self.user, test_dataset)
        response = self.client.get('/analysis/minimalpairs/', {'paginate_by':20}, follow=True)

        objects_on_page = response.__dict__['context_data']['objects_on_page']

        # check that all objects retrieved by minimal pairs are also displayed
        # objects_on_page is a list of object ids
        # check for these rows
        for obj in objects_on_page:
            pattern_gloss = 'focusgloss_' + str(obj)
            self.assertContains(response, pattern_gloss)

        # now fetch the table row contents for each object, using the ajax call of the template
        # check that the repeat phonology field is correctly displayed as Yes and No for True and False
        for obj in objects_on_page:
            response_row = self.client.get('/dictionary/ajax/minimalpairs/' + str(obj) + '/')
            minimal_pairs_dict = response_row.context['minimal_pairs_dict']

            # uncomment print statement to see what the minimal pairs are

            for minimalpair in minimal_pairs_dict:
                # check that there is a row for this minimal pair in the html
                other_gloss_id = str(minimalpair['other_gloss'].id)
                pattern_cell = 'cell_' + str(obj) + '_' + other_gloss_id
                self.assertContains(response_row, pattern_cell)
                # check that the field 'repeat' has different values in the table
                # we make use of the fact that the values in the minimal_pairs_dict returned by the ajax call are used
                field = minimalpair['field']
                focus_gloss_value = minimalpair['focus_gloss_value']
                other_gloss_value = minimalpair['other_gloss_value']
                other_gloss_idgloss = minimalpair['other_gloss_idgloss']

                # uncomment print statement to see what the minimal pairs are
                # print('                                  ', other_gloss_idgloss, '     ', field, '     ', focus_gloss_value, '   ', other_gloss_value)

                # this test makes sure that when minimal pair rows are displayed that the values differ in the display
                self.assertNotEqual(focus_gloss_value, other_gloss_value)

    def test_emptyvalues_minimalpairs(self):

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Create 10 lemmas for use in testing
        language = Language.objects.get(id=get_default_language_id())
        lemmas = {}
        for lemma_id in range(1,15):
            new_lemma = LemmaIdgloss(dataset=test_dataset)
            new_lemma.save()
            new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation" + str(lemma_id),
                                                                  lemma=new_lemma, language=language)
            new_lemmaidglosstranslation.save()
            lemmas[lemma_id] = new_lemma

        # Create 10 glosses that start out being the same
        glosses = {}
        for gloss_id in range(1,15):
            gloss_data = {
                'lemma' : lemmas[gloss_id],
                'handedness': self.handedness_fieldchoice_1,
                'domhndsh' : self.test_handshape1,
                'locprim': self.locprim_fieldchoice_1,
                'tokNo': 0,
                'tokNoSgnr': 0
            }
            new_gloss = Gloss(**gloss_data)
            new_gloss.save()
            for language in test_dataset.translation_languages.all():
                language_code_2char = language.language_code_2char
                annotationIdgloss = AnnotationIdglossTranslation()
                annotationIdgloss.gloss = new_gloss
                annotationIdgloss.language = language
                annotationIdgloss.text = 'thisisatemporarytestgloss_' + language_code_2char + str(gloss_id)
                annotationIdgloss.save()
            glosses[gloss_id] = new_gloss

        # Set up the fields of the new glosses to differ by one phonology field to glosses[1]
        # gloss 1 doesn't set the repeat or altern fields, they are left as whatever the default is

        glosses[3].locprim = None
        glosses[3].save()

        # gloss 9 has an empty handedness, it has no minimal pairs
        glosses[9].handedness = None
        glosses[9].save()

        glosses[10].domhndsh = self.test_handshape2
        glosses[10].domhndsh_letter = True
        glosses[10].save()

        glosses[11].handedness = self.handedness_fieldchoice_2
        glosses[11].weakdrop = False
        glosses[11].save()

        glosses[12].handedness = self.handedness_fieldchoice_2
        glosses[12].weakdrop = True
        glosses[12].save()

        glosses[13].domhndsh = self.test_handshape2
        glosses[13].handedness = self.handedness_fieldchoice_2
        glosses[13].save()

        glosses[14].domhndsh = self.test_handshape2
        glosses[14].handedness = self.handedness_fieldchoice_2
        glosses[14].subhndsh = self.test_handshape2
        glosses[14].save()

        glosses_to_ids = {}

        for gloss_id in range(1,15):
            glosses_to_ids[str(glosses[gloss_id].id)] = str(gloss_id)

        self.client.login(username='test-user', password='test-user')

        assign_perm('view_dataset', self.user, test_dataset)
        response = self.client.get('/analysis/minimalpairs/', {'paginate_by':20}, follow=True)

        objects_on_page = response.__dict__['context_data']['objects_on_page']

        # check that all objects retrieved by minimal pairs are also displayed
        # objects_on_page is a list of object ids
        # check for these rows
        for obj in objects_on_page:
            pattern_gloss = 'focusgloss_' + str(obj)
            self.assertContains(response, pattern_gloss)

        # now fetch the table row contents for each object, using the ajax call of the template
        # check that the repeat phonology field is correctly displayed as Yes and No for True and False
        for obj in objects_on_page:
            response_row = self.client.get('/dictionary/ajax/minimalpairs/' + str(obj) + '/')
            minimal_pairs_dict = response_row.context['minimal_pairs_dict']
            # if str(obj) == str(glosses[9].id):
            #     # make sure no minimal pairs for this gloss, since handedness is empty
            #     self.assertEqual(minimal_pairs_dict, [])
            #     continue

            # uncomment print statement to see what the minimal pairs are
            # print('minimal pairs for ', response_row.context['focus_gloss_translation'], ' (glosses[', glosses_to_ids[str(obj)], '])')

            for minimalpair in minimal_pairs_dict:
                # check that there is a row for this minimal pair in the html
                other_gloss_id = str(minimalpair['other_gloss'].id)
                pattern_cell = 'cell_' + str(obj) + '_' + other_gloss_id
                self.assertContains(response_row, pattern_cell)
                # check that the field 'repeat' has different values in the table
                # we make use of the fact that the values in the minimal_pairs_dict returned by the ajax call are used
                field = minimalpair['field']
                focus_gloss_value = minimalpair['focus_gloss_value']
                other_gloss_value = minimalpair['other_gloss_value']
                other_gloss_idgloss = minimalpair['other_gloss_idgloss']

                # uncomment print statement to see what the minimal pairs are
                # print('          ', other_gloss_idgloss, ' (glosses[', glosses_to_ids[other_gloss_id], ']) ', field, '     ', focus_gloss_value, '     ', other_gloss_value)

                # this test makes sure that when minimal pair rows are displayed that the values differ in the display
                self.assertNotEqual(focus_gloss_value, other_gloss_value)


# Helper function to retrieve contents of json-encoded message
def decode_messages(data):
    if not data:
        return None
    bits = data.split('$', 1)
    if len(bits) == 2:
        hash, value = bits
        return value
    return None


class GlossApiGetSignNameAndMediaInfoTests(TestCase):

    @classmethod
    def setUpTestData(self):

        self.dataset = 0
        self.results = 50
        self.search_term = "test_gloss_api"
        self.gloss_name = 'test_gloss_api'
        self.gloss_id = 0
        self.video_url = 'test_video_url_in_gloss_api_tests'
        self.file_path = path.join(settings.WRITABLE_FOLDER, self.video_url)

        self.factory = RequestFactory()

        # Use a default dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)
        self.dataset = test_dataset.id

        # Use default language
        language = Language.objects.get(id=get_default_language_id())

        # Create a lemma and a translation so the api method can filter on the text
        test_lemma = LemmaIdgloss(dataset=test_dataset)
        test_lemma.save()

        test_lemmaidglosstranslation = LemmaIdglossTranslation(text=self.gloss_name, lemma=test_lemma, language=language)
        test_lemmaidglosstranslation.save()

        # Create a with a video that the api should return

        new_gloss = Gloss()
        new_gloss.lemma = test_lemma
        new_gloss.inWeb = True
        new_gloss.save()
        self.gloss_id = new_gloss.id

        test_gloss_video = GlossVideo(gloss=new_gloss)
        test_gloss_video.videofile = self.video_url
        test_gloss_video.save()

    def setUp(self):
        # Create the file for the video which the gloss will return when get_video_url is called
        if not os.path.exists(self.file_path):
            Path(self.file_path).mkdir()

    def tearDown(self):
        # Remove video path
        if os.path.exists(self.file_path):
            Path(self.file_path).rmdir()

    def test_other_request_methode_then_GET_or_POST(self):
        """
        Check if an error is returned with another request methode than GET or POST
        """
        data = {"results": self.results}
        response = self.client.put(reverse('dictionary:gloss_api_get_info'), data, format='json')
        self.assertEqual(response.status_code, 405)

    def test_no_data_set_selected(self):
        """
        Check if an error is returned if no dataset is selected.
        """
        assert_json = '{"Error": "No dataset selected"}'
        data = {"search": self.search_term, "results": self.results}
        response = self.client.get(reverse('dictionary:gloss_api_get_info'), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, assert_json)

    def test_no_search_term_provided(self):
        """
        Check if an error is returned if no search term is provided.
        """
        assert_json = '{"Error": "No search term found"}'
        data = {"dataset": self.dataset, "results": self.results}
        response = self.client.get(reverse('dictionary:gloss_api_get_info'), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, assert_json)

    def test_no_results_amount_given(self):
        """
        Check if an error is returned if the amount of results is not provided.
        """
        assert_json = '{"Error": "No amount of search results given"}'
        data = {"dataset": self.dataset, "search": self.search_term}
        response = self.client.get(reverse('dictionary:gloss_api_get_info'), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, assert_json)

    def test_json_data_structure(self):
        """
        Check that if the returned json is correct if the dataset and the search term are provided
        """
        assert_json = []
        sign_json = {
                "sign_name": self.gloss_name,
                "image_url": "",
                "video_url": self.video_url
                }
        assert_json.append(sign_json)

        data = {"dataset": self.dataset, "search": self.gloss_name, "results": self.results}
        response = self.client.get(reverse('dictionary:gloss_api_get_info'), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, assert_json)

    def test_POST_retrieve_gloss_data_from_list_of_ids(self):
        """
        Check if POST request with list of sign id's return json object with media info of those signs
        """
        assert_json = []
        sign_json = {
                "sign_name": self.gloss_name,
                "image_url": "",
                "video_url": self.video_url
                }
        assert_json.append(sign_json)

        data = json.dumps([self.gloss_id])

        request = self.factory.post(reverse('dictionary:gloss_api_get_info'), data=data, content_type='application/json')

        response = gloss_api_get_sign_name_and_media_info(request)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, assert_json)
