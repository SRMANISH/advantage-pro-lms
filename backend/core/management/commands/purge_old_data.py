"""Purge old activity data past the retention window (cron target).

Removes audit logs and read notifications older than the configured retention period.
Never touches academic or legal records. Use --dry-run to preview counts.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from core.retention import purge_old_data


class Command(BaseCommand):
    help = "Delete audit logs and read notifications past the retention window."

    def add_arguments(self, parser):
        parser.add_argument("--audit-days", type=int, default=settings.RETENTION_AUDIT_DAYS)
        parser.add_argument(
            "--notification-days", type=int, default=settings.RETENTION_NOTIFICATION_DAYS
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        result = purge_old_data(
            audit_days=options["audit_days"],
            notification_days=options["notification_days"],
            dry_run=options["dry_run"],
        )
        verb = "Would purge" if result["dry_run"] else "Purged"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {result['audit_logs']} audit log(s) and "
                f"{result['notifications']} read notification(s)."
            )
        )
