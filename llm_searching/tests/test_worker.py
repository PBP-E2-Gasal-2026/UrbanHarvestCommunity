from concurrent.futures import Future
from collections import deque
from unittest.mock import Mock
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils import timezone
from llm_searching.jobs import submit_job, claim_job
from llm_searching.models import SearchJob
from llm_searching.transport import BrokerUnavailable, Delivery
from llm_searching.worker import WorkerCoordinator

class ImmediateExecutor:
    def submit(self, fn, *args):
        future = Future()
        try: future.set_result(fn(*args))
        except Exception as error: future.set_exception(error)
        return future
    def shutdown(self, wait=True): pass

class Broker:
    def __init__(self):
        self.available = True
        self.ambiguous = False
        self.queue = deque()
        self.acked = []
    def factory(self):
        broker = self
        class Connection:
            def connect(self):
                if not broker.available: raise BrokerUnavailable()
            def publish(self, job_id):
                if not broker.available: raise BrokerUnavailable()
                broker.queue.append(Delivery(str(job_id), job_id))
                if broker.ambiguous: raise BrokerUnavailable()
            def receive(self):
                if not broker.available: raise BrokerUnavailable()
                return broker.queue.popleft() if broker.queue else None
            def ack(self, delivery): broker.acked.append(delivery.tag)
            def maintain(self):
                if not broker.available: raise BrokerUnavailable()
            def close(self): pass
        return Connection()

class WorkerTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("worker", "worker@example.com", "Pass!1234")
        self.broker = Broker()
        self.clock = 0
        self.service = Mock()
        self.service.run.return_value = {"status": "succeeded", "products": [], "filters": {}, "explanation": "ok", "degraded": False}
        self.worker = WorkerCoordinator(transport_factory=self.broker.factory, service_factory=lambda: self.service,
                                        executor=ImmediateExecutor(), clock=lambda: self.clock)
    def tearDown(self): self.worker.close()

    def test_healthy_delivery_and_redelivery_only_finalize_once(self):
        job = submit_job(self.user.pk, "tomat")
        self.worker.tick()
        job.refresh_from_db()
        self.assertEqual(job.status, "succeeded")
        self.broker.queue.append(Delivery("duplicate", job.pk))
        self.worker.tick()
        self.assertEqual(self.service.run.call_count, 1)
        self.assertIn("duplicate", self.broker.acked)

    def test_missing_broker_processes_one_job_per_tick_and_recovers(self):
        self.broker.available = False
        jobs = [submit_job(self.user.pk, "tomat") for _ in range(3)]
        self.worker.tick()
        self.assertEqual(SearchJob.objects.filter(status="succeeded").count(), 1)
        self.assertFalse(self.worker.broker_healthy)
        self.clock = 31
        self.broker.available = True
        self.worker.tick()
        self.assertTrue(self.worker.broker_healthy)
        self.assertEqual(SearchJob.objects.filter(status="succeeded").count(), len(jobs))

    def test_ambiguous_publish_falls_back_and_late_message_is_harmless(self):
        job = submit_job(self.user.pk, "tomat")
        self.broker.ambiguous = True
        self.worker.tick()
        job.refresh_from_db()
        self.assertEqual(job.status, "succeeded")
        self.broker.ambiguous = False
        self.clock = 31
        self.worker.tick()
        self.assertEqual(self.service.run.call_count, 1)

    def test_fallback_waits_for_inflight_and_recovers_expired_claim(self):
        job = submit_job(self.user.pk, "tomat")
        claim_job(job.pk, now=timezone.now())
        SearchJob.objects.filter(pk=job.pk).update(lease_expires_at=timezone.now()-timedelta(seconds=1))
        future = Future()
        self.worker.futures.add(future)
        self.broker.available = False
        self.worker.tick()
        self.assertEqual(self.service.run.call_count, 0)
        future.set_result(None)
        self.worker.tick()
        job.refresh_from_db()
        self.assertEqual(job.status, "succeeded")
