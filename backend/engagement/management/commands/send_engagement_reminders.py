"""Send LinkedIn-follow, Google-review and next-plan reminders (cron target)."""

from django.core.management.base import BaseCommand

from core.cron import LockHeld, cron_lock
from engagement.services import run_engagement_reminders


class Command(BaseCommand):
    help = "Send LinkedIn follow, Google review, and next-plan reminders."

    def handle(self, *args, **options):
        try:
            with cron_lock("send_engagement_reminders"):
                result = run_engagement_reminders()
        except LockHeld as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Engagement reminders: {result['linkedin']} LinkedIn, "
                f"{result['google_review']} Google review, {result['next_plan']} next-plan."
            )
        )
