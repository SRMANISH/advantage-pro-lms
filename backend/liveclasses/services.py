"""Live-class reminders. A cron job calls send_due_live_reminders() every few minutes.

Each (class, offset) reminder is sent at most once. This needs no Celery/Redis — just
cron -> the ``send_due_reminders`` management command (or the scheduler adapter).
"""

from datetime import timedelta

from django.utils import timezone

from notifications.services import batch_student_users, notify_many

from .models import LiveClass, LiveReminder

REMINDER_OFFSETS = (60, 15)  # minutes before the class


def send_due_live_reminders() -> int:
    now = timezone.now()
    upcoming = LiveClass.objects.filter(
        scheduled_at__gt=now, scheduled_at__lte=now + timedelta(hours=2)
    ).select_related("batch")
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
