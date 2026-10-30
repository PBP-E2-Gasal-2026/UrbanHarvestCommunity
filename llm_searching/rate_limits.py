"""Rolling admission limit for persisted search jobs, shared across workers."""

import math
from datetime import timedelta

from django.utils import timezone

from .exceptions import RateLimited
from .models import SearchJob

JOB_RATE_LIMIT = 5
JOB_RATE_WINDOW = timedelta(seconds=60)


def enforce_job_rate_limit(user_id: int, *, now=None) -> None:
    """Reject the sixth job in a rolling minute.

    The caller must hold the owner's row lock until the new job is persisted,
    so concurrent requests cannot both consume the same remaining allowance.
    Completed and failed jobs also consume allowance until their window expires.
    """
    now = now if now is not None else timezone.now()
    recent = list(
        SearchJob.objects.filter(owner_id=user_id, created_at__gt=now - JOB_RATE_WINDOW)
        .order_by("created_at")
        .values_list("created_at", flat=True)[:JOB_RATE_LIMIT]
    )
    if len(recent) < JOB_RATE_LIMIT:
        return
    retry_after = max(1, math.ceil((recent[0] + JOB_RATE_WINDOW - now).total_seconds()))
    raise RateLimited(retry_after)
