"""Remind students who missed login attendance today (cron/scheduler target)."""

from django.core.management.base import BaseCommand

from attendance.services import remind_absentees


class Command(BaseCommand):
    help = "Notify students who did not log in today (login-attendance absentees)."

    def handle(self, *args, **options):
        sent = remind_absentees()
        self.stdout.write(self.style.SUCCESS(f"Absence reminders: {sent} sent."))
