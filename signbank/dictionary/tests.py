from signbank.dictionary.adminviews import *
from signbank.dictionary.forms import GlossCreateForm
from signbank.settings.base import WRITABLE_FOLDER

from django.contrib.auth.models import User, Permission
from django.test import TestCase
import json
from django.test import Client
from django.contrib.messages.storage.cookie import MessageDecoder

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
            if gloss.idgloss == 'thisisatemporarytestgloss':
                found += 1
            total_nr_of_glosses += 1

        self.assertEqual(found,0)
        #self.assertGreater(total_nr_of_glosses,0) #Verify that the database is not empty

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.idgloss = 'thisisatemporarytestgloss'
        new_gloss.handedness = 4
        new_gloss.save()

        #Is the gloss there now?
        found = 0
        for gloss in Gloss.objects.filter(handedness=4):
            if gloss.idgloss == 'thisisatemporarytestgloss':
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

        #We can even add and remove stuff to the keyword table
        self.assertEqual(Keyword.objects.all().count(), 0)
        self.assertEqual(Translation.objects.all().count(), 0)
        client.post('/dictionary/update/gloss/'+str(new_gloss.pk),{'id':'keywords_nl','value':'a, b, c, d, e'})
        self.assertEqual(Keyword.objects.all().count(), 5)
        self.assertEqual(Translation.objects.all().count(), 5)
        client.post('/dictionary/update/gloss/'+str(new_gloss.pk),{'id':'keywords_nl','value':'a, b, c'})
        self.assertEqual(Keyword.objects.all().count(), 5)
        self.assertEqual(Translation.objects.all().count(), 3)

        #Throwing stuff away with the update functionality
        client.post('/dictionary/update/gloss/'+str(new_gloss.pk),{'id':'handedness','value':'confirmed',
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
        dataset_name = DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        # Construct the Create Gloss form data
        create_gloss_form_data = {'dataset': test_dataset.id, 'idgloss': "idgloss_test"}
        for language in test_dataset.translation_languages.all():
            create_gloss_form_data[GlossCreateForm.gloss_create_field_prefix + language.language_code_2char] = \
                "annotationidglosstranslation_test_" + language.language_code_2char

        # User does not have permission to change dataset. Creating a gloss should fail.
        response = client.post('/dictionary/update/gloss/', create_gloss_form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You are not authorized to change the selected dataset.")

        # Give the test user permission to change a dataset
        assign_perm('change_dataset', self.user, test_dataset)
        response = client.post('/dictionary/update/gloss/', create_gloss_form_data)

        glosses = Gloss.objects.filter(dataset=test_dataset, idgloss="idgloss_test")
        for language in test_dataset.translation_languages.all():
            glosses = glosses.filter(annotationidglosstranslation__language=language,
                                     annotationidglosstranslation__text__exact="annotationidglosstranslation_test_" + language.language_code_2char)

        self.assertEqual(len(glosses), 1)

        self.assertRedirects(response, reverse('dictionary:admin_gloss_view', kwargs={'pk': glosses[0].id})+'?edit')

    def testSearchForGlosses(self):

        #Create a client and log in
        client = Client()
        client.login(username='test-user', password='test-user')

        # Give the test user permission to search glosses
        assign_perm('dictionary.search_gloss', self.user)

        #Create the glosses
        dataset_name = DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        new_gloss = Gloss()
        new_gloss.idgloss = 'tempgloss1'
        new_gloss.handedness = 4
        new_gloss.dataset = test_dataset
        new_gloss.save()

        new_gloss = Gloss()
        new_gloss.idgloss = 'tempgloss2'
        new_gloss.handedness = 4
        new_gloss.dataset = test_dataset
        new_gloss.save()

        new_gloss = Gloss()
        new_gloss.idgloss = 'tempgloss3'
        new_gloss.handedness = 5
        new_gloss.dataset = test_dataset
        new_gloss.save()

        #Search
        response = client.get('/signs/search/',{'handedness':4})
        self.assertEqual(len(response.context['object_list']), 0) #Nothing without dataset permission

        assign_perm('view_dataset', self.user, test_dataset)
        response = client.get('/signs/search/',{'handedness[]':4})
        self.assertEqual(len(response.context['object_list']), 2)

        response = client.get('/signs/search/',{'handedness[]':5})
        self.assertEqual(len(response.context['object_list']), 1)

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
        dataset_name = DEFAULT_DATASET

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('view_dataset', self.user, test_dataset)
        assign_perm('change_dataset', self.user, test_dataset)
        assign_perm('dictionary.search_gloss', self.user)
        self.user.save()

        # #Create the gloss
        new_gloss = Gloss()
        new_gloss.idgloss = 'thisisatemporarytestgloss'
        new_gloss.handedness = 4
        new_gloss.dataset = test_dataset
        new_gloss.save()
        for language in test_dataset.translation_languages.all():
            annotationIdgloss = AnnotationIdglossTranslation()
            annotationIdgloss.gloss = new_gloss
            annotationIdgloss.language = language
            annotationIdgloss.text = 'thisisatemporarytestgloss'
            annotationIdgloss.save()

        #Search
        # response = client.get('/signs/search/?handedness=4')
        # response = client.get('/signs/search/?handedness=4', follow=True)
        response = client.get('/signs/search/?handedness=4&glosssearch_nl=test', follow=True)

        #print(response)
        #print(response.context.keys())
        #print(response.context['object_list'],response.context['glosscount'])
        #print(response.context['selected_datasets'])

class ImportExportTests(TestCase):

    # Three test case scenario's for exporting ECV via the DatasetListView with DEFAULT_DATASET
    #       /datasets/available/?dataset_name=DEFAULT_DATASET&export_ecv=ECV
    # 1. The user is logged in and has permission to change dataset
    # 2. The user is logged in but does not have permission to change dataset
    # 3. The user is not logged in

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')

    def test_DatasetListView_ECV_export_permission_change_dataset(self):

        print('Test DatasetListView export_ecv with permission change_dataset')

        dataset_name = DEFAULT_DATASET
        print('Test Dataset is: ', dataset_name)

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(name=dataset_name)
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
        print('Message: ', json_message)

        self.assertEqual(str(json_message), 'ECV ' + dataset_name + ' successfully updated.')

    def test_DatasetListView_ECV_export_no_permission_change_dataset(self):

        print('Test DatasetListView export_ecv without permission')

        dataset_name = DEFAULT_DATASET
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

        dataset_name = DEFAULT_DATASET
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

        dataset_name = DEFAULT_DATASET
        print('Test Dataset is: ', dataset_name)

        # Give the test user permission to change a dataset
        test_dataset = Dataset.objects.get(name=dataset_name)
        assign_perm('change_dataset', self.user, test_dataset)
        print('User has permmission to change dataset.')

        assign_perm('dictionary.export_csv', self.user)
        print('User has permmission to export csv.')

        response = client.get('/signs/search/', {"search_type": "sign", "glosssearch_nl": "wesseltest6", "format": "CSV"})

        # print(str(response['Content-Type']))
        # print(str(response.status_code))
        # print(str(response.wsgi_request))
        # print(str(response.content))

        self.assertEqual(response['Content-Type'], "text/csv")
        self.assertContains(response, b'Signbank ID,Lemma ID Gloss,Dataset')

class VideoTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')


    def test_create_and_delete_video(self):

        NAME = 'thisisatemporarytestgloss'

        #Create the gloss
        new_gloss = Gloss()
        new_gloss.idgloss = NAME
        new_gloss.handedness = 4
        new_gloss.save()

        client = Client()
        client.login(username='test-user', password='test-user')

        video_url = '/dictionary/protected_media/glossvideo/'+NAME[0:2]+'/'+NAME+'-'+str(new_gloss.pk)+'.mp4'

        #We expect no video before
        response = client.get(video_url)
        self.assertEqual(response.status_code,302)

        #Upload the video
        videofile = open(settings.WRITABLE_FOLDER+'test_data/video.mp4','rb')
        client.post('/video/upload/',{'gloss_id':new_gloss.pk, 'videofile': videofile,'redirect':'/dictionary/gloss/'+str(new_gloss.pk)+'/?edit'})

        #We expect a video now
        response = client.get(video_url)
        self.assertEqual(response.status_code,200)

        #You can't see it if you log out
        client.logout()
        response = client.get(video_url)
        self.assertEqual(response.status_code,401)

        #Remove the video
        client.login(username='test-user',password='test-user')
        client.post('/video/delete/'+str(new_gloss.pk))

        #We expect no video anymore
        response = client.get(video_url)
        self.assertEqual(response.status_code,302)

class AjaxTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')


    def test_GlossSuggestion(self):

        NAME = 'thisisatemporarytestgloss'

        #Create the dataset
        dataset_name = DEFAULT_DATASET
        test_dataset = Dataset.objects.get(name=dataset_name)

        #Add a gloss to this dataset
        new_gloss = Gloss()
        new_gloss.idgloss = NAME
        new_gloss.annotation_idgloss = NAME
        new_gloss.dataset = test_dataset
        new_gloss.save()

        #Add a translation to be shown with ajax (in the language of the dataset)
        annotationidglosstranslation = AnnotationIdglossTranslation()
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
        self.assertContains(response,NAME)

class FrontEndTests(TestCase):

    def setUp(self):

        # a new test user is created for use during the tests
        self.user = User.objects.create_user('test-user', 'example@example.com', 'test-user')

        NAME = 'thisisatemporarytestgloss'

        #Create the dataset
        dataset_name = DEFAULT_DATASET
        self.test_dataset = Dataset.objects.get(name=dataset_name)

        #Add a gloss to this dataset
        self.hidden_gloss = Gloss()
        self.hidden_gloss.idgloss = NAME+'hidden'
        self.hidden_gloss.annotation_idgloss = NAME+'hidden'
        self.hidden_gloss.dataset = self.test_dataset
        self.hidden_gloss.save()

        self.public_gloss = Gloss()
        self.public_gloss.idgloss = NAME+'public'
        self.public_gloss.annotation_idgloss = NAME+'public'
        self.public_gloss.dataset = self.test_dataset
        self.public_gloss.inWeb = True
        self.public_gloss.save()

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

# Helper function to retrieve contents of json-encoded message
def decode_messages(data):
    if not data:
        return None
    bits = data.split('$', 1)
    if len(bits) == 2:
        hash, value = bits
        return value
    return None
