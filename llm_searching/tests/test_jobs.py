from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from llm_searching.exceptions import MarketplaceUnavailable, QueueFull, SearchError
from llm_searching.jobs import claim_job, finish_job, process_job, submit_job
from llm_searching.models import SearchJob


class JobsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "farmer", "farmer@example.com", "Pass!1234"
        )
        self.result = {
            "status": "succeeded",
            "products": [{"id": 1}],
            "filters": {},
            "explanation": "Tomat",
            "degraded": False,
        }

    def test_per_owner_active_quota(self):
        for _ in range(3):
            submit_job(self.user.pk, "tomat")
        with self.assertRaises(QueueFull):
            submit_job(self.user.pk, "tomat")
        self.assertEqual(SearchJob.objects.count(), 3)

    def test_atomic_claim_lease_and_stale_writer_fencing(self):
        job = submit_job(self.user.pk, "tomat")
        now = timezone.now()
        first = claim_job(job.pk, now=now)
        self.assertIsNotNone(first)
        self.assertIsNone(claim_job(job.pk, now=now))
        SearchJob.objects.filter(pk=job.pk).update(
            lease_expires_at=now - timedelta(seconds=1)
        )
        second = claim_job(job.pk, now=now)
        self.assertNotEqual(first, second)
        self.assertFalse(finish_job(job.pk, first, self.result))
        self.assertTrue(finish_job(job.pk, second, self.result))
        self.assertIsNone(claim_job(job.pk, now=now))
        job.refresh_from_db()
        self.assertEqual(job.result["products"], [{"id": 1}])

    def test_expired_owner_cannot_finalize(self):
        job = submit_job(self.user.pk, "tomat")
        token = claim_job(job.pk, now=timezone.now())
        SearchJob.objects.filter(pk=job.pk).update(
            lease_expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertFalse(finish_job(job.pk, token, self.result))

    def test_processing_terminal_and_safe_error_codes(self):
        job = submit_job(self.user.pk, "tomat")
        service = Mock()
        service.run.side_effect = MarketplaceUnavailable("private schema details")
        self.assertTrue(process_job(job.pk, service))
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error_code, "marketplace_unavailable")
        self.assertNotIn("private", str(job.result))
        self.assertFalse(process_job(job.pk, service))
        self.assertEqual(service.run.call_count, 1)

    def test_success_and_cleanup_only_old_terminal_jobs(self):
        job = submit_job(self.user.pk, "tomat")
        self.assertTrue(process_job(job.pk, Mock(run=Mock(return_value=self.result))))
        active = submit_job(self.user.pk, "tomat")
        old = timezone.now() - timedelta(hours=25)
        SearchJob.objects.filter(pk__in=[job.pk, active.pk]).update(
            created_at=old, finished_at=old
        )
        call_command("cleanup_llm_jobs", verbosity=0)
        self.assertFalse(SearchJob.objects.filter(pk=job.pk).exists())
        self.assertTrue(SearchJob.objects.filter(pk=active.pk).exists())

    def test_five_jobs_per_rolling_minute_including_finished_jobs(self):
        for _ in range(5):
            job = submit_job(self.user.pk, "tomat")
            SearchJob.objects.filter(pk=job.pk).update(status="succeeded")
        with self.assertRaises(SearchError) as error:
            submit_job(self.user.pk, "tomat")
        self.assertEqual(error.exception.code, "rate_limited")
        self.assertTrue(1 <= error.exception.retry_after <= 60)
        other = get_user_model().objects.create_user(
            "other", "other@example.com", password="Pass!1234"
        )
        self.assertIsNotNone(submit_job(other.pk, "tomat"))
        SearchJob.objects.filter(owner=self.user).update(
            created_at=timezone.now() - timedelta(seconds=61)
        )
        self.assertIsNotNone(submit_job(self.user.pk, "tomat"))

    def test_rolling_window_expiry_and_retry_after(self):
        now = timezone.now()
        for seconds_ago in (50, 40, 30, 20, 10):
            job = SearchJob.objects.create(
                owner=self.user, prompt="tomat", status="succeeded"
            )
            SearchJob.objects.filter(pk=job.pk).update(
                created_at=now - timedelta(seconds=seconds_ago)
            )
        with patch("llm_searching.jobs.timezone.now", return_value=now):
            with self.assertRaises(SearchError) as error:
                submit_job(self.user.pk, "tomat")
            self.assertEqual(error.exception.code, "rate_limited")
            self.assertEqual(error.exception.retry_after, 10)
        with patch(
            "llm_searching.jobs.timezone.now", return_value=now + timedelta(seconds=10)
        ):
            self.assertIsNotNone(submit_job(self.user.pk, "tomat"))
