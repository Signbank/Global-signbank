from datetime import timedelta

from django.contrib.auth.models import User, AnonymousUser
from django.core.cache import cache
from django.http import JsonResponse
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone
from guardian.shortcuts import assign_perm

from signbank.api_token import (create_api_token, put_api_user_in_request, put_api_user_in_request_read_only,
                                 hash_token)
from signbank.api_interface import upload_videos_to_glosses
from signbank.dictionary.models import SignbankAPIToken, Dataset
from signbank.dictionary.views import info


@put_api_user_in_request
def whoami(request):
    return JsonResponse({'username': request.user.username if request.user.is_authenticated else None})


@put_api_user_in_request_read_only
def whoami_read_only(request):
    return JsonResponse({'username': request.user.username if request.user.is_authenticated else None})


class APITokenAuthTests(TestCase):

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='token_user', password='pw')

    def call(self, token, method='get', view=whoami):
        request = getattr(self.factory, method)('/api/', HTTP_AUTHORIZATION=f'Bearer {token}')
        return view(request)

    def test_valid_token(self):
        signbank_token, token = create_api_token(self.user, name='script')
        self.assertEqual(len(token), 40)
        self.assertEqual(signbank_token.api_token, hash_token(token))
        self.assertEqual(signbank_token.prefix, token[:6])
        response = self.call(token)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'username': 'token_user'})
        signbank_token.refresh_from_db()
        self.assertIsNotNone(signbank_token.last_used_at)

    def test_no_token_is_anonymous(self):
        # requests without a token keep working anonymously for public data
        request = self.factory.get('/api/')
        request.user = AnonymousUser()
        response = whoami(request)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'username': None})

    def test_unknown_token(self):
        self.assertEqual(self.call('nonsense').status_code, 401)

    def test_expired_token(self):
        _signbank_token, token = create_api_token(self.user, expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.call(token).status_code, 401)

    def test_inactive_token(self):
        signbank_token, token = create_api_token(self.user)
        signbank_token.is_active = False
        signbank_token.save()
        self.assertEqual(self.call(token).status_code, 401)

    def test_inactive_user(self):
        _signbank_token, token = create_api_token(self.user)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.call(token).status_code, 401)

    def test_read_only_token(self):
        # read only tokens only work on endpoints marked read only, whatever the HTTP method
        _signbank_token, token = create_api_token(self.user, read_only=True)
        self.assertEqual(self.call(token, 'get', whoami_read_only).status_code, 200)
        self.assertEqual(self.call(token, 'post', whoami_read_only).status_code, 200)
        self.assertEqual(self.call(token, 'get').status_code, 403)
        self.assertEqual(self.call(token, 'post').status_code, 403)

    def test_read_only_token_on_real_endpoints(self):
        _signbank_token, token = create_api_token(self.user, read_only=True)
        self.assertEqual(self.call(token, 'get', info).status_code, 200)
        # an endpoint that changes data does not check the HTTP method itself
        request = self.factory.get('/api/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(upload_videos_to_glosses(request, '1').status_code, 403)

    def test_read_write_token_on_read_only_endpoint(self):
        _signbank_token, token = create_api_token(self.user)
        self.assertEqual(self.call(token, 'get', whoami_read_only).status_code, 200)

    def test_rate_limit(self):
        _signbank_token, token = create_api_token(self.user, rate_limit=2)
        self.assertEqual(self.call(token).status_code, 200)
        self.assertEqual(self.call(token).status_code, 200)
        self.assertEqual(self.call(token).status_code, 429)

    @override_settings(API_TOKEN_DEFAULT_RATE_LIMIT=1)
    def test_default_rate_limit(self):
        _signbank_token, token = create_api_token(self.user)
        self.assertEqual(self.call(token).status_code, 200)
        self.assertEqual(self.call(token).status_code, 429)

    def test_legacy_token_without_prefix(self):
        # tokens made before prefixes existed were 16 characters and only stored as a hash
        legacy_token = 'abcdefghijklmnop'
        SignbankAPIToken.objects.create(signbank_user=self.user, api_token=hash_token(legacy_token))
        self.assertEqual(self.call(legacy_token).status_code, 200)


class APITokenProfileTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='token_user', password='pw')
        self.other_user = User.objects.create_user(username='other_user', password='pw')
        self.client.login(username='token_user', password='pw')

    def test_generate_token(self):
        response = self.client.post(reverse('registration:generate_api_token'),
                                    {'name': 'upload script', 'expiry_days': '30', 'rate_limit': '100',
                                     'read_only': 'on'})
        self.assertEqual(response.status_code, 200)
        token = response.json()['new_token']
        signbank_token = SignbankAPIToken.objects.get(signbank_user=self.user)
        self.assertEqual(signbank_token.api_token, hash_token(token))
        self.assertEqual(signbank_token.name, 'upload script')
        self.assertEqual(signbank_token.rate_limit, 100)
        self.assertTrue(signbank_token.read_only)
        self.assertAlmostEqual(signbank_token.expires_at, timezone.now() + timedelta(days=30),
                               delta=timedelta(minutes=1))

    def test_generate_token_never_expires(self):
        response = self.client.post(reverse('registration:generate_api_token'), {'expiry_days': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(SignbankAPIToken.objects.get(signbank_user=self.user).expires_at)

    def test_generate_token_invalid_input(self):
        self.assertEqual(self.client.post(reverse('registration:generate_api_token'), {'expiry_days': '12'}).status_code, 400)
        for rate_limit in ['-5', '0', 'abc', '1000001', '9' * 5000]:
            response = self.client.post(reverse('registration:generate_api_token'), {'rate_limit': rate_limit})
            self.assertEqual(response.status_code, 400, rate_limit)
        self.assertFalse(SignbankAPIToken.objects.filter(signbank_user=self.user).exists())

    @override_settings(API_TOKEN_DEFAULT_RATE_LIMIT=50)
    def test_generate_token_rate_limit_above_default(self):
        response = self.client.post(reverse('registration:generate_api_token'), {'rate_limit': '51'})
        self.assertEqual(response.status_code, 400)

    def test_generate_token_requires_post_and_login(self):
        self.assertEqual(self.client.get(reverse('registration:generate_api_token')).status_code, 405)
        self.client.logout()
        self.client.post(reverse('registration:generate_api_token'))
        self.assertFalse(SignbankAPIToken.objects.filter(signbank_user=self.user).exists())

    def test_delete_own_token(self):
        signbank_token, _token = create_api_token(self.user)
        response = self.client.post(reverse('registration:delete_api_token', args=[signbank_token.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SignbankAPIToken.objects.filter(pk=signbank_token.pk).exists())

    def test_cannot_delete_other_users_token(self):
        signbank_token, _token = create_api_token(self.other_user)
        self.client.post(reverse('registration:delete_api_token', args=[signbank_token.id]))
        self.assertTrue(SignbankAPIToken.objects.filter(pk=signbank_token.pk).exists())


class APITokenPagesTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(username='token_admin', password='pw', email='a@example.com')
        self.client.login(username='token_admin', password='pw')

    def test_profile_lists_tokens_and_links_manual(self):
        # the API section is only shown to users who can change glosses in a dataset
        dataset = Dataset.objects.first()
        assign_perm('view_dataset', self.admin, dataset)
        assign_perm('change_dataset', self.admin, dataset)
        create_api_token(self.admin, name='my upload script')
        response = self.client.get(reverse('registration:user_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'my upload script')
        self.assertContains(response, 'https://signbank.github.io/Global-signbank/')

    @override_settings(API_MANUAL_URL='')
    def test_profile_hides_manual_link_when_not_set(self):
        dataset = Dataset.objects.first()
        assign_perm('view_dataset', self.admin, dataset)
        assign_perm('change_dataset', self.admin, dataset)
        response = self.client.get(reverse('registration:user_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Signbank API manual')

    def test_admin_extend_tokens(self):
        now = timezone.now()
        long_token, _token = create_api_token(self.admin, expires_at=now + timedelta(days=300))
        expired_token, _token = create_api_token(self.admin, expires_at=now - timedelta(days=10))
        permanent_token, _token = create_api_token(self.admin)
        self.client.post(reverse('admin:dictionary_signbankapitoken_changelist'),
                         {'action': 'extend_tokens_90_days',
                          '_selected_action': [long_token.id, expired_token.id, permanent_token.id]})
        for signbank_token in [long_token, expired_token, permanent_token]:
            signbank_token.refresh_from_db()
        # extended from the current expiry, from now for expired tokens, never expiring tokens unchanged
        self.assertAlmostEqual(long_token.expires_at, now + timedelta(days=390), delta=timedelta(minutes=1))
        self.assertAlmostEqual(expired_token.expires_at, now + timedelta(days=90), delta=timedelta(minutes=1))
        self.assertIsNone(permanent_token.expires_at)

    def test_admin_pages(self):
        signbank_token, _token = create_api_token(self.admin, name='admin listed token')
        response = self.client.get(reverse('admin:dictionary_signbankapitoken_changelist'))
        self.assertContains(response, 'admin listed token')
        response = self.client.get(reverse('admin:auth_user_change', args=[self.admin.id]))
        self.assertContains(response, 'admin listed token')

    def test_admin_add_generates_token(self):
        response = self.client.post(reverse('admin:dictionary_signbankapitoken_add'),
                                    {'signbank_user': self.admin.id, 'name': 'made in admin', 'is_active': 'on'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        signbank_token = SignbankAPIToken.objects.get(name='made in admin')
        self.assertEqual(len(signbank_token.api_token), 64)
        self.assertContains(response, signbank_token.prefix)
