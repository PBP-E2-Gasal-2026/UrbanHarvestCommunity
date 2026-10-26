from datetime import timedelta
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from llm_searching.models import SearchJob
from llm_searching.jobs import submit_job, claim_job, finish_job, process_job
from llm_searching.exceptions import QueueFull, MarketplaceUnavailable


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
