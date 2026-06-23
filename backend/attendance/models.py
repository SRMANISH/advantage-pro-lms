"""Auto-captured attendance: one event per engagement (video/test/task/live)."""

from django.conf import settings
from django.db import models

from batches.models import Batch
from core.models import TimeStampedModel


class AttendanceSource(models.TextChoices):
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "source", "reference_id"], name="uniq_attendance_event"
            )
        ]
        indexes = [models.Index(fields=["student", "batch"]), models.Index(fields=["batch"])]
