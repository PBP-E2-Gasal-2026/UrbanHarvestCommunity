"""One coordinator per deployment; RabbitMQ is optional for progress."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import logging
import time

from django.conf import settings
from django.db import close_old_connections
from django.db.models import Q
from django.utils import timezone

from .jobs import eligible_jobs, process_job
from .service import SearchService
from .transport import BrokerUnavailable, RabbitTransport

logger = logging.getLogger(__name__)

class WorkerCoordinator:
    def __init__(self, *, transport_factory=None, service_factory=SearchService, executor=None, clock=time.monotonic):
        self.transport_factory = transport_factory or (lambda: RabbitTransport(settings.LLM_RABBITMQ_URL))
        self.service_factory = service_factory
        self.pool_size = settings.LLM_WORKERS
        self.executor = executor or ThreadPoolExecutor(max_workers=self.pool_size, thread_name_prefix="llm-search")
        self.clock = clock
        self.transport = None
        self.futures = set()
        self.retry_at = 0
        self.backoff = 1
        self.broker_healthy = False

    def _disconnect(self):
        if self.transport is not None:
            self.transport.close()
        self.transport = None
        self.broker_healthy = False
        self.retry_at = self.clock() + self.backoff
        self.backoff = min(30, self.backoff * 2)

    def _consume_one(self):
        close_old_connections()
        transport = self.transport_factory()
        try:
            transport.connect()
            delivery = transport.receive()
            if delivery is not None:
                # If claim fails, the DB-backed coordinator will recover expired work;
                # a duplicate or terminal message can safely be acknowledged.
                process_job(delivery.job_id, self.service_factory())
                transport.ack(delivery)
        finally:
            transport.close()
            close_old_connections()

    def tick(self):
        failed = False
        for future in list(self.futures):
            if future.done():
                self.futures.remove(future)
                if future.exception() is not None:
                    failed = True
        if failed:
            self._disconnect()
        if self.transport is None and self.clock() >= self.retry_at:
            transport = self.transport_factory()
            try:
                transport.connect()
                self.transport = transport
                self.broker_healthy = True
                self.backoff = 1
            except BrokerUnavailable:
                transport.close()
                self._disconnect()
        if self.transport is not None:
            try:
                self.transport.maintain()
                capacity = max(0, self.pool_size - len(self.futures))
                now = timezone.now()
                ready = eligible_jobs(now).filter(Q(dispatch_after__isnull=True) | Q(dispatch_after__lte=now))
                for job_id in list(ready.values_list("id", flat=True)[:capacity]):
                    # Reserve dispatch before publishing: ambiguous confirms cannot create a tight duplicate loop.
                    eligible_jobs(now).filter(pk=job_id).update(dispatch_after=now + timedelta(seconds=30))
                    self.transport.publish(job_id)
                for _ in range(capacity):
                    self.futures.add(self.executor.submit(self._consume_one))
                return
            except BrokerUnavailable:
                self._disconnect()
        # Drain any existing parallel work before admitting a serial fallback job.
        if not self.futures:
            job_id = eligible_jobs().values_list("id", flat=True).first()
            if job_id is not None:
                process_job(job_id, self.service_factory())

    def close(self):
        self.executor.shutdown(wait=True)
        if self.transport is not None:
            self.transport.close()
        close_old_connections()
