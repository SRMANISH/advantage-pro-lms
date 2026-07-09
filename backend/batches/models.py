"""Courses and batches — the unit everything in the LMS hangs off."""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Course(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Defined by Super Admin along with the course itself (procedure update).
    duration = models.CharField(max_length=60, blank=True)  # e.g. "3 months"
    fees = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

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


# Weekly-schedule day codes; ``date.weekday()`` (0=Mon) indexes into this.
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class Batch(TimeStampedModel):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="batches")
    start_date = models.DateField()
    end_date = models.DateField()
    # Weekly class schedule — mandatory at creation (serializer-enforced). ``class_days``
    # holds WEEKDAYS codes; the time window is used for the faculty-occupied conflict check.
    class_days = models.JSONField(default=list, blank=True)
    class_start_time = models.TimeField(null=True, blank=True)
    class_end_time = models.TimeField(null=True, blank=True)
    state = models.CharField(max_length=12, choices=BatchState.choices, default=BatchState.DRAFT)
    # ``primary_faculty`` leads the batch; ``faculty`` (M2M) is the *full* assigned set
    # (primary always included), so every existing faculty-scoped query keeps working.
    # Soft/support faculty = the M2M minus the primary.
    primary_faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="primary_batches",
    )
    faculty = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="batches", blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["course"]),
        ]

    def __str__(self) -> str:
        return self.code
