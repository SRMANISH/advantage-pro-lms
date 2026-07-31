"""Recording and aggregating attendance.

Attendance is **login-based**: present-days = distinct days the student logged in;
expected-days = elapsed active days of the batch (start_date .. min(today, end_date)).
Engagement events (video/test/task/live) are still recorded for activity/history but
do not count toward the attendance metric.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import AbsenceFollowUp, AttendanceEvent, AttendanceSource, FollowUpStatus

# Django's ``date__week_day`` lookup: 1=Sunday, 2=Monday, …, 7=Saturday.
_WEEKDAYS = (2, 3, 4, 5, 6)


def _count_weekends() -> bool:
    return bool(getattr(settings, "ATTENDANCE_COUNT_WEEKENDS", True))


def is_rest_day(day) -> bool:
    """True when this calendar day doesn't count toward attendance (a weekend while
    ``ATTENDANCE_COUNT_WEEKENDS`` is off). Used to suppress weekend absentee reminders
    and to flag the daily roster."""
    return not _count_weekends() and day.weekday() >= 5


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
    from batches.models import BatchState
    from enrollments.models import Enrollment

    today = timezone.localdate()
    created = 0
    # A finished student may still log in (to enter a Certificate ID), but that must not
    # add attendance to a completed batch. Non-completed batches still record normally;
    # any out-of-window rows are excluded on the read side (see login_present_days).
    batch_ids = (
        Enrollment.objects.filter(student=student)
        .exclude(batch__state=BatchState.COMPLETED)
        .values_list("batch_id", flat=True)
        .distinct()
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
    """Elapsed active days of the batch up to today (inclusive).

    With ``ATTENDANCE_COUNT_WEEKENDS = False`` Saturdays/Sundays are excluded (and the
    present-day counters exclude weekend logins to match), so the percentage stays a
    weekday-over-weekday ratio.
    """
    upto = upto or timezone.localdate()
    end = min(upto, batch.end_date)
    if end < batch.start_date:
        return 0
    if _count_weekends():
        return (end - batch.start_date).days + 1
    return _weekdays_between(batch.start_date, end)


def _weekdays_between(start, end) -> int:
    """Number of Monday–Friday days in [start, end] inclusive."""
    total = (end - start).days + 1
    full_weeks, remainder = divmod(total, 7)
    count = full_weeks * 5
    day = start + timedelta(days=full_weeks * 7)
    for _ in range(remainder):
        if day.weekday() < 5:
            count += 1
        day += timedelta(days=1)
    return count


def login_present_days(student, batch) -> int:
    """Distinct days the student logged in *within the batch's calendar window*.

    Bounded to ``start_date..end_date`` so the present-day count (numerator) can never
    exceed the expected-days window (denominator) — e.g. post-completion certificate
    logins don't push attendance past 100%.
    """
    qs = AttendanceEvent.objects.filter(
        student=student,
        batch=batch,
        source=AttendanceSource.LOGIN,
        date__gte=batch.start_date,
        date__lte=batch.end_date,
    )
    if not _count_weekends():
        # django-stubs mistypes week_day__in as dates; ints are the documented values.
        qs = qs.filter(date__week_day__in=_WEEKDAYS)  # type: ignore[misc]
    return qs.values("date").distinct().count()


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


def batch_attendance_summaries(batch, students=None) -> dict:
    """Login-attendance summary per student in a **single** grouped query.

    Returns ``{student_id: {"present", "total", "percent"}}``. This is the set-based
    counterpart to :func:`student_summary`, used by the performance board, the attendance
    report and the low-attendance escalation so none of them fan out to one query per
    student.
    """
    from django.db.models import Count

    from accounts.models import User

    if students is None:
        students = User.objects.filter(enrollments__batch=batch).distinct()
    ids = [s.id for s in students]
    total = expected_days(batch)
    # Bound to the batch window so present-days (numerator) can't exceed expected-days
    # (denominator) — mirrors login_present_days.
    present_qs = AttendanceEvent.objects.filter(
        batch=batch,
        source=AttendanceSource.LOGIN,
        student_id__in=ids,
        date__gte=batch.start_date,
        date__lte=batch.end_date,
    )
    if not _count_weekends():
        # django-stubs mistypes week_day__in as dates; ints are the documented values.
        present_qs = present_qs.filter(date__week_day__in=_WEEKDAYS)  # type: ignore[misc]
    present = dict(
        present_qs.values("student_id")
        .annotate(days=Count("date", distinct=True))
        .values_list("student_id", "days")
    )
    return {
        sid: {
            "present": present.get(sid, 0),
            "total": total,
            "percent": round(present.get(sid, 0) / total * 100) if total else 0,
        }
        for sid in ids
    }


def get_followup(student, batch) -> AbsenceFollowUp | None:
    return AbsenceFollowUp.objects.filter(student=student, batch=batch).first()


def set_followup(student, batch, status: str, *, owner=None, note: str = "") -> AbsenceFollowUp:
    """Upsert the Counselor/MIS follow-up record for a student's absences in a batch.

    Locked because this is read-modify-write on a row two people share: a Counselor and MIS
    can be working the same absentee list, and without the lock the later save silently
    discards the other's note or status change with nothing to show it happened.

    ``select_for_update`` is a silent no-op on SQLite (Django omits the clause rather than
    erroring), so this is only a real lock on PostgreSQL — which is what production runs.
    """
    with transaction.atomic():
        AbsenceFollowUp.objects.get_or_create(student=student, batch=batch)
        # Re-read inside the lock: get_or_create above may have returned a copy that another
        # writer has since changed.
        followup = AbsenceFollowUp.objects.select_for_update().get(student=student, batch=batch)
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

    Idempotent across concurrent runs: an ``AbsenceReminderLog`` row for (student, day) is
    claimed before the send, and a unique constraint means only one caller can claim it.
    Returns the number of reminders sent. Counselor and MIS follow up off the same login
    data.
    """
    from batches.models import Batch, BatchState
    from notifications.services import notify

    from .models import AbsenceReminderLog

    day = day or timezone.localdate()
    # With weekends excluded from attendance, a Saturday/Sunday "you didn't log in today"
    # message would go to the whole roster — suppress it.
    if is_rest_day(day):
        return 0
    sent = 0
    for batch in Batch.objects.filter(state=BatchState.ACTIVE):
        if day < batch.start_date or day > batch.end_date:
            continue
        for student in absentee_students(batch, day):
            # The insert *is* the claim. This replaced an in-memory set built from today's
            # Notification rows, which two overlapping runs could both read as empty before
            # either wrote. It still covers the in-process case it always did: a student
            # absent in two batches finds their own row on the second batch's pass.
            _, claimed = AbsenceReminderLog.objects.get_or_create(student=student, day=day)
            if not claimed:
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
