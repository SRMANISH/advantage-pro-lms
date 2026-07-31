"""Course certification — one Certificate ID per enrolment, entered by the student.

MIS owns follow-up until each student enters their Certificate ID. ``CertificateFollowUp``
tracks reminder cadence and the MIS follow-up state per enrolment.
"""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from enrollments.models import Enrollment


class Certificate(TimeStampedModel):
    # PROTECT, not CASCADE: a certificate is the institute's record that a student completed
    # the course, and it is the one row here that cannot be reconstructed from anything else.
    # BatchViewSet.perform_destroy already refuses to delete a batch that has certificates,
    # but that is an application check on one code path — a shell `Batch.objects.filter(...)
    # .delete()`, a data migration, or a future endpoint would cascade straight through
    # Enrollment and destroy them silently. The database refuses regardless of the caller.
    #
    # CertificateFollowUp below stays CASCADE deliberately: it is workflow state (who is
    # chasing whom), not a record of achievement, and loses nothing irreplaceable.
    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.PROTECT, related_name="certificate"
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
