"""Live-class reminders. A cron job calls send_due_live_reminders() every few minutes.

Each (class, offset) reminder is sent at most once. This needs no Celery/Redis — just
cron -> the ``send_due_reminders`` management command (or the scheduler adapter).
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from notifications.services import batch_student_users, notify_many

from .models import LiveClass, LiveReminder

REMINDER_OFFSETS = (60, 15)  # minutes before the class


def _class_duration_minutes() -> int:
    return getattr(settings, "LIVE_CLASS_DURATION_MINUTES", 120)


def active_live_class_for_batches(batch_ids):
    """The live class currently in session (scheduled_at .. +duration) for any batch."""
    now = timezone.now()
    window_start = now - timedelta(minutes=_class_duration_minutes())
    return (
        LiveClass.objects.filter(
            batch_id__in=list(batch_ids), scheduled_at__lte=now, scheduled_at__gte=window_start
        )
        .select_related("batch")
        .first()
    )


def active_live_class_for_student(student):
    """A live class in session now for any batch the student is enrolled in (or None)."""
    from enrollments.models import Enrollment

    batch_ids = Enrollment.objects.filter(student=student).values_list("batch_id", flat=True)
    return active_live_class_for_batches(batch_ids)


def is_live_class_active_for_faculty_student(faculty, student):
    """True if a class is in session now in a batch this faculty teaches and the
    student is enrolled in — the window in which Faculty may approve a device change."""
    from enrollments.models import Enrollment

    batch_ids = Enrollment.objects.filter(student=student, batch__faculty=faculty).values_list(
        "batch_id", flat=True
    )
    return active_live_class_for_batches(batch_ids) is not None


def notify_cancellation(live) -> None:
    """Tell students a class is cancelled. Immediate notice covers the '<1 day before'
    rule; cancelling earlier simply gives more lead time."""
    from .models import LiveClassStatus

    if live.status != LiveClassStatus.CANCELLED:
        return
    lead = live.scheduled_at - timezone.now()
    timing = "soon" if lead < timedelta(days=1) else "ahead of schedule"
    reason = f" Reason: {live.cancel_reason}." if live.cancel_reason else ""
    notify_many(
        batch_student_users(live.batch),
        "live_class_cancelled",
        f"'{live.title}' scheduled for {live.scheduled_at:%d %b %H:%M} has been cancelled "
        f"({timing}).{reason}",
        link="/student/live",
        subject="Live class cancelled",
        channels=("in_app", "email", "sms", "whatsapp"),
    )


def send_due_live_reminders() -> int:
    now = timezone.now()
    upcoming = (
        LiveClass.objects.filter(scheduled_at__gt=now, scheduled_at__lte=now + timedelta(hours=2))
        .exclude(status="cancelled")
        .select_related("batch")
    )
    count = 0
    for live in upcoming:
        students = None
        for offset in REMINDER_OFFSETS:
            remind_at = live.scheduled_at - timedelta(minutes=offset)
            already = LiveReminder.objects.filter(live_class=live, offset_min=offset).exists()
            if remind_at <= now and not already:
                LiveReminder.objects.create(live_class=live, offset_min=offset)
                if students is None:
                    students = batch_student_users(live.batch)
                notify_many(
                    students,
                    "live_reminder",
                    f"Reminder: '{live.title}' starts in about {offset} minutes.",
                    link="/student/live",
                    subject="Live class reminder",
                    channels=("in_app", "sms", "whatsapp"),
                )
                count += 1
    return count
