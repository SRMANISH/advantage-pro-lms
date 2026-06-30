"""Data retention: purge old *activity* data past the retention window.

Deliberately conservative — only audit logs and already-read notifications are purged.
Academic and legal records (enrolments, certificates, attendance, submissions, performance)
are never touched here.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def purge_old_data(
    audit_days: int | None = None,
    notification_days: int | None = None,
    dry_run: bool = False,
) -> dict:
    from audit.models import AuditLog
    from notifications.models import Notification

    audit_days = audit_days if audit_days is not None else settings.RETENTION_AUDIT_DAYS
    notification_days = (
        notification_days if notification_days is not None else settings.RETENTION_NOTIFICATION_DAYS
    )
    now = timezone.now()

    audit_qs = AuditLog.objects.filter(created_at__lt=now - timedelta(days=audit_days))
    # Only read notifications are removed; unread ones stay until the user sees them.
    notif_qs = Notification.objects.filter(
        read=True, created_at__lt=now - timedelta(days=notification_days)
    )

    counts = {"audit_logs": audit_qs.count(), "notifications": notif_qs.count()}
    if not dry_run:
        notif_qs.delete()
        audit_qs.delete()
    counts["dry_run"] = dry_run
    return counts
