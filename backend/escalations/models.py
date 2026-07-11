"""Escalation ledger — ensures each alert is sent at most once."""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Escalation(TimeStampedModel):
    kind = models.CharField(max_length=30)  # test_incomplete | low_attendance
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="escalations"
    )
    # Which batch the alert belongs to, so MIS/Counselor can review escalations batch-wise.
    batch = models.ForeignKey(
        "batches.Batch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="escalations",
    )
    reference_id = models.CharField(max_length=64)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "student", "reference_id"], name="uniq_escalation"
            )
        ]
