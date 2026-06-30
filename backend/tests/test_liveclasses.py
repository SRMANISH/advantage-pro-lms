"""Live classes: scheduling, listing, check-in marks attendance."""

import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from attendance.models import AttendanceEvent
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment
from liveclasses.models import CheckIn, LiveClass

URL = "/api/v1/liveclasses/"


def user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def world(db):
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="B1",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    admin = user("adm", Role.ADMIN)
    fac = user("fac", Role.FACULTY)
    batch.faculty.add(fac)
    other_fac = user("fac2", Role.FACULTY)
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {
        "batch": batch,
        "admin": admin,
        "fac": fac,
        "other_fac": other_fac,
        "student": student,
    }


def schedule_payload(batch):
    return {
        "batch": str(batch.id),
        "title": "React Hooks",
        "scheduled_at": "2026-02-01T18:00:00Z",
        "platform": "Google Meet",
        "meeting_link": "https://meet.example.com/abc",
    }


@pytest.mark.django_db
def test_faculty_schedules_own_batch_and_students_notified(world):
    resp = client_for(world["fac"]).post(URL, schedule_payload(world["batch"]), format="json")
    assert resp.status_code == 201
    assert LiveClass.objects.filter(title="React Hooks").exists()
    assert world["student"].notifications.filter(kind="new_live_class").exists()


@pytest.mark.django_db
def test_admin_cannot_schedule(world):
    # Live-class scheduling moved from Admin/MIS to Faculty under the updated procedure.
    resp = client_for(world["admin"]).post(URL, schedule_payload(world["batch"]), format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_faculty_cannot_schedule_other_batch(world):
    resp = client_for(world["other_fac"]).post(URL, schedule_payload(world["batch"]), format="json")
    # Not the faculty of this batch -> serializer rejects with 400.
    assert resp.status_code == 400


@pytest.mark.django_db
def test_student_cannot_schedule(world):
    resp = client_for(world["student"]).post(URL, schedule_payload(world["batch"]), format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_faculty_cancels_class_and_students_notified(world):
    live = LiveClass.objects.create(
        batch=world["batch"],
        title="To cancel",
        scheduled_at=timezone.now() + datetime.timedelta(days=2),
        meeting_link="https://meet.example.com/c",
    )
    resp = client_for(world["fac"]).post(
        f"{URL}{live.id}/cancel/", {"reason": "Faculty unwell"}, format="json"
    )
    assert resp.status_code == 200
    live.refresh_from_db()
    assert live.status == "cancelled"
    assert world["student"].notifications.filter(kind="live_class_cancelled").exists()


@pytest.mark.django_db
def test_student_cannot_cancel_class(world):
    live = LiveClass.objects.create(
        batch=world["batch"],
        title="X",
        scheduled_at=timezone.now() + datetime.timedelta(days=1),
        meeting_link="https://meet.example.com/x",
    )
    assert client_for(world["student"]).post(f"{URL}{live.id}/cancel/").status_code == 403


@pytest.mark.django_db
def test_cancelled_class_skipped_by_reminders(world):
    from liveclasses.services import send_due_live_reminders

    LiveClass.objects.create(
        batch=world["batch"],
        title="Cancelled soon",
        scheduled_at=timezone.now() + datetime.timedelta(minutes=30),
        meeting_link="https://meet.example.com/s",
        status="cancelled",
    )
    assert send_due_live_reminders() == 0


@pytest.mark.django_db
def test_check_in_marks_live_attendance(world):
    live = LiveClass.objects.create(
        batch=world["batch"],
        title="Class",
        scheduled_at=datetime.datetime(2026, 2, 1, 18, tzinfo=datetime.UTC),
        meeting_link="https://meet.example.com/x",
    )
    resp = client_for(world["student"]).post(f"{URL}{live.id}/check-in/")
    assert resp.status_code == 200
    assert resp.json()["meeting_link"] == "https://meet.example.com/x"
    assert CheckIn.objects.filter(live_class=live, student=world["student"]).exists()
    assert AttendanceEvent.objects.filter(
        student=world["student"], source="live", reference_id=str(live.id)
    ).exists()


@pytest.mark.django_db
def test_due_reminders_send_once_per_offset(world):
    from liveclasses.models import LiveReminder
    from liveclasses.services import send_due_live_reminders

    # Class 30 min away -> the 60-min reminder is due, the 15-min one is not.
    LiveClass.objects.create(
        batch=world["batch"],
        title="Soon",
        scheduled_at=timezone.now() + datetime.timedelta(minutes=30),
        meeting_link="https://meet.example.com/soon",
    )
    assert send_due_live_reminders() == 1
    assert world["student"].notifications.filter(kind="live_reminder").exists()
    assert LiveReminder.objects.count() == 1
    # Re-running does not re-send the same reminder.
    assert send_due_live_reminders() == 0


@pytest.mark.django_db
def test_student_sees_live_class_with_checked_in_flag(world):
    LiveClass.objects.create(
        batch=world["batch"],
        title="Class",
        scheduled_at=datetime.datetime(2026, 2, 1, 18, tzinfo=datetime.UTC),
        meeting_link="https://meet.example.com/x",
    )
    rows = client_for(world["student"]).get(URL).json()
    assert len(rows) == 1
    assert rows[0]["checked_in"] is False
