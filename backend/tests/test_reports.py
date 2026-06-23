"""CSV exports: role scoping and content."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment

STUDENTS = "/api/v1/reports/students/"
ATTENDANCE = "/api/v1/reports/attendance/"
PERFORMANCE = "/api/v1/reports/performance/"


def user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE, full_name=username
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
    fac = user("fac", Role.FACULTY)
    batch.faculty.add(fac)
    counselor = user("co", Role.COUNSELOR)
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")
    return {"batch": batch, "fac": fac, "counselor": counselor, "student": student}


@pytest.mark.django_db
def test_students_csv_export(world):
    resp = client_for(user("adm", Role.ADMIN)).get(f"{STUDENTS}?batch={world['batch'].id}")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert b"S1" in resp.content


@pytest.mark.django_db
def test_faculty_exports_own_batch_only(world):
    assert client_for(world["fac"]).get(f"{STUDENTS}?batch={world['batch'].id}").status_code == 200
    other = Batch.objects.create(
        code="B2",
        name="B2",
        course=world["batch"].course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    assert client_for(world["fac"]).get(f"{STUDENTS}?batch={other.id}").status_code == 403


@pytest.mark.django_db
def test_counselor_limited_to_attendance_and_performance(world):
    co = client_for(world["counselor"])
    assert co.get(f"{ATTENDANCE}?batch={world['batch'].id}").status_code == 200
    assert co.get(f"{PERFORMANCE}?batch={world['batch'].id}").status_code == 200
    # Counselor export does NOT include the student roster.
    assert co.get(f"{STUDENTS}?batch={world['batch'].id}").status_code == 403


@pytest.mark.django_db
def test_student_cannot_export(world):
    assert (
        client_for(world["student"]).get(f"{ATTENDANCE}?batch={world['batch'].id}").status_code
        == 403
    )
