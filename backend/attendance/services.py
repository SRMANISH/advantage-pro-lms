"""Recording and aggregating attendance.

Attendance is **login-based**: present-days = distinct days the student logged in;
expected-days = elapsed active days of the batch (start_date .. min(today, end_date)).
Engagement events (video/test/task/live) are still recorded for activity/history but
do not count toward the attendance metric.
"""

from __future__ import annotations

from django.utils import timezone

from .models import AbsenceFollowUp, AttendanceEvent, AttendanceSource, FollowUpStatus


def record_attendance(student, batch, source: str, reference_id) -> None:
    """Record an engagement (activity) event. Idempotent per student+source+item."""
    AttendanceEvent.objects.get_or_create(
        student=student,
        source=source,
        reference_id=str(reference_id),
        defaults={"batch": batch, "date": timezone.localdate()},
    )


def record_login_attendance(student, device_id: str = "") -> int:
    """Mark the student present (login attendance) for today in each enrolled batch.

    Idempotent per (student, batch, day) via the unique (student, source, reference_id)
    constraint where reference_id encodes the batch and date. Returns the number of new
    login-attendance rows created.
    """
    from enrollments.models import Enrollment

    today = timezone.localdate()
    created = 0
    batch_ids = (
        Enrollment.objects.filter(student=student).values_list("batch_id", flat=True).distinct()
    )
    for batch_id in batch_ids:
        _, was_created = AttendanceEvent.objects.get_or_create(
            student=student,
            source=AttendanceSource.LOGIN,
            reference_id=f"{batch_id}:{today.isoformat()}",
            defaults={"batch_id": batch_id, "date": today, "device_id": device_id or ""},
        )
        created += int(was_created)
    return created


def expected_days(batch, upto=None) -> int:
    """Elapsed active days of the batch up to today (inclusive)."""
    upto = upto or timezone.localdate()
    end = min(upto, batch.end_date)
    if end < batch.start_date:
        return 0
    return (end - batch.start_date).days + 1


def login_present_days(student, batch) -> int:
    """Distinct days the student logged in while in this batch."""
    return (
        AttendanceEvent.objects.filter(student=student, batch=batch, source=AttendanceSource.LOGIN)
        .values("date")
        .distinct()
        .count()
    )


def logged_in_on(student, batch, day) -> bool:
    return AttendanceEvent.objects.filter(
        student=student, batch=batch, source=AttendanceSource.LOGIN, date=day
    ).exists()


def student_summary(student, batch) -> dict:
    present = login_present_days(student, batch)
    total = expected_days(batch)
    return {
        "present": present,
        "total": total,
        "percent": round(present / total * 100) if total else 0,
    }


def get_followup(student, batch) -> AbsenceFollowUp | None:
    return AbsenceFollowUp.objects.filter(student=student, batch=batch).first()


def set_followup(student, batch, status: str, *, owner=None, note: str = "") -> AbsenceFollowUp:
    """Upsert the Counselor/MIS follow-up record for a student's absences in a batch."""
    followup, _ = AbsenceFollowUp.objects.get_or_create(student=student, batch=batch)
    followup.status = status
    if owner is not None:
        followup.owner = owner
    if note:
        followup.note = note
    followup.save()
    return followup


def absentee_students(batch, day=None):
    """Enrolled students with no login on ``day`` (default today)."""
    from accounts.models import User

    day = day or timezone.localdate()
    present_ids = AttendanceEvent.objects.filter(
        batch=batch, source=AttendanceSource.LOGIN, date=day
    ).values_list("student_id", flat=True)
    return User.objects.filter(enrollments__batch=batch).exclude(id__in=present_ids).distinct()


def remind_absentees(day=None) -> int:
    """Notify students who missed login today across active, in-window batches.

    Idempotent: at most one ``absence_reminder`` per student per day. Returns the
    number of reminders sent. Counselor and MIS follow up off the same login data.
    """
    from batches.models import Batch, BatchState
    from notifications.services import notify

    day = day or timezone.localdate()
    sent = 0
    for batch in Batch.objects.filter(state=BatchState.ACTIVE):
        if day < batch.start_date or day > batch.end_date:
            continue
        for student in absentee_students(batch, day):
            if student.notifications.filter(kind="absence_reminder", created_at__date=day).exists():
                continue
            notify(
                student,
                "absence_reminder",
                f"We didn't see you log in today for {batch.code}. Please log in to keep "
                "your attendance up to date. — Advantage Pro",
                subject="We missed you today",
                channels=("in_app", "email", "sms"),
            )
            sent += 1
    return sent


def daily_roster(batch, day=None) -> list[dict]:
    """Per-student login status for a day, with any follow-up state. Drives the
    'logged in / did not log in' and absentee dashboards for Counselor and MIS."""
    from accounts.models import User

    day = day or timezone.localdate()
    students = User.objects.filter(enrollments__batch=batch).distinct()
    present_ids = set(
        AttendanceEvent.objects.filter(
            batch=batch, source=AttendanceSource.LOGIN, date=day
        ).values_list("student_id", flat=True)
    )
    followups = {f.student_id: f for f in AbsenceFollowUp.objects.filter(batch=batch)}
    rows = []
    for s in students:
        f = followups.get(s.id)
        rows.append(
            {
                "student": str(s.id),
                "student_name": s.full_name or s.username,
                "registration_number": s.username,
                "logged_in": s.id in present_ids,
                "follow_up_status": f.status if f else FollowUpStatus.PENDING,
                "follow_up_note": f.note if f else "",
            }
        )
    return rows
