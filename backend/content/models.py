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
        constraints = [
            models.UniqueConstraint(fields=["video", "student"], name="uniq_video_student")
        ]
