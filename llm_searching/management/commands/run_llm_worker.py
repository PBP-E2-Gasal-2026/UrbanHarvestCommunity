import logging
import signal
import threading

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, close_old_connections

from llm_searching.worker import WorkerCoordinator

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run one LLM search coordinator (RabbitMQ pool or serial local fallback)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once", action="store_true", help="Run one coordinator tick and exit."
        )
        parser.add_argument("--poll-interval", type=float, default=1.0)

    def handle(self, *args, **options):
        if options["poll_interval"] < 0.05:
            raise CommandError("poll-interval must be at least 0.05 seconds")
        stopped = threading.Event()
        old_handlers = {}
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGTERM, signal.SIGINT):
                old_handlers[sig] = signal.signal(sig, lambda *_: stopped.set())
        coordinator = WorkerCoordinator()
        self.stdout.write("LLM search coordinator started.")
        try:
            while not stopped.is_set():
                try:
                    coordinator.tick()
                except DatabaseError:
                    logger.error("LLM worker database temporarily unavailable")
                    close_old_connections()
                if options["once"]:
                    break
                stopped.wait(options["poll_interval"])
        finally:
            coordinator.close()
            for sig, handler in old_handlers.items():
                signal.signal(sig, handler)
