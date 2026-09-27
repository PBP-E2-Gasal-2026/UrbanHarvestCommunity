from django.contrib.sessions.models import Session as DjangoSession
from django.test import Client, TestCase
from django.urls import reverse

from .models import Role, Session, User


class UserLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='sari', email='sari@example.com', password='secret-123'
        )
        self.user.roles.add(Role.objects.create(name='user', description='Pengguna'))

    def test_user_can_log_in_and_session_is_recorded(self):
        response = self.client.post(reverse('authentication:login'), {
            'username': 'sari', 'password': 'secret-123'
        })

        self.assertRedirects(response, reverse('main:show_main'))
        self.assertEqual(Session.objects.get(user=self.user).session_token,
                         self.client.session.session_key)

    def test_invalid_password_does_not_create_session(self):
        response = self.client.post(reverse('authentication:login'), {
            'username': 'sari', 'password': 'wrong'
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Session.objects.filter(user=self.user).exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_non_user_role_cannot_log_in(self):
        self.user.roles.clear()
        self.user.roles.add(Role.objects.create(name='farmer', description='Petani'))

        response = self.client.post(reverse('authentication:login'), {
            'username': 'sari', 'password': 'secret-123'
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Session.objects.filter(user=self.user).exists())

    def test_second_login_revokes_first_session(self):
        first = Client()
        second = Client()
        first.post(reverse('authentication:login'), {
            'username': 'sari', 'password': 'secret-123'
        })
        first_key = first.session.session_key

        second.post(reverse('authentication:login'), {
            'username': 'sari', 'password': 'secret-123'
        })

        self.assertFalse(DjangoSession.objects.filter(session_key=first_key).exists())
        self.assertEqual(Session.objects.filter(user=self.user).count(), 1)
        first.get(reverse('main:show_main'))
        self.assertNotIn('_auth_user_id', first.session)
        self.assertIn('_auth_user_id', second.session)

    def test_logout_revokes_session(self):
        self.client.post(reverse('authentication:login'), {
            'username': 'sari', 'password': 'secret-123'
        })
        key = self.client.session.session_key

        response = self.client.post(reverse('authentication:logout'))

        self.assertRedirects(response, reverse('authentication:login'))
        self.assertFalse(Session.objects.filter(user=self.user).exists())
        self.assertFalse(DjangoSession.objects.filter(session_key=key).exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_requires_post(self):
        self.client.post(reverse('authentication:login'), {
            'username': 'sari', 'password': 'secret-123'
        })

        response = self.client.get(reverse('authentication:logout'))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Session.objects.filter(user=self.user).exists())

    def test_deleted_session_record_invalidates_django_session(self):
        self.client.post(reverse('authentication:login'), {
            'username': 'sari', 'password': 'secret-123'
        })
        Session.objects.filter(user=self.user).delete()

        self.client.get(reverse('main:show_main'))

        self.assertNotIn('_auth_user_id', self.client.session)


class UserRegistrationTests(TestCase):
    def test_register_creates_user_with_default_role(self):
        response = self.client.post(reverse('authentication:register'), {
            'username': 'budi',
            'email': 'budi@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        })

        self.assertRedirects(response, reverse('authentication:login'))
        user = User.objects.get(username='budi')
        self.assertTrue(user.check_password('SecurePass123!'))
        self.assertEqual(list(user.roles.values_list('name', flat=True)), ['user'])
        self.assertNotIn('_auth_user_id', self.client.session)

        login_response = self.client.post(reverse('authentication:login'), {
            'username': 'budi', 'password': 'SecurePass123!'
        })
        self.assertRedirects(login_response, reverse('main:show_main'))

    def test_register_reuses_default_role(self):
        Role.objects.create(name='user', description='Pengguna')

        self.client.post(reverse('authentication:register'), {
            'username': 'budi',
            'email': 'budi@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        })

        self.assertEqual(Role.objects.filter(name='user').count(), 1)

    def test_register_rejects_duplicate_username_and_email(self):
        User.objects.create_user('budi', 'budi@example.com', 'SecurePass123!')

        response = self.client.post(reverse('authentication:register'), {
            'username': 'budi',
            'email': 'budi@example.com',
            'password': 'AnotherPass123!',
            'password_confirm': 'AnotherPass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertContains(response, 'Username')

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('authentication:register'), {
            'username': 'budi',
            'email': 'budi@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'DifferentPass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='budi').exists())

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user('sari', 'budi@example.com', 'SecurePass123!')

        response = self.client.post(reverse('authentication:register'), {
            'username': 'budi',
            'email': 'BUDI@example.com',
            'password': 'AnotherPass123!',
            'password_confirm': 'AnotherPass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email')
        self.assertEqual(User.objects.count(), 1)

    def test_register_rejects_weak_password(self):
        response = self.client.post(reverse('authentication:register'), {
            'username': 'budi',
            'email': 'budi@example.com',
            'password': 'password',
            'password_confirm': 'password',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='budi').exists())
