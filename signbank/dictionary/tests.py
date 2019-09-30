from itertools import zip_longest

from signbank.dictionary.adminviews import *
from signbank.dictionary.forms import GlossCreateForm
from signbank.dictionary.models import *
from signbank.settings.base import WRITABLE_FOLDER

from django.contrib.auth.models import User, Permission, Group
from django.test import TestCase, RequestFactory
import json
from django.test import Client
from django.contrib.messages.storage.cookie import MessageDecoder
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.messages.storage.cookie import CookieStorage
from itertools import *

from guardian.shortcuts import assign_perm

class BasicCRUDTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        self.user.save()

    def test_CRUD(self):

        #Is the gloss there before?
        found = 0
        total_nr_of_glosses = 0
        for gloss in Gloss.objects.filter(handedness=4):
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

        # Create a lemma idgloss translation
        language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=language)
        new_lemmaidglosstranslation.save()

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.handedness = 4
        new_gloss.lemma = new_lemma
        new_gloss.save()

        #Is the gloss there now?
        found = 0
        for gloss in Gloss.objects.filter(handedness=4):
            if gloss.idgloss == 'thisisatemporarytestlemmaidglosstranslation':
                found += 1

        self.assertEqual(found, 1)

        #The handedness before was 4
        self.assertEqual(new_gloss.handedness,4)

        #If you run an update post request, you can change the gloss
        client = Client()
        client.login(username='test-user', password='test-user')
        client.post('/dictionary/update/gloss/'+str(new_gloss.pk),{'id':'handedness','value':'_6'})

        changed_gloss = Gloss.objects.get(pk = new_gloss.pk)
        self.assertEqual(changed_gloss.handedness, '6')

        # set up keyword search parameter for default language
        default_language = Language.objects.get(id=get_default_language_id())
        keyword_search_field_prefix = "keywords_"
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
        client.post(settings.PREFIX_URL + '/dictionary/update/gloss/'+str(new_gloss.pk),{'id':'handedness','value':'confirmed',
                                                                   'field':'deletegloss'})
        found = 0
        for gloss in Gloss.objects.filter(handedness=4):
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

        # Create a lemma idgloss translation
        default_language = Language.objects.get(id=get_default_language_id())
        new_lemmaidglosstranslation = LemmaIdglossTranslation(text="thisisatemporarytestlemmaidglosstranslation",
                                                              lemma=new_lemma, language=default_language)
        new_lemmaidglosstranslation.save()




        new_gloss = Gloss()
        new_gloss.handedness = 4
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
        new_gloss.handedness = 4
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
        new_gloss.handedness = 5
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
        response = client.get('/signs/search/',{'handedness[]':4})
        self.assertEqual(len(response.context['object_list']), 0) #Nothing without dataset permission

        assign_perm('view_dataset', self.user, test_dataset)
        response = client.get('/signs/search/',{'handedness[]':4})
        self.assertEqual(len(response.context['object_list']), 2)

        response = client.get('/signs/search/',{'handedness[]':5})
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
        new_gloss.handedness = 4
        new_gloss.locprim = 8

        new_gloss.lemma = new_lemma
        new_gloss.save()
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss'
            annotationIdgloss.save()

        # set up keyword search parameter for default language
        keyword_search_field_prefix = "keywords_"
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
        new_gloss.handedness = 4
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
        response = client.get('/signs/search/?handedness=4&'+glosssearch_field_name+'=test', follow=True)
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
            except:
                try:
                    fname_nounderscore = fname.replace("_"," ")
                    dataset_of_filename = Dataset.objects.get(acronym__iexact=fname_nounderscore)
                except:
                    print('WARNING: ECV FILENAME DOES NOT MATCH DATASET ACRONYM: ', filename)
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

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')

    def test_DatasetListView_ECV_export_empty_dataset(self):

        print('Test DatasetListView export_ecv with empty dataset')

        dataset_name = settings.DEFAULT_DATASET_ACRONYM
        print('Test Dataset is: ', dataset_name)

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(acronym=dataset_name)
        assign_perm('change_dataset', self.user, test_dataset)
        print('User has permmission to change dataset.')

        client = Client()

        logged_in = client.login(username='test-user', password='test-user')

        url = '/datasets/available?dataset_name='+dataset_name+'&export_ecv=ECV'

        response = client.get(url)

        loaded_cookies = response.cookies.get('messages').value
        decoded_cookies = decode_messages(loaded_cookies)
        json_decoded_cookies = json.loads(decoded_cookies, cls=MessageDecoder)
        json_message = json_decoded_cookies[0]
        print('Message ONE: ', json_message)

        # the Dataset is Empty at this point, so export is not offered.

        self.assertEqual(str(json_message), 'The dataset ' + dataset_name + ' is empty, export ECV is not available.')


    def test_DatasetListView_ECV_export_permission_change_dataset(self):

        print('Test DatasetListView export_ecv with permission change_dataset')

        dataset_name = settings.DEFAULT_DATASET_ACRONYM
        print('Test Dataset is: ', dataset_name)

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(acronym=dataset_name)
        assign_perm('change_dataset', self.user, test_dataset)
        print('User has permmission to change dataset.')

        test_dataset_acronym = 'temp_' + dataset_name

        test_dataset.acronym = test_dataset_acronym
        test_dataset.save()
        print('Test dataset name changed to: ', test_dataset_acronym)
        client = Client()

        logged_in = client.login(username='test-user', password='test-user')

        # create a gloss and put it in the dataset so we can export it.
        # this has many steps

        # Create a lemma first
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

        # fill in the annotation translations for the new gloss
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss'
            annotationIdgloss.save()

        url = '/datasets/available?dataset_name=' + test_dataset_acronym + '&export_ecv=ECV'

        response = client.get(url)

        loaded_cookies = response.cookies.get('messages').value
        decoded_cookies = decode_messages(loaded_cookies)
        json_decoded_cookies = json.loads(decoded_cookies, cls=MessageDecoder)
        json_message = json_decoded_cookies[0]
        print('Message TWO: ', json_message)

        self.assertEqual(str(json_message), 'ECV ' + test_dataset_acronym + ' successfully updated.')

        # cleanup
        test_dataset.acronym = dataset_name
        test_dataset.save()

        location_ecv_files = ECV_FOLDER
        for filename in os.listdir(location_ecv_files):
            if filename == test_dataset_acronym.lower() + '.ecv':
                filename_path = os.path.join(location_ecv_files,filename)
                os.remove(filename_path)
                print('Temp ecv file removed.')

    def test_DatasetListView_ECV_export_no_permission_change_dataset(self):

        print('Test DatasetListView export_ecv without permission')

        dataset_name = settings.DEFAULT_DATASET_ACRONYM
        print('Test Dataset is: ', dataset_name)

        client = Client()

        logged_in = client.login(username='test-user', password='test-user')

        url = '/datasets/available?dataset_name='+dataset_name+'&export_ecv=ECV'

        response = client.get(url)

        loaded_cookies = response.cookies.get('messages').value
        decoded_cookies = decode_messages(loaded_cookies)
        json_decoded_cookies = json.loads(decoded_cookies, cls=MessageDecoder)
        json_message = json_decoded_cookies[0]
        print('Message: ', json_message)

        self.assertEqual(str(json_message), 'No permission to export dataset.')

    def test_DatasetListView_not_logged_in_ECV_export(self):

        print('Test DatasetListView export_ecv anonymous user not logged in')

        dataset_name = settings.DEFAULT_DATASET_ACRONYM
        print('Test Dataset is: ', dataset_name)

        client = Client()

        url = '/datasets/available?dataset_name=' + dataset_name + '&export_ecv=ECV'

        response = client.get(url)
        self.assertEqual(response.status_code, 302)
        auth_login_url = reverse('registration:auth_login')
        expected_url = settings.PREFIX_URL + auth_login_url
        self.assertEqual(response['Location'][:len(expected_url)], expected_url)

    def test_Export_csv(self):
        client = Client()
        logged_in = client.login(username=self.user.username, password='test-user')
        print(str(logged_in))

        dataset_name = settings.DEFAULT_DATASET
        print('Test Dataset is: ', dataset_name)

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('change_dataset', self.user, test_dataset)
        print('User has permmission to change dataset.')

        assign_perm('dictionary.export_csv', self.user)
        print('User has permmission to export csv.')

        # set the language for glosssearch field name
        default_language = Language.objects.get(id=get_default_language_id())
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

        dataset_name = settings.DEFAULT_DATASET
        print('Test Dataset is: ', dataset_name)

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('change_dataset', self.user, test_dataset)
        print('User has permmission to change dataset.')

        # Create test lemma idgloss
        lemma = LemmaIdgloss(dataset=test_dataset)
        lemma.save()

        # Create test lemma idgloss translations
        lemma_idgloss_translation_prefix = 'test_lemma_translation_'
        test_translation_index = 1
        for language in test_dataset.translation_languages.all():
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
        for language in test_dataset.translation_languages.all():
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
        for language in test_dataset.translation_languages.all():
            language_name = getattr(language, settings.DEFAULT_LANGUAGE_HEADER_COLUMN['English'])
            form_name = '{}.Lemma ID Gloss ({})'.format(gloss.id, language_name)
            form_data[form_name] = '{}{}_{}'.format(lemma_idgloss_translation_prefix, language.language_code_2char,
                                                    test_translation_index)
        print('Form data test 2 of test_Import_csv_update_gloss_for_lemma: \n', form_data)

        response = client.post(reverse_lazy('import_csv_update'), form_data, follow=True)
        self.assertContains(response, 'No changes were found.')

        count_dataset_translation_languages = test_dataset.translation_languages.all().count()
        print('Number of translation languages for the test dataset: ', count_dataset_translation_languages)

        # Prepare form data for linking to SEVERAL EXISTING LemmaIdgloss + LemmaIdglossTranslations
        form_data = {'update_or_create': 'update'}
        for index, language in enumerate(test_dataset.translation_languages.all()):
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
        for index, language in enumerate(test_dataset.translation_languages.all()):
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

        dataset_name = settings.DEFAULT_DATASET
        print('Test Dataset is: ', dataset_name)

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('change_dataset', self.user, test_dataset)
        print('User has permmission to change dataset.')

        gloss_id = 1
        lemma_idgloss_translation_prefix = 'test_lemma_translation_'
        annotation_idgloss_translation_prefix = 'test_annotation_translation_'

        # Prepare form data for making A NEW LemmaIdgloss + LemmaIdglossTranslations
        test_lemma_translation_index = 1
        test_annotation_translation_index = 1
        form_data = {'update_or_create': 'create', '{}.dataset'.format(gloss_id): test_dataset.acronym}
        for language in test_dataset.translation_languages.all():
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
        form_data = {'update_or_create': 'create', '{}.dataset'.format(gloss_id): test_dataset.acronym}
        for language in test_dataset.translation_languages.all():
            form_name = '{}.lemma_id_gloss_{}'.format(gloss_id, language.language_code_2char)
            form_data[form_name] = '{}{}_{}'.format(lemma_idgloss_translation_prefix, language.language_code_2char,
                                                    test_lemma_translation_index)
            form_name = '{}.annotation_id_gloss_{}'.format(gloss_id, language.language_code_2char)
            form_data[form_name] = '{}{}_{}'.format(annotation_idgloss_translation_prefix, language.language_code_2char,
                                                    test_annotation_translation_index)

        print('Form data test 2 of test_Import_csv_new_gloss_for_lemma: \n', form_data)
        response = client.post(reverse_lazy('import_csv_create'), form_data)
        self.assertContains(response, 'Changes are live.')

        count_dataset_translation_languages = test_dataset.translation_languages.all().count()
        print('Number of translation languages for the test dataset: ', count_dataset_translation_languages)

        # Prepare form data for linking to SEVERAL EXISTING LemmaIdgloss + LemmaIdglossTranslations
        test_annotation_translation_index = 3
        form_data = {'update_or_create': 'create', '{}.dataset'.format(gloss_id): test_dataset.acronym}
        for index, language in enumerate(test_dataset.translation_languages.all()):
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
        new_gloss.handedness = 4
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

        NAME = 'XXtéstlemmä  ~山脉 %20'  # %20 is an url encoded space

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
        new_gloss.handedness = 4
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

        #Add info of the dataset to the session (normally done in the detail view)
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

        #And we get a 302 for both detail views
        response = self.client.get('/dictionary/gloss/'+str(self.public_gloss.pk))
        self.assertEqual(response.status_code,302)

        response = self.client.get('/dictionary/gloss/'+str(self.hidden_gloss.pk))
        self.assertEqual(response.status_code,302)

        #Log in
        self.client = Client()
        self.client.login(username='test-user', password='test-user')

        #We can now request a detail view
        response = self.client.get('/dictionary/gloss/'+str(self.hidden_gloss.pk))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,
                            'The gloss you are trying to view ({}) is not in your selected datasets.'
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
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'Sign In'.format(self.user2.username))

        # Revoke view permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'delete_view_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'Sign In'.format(self.user2.username))

        # Grant change permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'Sign In'.format(self.user2.username))

        # Revoke change permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'delete_change_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
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
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'You must be in group Dataset Manager to modify dataset permissions.'
                            .format(self.user2.username))

        # Revoke view permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'delete_view_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'You must be in group Dataset Manager to modify dataset permissions.'
                            .format(self.user2.username))

        # Grant change permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'You must be in group Dataset Manager to modify dataset permissions.'
                            .format(self.user2.username))

        # Revoke change permission
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                     'delete_change_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
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
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'No permission to modify dataset permissions.'.format(self.user2.username))

        # Revoke view permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                    'delete_view_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'No permission to modify dataset permissions.'.format(self.user2.username))

        # Grant change permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'No permission to modify dataset permissions.'.format(self.user2.username))

        # Revoke change permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                    'delete_change_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
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
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'View permission for user {} ({} {}) successfully granted.'
                            .format(self.user2.username, self.user2.first_name, self.user2.last_name))

        # Revoke view permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                    'delete_view_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'View (and change) permission for user {} successfully revoked.'
                            .format(self.user2.username))

        # Grant change permission without view permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'User {} ({} {}) does not have view permission for this dataset. Please grant view permission first.'
                            .format(self.user2.username, self.user2.first_name, self.user2.last_name))

        # Grant change permission with view permission
        # Grant view permission first
        form_data = {'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_view_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # Grant change permission second
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username, 'add_change_perm': 'Grant'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'Change permission for user {} successfully granted.'
                            .format(self.user2.username))

        # Revoke change permission
        form_data ={'dataset_name': self.test_dataset.name, 'username': self.user2.username,
                    'delete_change_perm': 'Revoke'}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'Change permission for user {} successfully revoked.'
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
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'You must be in group Dataset Manager to modify dataset permissions.')

        # Make the user member of the group dataset managers
        dataset_manager_group = Group.objects.get(name='Dataset_Manager')
        dataset_manager_group.user_set.add(self.user)
        assign_perm('dictionary.change_dataset', self.user, self.test_dataset)
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, 'The default language of')

        # Try to add a language that is not in the translation language set of the test dataset
        language = Language(name="nonexistingtestlanguage", language_code_2char="ts", language_code_3char='tst')
        language.save()
        form_data = {'dataset_name': self.test_dataset.name, 'default_language': language.id}
        response = self.client.get(reverse('admin_dataset_manager'), form_data, follow=True)
        # print("Messages: " + ", ".join([m.message for m in response.context['messages']]))
        self.assertContains(response, '{} is not in the set of languages of dataset {}.'.format(
                                                            language.name, self.test_dataset.acronym))


class HandshapeTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        assign_perm('dictionary.search_gloss', self.user)
        assign_perm('dictionary.add_gloss', self.user)
        assign_perm('dictionary.change_gloss', self.user)
        self.user.save()

    def create_handshape(self):

        new_machine_value = 588
        new_english_name = 'thisisanewtesthandshape_en'
        new_dutch_name = 'thisisanewtesthandshape_nl'

        new_handshape = Handshape(machine_value=new_machine_value, english_name=new_english_name, dutch_name=new_dutch_name)
        new_handshape.save()

        print('New handshape ', new_handshape.machine_value, ' created: ', new_handshape.english_name, new_handshape.dutch_name)

        return new_handshape

    def test_create_handshape(self):

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('view_dataset', self.user, test_dataset)
        assign_perm('change_dataset', self.user, test_dataset)
        # assign_perm('dictionary.search_gloss', self.user)
        # assign_perm('dictionary.add_gloss', self.user)
        # assign_perm('dictionary.change_gloss', self.user)

        self.client.login(username='test-user', password='test-user')

        #Add info of the dataset to the session (normally done in the detail view)
        self.client.session['datasetid'] = test_dataset.pk
        self.client.session['search_results'] = None
        self.client.session.save()

        # new_machine_value = 588
        # new_english_name = 'thisisanewtesthandshape_en'
        # new_dutch_name = 'thisisanewtesthandshape_nl'
        #
        # new_handshape = Handshape(machine_value=new_machine_value, english_name=new_english_name, dutch_name=new_dutch_name)
        # new_handshape.save()
        #
        # print('New handshape ', new_handshape.machine_value, ' created: ', new_handshape.english_name, new_handshape.dutch_name)

        new_handshape = self.create_handshape()
        #We can now request a detail view
        print('Test HandshapeDetailView for new handshape.')
        response = self.client.get('/dictionary/handshape/'+str(new_handshape.machine_value), follow=True)
        self.assertEqual(response.status_code,200)

        # Querying the new handshape puts it into FieldChoice
        field_choices_handshapes = FieldChoice.objects.filter(field='Handshape')
        machine_values_of_field_choices_handshapes = [ h.machine_value for h in field_choices_handshapes]
        print('Test that the new handshape is in FieldChoice for Handshape')
        self.assertIn(new_handshape.machine_value, machine_values_of_field_choices_handshapes)

    def test_handshape_choices(self):

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

        # print('created lemmas: ', lemmas)

        test_handshape1 = Handshape.objects.get(machine_value = 62)
        test_handshape2 = Handshape.objects.get(machine_value = 154)

        # Create 10 glosses that start out being the same
        glosses = {}
        for gloss_id in range(1,4):
            gloss_data = {
                'lemma' : lemmas[gloss_id],
                'handedness': 2,
                'domhndsh' : str(test_handshape1.machine_value),
                'subhndsh': str(test_handshape2.machine_value),
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

        # print('created glosses: ', glosses)

        # Set up the fields of the new glosses to differ by one phonology field to glosses[1]
        # gloss 1 doesn't set the repeat or altern fields, they are left as whatever the default is

        self.client.login(username='test-user', password='test-user')

        new_handshape = self.create_handshape()
        #We can now request a detail view
        print('Test HandshapeDetailView for new handshape.')
        response = self.client.get('/dictionary/handshape/'+str(new_handshape.machine_value), follow=True)
        self.assertEqual(response.status_code,200)

        # Find out if the new handshape appears in the Field Choice menus
        print("Update a gloss to use the new handshape, using the choice list")
        self.client.post('/dictionary/update/gloss/'+str(glosses[1].pk),{'id':'domhndsh','value':'_588'})

        changed_gloss = Gloss.objects.get(pk = glosses[1].pk)
        print('Confirm the gloss was updated to the new handshape.')
        self.assertEqual(changed_gloss.domhndsh, '588')


class FieldChoiceTests(TestCase):

    from reversion.admin import VersionAdmin

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.user_permissions.add(Permission.objects.get(name='Can change gloss'))
        self.user.save()

        from signbank.dictionary.admin import FieldChoiceAdmin

        self.factory = RequestFactory()

        self.fieldchoice_admin = FieldChoiceAdmin(model=FieldChoice, admin_site=signbank)
        self.fieldchoice_admin.save_model(obj=FieldChoice(), request=None, form=None, change=None)

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
        from signbank.dictionary.models import FieldChoice

        request = self.factory.get('/admin/dictionary/fieldchoice/')
        request.user = self.user

        # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        for fieldchoice in fields_with_choices.keys():
            # get the first choice for the field
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                for fieldname in fields_with_choices[fieldchoice]:
                    setattr(new_gloss, fieldname, field_choice_in_use.machine_value)
        new_gloss.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no glosses with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options[2]
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), True)


    def test_delete_fieldchoice_handshape(self):

        from signbank.tools import fields_with_choices_handshapes
        fields_with_choices_handshapes = fields_with_choices_handshapes()

        #Create the handshape
        new_handshape = Handshape(english_name="thisisatemporarytesthandshape",
                                  dutch_name="thisisatemporarytesthandshape", chinese_name="thisisatemporarytesthandshape")
        new_handshape.save()

        new_handshape.machine_value = new_handshape.pk
        new_handshape.save()

        # now set all the choice fields of the gloss to the first choice of FieldChoice
        # it doesn't matter exactly which one, as long as the same one is used to check existence later
        from signbank.dictionary.models import FieldChoice

        request = self.factory.get('/admin/dictionary/fieldchoice/')
        request.user = self.user

        # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices_handshapes.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        for fieldchoice in fields_with_choices_handshapes.keys():
            # get the first choice for the field
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                for fieldname in fields_with_choices_handshapes[fieldchoice]:
                    setattr(new_handshape, fieldname, field_choice_in_use.machine_value)
                # for FingerSelection, set the Boolean fields of the fingers
                if fieldchoice == 'FingerSelection':
                    new_handshape.set_fingerSelection_display()
                    new_handshape.set_fingerSelection2_display()
                    new_handshape.set_unselectedFingers_display()
        new_handshape.save()

        print('TEST: new handshape created: ', new_handshape.__dict__)
        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices_handshapes.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no glosses with that choice
        # the test makes sure it can be deleted in admin
        for field_value in fields_with_choices_handshapes.keys():

            field_options = FieldChoice.objects.filter(field=field_value)
            for opt in field_options:
                if field_value in ['FingerSelection']:
                    print('TEST: test whether has_change_permission is False for FingerSelection choice ', opt.english_name)
                    self.assertEqual(self.fieldchoice_admin.has_change_permission(request=request, obj=opt), False)
                queries_h = [Q(**{ field_name : opt.machine_value }) for field_name in fields_with_choices_handshapes[field_value]]
                query_h = queries_h.pop()
                for item in queries_h:
                    query_h |= item
                field_is_in_use = Handshape.objects.filter(query_h).count()
                if field_is_in_use > 0:
                    print('TEST: test whether has_delete_permission is False for ', field_value, ' choice ', str(opt.english_name), ' (in use)')
                    self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=opt), False)
                else:
                    print('TEST: test whether has_delete_permission is True for ', field_value, ' choice ', str(opt.english_name), ' (not used)')
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
        from signbank.dictionary.models import FieldChoice

        #Create a definition
        new_definition = Definition(gloss=new_gloss, text="thisisatemporarytestnote", count=1, published=True)

        # set the role to the first choice
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                for field in fields_with_choices[fieldchoice]:
                    setattr(new_definition, field, field_choice_in_use.machine_value)
        new_definition.save()

        print('TEST new definition created: ', new_definition.__dict__)

        request = self.factory.get('/admin/dictionary/fieldchoice/')
        request.user = self.user

        # # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                print('TEST: test whether has_delete_permission is False for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.english_name), ' (in use)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no notes with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options[2]
                print('TEST: test whether has_delete_permission is True for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.english_name), ' (not used)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), True)

    def test_delete_fieldchoice_morphology_definition(self):

        # delete fieldchoice for OtherMediaType

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
        from signbank.dictionary.models import FieldChoice

        #Create a definition
        new_morphology_definition = MorphologyDefinition(parent_gloss=new_gloss, morpheme=new_gloss2)

        # set the morphology definition role to the first choice
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                for field in fields_with_choices[fieldchoice]:
                    setattr(new_morphology_definition, field, field_choice_in_use.machine_value)
        new_morphology_definition.save()

        print('TEST new morphology definition created: ', new_morphology_definition.__dict__)

        request = self.factory.get('/admin/dictionary/fieldchoice/')
        request.user = self.user

        # # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                print('TEST: test whether has_delete_permission is False for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.english_name), ' (in use)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no notes with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options[2]
                print('TEST: test whether has_delete_permission is True for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.english_name), ' (not used)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), True)

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
        from signbank.dictionary.models import FieldChoice

        #Create a definition
        new_othermedia = OtherMedia(parent_gloss=new_gloss,
                                    alternative_gloss="thisisatemporaryalternativegloss",
                                    path=str(new_gloss.id)+'/'+new_gloss.idgloss+'.mp4')

        # set the other media type to the first choice
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                for field in fields_with_choices[fieldchoice]:
                    setattr(new_othermedia, field, field_choice_in_use.machine_value)
        new_othermedia.save()

        print('TEST new othermedia created: ', new_othermedia.__dict__)

        request = self.factory.get('/admin/dictionary/fieldchoice/')
        request.user = self.user

        # # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                print('TEST: test whether has_delete_permission is False for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.english_name), ' (in use)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no notes with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options[2]
                print('TEST: test whether has_delete_permission is True for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.english_name), ' (not used)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), True)

    def test_delete_fieldchoice_morpheme_type(self):

        # delete fieldchoice for OtherMediaType

        from signbank.tools import fields_with_choices_morpheme_type
        fields_with_choices = fields_with_choices_morpheme_type()
        print('fields with choices morpheme type: ', fields_with_choices)
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
        from signbank.dictionary.models import FieldChoice

        # set the morpheme type to the first choice
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                for field in fields_with_choices[fieldchoice]:
                    print('field: ', field)
                    setattr(new_gloss, field, field_choice_in_use.machine_value)
                    setattr(new_morpheme, field, field_choice_in_use.machine_value)
        new_gloss.save()
        new_morpheme.save()

        print('TEST new morpheme created: ', new_morpheme.__dict__)

        request = self.factory.get('/admin/dictionary/fieldchoice/')
        request.user = self.user

        # # give the test user permission to delete field choices
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            for fc in field_options:
                assign_perm('delete_fieldchoice', self.user, fc)
        self.user.save()

        # make sure the field choice can't be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options.first()
                print('TEST: test whether has_delete_permission is False for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.english_name), ' (in use)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), False)

        # now do the same with the second choice
        # this time, there are no notes with that choice
        # the test makes sure it can be deleted in admin
        for fieldchoice in fields_with_choices.keys():
            field_options = FieldChoice.objects.filter(field=fieldchoice)
            if field_options:
                field_choice_in_use = field_options[2]
                print('TEST: test whether has_delete_permission is True for ', fieldchoice, ' choice ',
                      str(field_choice_in_use.english_name), ' (not used)')
                self.assertEqual(self.fieldchoice_admin.has_delete_permission(request=request, obj=field_choice_in_use), True)


