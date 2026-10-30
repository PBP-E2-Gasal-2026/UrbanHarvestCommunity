from django.contrib.sessions.models import Session as DjangoSession
from django.test import Client, TestCase
from django.urls import reverse

from .forms import LoginForm
from .models import Merchant, Profile, Role, SellerApplication, Session, User
from .permissions import has_role


class UserLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='sari', email='sari@example.com', password='secret-123'
        )
        self.user.roles.add(Role.objects.create(name='farmer', description='Petani'))

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

    def test_login_form_validates_credentials_and_exposes_user(self):
        form = LoginForm(data={'username': 'sari', 'password': 'secret-123'})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.get_user(), self.user)

    def test_login_form_rejects_missing_password(self):
        form = LoginForm(data={'username': 'sari'})

        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

    def test_login_form_rejects_user_without_role(self):
        self.user.roles.clear()
        form = LoginForm(data={'username': 'sari', 'password': 'secret-123'})

        self.assertFalse(form.is_valid())
        self.assertIsNone(form.get_user())

    def test_non_farmer_role_cannot_log_in(self):
        self.user.roles.clear()

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
        self.assertEqual(list(user.roles.values_list('name', flat=True)), ['farmer'])
        self.assertNotIn('_auth_user_id', self.client.session)

        login_response = self.client.post(reverse('authentication:login'), {
            'username': 'budi', 'password': 'SecurePass123!'
        })
        self.assertRedirects(login_response, reverse('main:show_main'))

    def test_register_reuses_default_role(self):
        Role.objects.create(name='farmer', description='Petani')

        self.client.post(reverse('authentication:register'), {
            'username': 'budi',
            'email': 'budi@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        })

        self.assertEqual(Role.objects.filter(name='farmer').count(), 1)

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

    def test_register_rejects_password_without_special_character(self):
            response = self.client.post(reverse('authentication:register'), {
                'username': 'budi',
                'email': 'budi@example.com',
                'password': 'SecurePass123',
                'password_confirm': 'SecurePass123',
            })
    
            self.assertEqual(response.status_code, 200)
            self.assertFalse(User.objects.filter(username='budi').exists())

class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='sari', email='sari@example.com', password='secret-123'
        )
        self.user.roles.add(Role.objects.create(name='farmer', description='Petani'))
        self.other = User.objects.create_user(
            username='budi', email='budi@example.com', password='secret-123'
        )
        Profile.objects.create(user=self.other, bio='Bio Budi')

    def login(self):
        self.client.post(reverse('authentication:login'), {
            'username': 'sari', 'password': 'secret-123'
        })

    def test_register_creates_profile(self):
        self.client.post(reverse('authentication:register'), {
            'username': 'andi',
            'email': 'andi@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        })

        self.assertTrue(Profile.objects.filter(user__username='andi').exists())

    def test_profile_page_shows_profile(self):
        response = self.client.get(reverse('authentication:profile', args=['budi']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bio Budi')

    def test_owner_can_edit_profile(self):
        self.login()

        response = self.client.post(reverse('authentication:profile_edit'), {
            'bio': 'Petani padi', 'location': 'Bogor', 'community': 'Tani Maju'
        })

        self.assertRedirects(response, reverse('authentication:profile', args=['sari']))
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.bio, 'Petani padi')
        self.assertEqual(profile.location, 'Bogor')

    def test_edit_only_changes_own_profile(self):
        self.login()

        self.client.post(reverse('authentication:profile_edit'), {
            'bio': 'Diubah', 'location': '', 'community': ''
        })

        self.other.profile.refresh_from_db()
        self.assertEqual(self.other.profile.bio, 'Bio Budi')

    def test_username_cannot_be_changed(self):
        self.login()

        self.client.post(reverse('authentication:profile_edit'), {
            'username': 'sari-baru', 'bio': '', 'location': '', 'community': ''
        })

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'sari')

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('authentication:profile_edit'))

        self.assertRedirects(
            response,
            f"{reverse('authentication:login')}?next={reverse('authentication:profile_edit')}",
        )

class SellerApplicationTests(TestCase):
    def setUp(self):
        self.farmer_role = Role.objects.create(name='farmer', description='Petani')
        self.admin_role = Role.objects.create(name='admin', description='Admin')

        self.farmer = User.objects.create_user('sari', 'sari@example.com', 'secret-123')
        self.farmer.roles.add(self.farmer_role)
        self.admin = User.objects.create_user('admin1', 'admin@example.com', 'secret-123')
        self.admin.roles.add(self.admin_role)

    def login(self, username):
        self.client.post(reverse('authentication:login'), {
            'username': username, 'password': 'secret-123'
        })

    def apply(self):
        return self.client.post(reverse('authentication:seller_apply'))

    def review(self, application, decision):
        return self.client.post(
            reverse('authentication:seller_application_review', args=[application.pk]),
            {'decision': decision, 'admin_note': ''},
        )

    def test_farmer_can_apply(self):
        self.login('sari')

        self.apply()

        application = SellerApplication.objects.get(applicant=self.farmer)
        self.assertEqual(application.status, SellerApplication.Status.PENDING)

    def test_second_pending_application_is_rejected(self):
        self.login('sari')

        self.apply()
        self.apply()

        self.assertEqual(SellerApplication.objects.filter(applicant=self.farmer).count(), 1)

    def test_can_reapply_after_rejection(self):
        SellerApplication.objects.create(
            applicant=self.farmer, status=SellerApplication.Status.REJECTED
        )
        self.login('sari')

        self.apply()

        self.assertEqual(SellerApplication.objects.filter(
            applicant=self.farmer, status=SellerApplication.Status.PENDING
        ).count(), 1)

    def test_anonymous_cannot_apply(self):
        response = self.apply()

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('authentication:login'), response.url)
        self.assertFalse(SellerApplication.objects.exists())

    def test_non_farmer_cannot_apply(self):
        self.login('admin1')

        response = self.apply()

        self.assertEqual(response.status_code, 403)
        self.assertFalse(SellerApplication.objects.exists())

    def test_non_admin_cannot_see_queue(self):
        self.login('sari')

        response = self.client.get(reverse('authentication:seller_applications'))

        self.assertEqual(response.status_code, 403)

    def test_non_admin_cannot_approve(self):
        application = SellerApplication.objects.create(applicant=self.farmer)
        self.login('sari')

        response = self.review(application, 'approved')

        self.assertEqual(response.status_code, 403)
        application.refresh_from_db()
        self.assertEqual(application.status, SellerApplication.Status.PENDING)
        self.assertFalse(has_role(self.farmer, 'farmer-seller'))

    def test_admin_approval_grants_seller_role(self):
        application = SellerApplication.objects.create(applicant=self.farmer)
        self.assertFalse(has_role(self.farmer, 'farmer-seller'))
        self.login('admin1')

        self.review(application, 'approved')

        application.refresh_from_db()
        self.assertEqual(application.status, SellerApplication.Status.APPROVED)
        self.assertEqual(application.reviewed_by, self.admin)
        self.assertIsNotNone(application.reviewed_at)
        self.assertTrue(has_role(self.farmer, 'farmer-seller'))
        self.assertTrue(has_role(self.farmer, 'farmer'))

    def test_admin_rejection_does_not_grant_seller_role(self):
        application = SellerApplication.objects.create(applicant=self.farmer)
        self.login('admin1')

        self.review(application, 'rejected')

        application.refresh_from_db()
        self.assertEqual(application.status, SellerApplication.Status.REJECTED)
        self.assertFalse(has_role(self.farmer, 'farmer-seller'))

    def test_reviewed_application_cannot_be_reviewed_again(self):
        application = SellerApplication.objects.create(
            applicant=self.farmer, status=SellerApplication.Status.REJECTED
        )
        self.login('admin1')

        self.review(application, 'approved')

        application.refresh_from_db()
        self.assertEqual(application.status, SellerApplication.Status.REJECTED)
        self.assertFalse(has_role(self.farmer, 'farmer-seller'))

    def test_seller_cannot_apply_again(self):
        self.farmer.roles.add(Role.objects.create(name='farmer-seller', description='Penjual'))
        self.login('sari')

        self.apply()

        self.assertFalse(SellerApplication.objects.exists())

    def test_review_requires_post(self):
        application = SellerApplication.objects.create(applicant=self.farmer)
        self.login('admin1')

        response = self.client.get(
            reverse('authentication:seller_application_review', args=[application.pk])
        )

        self.assertEqual(response.status_code, 405)

class MerchantTests(TestCase):
    def setUp(self):
        self.farmer_role = Role.objects.create(name='farmer', description='Petani')
        self.seller_role = Role.objects.create(name='farmer-seller', description='Penjual')

        self.seller = User.objects.create_user('sari', 'sari@example.com', 'secret-123')
        self.seller.roles.add(self.farmer_role, self.seller_role)
        self.farmer = User.objects.create_user('budi', 'budi@example.com', 'secret-123')
        self.farmer.roles.add(self.farmer_role)

    def login(self, username, client=None):
        (client or self.client).post(reverse('authentication:login'), {
            'username': username, 'password': 'secret-123'
        })

    def merchant_data(self, **overrides):
        data = {
            'name': 'Kebun Sari',
            'description': 'Sayur organik',
            'location': 'Bogor',
            'show_location': 'on',
            'contact': '08123456789',
        }
        data.update(overrides)
        return data

    def test_seller_can_create_merchant(self):
        self.login('sari')

        response = self.client.post(reverse('authentication:merchant_edit'), self.merchant_data())

        self.assertRedirects(response, reverse('authentication:profile', args=['sari']))
        merchant = Merchant.objects.get(owner=self.seller)
        self.assertEqual(merchant.name, 'Kebun Sari')
        self.assertFalse(merchant.show_contact)

    def test_seller_can_update_merchant_without_duplicate(self):
        Merchant.objects.create(owner=self.seller, name='Lama')
        self.login('sari')

        self.client.post(reverse('authentication:merchant_edit'), self.merchant_data(name='Baru'))

        self.assertEqual(Merchant.objects.filter(owner=self.seller).count(), 1)
        self.assertEqual(Merchant.objects.get(owner=self.seller).name, 'Baru')

    def test_unapproved_farmer_cannot_create_merchant(self):
        self.login('budi')

        get_response = self.client.get(reverse('authentication:merchant_edit'))
        post_response = self.client.post(
            reverse('authentication:merchant_edit'), self.merchant_data()
        )

        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        self.assertFalse(Merchant.objects.exists())

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('authentication:merchant_edit'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('authentication:login'), response.url)

    def test_owner_cannot_be_set_from_form(self):
        self.login('sari')

        self.client.post(
            reverse('authentication:merchant_edit'),
            self.merchant_data(owner=self.farmer.pk),
        )

        self.assertTrue(Merchant.objects.filter(owner=self.seller).exists())
        self.assertFalse(Merchant.objects.filter(owner=self.farmer).exists())

    def test_seller_role_revoked_blocks_merchant_edit(self):
        Merchant.objects.create(owner=self.seller, name='Kebun Sari')
        self.login('sari')
        self.seller.roles.remove(self.seller_role)

        response = self.client.post(
            reverse('authentication:merchant_edit'), self.merchant_data(name='Diubah')
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Merchant.objects.get(owner=self.seller).name, 'Kebun Sari')

    def test_profile_shows_merchant_for_seller(self):
        Merchant.objects.create(owner=self.seller, name='Kebun Sari', location='Bogor')

        response = self.client.get(reverse('authentication:profile', args=['sari']))

        self.assertContains(response, 'Kebun Sari')
        self.assertContains(response, 'Bogor')

    def test_profile_hides_merchant_if_not_seller(self):
        Merchant.objects.create(owner=self.seller, name='Kebun Sari')
        self.seller.roles.remove(self.seller_role)

        response = self.client.get(reverse('authentication:profile', args=['sari']))

        self.assertNotContains(response, 'Kebun Sari')

    def test_hidden_contact_not_shown_to_public(self):
        Merchant.objects.create(
            owner=self.seller, name='Kebun Sari', contact='08123456789', show_contact=False
        )

        response = self.client.get(reverse('authentication:profile', args=['sari']))

        self.assertNotContains(response, '08123456789')

    def test_hidden_contact_still_shown_to_owner(self):
        Merchant.objects.create(
            owner=self.seller, name='Kebun Sari', contact='08123456789', show_contact=False
        )
        self.login('sari')

        response = self.client.get(reverse('authentication:profile', args=['sari']))

        self.assertContains(response, '08123456789')

    def test_full_flow_apply_approve_then_create_merchant(self):
        admin = User.objects.create_user('admin1', 'admin@example.com', 'secret-123')
        admin.roles.add(Role.objects.create(name='admin', description='Admin'))
        farmer_client, admin_client = Client(), Client()
        self.login('budi', farmer_client)
        self.login('admin1', admin_client)

        before = farmer_client.get(reverse('authentication:merchant_edit'))
        farmer_client.post(reverse('authentication:seller_apply'))
        application = SellerApplication.objects.get(applicant=self.farmer)
        admin_client.post(
            reverse('authentication:seller_application_review', args=[application.pk]),
            {'decision': 'approved', 'admin_note': ''},
        )
        farmer_client.post(reverse('authentication:merchant_edit'), self.merchant_data())

        self.assertEqual(before.status_code, 403)
        self.assertTrue(Merchant.objects.filter(owner=self.farmer).exists())