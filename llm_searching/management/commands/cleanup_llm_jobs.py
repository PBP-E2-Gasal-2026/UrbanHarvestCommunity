from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from llm_searching.jobs import TERMINAL
from llm_searching.models import SearchJob


class Command(BaseCommand):
    help = "Delete terminal LLM jobs finished more than 24 hours ago."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        count, _ = SearchJob.objects.filter(
            status__in=TERMINAL, finished_at__lt=cutoff
        ).delete()
        self.stdout.write(f"Deleted {count} expired search job records.")
