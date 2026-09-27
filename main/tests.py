from django.test import TestCase, Client
from django.urls import reverse


class LandingPageTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_landing_page_url_exists_at_root(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_landing_page_uses_correct_template(self):
        response = self.client.get(reverse('main:show_main'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateUsed(response, 'includes/navbar.html')
        self.assertTemplateUsed(response, 'includes/footer.html')

    def test_landing_page_contains_key_elements(self):
        response = self.client.get('/')
        self.assertContains(response, 'Urban Harvest')
        self.assertContains(response, 'Growing The')
        self.assertContains(response, 'Future of Agriculture')
        self.assertContains(response, 'Marketplace')
        self.assertContains(response, 'Peta Kebun')
        self.assertContains(response, 'AI Search')

