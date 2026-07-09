"""Student enrolment — links a student account to one batch.

Per the plan there is NO record merging across courses: a person who enrols in a
different course gets a separate student account + registration number.
"""

from django.conf import settings
from django.db import models

from batches.models import Batch
from core.models import TimeStampedModel


class Enrollment(TimeStampedModel):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="enrollments")
    registration_number = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=255, blank=True)
    guardian = models.CharField(max_length=255, blank=True)
    employment_company = models.CharField(max_length=200, blank=True)
    # Welcome flow (reqs 16/17): a post-enrolment popup asks the student two questions —
    # is your address on file, and have you received your Advantage Pro goodies. Their
    # answers drive the Admin address/goodies register.
    welcome_answered = models.BooleanField(default=False)  # student responded to the popup
    address_confirmed = models.BooleanField(default=False)  # student confirmed/provided address
    goodies_received = models.BooleanField(default=False)  # student says they received goodies
    goodies_sent = models.BooleanField(default=False)  # admin marks goodies dispatched

    class Meta:
        ordering = ["registration_number"]
        constraints = [
            models.UniqueConstraint(fields=["student", "batch"], name="uniq_student_batch")
        ]

    def __str__(self) -> str:
        return f"{self.registration_number} -> {self.batch_id}"
