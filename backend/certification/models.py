"""Course certification — one Certificate ID per enrolment, entered by the student.

MIS owns follow-up until each student enters their Certificate ID. ``CertificateFollowUp``
tracks reminder cadence and the MIS follow-up state per enrolment.
"""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from enrollments.models import Enrollment


class Certificate(TimeStampedModel):
    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.CASCADE, related_name="certificate"
    )
    certificate_id = models.CharField(max_length=100)
    certified_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.certificate_id


class CertFollowUpStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONTACTED = "contacted", "Contacted"
    RECEIVED = "received", "Received"
    ESCALATED = "escalated", "Escalated"


class CertificateFollowUp(TimeStampedModel):
    """MIS follow-up + reminder tracking for a completed-course enrolment."""

    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.CASCADE, related_name="cert_followup"
    )
    status = models.CharField(
        max_length=12, choices=CertFollowUpStatus.choices, default=CertFollowUpStatus.PENDING
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reminder_count = models.PositiveIntegerField(default=0)
    last_reminder_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["status"])]
