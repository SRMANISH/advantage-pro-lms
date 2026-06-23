"""Device policy: first-login bind, new-device block + approval, course-end closure."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import DeviceChangeRequest, User, UserStatus
from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment

LOGIN = "/api/v1/auth/login/"
REQUESTS = "/api/v1/auth/devices/requests/"


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
def test_faculty_approves_then_new_device_works(world):
    login("stu", "device-A")
    login("stu", "device-B")  # creates pending request
    req = DeviceChangeRequest.objects.get(user=world["student"], status="pending")

    fac_client = APIClient()
    fac_client.force_authenticate(user=world["fac"])
    decided = fac_client.post(f"{REQUESTS}{req.id}/decide/", {"decision": "approve"}, format="json")
    assert decided.status_code == 200

    assert login("stu", "device-B").status_code == 200


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
