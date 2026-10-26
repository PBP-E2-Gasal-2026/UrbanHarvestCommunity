import uuid
from django.conf import settings
from django.db import models

class SearchJob(models.Model):
    class State(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        SUCCEEDED = "succeeded"
        NEEDS_CLARIFICATION = "needs_clarification"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="llm_search_jobs")
    prompt = models.CharField(max_length=2000)
    status = models.CharField(max_length=24, choices=State.choices, default=State.PENDING)
    result = models.JSONField(default=dict)
    error_code = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    lease_token = models.UUIDField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    dispatch_after = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["status", "created_at"], name="llm_job_status_created"),
                   models.Index(fields=["owner", "status"], name="llm_job_owner_status")]
