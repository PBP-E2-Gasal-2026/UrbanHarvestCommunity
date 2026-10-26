import json
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from authentication.models import Session
from llm_searching.jobs import submit_job
from llm_searching.models import SearchJob

class ViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("viewer", "viewer@example.com", "Pass!1234")
        self.url = "/llm-search/api/jobs/"
        self.login_client(self.client)

    def login_client(self, client):
        client.force_login(self.user)
        Session.objects.create(user=self.user, session_token=client.session.session_key,
                               expires_at=timezone.now()+timedelta(hours=1))

    def post(self, prompt="tomat", **kwargs):
        return self.client.post(self.url, json.dumps({"prompt": prompt}), content_type="application/json", **kwargs)

    def test_guest_page_and_api_require_login(self):
        guest = Client()
        self.assertEqual(guest.get("/llm-search/").status_code, 302)
        self.assertEqual(guest.post(self.url, "{}", content_type="application/json").status_code, 401)

    def test_authenticated_create_status_and_limits(self):
        response = self.post()
        self.assertEqual(response.status_code, 202)
        result = response.json()
        self.assertEqual(self.client.get(result["status_url"]).json()["status"], "pending")
        self.assertEqual(self.post().status_code, 202)
        self.assertEqual(self.post().status_code, 202)
        self.assertEqual(self.post().status_code, 429)
        self.assertEqual(self.post("").status_code, 400)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_job_ownership_and_safe_dependency_error(self):
        other = get_user_model().objects.create_user("other", "other@example.com", "Pass!1234")
        job = submit_job(other.pk, "tomat")
        self.assertEqual(self.client.get(f"{self.url}{job.pk}/").status_code, 404)
        own = submit_job(self.user.pk, "tomat")
        SearchJob.objects.filter(pk=own.pk).update(status="failed", error_code="marketplace_unavailable")
        body = self.client.get(f"{self.url}{own.pk}/").json()
        self.assertEqual(body["error_code"], "marketplace_unavailable")
        self.assertNotIn("prompt", body)
        self.assertNotIn("lease_token", body)

    def test_csrf_and_malformed_payloads(self):
        strict = Client(enforce_csrf_checks=True)
        self.login_client(strict)
        self.assertEqual(strict.post(self.url, '{"prompt":"tomat"}', content_type="application/json").status_code, 403)
        for body in ('{', '[]', '{"prompt":"tomat","sql":"DELETE"}', '{"prompt":"tomat","prompt":"x"}'):
            with self.subTest(body=body):
                self.assertEqual(self.client.post(self.url, body, content_type="application/json").status_code, 400)

    def test_page_and_card_escape_product_text(self):
        response = self.client.get("/llm-search/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'maxlength="2000"')
        self.assertContains(response, "csrfmiddlewaretoken")
        from django.template.loader import render_to_string
        html = render_to_string("llm_searching/card.html", {"product": {
            "name": "<script>alert(1)</script>", "id": 42, "url": "/marketplace/products/42/",
            "price": 10000, "unit": "kg", "stock": 1, "location": "Depok", "category": {"name": "Sayuran"}}})
        self.assertIn("/marketplace/products/42/", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
