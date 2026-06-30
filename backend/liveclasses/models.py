"""Live classes: Admin schedules a meeting link; students join and check in."""

from django.conf import settings
from django.db import models

from batches.models import Batch
from core.models import TimeStampedModel


class LiveClass(TimeStampedModel):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="live_classes")
    title = models.CharField(max_length=200)
    scheduled_at = models.DateTimeField()
    platform = models.CharField(max_length=50, default="Google Meet")
    meeting_link = models.URLField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self) -> str:
        return self.title


class CheckIn(TimeStampedModel):
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE, related_name="checkins")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_checkins"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["live_class", "student"], name="uniq_live_checkin")
        ]


class LiveReminder(TimeStampedModel):
    """Records that an N-minutes-before reminder was sent (idempotent dedupe)."""

    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE, related_name="reminders")
    offset_min = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["live_class", "offset_min"], name="uniq_live_reminder")
        ]
