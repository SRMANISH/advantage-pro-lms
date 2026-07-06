"""Send certificate-pending reminders (scheduler target in production)."""

from django.core.management.base import BaseCommand

from certification.services import run_certificate_reminders
from core.cron import LockHeld, cron_lock


class Command(BaseCommand):
    help = "Remind students in completed batches who have not entered a Certificate ID."

    def handle(self, *args, **options):
        try:
            with cron_lock("send_certificate_reminders"):
                count = run_certificate_reminders()
        except LockHeld as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
            return
        self.stdout.write(self.style.SUCCESS(f"Sent {count} certificate reminder(s)."))
