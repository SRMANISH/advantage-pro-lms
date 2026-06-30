"""Send due live-class reminders (run from cron every few minutes)."""

from django.core.management.base import BaseCommand

from liveclasses.services import send_due_live_reminders


class Command(BaseCommand):
    help = "Send 1h/15m live-class reminders that have come due."

    def handle(self, *args, **options):
        count = send_due_live_reminders()
        self.stdout.write(self.style.SUCCESS(f"Sent {count} live-class reminder(s)."))
