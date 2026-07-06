"""Send due live-class reminders (run from cron every few minutes)."""

from django.core.management.base import BaseCommand

from core.cron import LockHeld, cron_lock
from liveclasses.services import send_due_live_reminders


class Command(BaseCommand):
    help = "Send 1h/15m live-class reminders that have come due."

    def handle(self, *args, **options):
        try:
            # Short timeout: this runs every few minutes, so a stuck lock must clear fast.
            with cron_lock("send_due_reminders", timeout=120):
                count = send_due_live_reminders()
        except LockHeld as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
            return
        self.stdout.write(self.style.SUCCESS(f"Sent {count} live-class reminder(s)."))
