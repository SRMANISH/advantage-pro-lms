"""Procedure updates: forum responder rules, device routing to Tech Support,
ongoing-batch faculty guards, started-batch delete rules."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.device import handle_device_login
from accounts.models import DeviceBinding, DeviceChangeRequest, User, UserStatus
from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment
from forum.models import Thread


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
    fac = user("prof", Role.FACULTY)
    batch.faculty.add(fac)
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")
    return {"batch": batch, "fac": fac, "student": student}


# ---------- forum: MIS out; only Faculty + Tech Support respond ----------


@pytest.mark.django_db
def test_mis_has_no_forum_access(world):
    mis = user("mis", Role.MIS)
    assert client_for(mis).get("/api/v1/threads/").status_code == 403
    assert client_for(mis).get("/api/v1/forum/monitor/").status_code == 403


@pytest.mark.django_db
def test_students_cannot_reply_but_faculty_and_ts_can(world):
    thread = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Q", body="?"
    )
    url = f"/api/v1/threads/{thread.id}/reply/"

    blocked = client_for(world["student"]).post(url, {"body": "me too"}, format="json")
    assert blocked.status_code == 403

    assert client_for(world["fac"]).post(url, {"body": "answer"}, format="json").status_code == 200
    ts = user("ts", Role.TECH_SUPPORT)
    assert client_for(ts).post(url, {"body": "also this"}, format="json").status_code == 200


@pytest.mark.django_db
def test_thread_list_exposes_sla_waiting_fields(world):
    Thread.objects.create(batch=world["batch"], author=world["student"], title="Q", body="?")
    rows = client_for(world["fac"]).get("/api/v1/threads/").json()["results"]
    assert "hours_waiting" in rows[0] and "overdue" in rows[0]
    assert rows[0]["overdue"] is False  # fresh doubt is inside the window


# ---------- devices: notifications to Tech Support, never MIS ----------


@pytest.mark.django_db
def test_new_device_outside_class_notifies_tech_support_not_mis(world):
    ts = user("ts", Role.TECH_SUPPORT)
    mis = user("mis", Role.MIS)
    student = world["student"]
    DeviceBinding.objects.create(user=student, device_id="device-A")

    ok, _reason = handle_device_login(student, "device-B")
    assert ok is False
    assert ts.notifications.filter(kind="new_device").exists()
    assert not mis.notifications.filter(kind="new_device").exists()


@pytest.mark.django_db
def test_tech_support_can_approve_outside_class(world):
    ts = user("ts", Role.TECH_SUPPORT)
    student = world["student"]
    DeviceBinding.objects.create(user=student, device_id="device-A")
    handle_device_login(student, "device-B")
    req = DeviceChangeRequest.objects.get(user=student)

    resp = client_for(ts).post(
        f"/api/v1/auth/devices/requests/{req.id}/decide/", {"decision": "approve"}, format="json"
    )
    assert resp.status_code == 200
    assert DeviceBinding.objects.get(user=student).device_id == "device-B"


# ---------- faculty locked while on an ongoing batch ----------


@pytest.mark.django_db
def test_faculty_on_ongoing_batch_cannot_be_suspended_or_role_changed(world):
    sa = user("sa", Role.SUPER_ADMIN)
    fac = world["fac"]

    suspended = client_for(sa).post(
        f"/api/v1/auth/users/{fac.id}/status/", {"suspend": True}, format="json"
    )
    assert suspended.status_code == 400
    assert "ongoing batch" in suspended.json()["detail"]

    role_change = client_for(sa).post(
        f"/api/v1/auth/users/{fac.id}/role/", {"role": Role.MIS}, format="json"
    )
    assert role_change.status_code == 400

    # Complete the batch -> faculty is released and can now be suspended.
    world["batch"].state = BatchState.COMPLETED
    world["batch"].save(update_fields=["state"])
    assert (
        client_for(sa)
        .post(f"/api/v1/auth/users/{fac.id}/status/", {"suspend": True}, format="json")
        .status_code
        == 200
    )
