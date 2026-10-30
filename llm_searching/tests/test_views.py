import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from authentication.models import Session
from llm_searching import views
from llm_searching.jobs import submit_job
from llm_searching.models import SearchJob


class ViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "viewer", "viewer@example.com", "Pass!1234"
        )
        self.url = "/llm-search/api/jobs/"
        self.login_client(self.client)

    def login_client(self, client):
        client.force_login(self.user)
        Session.objects.create(
            user=self.user,
            session_token=client.session.session_key,
            expires_at=timezone.now() + timedelta(hours=1),
        )

    def post(self, prompt="tomat", **kwargs):
        return self.client.post(
            self.url,
            json.dumps({"prompt": prompt}),
            content_type="application/json",
            **kwargs,
        )

    def test_guest_page_and_api_require_login(self):
        guest = Client()
        self.assertEqual(guest.get("/llm-search/").status_code, 302)
        self.assertEqual(
            guest.post(self.url, "{}", content_type="application/json").status_code, 401
        )

    def test_authenticated_create_status_and_limits(self):
        response = self.post()
        self.assertEqual(response.status_code, 202)
        result = response.json()
        self.assertEqual(
            self.client.get(result["status_url"]).json()["status"], "pending"
        )
        self.assertEqual(self.post().status_code, 202)
        self.assertEqual(self.post().status_code, 202)
        self.assertEqual(self.post().status_code, 429)
        self.assertEqual(self.post("").status_code, 400)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_job_ownership_and_safe_dependency_error(self):
        other = get_user_model().objects.create_user(
            "other", "other@example.com", "Pass!1234"
        )
        job = submit_job(other.pk, "tomat")
        self.assertEqual(self.client.get(f"{self.url}{job.pk}/").status_code, 404)
        own = submit_job(self.user.pk, "tomat")
        SearchJob.objects.filter(pk=own.pk).update(
            status="failed", error_code="marketplace_unavailable"
        )
        body = self.client.get(f"{self.url}{own.pk}/").json()
        self.assertEqual(body["error_code"], "marketplace_unavailable")
        self.assertNotIn("prompt", body)
        self.assertNotIn("lease_token", body)

    def test_word_limit_is_enforced_before_creating_a_job(self):
        response = self.post("tomat " * 501)
        self.assertEqual(response.status_code, 400)
        self.assertIn("500 kata", response.json()["message"])
        self.assertEqual(SearchJob.objects.count(), 0)

        prompt = "tomat segar\n" * 250
        response = self.post(prompt)
        self.assertEqual(response.status_code, 202)
        job = SearchJob.objects.get(pk=response.json()["id"])
        self.assertEqual(job.prompt, prompt.strip())
        job.full_clean(exclude=["result"])

    def test_csrf_and_malformed_payloads(self):
        strict = Client(enforce_csrf_checks=True)
        self.login_client(strict)
        self.assertEqual(
            strict.post(
                self.url, '{"prompt":"tomat"}', content_type="application/json"
            ).status_code,
            403,
        )
        for body in (
            "{",
            "[]",
            '{"prompt":"tomat","sql":"DELETE"}',
            '{"prompt":"tomat","prompt":"x"}',
        ):
            with self.subTest(body=body):
                self.assertEqual(
                    self.client.post(
                        self.url, body, content_type="application/json"
                    ).status_code,
                    400,
                )

    def test_character_limit_is_enforced_before_creating_a_job(self):
        response = self.post("x" * 5001)
        self.assertEqual(response.status_code, 400)
        self.assertIn("5.000 karakter", response.json()["message"])
        self.assertEqual(SearchJob.objects.count(), 0)

        prompt = "x" * 5000
        response = self.post(prompt)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(SearchJob.objects.get(pk=response.json()["id"]).prompt, prompt)

    def test_page_and_card_escape_product_text(self):
        response = self.client.get("/llm-search/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0/500 kata")
        self.assertContains(
            response, 'aria-describedby="search-prompt-limit search-word-count"'
        )
        self.assertContains(response, "csrfmiddlewaretoken")
        from django.template.loader import render_to_string

        html = render_to_string(
            "llm_searching/card.html",
            {
                "product": {
                    "name": "<script>alert(1)</script>",
                    "id": 42,
                    "url": "/marketplace/products/42/",
                    "price": 10000,
                    "unit": "kg",
                    "stock": 1,
                    "location": "Depok",
                    "category": {"name": "Sayuran"},
                }
            },
        )
        self.assertIn("/marketplace/products/42/", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_rate_limit_returns_retry_after(self):
        for _ in range(5):
            response = self.post()
            self.assertEqual(response.status_code, 202)
            SearchJob.objects.filter(pk=response.json()["id"]).update(
                status="succeeded"
            )
        response = self.post()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error_code"], "rate_limited")
        self.assertTrue(1 <= int(response["Retry-After"]) <= 60)


class InlineJobTests(TestCase):
    """Tanpa worker terpisah (PWS), job harus diproses langsung setelah dibuat."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("inline", "inline@example.com", "Pass!1234")
        ViewsTests.login_client(self, self.client)

    def post(self):
        return self.client.post(
            "/llm-search/api/jobs/", json.dumps({"prompt": "tomat"}), content_type="application/json"
        )

    @override_settings(LLM_INLINE_JOBS=True)
    def test_job_is_started_inline_after_commit(self):
        with patch("llm_searching.views._start_inline_job") as start, self.captureOnCommitCallbacks(execute=True):
            response = self.post()
        self.assertEqual(response.status_code, 202)
        start.assert_called_once_with(SearchJob.objects.get().pk)

    @override_settings(LLM_INLINE_JOBS=False)
    def test_job_waits_for_worker_when_inline_disabled(self):
        with patch("llm_searching.views._start_inline_job") as start, self.captureOnCommitCallbacks(execute=True):
            self.post()
        start.assert_not_called()

    def test_inline_runner_finishes_job(self):
        job = submit_job(self.user.pk, "tomat")
        service = type("Fake", (), {"run": lambda self, prompt: {
            "status": "succeeded", "products": [], "filters": {}, "explanation": "ok", "degraded": False,
        }})
        with patch("llm_searching.views.SearchService", service):
            views._run_job_inline(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, "succeeded")
