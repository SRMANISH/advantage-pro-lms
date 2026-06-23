"""Certificate reminders — recurring until the student enters their Certificate ID."""

from __future__ import annotations


def run_certificate_reminders() -> int:
    """Remind every student in a completed batch who has not yet certified."""
    from batches.models import BatchState
    from enrollments.models import Enrollment
    from notifications.services import notify

    pending = Enrollment.objects.filter(
        batch__state=BatchState.COMPLETED, certificate__isnull=True
    ).select_related("student", "batch")
    count = 0
    for enrollment in pending:
        notify(
            enrollment.student,
            "certificate_pending",
            f"Enter your Certificate ID for {enrollment.batch.code} to finish certifying.",
            link="/student/certificate",
            subject="Certificate pending",
            channels=("in_app", "email"),
        )
        count += 1
    return count
