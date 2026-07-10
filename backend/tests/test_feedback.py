"""Feedback to management (req 20): student sends; only Super Admin reads + WhatsApp."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment
from feedback.models import Feedback
from notifications.models import Notification


def user(username, role, **extra):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE, **extra
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def world(db):
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="FS-1",
        name="B",
        course=course,
        state=BatchState.ACTIVE,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 1),
    )
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")
    sa = user("sa", Role.SUPER_ADMIN, phone="9876500000")
    return {"student": student, "sa": sa, "batch": batch}


@pytest.mark.django_db
def test_student_feedback_reaches_super_admin_with_context(world):
    resp = client_for(world["student"]).post(
        "/api/v1/feedback/",
        {"subject": "Faculty punctuality", "message": "Classes often start late."},
        format="json",
    )
    assert resp.status_code == 201

    fb = Feedback.objects.get(student=world["student"])
    assert fb.batch_code == "FS-1" and fb.course_name == "Full Stack"
    assert fb.registration_number == "S1"

    # Super Admin got an in-app notification (WhatsApp goes via the queued channel).
    note = Notification.objects.filter(recipient=world["sa"], kind="management_feedback").first()
    assert note is not None
    assert "Faculty punctuality" in note.message and "FS-1" in note.message


@pytest.mark.django_db
def test_only_super_admin_reads_the_inbox(world):
    client_for(world["student"]).post(
        "/api/v1/feedback/", {"subject": "s", "message": "m"}, format="json"
    )
    # Super Admin sees it.
    inbox = client_for(world["sa"]).get("/api/v1/feedback/inbox/")
    assert inbox.status_code == 200 and len(inbox.json()) == 1

    # No one else can — not even Admin/MIS.
    admin = user("ad", Role.ADMIN)
    assert client_for(admin).get("/api/v1/feedback/inbox/").status_code == 403
    assert client_for(world["student"]).get("/api/v1/feedback/inbox/").status_code == 403


@pytest.mark.django_db
def test_staff_cannot_submit_student_feedback(world):
    admin = user("ad", Role.ADMIN)
    resp = client_for(admin).post(
        "/api/v1/feedback/", {"subject": "s", "message": "m"}, format="json"
    )
    assert resp.status_code == 403
