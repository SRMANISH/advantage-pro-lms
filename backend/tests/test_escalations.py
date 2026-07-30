"""Escalation rules: incomplete-test reminders and the 50%-attendance alert."""

import datetime

import pytest
from rest_framework.test import APIClient

from assessments.models import Choice, Question, Test
from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment
from escalations.models import Escalation
from escalations.services import run_escalations
from notifications.models import Notification

from .helpers import user

RUN_URL = "/api/v1/escalations/run/"


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
    fac = user("fac", Role.FACULTY)
    batch.faculty.add(fac)
    mis = user("mis", Role.MIS)
    counselor = user("co", Role.COUNSELOR)
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    test = Test.objects.create(batch=batch, title="Quiz")
    q = Question.objects.create(test=test, text="q")
    Choice.objects.create(question=q, text="a", is_correct=True)
    return {
        "batch": batch,
        "fac": fac,
        "mis": mis,
        "counselor": counselor,
        "student": student,
        "test": test,
    }


@pytest.mark.django_db
def test_incomplete_test_reminders(world):
    result = run_escalations()
    assert result["test_reminders"] == 1
    # Student reminded; faculty + MIS notified.
    assert Notification.objects.filter(recipient=world["student"], kind="test_incomplete").exists()
    assert Notification.objects.filter(
        recipient=world["fac"], kind="test_incomplete_staff"
    ).exists()
    assert Notification.objects.filter(
        recipient=world["mis"], kind="test_incomplete_staff"
    ).exists()


@pytest.mark.django_db
def test_escalations_are_not_duplicated(world):
    run_escalations()
    second = run_escalations()
    assert second["test_reminders"] == 0
    assert Escalation.objects.filter(kind="test_incomplete").count() == 1


@pytest.mark.django_db
def test_low_attendance_alert(world):
    # Student has an opportunity (the test) but did nothing -> 0% -> alert faculty/counselor/MIS.
    result = run_escalations()
    assert result["attendance_alerts"] == 1
    assert Notification.objects.filter(recipient=world["counselor"], kind="low_attendance").exists()
    assert Notification.objects.filter(recipient=world["fac"], kind="low_attendance").exists()


@pytest.mark.django_db
def test_run_endpoint_requires_staff(world):
    admin = user("adm", Role.ADMIN)
    staff = APIClient()
    staff.force_authenticate(user=admin)
    assert staff.post(RUN_URL).status_code == 200

    student_client = APIClient()
    student_client.force_authenticate(user=world["student"])
    assert student_client.post(RUN_URL).status_code == 403


# ---------- req 23: batch-wise escalation view ----------


@pytest.mark.django_db
def test_escalations_are_tagged_with_their_batch(world):
    run_escalations()
    esc = Escalation.objects.filter(kind="low_attendance").first()
    assert esc.batch_id == world["batch"].id


@pytest.mark.django_db
def test_escalation_list_filters_by_batch(world):
    run_escalations()
    client = APIClient()
    client.force_authenticate(user=world["mis"])
    assert client.get("/api/v1/escalations/").json()["count"] >= 1

    scoped = client.get(f"/api/v1/escalations/?batch={world['batch'].id}")
    assert scoped.status_code == 200 and scoped.json()["count"] >= 1

    other = Batch.objects.create(
        code="B2",
        name="B2",
        course=world["batch"].course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
        state=BatchState.ACTIVE,
    )
    assert client.get(f"/api/v1/escalations/?batch={other.id}").json()["results"] == []


@pytest.mark.django_db
def test_escalation_list_blocks_students(world):
    client = APIClient()
    client.force_authenticate(user=world["student"])
    assert client.get("/api/v1/escalations/").status_code == 403
