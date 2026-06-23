"""Send certificate-pending reminders (scheduler target in production)."""

from django.core.management.base import BaseCommand

from certification.services import run_certificate_reminders


class Command(BaseCommand):
    help = "Remind students in completed batches who have not entered a Certificate ID."

    def handle(self, *args, **options):
        count = run_certificate_reminders()
        self.stdout.write(self.style.SUCCESS(f"Sent {count} certificate reminder(s)."))
