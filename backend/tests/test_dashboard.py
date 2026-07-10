"""Role-aware dashboard summaries."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment

URL = "/api/v1/dashboard/"


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
        name="Batch 1",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    fac = user("fac", Role.FACULTY)
    batch.faculty.add(fac)
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"course": course, "batch": batch, "fac": fac, "student": student}


@pytest.mark.django_db
def test_student_dashboard_shows_their_batch(world):
    resp = client_for(world["student"]).get(URL)
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == Role.STUDENT
    assert body["batches"][0]["code"] == "B1"
    assert "Full Stack" == body["batches"][0]["course"]


@pytest.mark.django_db
def test_faculty_dashboard_counts_students(world):
    resp = client_for(world["fac"]).get(URL)
    assert resp.status_code == 200
    body = resp.json()
    assert body["totals"]["batches"] == 1
    assert body["totals"]["students"] == 1


@pytest.mark.django_db
def test_admin_dashboard_totals(world):
    resp = client_for(user("adm", Role.ADMIN)).get(URL)
    assert resp.status_code == 200
    totals = resp.json()["totals"]
    assert totals["batches"] == 1
    assert totals["students"] == 1
    assert totals["courses"] == 1


@pytest.mark.django_db
def test_tech_support_dashboard_counts_pending_device_requests(world):
    """R-05: Tech Support owns outside-class device approvals, so the queue count must
    surface on their dashboard the way it does for MIS."""
    from accounts.models import DeviceChangeRequest

    DeviceChangeRequest.objects.create(user=world["student"], new_device_id="dev-new")

    resp = client_for(user("ts", Role.TECH_SUPPORT)).get(URL)
    assert resp.status_code == 200
    assert resp.json()["attention"]["device_requests"] == 1
