from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.utils import timezone

from llm_searching.exceptions import QueueFull
from llm_searching.jobs import claim_job, submit_job
from llm_searching.models import SearchJob


@skipUnless(connection.vendor == "postgresql", "Requires real PostgreSQL row locking")
class PostgresConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "race", "race@example.com", "Pass!1234"
        )

    def test_concurrent_admission_never_exceeds_owner_quota(self):
        gate = Barrier(6)

        def submit():
            close_old_connections()
            try:
                gate.wait(timeout=10)
                try:
                    submit_job(self.user.pk, "tomat")
                    return "accepted"
                except QueueFull:
                    return "full"
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: submit(), range(6)))
        self.assertEqual(results.count("accepted"), 3)
        self.assertEqual(results.count("full"), 3)
        self.assertEqual(SearchJob.objects.count(), 3)

    def test_competing_workers_only_one_claim_succeeds(self):
        job = submit_job(self.user.pk, "tomat")
        gate = Barrier(4)

        def claim():
            close_old_connections()
            try:
                gate.wait(timeout=10)
                return claim_job(job.pk, now=timezone.now())
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=4) as pool:
            tokens = list(pool.map(lambda _: claim(), range(4)))
        self.assertEqual(sum(token is not None for token in tokens), 1)
