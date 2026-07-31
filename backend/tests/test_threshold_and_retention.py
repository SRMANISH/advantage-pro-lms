"""The 50%-attendance boundary, and what retention is allowed to delete.

The escalation rule compared a *rounded* percentage, so every case in [49.5%, 50%) was
silently skipped: round(49.5) is 50 in Python (halves go to even), and the guard was
`percent >= 50`. Those are exactly the students closest to the line — the ones the rule
exists to catch.
"""

import datetime

import pytest
from django.utils import timezone

from attendance.models import AbsenceReminderLog, AttendanceEvent, AttendanceSource
from audit.models import AuditLog
from batches.models import Batch, BatchState, Course
from core.retention import purge_old_data
from core.roles import Role
from enrollments.models import Enrollment
from escalations.models import Escalation
from escalations.services import run_escalations
from notifications.models import Notification

from .helpers import user


def _batch_with_window(code, days):
    """A batch whose elapsed window is exactly `days` days, weekends counted."""
    today = datetime.date.today()
    course = Course.objects.create(code=code, name=code)
    return Batch.objects.create(
        code=code,
        name=code,
        course=course,
        start_date=today - datetime.timedelta(days=days - 1),
        end_date=today + datetime.timedelta(days=30),
        state=BatchState.ACTIVE,
    )


def _present_for(student, batch, count):
    """Mark `count` distinct days present inside the batch window."""
    for i in range(count):
        day = batch.start_date + datetime.timedelta(days=i)
        AttendanceEvent.objects.create(
            student=student,
            batch=batch,
            source=AttendanceSource.LOGIN,
            reference_id=f"{batch.id}:{day.isoformat()}",
            date=day,
        )


@pytest.mark.django_db
def test_a_student_at_49_5_percent_is_escalated(settings):
    """The regression test, at the exact value the rounding hid: 99 of 200 days."""
    settings.ATTENDANCE_COUNT_WEEKENDS = True
    batch = _batch_with_window("ESC1", 200)
    student = user("esc_49", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="esc_49")
    _present_for(student, batch, 99)  # 49.5% -> round() gives 50, the old guard skipped it

    run_escalations()

    assert Escalation.objects.filter(student=student, kind="low_attendance").exists()


@pytest.mark.django_db
def test_a_student_at_exactly_50_percent_is_not_escalated(settings):
    """The other side of the boundary must stay closed — the rule is *below* 50%."""
    settings.ATTENDANCE_COUNT_WEEKENDS = True
    batch = _batch_with_window("ESC2", 200)
    student = user("esc_50", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="esc_50")
    _present_for(student, batch, 100)  # exactly 50%

    run_escalations()

    assert not Escalation.objects.filter(student=student, kind="low_attendance").exists()


@pytest.mark.django_db
def test_the_alert_reports_days_rather_than_the_rounded_percent(settings):
    """The message used the same rounded number, so it read "below 50% attendance … (50%)"."""
    settings.ATTENDANCE_COUNT_WEEKENDS = True
    batch = _batch_with_window("ESC3", 200)
    student = user("esc_msg", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="esc_msg")
    _present_for(student, batch, 99)
    staff = user("esc_mis", Role.MIS)

    run_escalations()

    note = Notification.objects.filter(recipient=staff, kind="low_attendance").first()
    assert note is not None
    assert "99/200 days" in note.message
    assert "(50%)" not in note.message  # the self-contradicting old wording


# --------------------------- retention ---------------------------


@pytest.mark.django_db
def test_purge_removes_the_bookkeeping_it_is_allowed_to():
    student = user("ret_stu", Role.STUDENT)
    old = timezone.now() - datetime.timedelta(days=800)

    audit = AuditLog.objects.create(action="x")
    AuditLog.objects.filter(pk=audit.pk).update(created_at=old)
    for read in (True, False):
        n = Notification.objects.create(recipient=student, kind="k", message="m", read=read)
        Notification.objects.filter(pk=n.pk).update(created_at=old)
    AbsenceReminderLog.objects.create(student=student, day=old.date())

    counts = purge_old_data()

    assert counts["audit_logs"] == 1
    assert counts["notifications"] == 1  # the read one
    assert counts["unread_notifications"] == 1  # the abandoned one
    assert counts["absence_reminder_logs"] == 1
    assert not Notification.objects.exists()
    assert not AbsenceReminderLog.objects.exists()


@pytest.mark.django_db
def test_a_recent_unread_notification_is_never_purged():
    """The long backstop must not swallow something the user has yet to read."""
    student = user("ret_stu2", Role.STUDENT)
    recent = timezone.now() - datetime.timedelta(days=200)  # past the *read* window only
    n = Notification.objects.create(recipient=student, kind="k", message="m", read=False)
    Notification.objects.filter(pk=n.pk).update(created_at=recent)

    purge_old_data()

    assert Notification.objects.filter(pk=n.pk).exists()


@pytest.mark.django_db
def test_purge_never_touches_the_academic_record():
    """The exclusion is the point of the module, so it is asserted rather than assumed."""
    batch = _batch_with_window("RET1", 30)
    student = user("ret_stu3", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="ret_stu3")
    _present_for(student, batch, 5)
    AttendanceEvent.objects.update(created_at=timezone.now() - datetime.timedelta(days=900))

    purge_old_data()

    assert AttendanceEvent.objects.count() == 5
    assert Enrollment.objects.count() == 1


@pytest.mark.django_db
def test_dry_run_reports_without_deleting():
    student = user("ret_stu4", Role.STUDENT)
    AbsenceReminderLog.objects.create(
        student=student, day=(timezone.now() - datetime.timedelta(days=800)).date()
    )
    counts = purge_old_data(dry_run=True)
    assert counts["absence_reminder_logs"] == 1 and counts["dry_run"] is True
    assert AbsenceReminderLog.objects.count() == 1
