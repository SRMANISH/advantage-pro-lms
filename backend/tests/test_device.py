"""Device policy: first-login bind, new-device block + approval, course-end closure."""

import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import DeviceChangeRequest, User, UserStatus
from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment
from liveclasses.models import LiveClass

LOGIN = "/api/v1/auth/login/"
REQUESTS = "/api/v1/auth/devices/requests/"


def active_class(batch):
    """A live class in session right now for the batch."""
    return LiveClass.objects.create(
        batch=batch,
        title="Live Now",
        scheduled_at=timezone.now(),
        meeting_link="https://meet.example.com/now",
    )


def decide(staff, req_id, decision="approve", reason=""):
    c = APIClient()
    c.force_authenticate(user=staff)
    return c.post(
        f"{REQUESTS}{req_id}/decide/", {"decision": decision, "reason": reason}, format="json"
    )


def mis_user():
    return User.objects.create_user(
        username="mis", password="x", role=Role.MIS, status=UserStatus.ACTIVE
    )


def make_student(username="stu", password="x"):
    return User.objects.create_user(
        username=username, password=password, role=Role.STUDENT, status=UserStatus.ACTIVE
    )


def login(username, device_id, password="x"):
    return APIClient().post(
        LOGIN,
        {"username": username, "password": password, "role": Role.STUDENT, "device_id": device_id},
        format="json",
    )


@pytest.fixture
def world(db):
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="B1",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
        state=BatchState.ACTIVE,
    )
    fac = User.objects.create_user(
        username="fac", password="x", role=Role.FACULTY, status=UserStatus.ACTIVE
    )
    batch.faculty.add(fac)
    student = make_student()
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "fac": fac, "student": student}


@pytest.mark.django_db
def test_first_login_binds_device(world):
    assert login("stu", "device-A").status_code == 200
    # Same device works again.
    assert login("stu", "device-A").status_code == 200


@pytest.mark.django_db
def test_new_device_is_blocked_and_raises_request(world):
    assert login("stu", "device-A").status_code == 200
    resp = login("stu", "device-B")
    assert resp.status_code == 403
    assert "new device" in resp.json()["detail"].lower()
    assert DeviceChangeRequest.objects.filter(user=world["student"], status="pending").exists()


@pytest.mark.django_db
def test_faculty_approves_during_live_class(world):
    login("stu", "device-A")
    active_class(world["batch"])  # a class is in session
    login("stu", "device-B")  # raised during class -> routed to faculty
    req = DeviceChangeRequest.objects.get(user=world["student"], status="pending")
    assert req.during_class is True

    decided = decide(world["fac"], req.id, reason="Verified in class")
    assert decided.status_code == 200
    req.refresh_from_db()
    assert req.approver_role == Role.FACULTY
    assert login("stu", "device-B").status_code == 200


@pytest.mark.django_db
def test_faculty_cannot_approve_outside_class(world):
    login("stu", "device-A")
    login("stu", "device-B")  # no class in session
    req = DeviceChangeRequest.objects.get(user=world["student"], status="pending")
    assert decide(world["fac"], req.id).status_code == 403


@pytest.mark.django_db
def test_mis_approves_outside_class(world):
    login("stu", "device-A")
    login("stu", "device-B")  # no class in session -> routed to MIS
    req = DeviceChangeRequest.objects.get(user=world["student"], status="pending")
    assert req.during_class is False

    assert decide(mis_user(), req.id).status_code == 200
    assert login("stu", "device-B").status_code == 200


@pytest.mark.django_db
def test_mis_cannot_approve_during_class(world):
    login("stu", "device-A")
    active_class(world["batch"])
    login("stu", "device-B")
    req = DeviceChangeRequest.objects.get(user=world["student"], status="pending")
    assert decide(mis_user(), req.id).status_code == 403


@pytest.mark.django_db
def test_faculty_only_sees_their_students_requests(world):
    login("stu", "device-A")
    login("stu", "device-B")
    fac_client = APIClient()
    fac_client.force_authenticate(user=world["fac"])
    resp = fac_client.get(REQUESTS)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    other_fac = User.objects.create_user(
        username="fac2", password="x", role=Role.FACULTY, status=UserStatus.ACTIVE
    )
    other_client = APIClient()
    other_client.force_authenticate(user=other_fac)
    assert other_client.get(REQUESTS).json() == []


@pytest.mark.django_db
def test_course_end_blocks_device_change_but_not_bound_device(world):
    assert login("stu", "device-A").status_code == 200  # bind
    world["batch"].state = BatchState.COMPLETED
    world["batch"].save()
    # Bound device still works (to enter the Certificate ID).
    assert login("stu", "device-A").status_code == 200
    # But a device change is closed after course end.
    resp = login("stu", "device-B")
    assert resp.status_code == 403
    assert "ended" in resp.json()["detail"].lower()
