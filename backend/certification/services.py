"""Certificate reminders — weekly, recurring until the student enters their Certificate ID.

MIS owns the follow-up. Reminders go out via email + WhatsApp (and in-app) at most once
a week per pending student, with the count and last-sent time tracked per enrolment.
"""

from __future__ import annotations

from datetime import timedelta


def run_certificate_reminders() -> int:
    """Remind students in completed batches who have not certified, at most weekly."""
    from django.utils import timezone

    from batches.models import BatchState
    from enrollments.models import Enrollment
    from notifications.services import notify

    from .models import CertificateFollowUp

    now = timezone.now()
    week_ago = now - timedelta(days=7)
    pending = Enrollment.objects.filter(
        batch__state=BatchState.COMPLETED, certificate__isnull=True
    ).select_related("student", "batch")

    count = 0
    for enrollment in pending:
        followup, _ = CertificateFollowUp.objects.get_or_create(enrollment=enrollment)
        if followup.last_reminder_at and followup.last_reminder_at > week_ago:
            continue  # already reminded this week
        notify(
            enrollment.student,
            "certificate_pending",
            f"Enter your Certificate ID for {enrollment.batch.code} to finish certifying.",
            link="/student/certificate",
            subject="Certificate pending",
            channels=("in_app", "email", "whatsapp"),
        )
        followup.reminder_count += 1
        followup.last_reminder_at = now
        followup.save(update_fields=["reminder_count", "last_reminder_at", "updated_at"])
        count += 1
    return count
