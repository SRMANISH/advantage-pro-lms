"""Feedback to management (req 20): student sends; only Super Admin reads + WhatsApp."""

import datetime

import pytest

from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment
from feedback.models import Feedback
from notifications.models import Notification

from .helpers import client_for, user


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
    # Super Admin sees it, in a paginated envelope.
    inbox = client_for(world["sa"]).get("/api/v1/feedback/inbox/")
    assert inbox.status_code == 200
    assert inbox.json()["count"] == 1 and len(inbox.json()["results"]) == 1

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


@pytest.mark.django_db
def test_feedback_is_rate_limited_per_student(world):
    """The scoped throttle (5/hour) stops a student spamming management's WhatsApp."""
    c = client_for(world["student"])
    body = {"subject": "s", "message": "m"}
    for _ in range(5):
        assert c.post("/api/v1/feedback/", body, format="json").status_code == 201
    assert c.post("/api/v1/feedback/", body, format="json").status_code == 429


@pytest.mark.django_db
def test_feedback_inbox_is_paginated(world):
    """The inbox grows with every submission and was serialised in full on every open."""
    Feedback.objects.bulk_create(
        [
            Feedback(student=world["student"], subject=f"s{i}", message="m")
            for i in range(30)  # > the 25 default page size
        ]
    )
    sa = client_for(world["sa"])

    first = sa.get("/api/v1/feedback/inbox/").json()
    assert first["count"] == 30
    assert len(first["results"]) == 25
    assert first["next"]

    second = sa.get("/api/v1/feedback/inbox/", {"page": 2}).json()
    assert len(second["results"]) == 5
    # No row is served twice or skipped across the boundary.
    assert not {r["id"] for r in first["results"]} & {r["id"] for r in second["results"]}
