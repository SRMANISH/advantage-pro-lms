"""Course certification — one Certificate ID per enrolment, entered by the student."""

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
