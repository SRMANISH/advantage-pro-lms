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
def test_reminders_are_weekly_and_tracked():
    import datetime as _dt

    from django.utils import timezone

    from certification.models import CertificateFollowUp

    batch = make_batch(BatchState.COMPLETED)
    student = user("stu", Role.STUDENT)
    enrollment = Enrollment.objects.create(student=student, batch=batch, registration_number="stu")

    assert run_certificate_reminders() == 1
    fu = CertificateFollowUp.objects.get(enrollment=enrollment)
    assert fu.reminder_count == 1
    # A second run the same week does not re-send.
    assert run_certificate_reminders() == 0
    # Backdate the last reminder beyond a week -> it sends again.
    CertificateFollowUp.objects.filter(pk=fu.pk).update(
        last_reminder_at=timezone.now() - _dt.timedelta(days=8)
    )
    assert run_certificate_reminders() == 1
    fu.refresh_from_db()
    assert fu.reminder_count == 2


@pytest.mark.django_db
def test_mis_certificate_follow_up_dashboard_and_status():
    batch = make_batch(BatchState.COMPLETED)
    student = user("stu", Role.STUDENT)
    enrollment = Enrollment.objects.create(student=student, batch=batch, registration_number="REG1")
    mis = user("mis", Role.MIS)

    listing = client_for(mis).get("/api/v1/certification/follow-up/")
    assert listing.status_code == 200
    rows = listing.json()["results"]
    assert any(r["registration_number"] == "REG1" and r["certified"] is False for r in rows)

    set_resp = client_for(mis).post(
        "/api/v1/certification/follow-up/status/",
        {"enrollment": str(enrollment.id), "status": "contacted", "note": "Called"},
        format="json",
    )
    assert set_resp.status_code == 200
    from certification.models import CertificateFollowUp

    assert CertificateFollowUp.objects.get(enrollment=enrollment).status == "contacted"


@pytest.mark.django_db
def test_student_cannot_see_certificate_follow_up():
    student = user("stu", Role.STUDENT)
    assert client_for(student).get("/api/v1/certification/follow-up/").status_code == 403


@pytest.mark.django_db
def test_cannot_certify_active_course():
    batch = make_batch(BatchState.ACTIVE)
    student = user("stu", Role.STUDENT)
    enrollment = Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    resp = client_for(student).post(
        SUBMIT, {"enrollment": str(enrollment.id), "certificate_id": "X"}, format="json"
    )
    assert resp.status_code == 404
