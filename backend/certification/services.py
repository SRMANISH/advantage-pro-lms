"""Certificate reminders — weekly, recurring until the student enters their Certificate ID.

MIS owns the follow-up. Reminders go out via email + WhatsApp (and in-app) at most once
a week per pending student, with the count and last-sent time tracked per enrolment.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Q


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
        CertificateFollowUp.objects.get_or_create(enrollment=enrollment)
        # Claim the week before sending, with the window in the WHERE clause rather than in
        # Python. The old read-then-write let two overlapping runs — a retried cron, a manual
        # trigger racing the scheduled one — both see a stale last_reminder_at and both send,
        # so a student got the same "certificate pending" email and WhatsApp twice.
        #
        # A conditional UPDATE, not select_for_update: it is one statement the database
        # applies to one row or none, it holds no lock across the send, and it behaves the
        # same on SQLite as on PostgreSQL (row locking is silently dropped on SQLite), so the
        # test suite genuinely exercises this.
        claimed = (
            CertificateFollowUp.objects.filter(enrollment=enrollment)
            .filter(Q(last_reminder_at__isnull=True) | Q(last_reminder_at__lte=week_ago))
            .update(
                reminder_count=F("reminder_count") + 1,
                last_reminder_at=now,
                updated_at=now,
            )
        )
        if not claimed:
            continue  # already reminded this week, or another run got there first
        # After the claim: at-most-once. A send that fails is not retried, because a duplicate
        # chase-up is worse than a missed one — the next weekly run picks it up anyway.
        notify(
            enrollment.student,
            "certificate_pending",
            f"Enter your Certificate ID for {enrollment.batch.code} to finish certifying.",
            link="/student/certificate",
            subject="Certificate pending",
            channels=("in_app", "email", "whatsapp"),
        )
        count += 1
    return count
