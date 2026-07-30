"""Attendance auto-capture from tests/tasks/videos and aggregation."""

import datetime

import pytest
from django.db import IntegrityError, transaction

from assessments.models import Choice, Question, Task, Test
from attendance.models import AbsenceFollowUp, AbsenceReminderLog, AttendanceEvent
from attendance.services import (
    expected_days,
    record_login_attendance,
    remind_absentees,
    student_summary,
)
from batches.models import Batch, BatchState, Course
from content.models import Video
from core.roles import Role
from enrollments.models import Enrollment
from .helpers import client_for, user

ME_URL = "/api/v1/attendance/me/"
BATCH_URL = "/api/v1/attendance/"


@pytest.fixture
def world(db):
    course = Course.objects.create(code="FS", name="Full Stack")
    # Window spans "today" so a login recorded now falls inside the batch's calendar
    # (login-attendance only counts days within start_date..end_date).
    today = datetime.date.today()
    batch = Batch.objects.create(
        code="B1",
        name="B",
        course=course,
        start_date=today - datetime.timedelta(days=30),
        end_date=today + datetime.timedelta(days=30),
    )
    fac = user("fac", Role.FACULTY)
    batch.faculty.add(fac)
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "fac": fac, "student": student}


@pytest.mark.django_db
def test_test_submit_marks_present(world):
    test = Test.objects.create(batch=world["batch"], title="T")
    q = Question.objects.create(test=test, text="q")
    c = Choice.objects.create(question=q, text="a", is_correct=True)
    resp = client_for(world["student"]).post(
        f"/api/v1/tests/{test.id}/submit/",
        {"answers": [{"question": str(q.id), "choice": str(c.id)}]},
        format="json",
    )
    assert resp.status_code == 201
    assert AttendanceEvent.objects.filter(
        student=world["student"], source="test", reference_id=str(test.id)
    ).exists()


@pytest.mark.django_db
def test_task_submit_marks_present(world):
    task = Task.objects.create(batch=world["batch"], title="Essay")
    resp = client_for(world["student"]).post(
        f"/api/v1/tasks/{task.id}/submit/", {"text": "done"}, format="json"
    )
    assert resp.status_code == 201
    assert AttendanceEvent.objects.filter(
        student=world["student"], source="task", reference_id=str(task.id)
    ).exists()


@pytest.mark.django_db
def test_video_80_percent_marks_present(world):
    video = Video.objects.create(batch=world["batch"], title="V", storage_key="videos/x.mp4")
    resp = client_for(world["student"]).post(
        f"/api/v1/videos/{video.id}/progress/",
        {"percent": 90, "watched_seconds": 90, "last_position": 90},
        format="json",
    )
    assert resp.status_code == 200
    assert AttendanceEvent.objects.filter(source="video", reference_id=str(video.id)).exists()


@pytest.mark.django_db
def test_attendance_is_login_based(world):
    # Engagement (a task submission) no longer counts as attendance.
    task = Task.objects.create(batch=world["batch"], title="Essay")
    client_for(world["student"]).post(
        f"/api/v1/tasks/{task.id}/submit/", {"text": "done"}, format="json"
    )
    assert student_summary(world["student"], world["batch"])["present"] == 0

    # A login marks the student present for today.
    record_login_attendance(world["student"])
    summary = student_summary(world["student"], world["batch"])
    total = expected_days(world["batch"])
    assert summary["present"] == 1
    assert summary["total"] == total
    assert summary["percent"] == (round(1 / total * 100) if total else 0)

    # Same-day re-login is idempotent (one present-day).
    record_login_attendance(world["student"])
    assert student_summary(world["student"], world["batch"])["present"] == 1


