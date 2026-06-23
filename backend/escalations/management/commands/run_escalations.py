"""Run escalation checks (cron/scheduler target in production)."""

from django.core.management.base import BaseCommand

from escalations.services import run_escalations


class Command(BaseCommand):
    help = "Send incomplete-test reminders and 50%-attendance alerts."

    def handle(self, *args, **options):
        result = run_escalations()
        self.stdout.write(
            self.style.SUCCESS(
                f"Escalations: {result['test_reminders']} test reminder(s), "
                f"{result['attendance_alerts']} attendance alert(s)."
            )
        )
