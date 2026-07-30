"""Attendance.

Under the updated operating procedure attendance is **login-based**: a student is
present for a day if they log in that day (source ``LOGIN``). Engagement events
(video/test/task/live) are still recorded as *activity* signals but no longer count
toward the attendance metric. Absentee follow-up is owned by Counselor **and** MIS.
"""

from django.conf import settings
from django.db import models

from batches.models import Batch
from core.models import TimeStampedModel


class AttendanceSource(models.TextChoices):
    LOGIN = "login", "Login"
    LIVE = "live", "Live class"
    VIDEO = "video", "Video"
    TEST = "test", "Test"
    TASK = "task", "Task"


class AttendanceEvent(TimeStampedModel):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_events"
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="attendance_events")
    source = models.CharField(max_length=10, choices=AttendanceSource.choices)
    reference_id = models.CharField(max_length=64)
    date = models.DateField()
    device_id = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "source", "reference_id"], name="uniq_attendance_event"
            )
        ]
        indexes = [
            models.Index(fields=["student", "batch"]),
            models.Index(fields=["batch"]),
            models.Index(fields=["batch", "source", "date"]),
            # Serves login_present_days()'s per-student lookup at scale (batch,source,date
            # above already serves the grouped per-batch query in
            # batch_attendance_summaries()).
            models.Index(fields=["student", "batch", "source", "date"]),
        ]


class FollowUpStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONTACTED = "contacted", "Contacted"
    NOT_REACHABLE = "not_reachable", "Not reachable"
    RESOLVED = "resolved", "Resolved"
    ESCALATED = "escalated", "Escalated"


class AbsenceFollowUp(TimeStampedModel):
    """Counselor/MIS follow-up on a student's login absences for a batch."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="absence_followups"
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="absence_followups")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_followups",
    )
    status = models.CharField(
        max_length=16, choices=FollowUpStatus.choices, default=FollowUpStatus.PENDING
    )
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "batch"], name="uniq_absence_followup")
        ]
        indexes = [models.Index(fields=["batch", "status"])]


class AbsenceReminderLog(TimeStampedModel):
    """One row per (student, day), claimed *before* the reminder is sent.

    ``remind_absentees`` used to dedup by querying today's ``absence_reminder``
    Notification rows into a set and skipping anyone already in it. That is
    check-then-write: two overlapping runs — a retried cron, a manual trigger racing the
    scheduled one, two workers off the same queue — both read the set before either
    writes, and both send. Making the *insert* the claim moves the decision into the
    database, where exactly one writer can win.

    Deliberately at-most-once: the row is claimed first, so a send that fails afterwards
    is not retried. A duplicate "we missed you today" is worse than a missed one here.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="absence_reminder_logs"
    )
    day = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "day"], name="uniq_absence_reminder_per_day")
        ]
        indexes = [models.Index(fields=["day"])]

    def __str__(self) -> str:
        return f"absence_reminder<{self.student_id}@{self.day}>"
