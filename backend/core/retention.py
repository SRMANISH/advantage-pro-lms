"""Data retention: purge old *activity* data past the retention window.

Deliberately conservative. What is purged is bookkeeping: audit logs, notifications the user
has already read (or will provably never read), and the absence-reminder dedup ledger.

What is NOT purged, and must not be added here without a deliberate policy decision:
``AttendanceEvent``, ``TestAttempt``, ``TaskSubmission``, ``Enrollment``, ``Certificate``.
Those are the academic record — the evidence behind an issued certificate and behind any
dispute about whether a student met the attendance or assessment bar. An institute can be
asked to produce them years later. Their growth is bounded by enrolment, not by traffic, so
there is no operational pressure to drop them either. ``Certificate.enrollment`` is PROTECT
for the same reason (see certification/models.py).
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def purge_old_data(
    audit_days: int | None = None,
    notification_days: int | None = None,
    unread_notification_days: int | None = None,
    absence_reminder_days: int | None = None,
    dry_run: bool = False,
) -> dict:
    from attendance.models import AbsenceReminderLog
    from audit.models import AuditLog
    from notifications.models import Notification

    audit_days = audit_days if audit_days is not None else settings.RETENTION_AUDIT_DAYS
    notification_days = (
        notification_days if notification_days is not None else settings.RETENTION_NOTIFICATION_DAYS
    )
    unread_notification_days = (
        unread_notification_days
        if unread_notification_days is not None
        else settings.RETENTION_UNREAD_NOTIFICATION_DAYS
    )
    absence_reminder_days = (
        absence_reminder_days
        if absence_reminder_days is not None
        else settings.RETENTION_ABSENCE_REMINDER_DAYS
    )
    now = timezone.now()

    audit_qs = AuditLog.objects.filter(created_at__lt=now - timedelta(days=audit_days))
    # Read notifications go on the short window.
    notif_qs = Notification.objects.filter(
        read=True, created_at__lt=now - timedelta(days=notification_days)
    )
    # Unread ones stay until the user sees them, bounded by a much longer backstop — past it,
    # an unread message is abandoned rather than pending, and the table would grow forever.
    unread_qs = Notification.objects.filter(
        read=False, created_at__lt=now - timedelta(days=unread_notification_days)
    )
    # The absence-reminder dedup ledger: once its day is past the window it can no longer
    # suppress a send, so the row has no remaining function.
    reminder_qs = AbsenceReminderLog.objects.filter(
        day__lt=(now - timedelta(days=absence_reminder_days)).date()
    )

    counts = {
        "audit_logs": audit_qs.count(),
        "notifications": notif_qs.count(),
        "unread_notifications": unread_qs.count(),
        "absence_reminder_logs": reminder_qs.count(),
    }
    if not dry_run:
        reminder_qs.delete()
        unread_qs.delete()
        notif_qs.delete()
        audit_qs.delete()
    counts["dry_run"] = dry_run
    return counts