@pytest.mark.django_db
def test_login_endpoint_records_login_attendance(world, client):
    resp = client.post(
        "/api/v1/auth/login/",
        {"username": "stu", "password": "x", "role": "student", "device_id": "dev-1"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert AttendanceEvent.objects.filter(
        student=world["student"], batch=world["batch"], source="login", device_id="dev-1"
    ).exists()


@pytest.mark.django_db
def test_absentee_roster_and_followup_by_counselor_and_mis(world):
    co = user("co", Role.COUNSELOR)
    mis = user("mis", Role.MIS)
    batch_id = world["batch"].id

    # Student has not logged in today -> shows as absentee to the Counselor.
    resp = client_for(co).get(f"/api/v1/attendance/daily/?batch={batch_id}")
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    assert any(r["registration_number"] == "stu" and r["logged_in"] is False for r in rows)

    # Counselor sets a follow-up status...
    set_url = "/api/v1/attendance/follow-up/status/"
    co_resp = client_for(co).post(
        set_url,
        {
            "batch": str(batch_id),
            "student_id": str(world["student"].id),
            "status": "contacted",
            "note": "Called the student.",
        },
        format="json",
    )
    assert co_resp.status_code == 200

    # ...and MIS can also update the same follow-up (both own absentee follow-up).
    mis_resp = client_for(mis).post(
        set_url,
        {"batch": str(batch_id), "student_id": str(world["student"].id), "status": "resolved"},
        format="json",
    )
    assert mis_resp.status_code == 200
    f = AbsenceFollowUp.objects.get(student=world["student"], batch=world["batch"])
    assert f.status == "resolved"


@pytest.mark.django_db
def test_remind_absentees_notifies_then_dedupes(db):
    today = datetime.date.today()
    course = Course.objects.create(code="FS2", name="FS2")
    batch = Batch.objects.create(
        code="BR",
        name="BR",
        course=course,
        start_date=today - datetime.timedelta(days=5),
        end_date=today + datetime.timedelta(days=30),
        state=BatchState.ACTIVE,
    )
    student = user("stuR", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stuR")

    assert remind_absentees() == 1
    assert student.notifications.filter(kind="absence_reminder").exists()
    # A second run on the same day does not re-send.
    assert remind_absentees() == 0


@pytest.mark.django_db
def test_weekend_absentee_reminders_respect_the_flag(db, settings):
    """R-10: with weekends excluded, a Saturday 'you didn't log in' blast is suppressed."""
    saturday = datetime.date(2026, 1, 3)
    assert saturday.weekday() == 5
    course = Course.objects.create(code="FSW", name="FSW")
    batch = Batch.objects.create(
        code="BW",
        name="BW",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 1),
        state=BatchState.ACTIVE,
    )
    student = user("stuW", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stuW")

    settings.ATTENDANCE_COUNT_WEEKENDS = False
    assert remind_absentees(day=saturday) == 0
    assert not student.notifications.filter(kind="absence_reminder").exists()

    settings.ATTENDANCE_COUNT_WEEKENDS = True
    assert remind_absentees(day=saturday) == 1


@pytest.mark.django_db
def test_my_attendance_endpoint(world):
    resp = client_for(world["student"]).get(ME_URL)
    assert resp.status_code == 200
    assert resp.json()[0]["batch"] == "B1"


@pytest.mark.django_db
def test_batch_roster_access(world):
    # Faculty of the batch can see the roster; a student cannot use this endpoint.
    fac_resp = client_for(world["fac"]).get(f"{BATCH_URL}?batch={world['batch'].id}")
    assert fac_resp.status_code == 200
    assert any(r["registration_number"] == "stu" for r in fac_resp.json())
    assert (
        client_for(world["student"]).get(f"{BATCH_URL}?batch={world['batch'].id}").status_code
        == 403
    )


# --------------------------- absence-reminder dedup ---------------------------
# The dedup used to be an in-memory set built from today's absence_reminder Notification
# rows. Two overlapping runs — a retried cron, a manual trigger racing the scheduled one —
# both read that set before either wrote, and both sent. The claim now lives in a row with
# a unique (student, day) constraint, so only one run can win.


def _reminder_world(code, username):
    today = datetime.date.today()
    course = Course.objects.create(code=code, name=code)
    batch = Batch.objects.create(
        code=code,
        name=code,
        course=course,
        start_date=today - datetime.timedelta(days=5),
        end_date=today + datetime.timedelta(days=30),
        state=BatchState.ACTIVE,
    )
    student = user(username, Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number=username)
    return student


@pytest.mark.django_db
def test_absence_reminder_dedup_survives_notification_history_being_gone():
    """The regression test for the actual change.

    Under the old implementation the dedup signal *was* the Notification row, so clearing
    notifications made a second run re-send. The durable claim must hold on its own.
    """
    student = _reminder_world("FSD", "stuD")

    assert remind_absentees() == 1
    assert AbsenceReminderLog.objects.filter(student=student).count() == 1

    student.notifications.filter(kind="absence_reminder").delete()

    assert remind_absentees() == 0
    assert not student.notifications.filter(kind="absence_reminder").exists()


@pytest.mark.django_db
def test_database_refuses_a_second_claim_for_the_same_student_and_day():
    """Proves the guarantee is enforced by the database rather than by the loop's own
    bookkeeping — otherwise genuinely concurrent runs would still both send."""
    student = _reminder_world("FSE", "stuE")
    today = datetime.date.today()
    AbsenceReminderLog.objects.create(student=student, day=today)

    with pytest.raises(IntegrityError), transaction.atomic():
        AbsenceReminderLog.objects.create(student=student, day=today)


@pytest.mark.django_db
def test_absence_reminder_claim_is_per_day_not_forever():
    """Yesterday's claim must not suppress today's reminder."""
    student = _reminder_world("FSF", "stuF")
    today = datetime.date.today()
    AbsenceReminderLog.objects.create(student=student, day=today - datetime.timedelta(days=1))

    assert remind_absentees() == 1
    assert AbsenceReminderLog.objects.filter(student=student, day=today).exists()
