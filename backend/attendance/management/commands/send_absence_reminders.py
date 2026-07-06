"""Remind students who missed login attendance today (cron/scheduler target)."""

from django.core.management.base import BaseCommand

from attendance.services import remind_absentees
from core.cron import LockHeld, cron_lock


class Command(BaseCommand):
    help = "Notify students who did not log in today (login-attendance absentees)."

    def handle(self, *args, **options):
        try:
            with cron_lock("send_absence_reminders"):
                sent = remind_absentees()
        except LockHeld as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
            return
        self.stdout.write(self.style.SUCCESS(f"Absence reminders: {sent} sent."))
