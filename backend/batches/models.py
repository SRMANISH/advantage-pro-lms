"""Courses and batches — the unit everything in the LMS hangs off."""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Course(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class BatchState(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"


# Forward-only lifecycle: Draft -> Active -> Completed.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    BatchState.DRAFT: {BatchState.ACTIVE},
    BatchState.ACTIVE: {BatchState.COMPLETED},
    BatchState.COMPLETED: set(),
}


class Batch(TimeStampedModel):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="batches")
    start_date = models.DateField()
    end_date = models.DateField()
    state = models.CharField(max_length=12, choices=BatchState.choices, default=BatchState.DRAFT)
    faculty = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="batches", blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["course"]),
        ]

    def __str__(self) -> str:
        return self.code
