"""Live classes: scheduling, listing, check-in marks attendance."""

import datetime

import pytest
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
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "admin": admin, "student": student}


def schedule_payload(batch):
    return {
        "batch": str(batch.id),
        "title": "React Hooks",
        "scheduled_at": "2026-02-01T18:00:00Z",
        "platform": "Google Meet",
        "meeting_link": "https://meet.example.com/abc",
    }


@pytest.mark.django_db
def test_admin_schedules_and_students_notified(world):
    resp = client_for(world["admin"]).post(URL, schedule_payload(world["batch"]), format="json")
    assert resp.status_code == 201
    assert LiveClass.objects.filter(title="React Hooks").exists()
    assert world["student"].notifications.filter(kind="new_live_class").exists()


@pytest.mark.django_db
def test_student_cannot_schedule(world):
    resp = client_for(world["student"]).post(URL, schedule_payload(world["batch"]), format="json")
    assert resp.status_code == 403


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
