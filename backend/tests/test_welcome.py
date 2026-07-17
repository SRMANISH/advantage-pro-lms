"""Welcome flow (reqs 16/17): address + goodies popup and the admin register."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment
from notifications.models import Notification


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
        code="FS-1",
        name="B",
        course=course,
        state=BatchState.ACTIVE,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 1),
    )
    student = user("S1", Role.STUDENT)
    enr = Enrollment.objects.create(student=student, batch=batch, registration_number="S1")
    return {"batch": batch, "student": student, "enr": enr, "admin": user("ad", Role.ADMIN)}


@pytest.mark.django_db
def test_pending_prompt_then_disappears_after_answer(world):
    c = client_for(world["student"])
    assert len(c.get("/api/v1/welcome/me/").json()) == 1

    resp = c.post(
        "/api/v1/welcome/submit/",
        {"enrollment": str(world["enr"].id), "address_on_file": True, "goodies_received": True},
        format="json",
    )
    assert resp.status_code == 200
    # Answered -> no longer pending.
    assert c.get("/api/v1/welcome/me/").json() == []
    world["enr"].refresh_from_db()
    assert world["enr"].welcome_answered and world["enr"].address_confirmed


@pytest.mark.django_db
def test_both_no_captures_address_and_alerts_admins(world):
    c = client_for(world["student"])
    resp = c.post(
        "/api/v1/welcome/submit/",
        {
            "enrollment": str(world["enr"].id),
            "address_on_file": False,
            "goodies_received": False,
            "address": "12 Main St, Chennai 600001",
        },
        format="json",
    )
    assert resp.status_code == 200
    world["enr"].refresh_from_db()
    assert world["enr"].address == "12 Main St, Chennai 600001"
    assert not world["enr"].goodies_received
    # Admin was notified with the address for goodies dispatch.
    assert Notification.objects.filter(recipient=world["admin"], kind="address_collected").exists()


@pytest.mark.django_db
def test_admin_register_and_mark_goodies_sent(world):
    admin = client_for(world["admin"])
    rows = admin.get("/api/v1/welcome/register/").json()["results"]
    row = next(r for r in rows if r["enrollment"] == str(world["enr"].id))
    assert row["goodies_sent"] is False

    sent = admin.post(
        "/api/v1/welcome/goodies/",
        {"enrollment": str(world["enr"].id), "sent": True},
        format="json",
    )
    assert sent.status_code == 200
    world["enr"].refresh_from_db()
    assert world["enr"].goodies_sent is True


@pytest.mark.django_db
def test_students_cannot_see_the_register(world):
    assert client_for(world["student"]).get("/api/v1/welcome/register/").status_code == 403
