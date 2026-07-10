"""Direct-to-management feedback (req 20).

A student sends a private message (subject + body) to management. Only Super Admin can
read it; it's delivered to Super Admin's WhatsApp along with the student's course/batch
details. Batch/course/registration are snapshotted so the record stands alone even if the
enrolment later changes.
"""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Feedback(TimeStampedModel):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_sent"
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    # Context snapshot at submission time.
    registration_number = models.CharField(max_length=50, blank=True)
    batch_code = models.CharField(max_length=40, blank=True)
    course_name = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"feedback<{self.student_id}: {self.subject}>"
