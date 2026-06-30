"""Send LinkedIn-follow, Google-review and next-plan reminders (cron target)."""

from django.core.management.base import BaseCommand

from engagement.services import run_engagement_reminders


class Command(BaseCommand):
    help = "Send LinkedIn follow, Google review, and next-plan reminders."

    def handle(self, *args, **options):
        result = run_engagement_reminders()
        self.stdout.write(
            self.style.SUCCESS(
                f"Engagement reminders: {result['linkedin']} LinkedIn, "
                f"{result['google_review']} Google review, {result['next_plan']} next-plan."
            )
        )
