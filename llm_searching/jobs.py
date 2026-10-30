"""Durable job state; transactions never span external HTTP requests."""

import logging
import math
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from .exceptions import QueueFull, RateLimited, SearchError
from .filters import validate_prompt
from .models import SearchJob

logger = logging.getLogger(__name__)
TERMINAL = ("succeeded", "needs_clarification", "failed")
ACTIVE = ("pending", "processing")


def submit_job(user_id: int, prompt: str) -> SearchJob:
    prompt = validate_prompt(prompt)
    with transaction.atomic():
        # This identity lock belongs to job admission, not marketplace searching.
        get_user_model().objects.select_for_update().get(pk=user_id)
        now = timezone.now()
        recent = SearchJob.objects.filter(
            owner_id=user_id, created_at__gt=now - timedelta(seconds=60)
        ).order_by("created_at")
        if recent.count() >= 5:
            retry_after = max(
                1,
                math.ceil(
                    (
                        recent.first().created_at + timedelta(seconds=60) - now
                    ).total_seconds()
                ),
            )
            raise RateLimited(retry_after)
        if (
            SearchJob.objects.filter(owner_id=user_id, status__in=ACTIVE).count()
            >= settings.LLM_MAX_ACTIVE_JOBS
        ):
            raise QueueFull("Tunggu pencarian sebelumnya selesai sebelum mencoba lagi.")
        return SearchJob.objects.create(owner_id=user_id, prompt=prompt)


def eligible_jobs(now=None):
    now = now or timezone.now()
    return SearchJob.objects.filter(
        Q(status="pending") | Q(status="processing", lease_expires_at__lte=now)
    ).order_by("created_at", "id")


def claim_job(job_id, *, now):
    token = uuid.uuid4()
    updated = (
        eligible_jobs(now)
        .filter(pk=job_id)
        .update(
            status="processing",
            lease_token=token,
            lease_expires_at=now + timedelta(seconds=settings.LLM_LEASE_SECONDS),
            attempts=F("attempts") + 1,
        )
    )
    return token if updated else None


def finish_job(job_id, token, result):
    status = result.get("status")
    if status not in TERMINAL:
        raise ValueError("Invalid terminal job status")
    return bool(
        SearchJob.objects.filter(
            pk=job_id,
            status="processing",
            lease_token=token,
            lease_expires_at__gt=timezone.now(),
        ).update(
            status=status,
            result=result,
            error_code=result.get("error_code", ""),
            finished_at=timezone.now(),
            lease_token=None,
            lease_expires_at=None,
        )
    )


def process_job(job_id, service):
    token = claim_job(job_id, now=timezone.now())
    if token is None:
        return False
    job = SearchJob.objects.get(pk=job_id)
    try:
        result = service.run(job.prompt)
    except SearchError as exc:
        result = {
            "status": "failed",
            "error_code": exc.code,
            "products": [],
            "filters": {},
            "explanation": "Pencarian belum dapat diselesaikan. Silakan coba lagi.",
            "degraded": False,
        }
    except Exception:  # noqa: BLE001 - job boundary must persist a safe failure without leaking upstream details
        # No exception text: upstream errors can contain prompts, tokens or SQL parameters.
        logger.error(
            "LLM search job failed unexpectedly", extra={"job_id": str(job_id)}
        )
        result = {
            "status": "failed",
            "error_code": "search_failed",
            "products": [],
            "filters": {},
            "explanation": "Pencarian belum dapat diselesaikan. Silakan coba lagi.",
            "degraded": False,
        }
    return finish_job(job_id, token, result)
