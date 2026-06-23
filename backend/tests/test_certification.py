"""Certification: enter Certificate ID, status, and recurring reminders."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, BatchState, Course
from certification.models import Certificate
from certification.services import run_certificate_reminders
from core.roles import Role
from enrollments.models import Enrollment

ME = "/api/v1/certification/me/"
SUBMIT = "/api/v1/certification/submit/"


def user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def make_batch(state):
    course = Course.objects.create(code=f"C{state}", name="Course")
    return Batch.objects.create(
        code=f"B-{state}",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
        state=state,
    )


@pytest.mark.django_db
def test_completed_course_shows_pending_then_certified():
    batch = make_batch(BatchState.COMPLETED)
    student = user("stu", Role.STUDENT)
    enrollment = Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    sc = client_for(student)

    rows = sc.get(ME).json()
    assert len(rows) == 1
    assert rows[0]["certified"] is False

    resp = sc.post(
        SUBMIT, {"enrollment": str(enrollment.id), "certificate_id": "CERT-123"}, format="json"
    )
    assert resp.status_code == 200
    assert Certificate.objects.get(enrollment=enrollment).certificate_id == "CERT-123"
    assert sc.get(ME).json()[0]["certified"] is True


@pytest.mark.django_db
def test_reminders_target_uncertified_and_stop_after_entry():
    batch = make_batch(BatchState.COMPLETED)
    student = user("stu", Role.STUDENT)
    enrollment = Enrollment.objects.create(student=student, batch=batch, registration_number="stu")

    assert run_certificate_reminders() == 1
    assert student.notifications.filter(kind="certificate_pending").exists()

    Certificate.objects.create(enrollment=enrollment, certificate_id="CERT-9")
    assert run_certificate_reminders() == 0  # stops once entered


@pytest.mark.django_db
def test_cannot_certify_active_course():
    batch = make_batch(BatchState.ACTIVE)
    student = user("stu", Role.STUDENT)
    enrollment = Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    resp = client_for(student).post(
        SUBMIT, {"enrollment": str(enrollment.id), "certificate_id": "X"}, format="json"
    )
    assert resp.status_code == 404
