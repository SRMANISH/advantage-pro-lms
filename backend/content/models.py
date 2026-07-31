"""Class videos, study materials, and per-student video progress."""

from django.conf import settings
from django.db import models

from batches.models import Batch
from core.models import TimeStampedModel


class Video(TimeStampedModel):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="videos")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    storage_key = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, default="video/mp4")
    duration_seconds = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return self.title


class Material(TimeStampedModel):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=200)
    storage_key = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, default="application/octet-stream")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.title


class VideoProgress(TimeStampedModel):
    """≥80% watched counts as present (attendance is wired in a later module)."""

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="progresses")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_progress"
    )
    watched_seconds = models.PositiveIntegerField(default=0)
    last_position = models.PositiveIntegerField(default=0)
    percent = models.PositiveSmallIntegerField(default=0)
    completed = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "video progress"
        constraints = [
            models.UniqueConstraint(fields=["video", "student"], name="uniq_video_student")
        ]
        # Serves a student's completed-video count across batches (dashboards, exports)
        # without joining through Video for every row.
        indexes = [models.Index(fields=["student", "completed"])]


class VideoAccessRevocation(TimeStampedModel):
    """Blocks video/material streaming for students.

    * ``student`` set, ``batch`` null  -> individual revoke across all the student's batches (MIS).
    * ``student`` set, ``batch`` set    -> individual revoke for that student in that batch (MIS).
    * ``student`` null, ``batch`` set   -> course-end closure for the whole batch (Admin + MIS).
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="video_revocations",
    )
    batch = models.ForeignKey(
        Batch, null=True, blank=True, on_delete=models.CASCADE, related_name="video_revocations"
    )
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["batch"]),
        ]
