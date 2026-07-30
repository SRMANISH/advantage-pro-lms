"""Counselor workflow: review batches list + absence follow-up message."""

import datetime

import pytest

from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment
from notifications.models import Notification

from .helpers import client_for, user

BATCHES_URL = "/api/v1/attendance/batches/"
FOLLOWUP_URL = "/api/v1/attendance/follow-up/"


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
    counselor = user("co", Role.COUNSELOR)
    student = user("stu", Role.STUDENT, email="stu@example.com")
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "counselor": counselor, "student": student}


@pytest.mark.django_db
def test_counselor_can_list_review_batches(world):
    resp = client_for(world["counselor"]).get(BATCHES_URL)
    assert resp.status_code == 200
    assert any(b["code"] == "B1" for b in resp.json())


@pytest.mark.django_db
def test_counselor_sends_follow_up(world):
    resp = client_for(world["counselor"]).post(
        FOLLOWUP_URL, {"student_id": str(world["student"].id)}, format="json"
    )
    assert resp.status_code == 200
    assert Notification.objects.filter(recipient=world["student"], kind="absence_followup").exists()


@pytest.mark.django_db
def test_custom_follow_up_message(world):
    resp = client_for(world["counselor"]).post(
        FOLLOWUP_URL,
        {"student_id": str(world["student"].id), "message": "Please attend Monday's class."},
        format="json",
    )
    assert resp.status_code == 200
    note = Notification.objects.get(recipient=world["student"], kind="absence_followup")
    assert note.message == "Please attend Monday's class."


@pytest.mark.django_db
def test_student_cannot_send_follow_up(world):
    resp = client_for(world["student"]).post(
        FOLLOWUP_URL, {"student_id": str(world["student"].id)}, format="json"
    )
    assert resp.status_code == 403