class testFrequencyAnalysis(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')
        self.user.save()

        self.client = Client()

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

        test_handshape1 = Handshape.objects.get(machine_value = 62)
        test_handshape2 = Handshape.objects.get(machine_value = 154)

        glosses = {}
        for gloss_id in range(1,10):
            gloss_data = {
                'lemma' : lemmas[gloss_id],
                'handedness': 2,
                'domhndsh' : str(test_handshape1.machine_value),
                'subhndsh': str(test_handshape2.machine_value),
                'locprim': 5,
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

        glosses[2].locprim = 8
        glosses[2].save()

        glosses[3].handedness = 4
        glosses[3].save()

        glosses[4].handCh = 7
        glosses[4].save()

        glosses[5].domhndsh = str(test_handshape2.machine_value)
        glosses[5].save()

        glosses[6].handedness = 5
        glosses[6].save()

        glosses[7].domhndsh = str(test_handshape2.machine_value)
        glosses[7].save()

        glosses[8].namEnt = 16
        glosses[8].save()

        glosses[9].handedness = 6
        glosses[9].save()

        self.client.login(username='test-user', password='test-user')

        assign_perm('view_dataset', self.user, test_dataset)

        response = self.client.get('/analysis/frequencies/', follow=True)
        self.assertEqual(response.status_code,200)

        table_code = str(test_dataset.id) + '_results_'

        frequency_dict = test_dataset.generate_frequency_dict(language.language_code_2char)

        for fieldname in frequency_dict.keys():
            self.assertContains(response, table_code + fieldname)

        table_code_empty_prefix = str(test_dataset.id) + '_field_'
        table_code_empty_suffix = '_empty_frequency'

        for (k,d) in frequency_dict.items():

            for (c,v) in d.items():
                if v:
                    print('Frequency analysis field ', k, ', choice ', c, ' (', v, ' results)')
                    self.assertNotContains(response, table_code_empty_prefix + k + '_' + c + table_code_empty_suffix)
                else:
                    self.assertContains(response, table_code_empty_prefix + k + '_' + c + table_code_empty_suffix)


    def test_frequency_sorting(self):

        # set the test dataset
        dataset_name = settings.DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        language = Language.objects.get(id=get_default_language_id())
        language_code = language.language_code_2char

        codes_to_adjectives = dict(settings.LANGUAGES)

        if language_code not in codes_to_adjectives.keys():
            adjective = settings.FALLBACK_FIELDCHOICE_HUMAN_LANGUAGE
        else:
            adjective = codes_to_adjectives[language_code].lower()

        frequency_dict = test_dataset.generate_frequency_dict(language_code)
        frequency_dict_keys = frequency_dict.keys()

        fields_data = [(field.name, field.verbose_name.title(), field.field_choice_category)
                                                for field in Gloss._meta.fields if (field.name in FIELDS['phonology'] + FIELDS['semantics']) and hasattr(field, 'field_choice_category') ]
        fields_data_keys = [ f_name for (f_name,v_verbose,c_category) in fields_data]

        self.assertNotEqual(len(fields_data),0)
        self.assertEqual(len(frequency_dict_keys), len(fields_data_keys))

        ordered_fields_data = sorted(fields_data, key=lambda x: x[1])
        for (f, field_verbose_name, fieldchoice_category) in ordered_fields_data:

            choice_list = FieldChoice.objects.filter(field__iexact=fieldchoice_category).order_by(adjective + '_name')

            if len(choice_list) > 0:
                translated_choices = choicelist_queryset_to_translated_dict(choice_list, language_code, ordered=False, shortlist=False)
            else:
                translated_choices = []
            frequency_choices_f = frequency_dict[f]

            self.assertEqual(len(translated_choices), len(frequency_choices_f))

            frequency_choices_f_keys = [ k for k in frequency_choices_f.keys() ]
            translated_choices_keys = [ k for (k,v) in translated_choices ]

            # Make sure the sorted field choices are in the same order
            self.assertEqual(translated_choices_keys, frequency_choices_f_keys)


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
                        if setting_first_file not in all_settings_strings[second_file]:
                            comparison_table_first_not_in_second[first_file][second_file].append(setting_first_file)

        for first_file in all_settings:
            for second_file in all_settings:
                # the default.py file is part of the installation (should this filename be a setting?)
                # check that other settings files do not contain settings that are not in the default settings file
                if first_file != second_file and second_file == 'default.py':
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
                self.assertIn(f, gloss_fields_names.keys())
                # the following is true, which is weird, but just to state it explicitly since it's assumed sometimes in the code
                self.assertTrue(hasattr(gloss_fields_names[f], 'choices'))
                # make sure the field_choice_category attribute (only) appears on fields we expect to have choice lists
                if not isinstance(gloss_fields_names[f], models.CharField):
                    # field is instance of: NullBooleanField, IntegerField, TextField, DateField, DateTimeField, ForeignKey, ManyToManyField
                    self.assertFalse(hasattr(gloss_fields_names[f], 'field_choice_category'))
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                elif not gloss_fields_names[f].choices:
                    # the models declaration of the field was not constructed using build_choice_list or the choices list is empty
                    self.assertFalse(hasattr(gloss_fields_names[f], 'field_choice_category'))
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                else:
                    # we expect the field to be a choice list field and to have field_choice_category defined
                    self.assertEqual(fieldname_to_kind_table[f], 'list')
                    if hasattr(gloss_fields_names[f], 'max_length') and gloss_fields_names[f].max_length > 9:
                        print('Note: phonology field ', f, ' has max_length ', str(gloss_fields_names[f].max_length), ' but also has field choices.')
                    self.assertTrue(hasattr(gloss_fields_names[f], 'field_choice_category'))
                    fc_category = gloss_fields_names[f].field_choice_category
                    # make sure there are fields for the category
                    fields_for_this_category = FieldChoice.objects.filter(field__iexact=fc_category)
                    self.assertGreater(len(fields_for_this_category),0)

        if 'semantics' in settings.FIELDS.keys():
            semantics_fields = settings.FIELDS['semantics']
            gloss_fields_names = { f.name: f for f in Gloss._meta.fields }
            print('Testing semantics fields for declaration in Gloss model with field_choice_category in FieldChoice table.')
            for f in semantics_fields:
                # make sure all semantics fields are defined in Gloss
                self.assertIn(f, gloss_fields_names.keys())
                # the following is true, which is weird, but just to state it explicitly since it's assumed sometimes in the code
                self.assertTrue(hasattr(gloss_fields_names[f], 'choices'))
                # make sure the field_choice_category attribute (only) appears on fields we expect to have choice lists
                if not isinstance(gloss_fields_names[f], models.CharField):
                    # field is instance of: NullBooleanField, IntegerField, TextField, DateField, DateTimeField, ForeignKey, ManyToManyField
                    self.assertFalse(hasattr(gloss_fields_names[f], 'field_choice_category'))
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                elif not gloss_fields_names[f].choices:
                    # the models declaration of the field was not constructed using build_choice_list or the choices list is empty
                    self.assertFalse(hasattr(gloss_fields_names[f], 'field_choice_category'))
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                else:
                    # we expect the field to be a choice list field and have field_choice_category defined
                    self.assertEqual(fieldname_to_kind_table[f], 'list')
                    if hasattr(gloss_fields_names[f], 'max_length') and gloss_fields_names[f].max_length > 9:
                        print('Note: semantics field ', f, ' has max_length ', str(gloss_fields_names[f].max_length), ' but also has field choices.')
                    self.assertTrue(hasattr(gloss_fields_names[f], 'field_choice_category'))
                    fc_category = gloss_fields_names[f].field_choice_category
                    # make sure there are fields for the category
                    fields_for_this_category = FieldChoice.objects.filter(field__iexact=fc_category)
                    self.assertGreater(len(fields_for_this_category),0)

        if 'handshape' in settings.FIELDS.keys():
            handshape_fields = settings.FIELDS['handshape']
            handshape_fields_names = { f.name: f for f in Handshape._meta.fields }
            print('Testing handshape fields for declaration in Handshape model with field_choice_category in FieldChoice table.')
            for f in handshape_fields:
                # make sure all handshape fields are defined in Gloss
                self.assertIn(f, handshape_fields_names.keys())
                # the following is true, which is weird, but just to state it explicitly since it's assumed sometimes in the code
                self.assertTrue(hasattr(handshape_fields_names[f], 'choices'))
                # make sure the field_choice_category attribute (only) appears on fields we expect to have choice lists
                if not isinstance(handshape_fields_names[f], models.CharField):
                    # field is instance of: NullBooleanField, IntegerField, TextField, DateField, DateTimeField, ForeignKey, ManyToManyField
                    self.assertFalse(hasattr(handshape_fields_names[f], 'field_choice_category'))
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                elif not handshape_fields_names[f].choices:
                    # the models declaration of the field was not constructed using build_choice_list or the choices list is empty
                    self.assertFalse(hasattr(handshape_fields_names[f], 'field_choice_category'))
                    self.assertNotEqual(fieldname_to_kind_table[f], 'list')
                else:
                    # we expect the field to be a choice list field and have field_choice_category defined
                    self.assertEqual(fieldname_to_kind_table[f], 'list')
                    if hasattr(handshape_fields_names[f], 'max_length') and handshape_fields_names[f].max_length > 9:
                        print('Note: handshape field ', f, ' has max_length ', str(handshape_fields_names[f].max_length), ' but also has field choices.')
                    self.assertTrue(hasattr(handshape_fields_names[f], 'field_choice_category'))
                    fc_category = handshape_fields_names[f].field_choice_category
                    # make sure there are fields for the category
                    fields_for_this_category = FieldChoice.objects.filter(field__iexact=fc_category)
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
                matches_to_string = [ ( m.field, str(m.machine_value),m.english_name) for m in matches_to_field ]
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
        gloss_fields_names = {f.name: f for f in Gloss._meta.fields}

        # make a bunch of new field choices
        for f in gloss_fields_names.keys():
            if hasattr(gloss_fields_names[f], 'field_choice_category'):
                fc_category = gloss_fields_names[f].field_choice_category
                new_machine_value = 500
                new_human_value = 'fieldchoice_' + fc_category + '_500'
                this_field_choice = FieldChoice(machine_value=new_machine_value,
                                                field=fc_category,
                                                english_name=new_human_value,
                                                dutch_name=new_human_value,
                                                chinese_name=new_human_value)
                this_field_choice.save()

        for f in gloss_fields:
            if hasattr(gloss_fields_names[f], 'field_choice_category'):
                new_machine_value_string = '_500'
                gloss_update_phonology_data.append({'id' : f, 'value' : new_machine_value_string})
            elif isinstance(gloss_fields_names[f], CharField) or isinstance(gloss_fields_names[f], TextField):
                new_machine_value_string = f + '_string'
                gloss_update_phonology_data.append({'id' : f, 'value' : new_machine_value_string})
            elif f in settings.HANDSHAPE_ETYMOLOGY_FIELDS:
                new_machine_value_string = 'true'
                gloss_update_phonology_data.append({'id' : f, 'value' : new_machine_value_string})
            elif f in settings.HANDEDNESS_ARTICULATION_FIELDS:
                new_machine_value_string = '2'
                gloss_update_phonology_data.append({'id': f, 'value': new_machine_value_string})
            elif isinstance(gloss_fields_names[f], NullBooleanField):
                new_machine_value_string = 'true'
                gloss_update_phonology_data.append({'id' : f, 'value' : new_machine_value_string})

        client = Client()
        client.login(username='test-user', password='test-user')

        for update_data in gloss_update_phonology_data:
            client.post('/dictionary/update/gloss/' + str(new_gloss.pk), update_data)

        all_revisions = GlossRevision.objects.filter(gloss=new_gloss.pk, user=self.user)
        updated_fields = [ r.field_name for r in all_revisions ]

        for f in gloss_fields:
            self.assertTrue(f in updated_fields)


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

        # print('created lemmas: ', lemmas)

        test_handshape1 = Handshape.objects.get(machine_value = 62)
        test_handshape2 = Handshape.objects.get(machine_value = 154)

        # Create 10 glosses that start out being the same
        glosses = {}
        for gloss_id in range(1,15):
            gloss_data = {
                'lemma' : lemmas[gloss_id],
                'handedness': 2,
                'domhndsh' : str(test_handshape1.machine_value),
                'locprim': 7,
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

        # print('created glosses: ', glosses)

        # Set up the fields of the new glosses to differ by one phonology field to glosses[1]
        # gloss 1 doesn't set the repeat or altern fields, they are left as whatever the default is

        glosses[2].locprim = 8
        glosses[2].save()

        glosses[3].repeat = True
        glosses[3].save()

        glosses[4].handedness = 4
        glosses[4].save()

        glosses[5].domhndsh_letter = True
        glosses[5].save()

        glosses[6].weakdrop = True
        glosses[6].save()

        glosses[7].weakdrop = False
        glosses[7].save()

        glosses[8].altern = True
        glosses[8].save()

        glosses[9].handCh = 7
        glosses[9].save()

        glosses[10].domhndsh = str(test_handshape2.machine_value)
        glosses[10].domhndsh_letter = True
        glosses[10].save()

        glosses[11].handedness = 4
        glosses[11].weakdrop = False
        glosses[11].save()

        glosses[12].handedness = 4
        glosses[12].weakdrop = True
        glosses[12].save()

        glosses[13].handedness = 4
        glosses[13].save()

        glosses[14].domhndsh = str(test_handshape2.machine_value)
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
            # print('minimal pairs ', response_row.context['focus_gloss_translation'])

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

        # print('created lemmas: ', lemmas)

        test_handshape1 = Handshape.objects.get(machine_value = 62)
        test_handshape2 = Handshape.objects.get(machine_value = 154)

        # Create 10 glosses that start out being the same
        glosses = {}
        for gloss_id in range(1,15):
            gloss_data = {
                'lemma' : lemmas[gloss_id],
                'handedness': 2,
                'domhndsh' : test_handshape1.machine_value,
                'locprim': 7,
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

        # print('created glosses: ', glosses)

        # Set up the fields of the new glosses to differ by one phonology field to glosses[1]
        # gloss 1 doesn't set the repeat or altern fields, they are left as whatever the default is

        # pretend locprim hasn't been assigned
        glosses[2].locprim = None
        glosses[2].save()

        glosses[3].locprim = ''
        glosses[3].save()

        glosses[4].locprim = '-'
        glosses[4].save()

        # this is an errorneous None value
        glosses[5].locprim = 'None'
        glosses[5].save()
        error_none_gloss_5 = 'ERROR_None'

        glosses[6].locprim = 337
        glosses[6].save()
        error_337_gloss_6 = 'ERROR_337'

        glosses[7].locprim = 0
        glosses[7].save()

        glosses[8].locprim = '0'
        glosses[8].save()

        # gloss 9 has an empty handedness, it has no minimal pairs
        glosses[9].handedness = None
        glosses[9].save()

        glosses[10].domhndsh = test_handshape2.machine_value
        glosses[10].domhndsh_letter = True
        glosses[10].save()

        glosses[11].handedness = 4
        glosses[11].weakdrop = False
        glosses[11].save()

        glosses[12].handedness = 4
        glosses[12].weakdrop = True
        glosses[12].save()

        glosses[13].domhndsh = test_handshape2.machine_value
        glosses[13].handedness = 4
        glosses[13].save()

        glosses[14].domhndsh = test_handshape2.machine_value
        glosses[14].handedness = 4
        glosses[14].subhndsh = test_handshape2.machine_value
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

            if str(obj) == str(glosses[9].id):
                # make sure no minimal pairs for this gloss, since handedness is empty
                self.assertEqual(minimal_pairs_dict, [])
                continue

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

                if str(obj) == str(glosses[5].id):
                    # gloss 5 contains an erroneous None value
                    self.assertEqual(focus_gloss_value, error_none_gloss_5)
                    continue
                if other_gloss_id == str(glosses[5].id):
                    # gloss 5 contains an erroneous None value
                    self.assertEqual(other_gloss_value, error_none_gloss_5)
                    continue
                if str(obj) == str(glosses[6].id):
                    # gloss 6 contains an erroneous locprim value
                    self.assertEqual(focus_gloss_value, error_337_gloss_6)
                    continue
                if other_gloss_id == str(glosses[6].id):
                    # gloss 6 contains an erroneous locprim value
                    self.assertEqual(other_gloss_value, error_337_gloss_6)
                    continue

# Helper function to retrieve contents of json-encoded message
def decode_messages(data):
    if not data:
        return None
    bits = data.split('$', 1)
    if len(bits) == 2:
        hash, value = bits
        return value
    return None
