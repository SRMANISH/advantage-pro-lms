"""Courses, batches, role-scoping, lifecycle, and faculty assignment."""

import datetime

import pytest

from accounts.models import User, UserStatus
from batches.models import Batch, BatchState, Course
from core.roles import Role
from .helpers import client_for

COURSES_URL = "/api/v1/courses/"
BATCHES_URL = "/api/v1/batches/"

# Class schedule is mandatory at batch creation (req 14).
SCHEDULE = {
    "class_days": ["mon", "wed", "fri"],
    "class_start_time": "18:00",
    "class_end_time": "20:00",
}


def make_user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


@pytest.fixture
def users(db):
    return {
        "super": make_user("sa", Role.SUPER_ADMIN),
        "admin": make_user("ad", Role.ADMIN),
        "mis": make_user("mis", Role.MIS),
        "faculty": make_user("fac", Role.FACULTY),
        "faculty2": make_user("fac2", Role.FACULTY),
        "student": make_user("stu", Role.STUDENT),
        "counselor": make_user("co", Role.COUNSELOR),
    }


@pytest.fixture
def course(db):
    return Course.objects.create(code="FS", name="Full Stack")


def make_batch(course, code="B1", **extra):
    return Batch.objects.create(
        code=code,
        name="Batch 1",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
        **extra,
    )


@pytest.mark.django_db
def test_only_super_admin_creates_courses(users, course):
    # Updated procedure: courses (incl. duration/fees) are defined by Super Admin alone.
    payload = {"code": "DS", "name": "Data Science", "duration": "3 months", "fees": "45000.00"}
    created = client_for(users["super"]).post(COURSES_URL, payload)
    assert created.status_code == 201
    body = created.json()
    assert body["duration"] == "3 months" and body["fees"] == "45000.00"
    assert (
        client_for(users["admin"]).post(COURSES_URL, {"code": "X", "name": "X"}).status_code == 403
    )
    assert (
        client_for(users["faculty"]).post(COURSES_URL, {"code": "Y", "name": "Y"}).status_code
        == 403
    )
    # Student is not even allowed onto the courses endpoint.
    assert client_for(users["student"]).get(COURSES_URL).status_code == 403


@pytest.mark.django_db
def test_admin_creates_batch(users, course):
    payload = {
        "code": "FS-2026A",
        "name": "FS Morning",
        "course": str(course.id),
        "start_date": "2026-01-01",
        "end_date": "2026-04-01",
        **SCHEDULE,
    }
    resp = client_for(users["admin"]).post(BATCHES_URL, payload, format="json")
    assert resp.status_code == 201
    assert resp.json()["state"] == BatchState.DRAFT
    assert resp.json()["class_days"] == ["mon", "wed", "fri"]


@pytest.mark.django_db
def test_batch_creation_requires_a_schedule(users, course):
    # No class_days/times -> rejected (req 14).
    payload = {
        "code": "NOSCHED",
        "name": "No schedule",
        "course": str(course.id),
        "start_date": "2026-01-01",
        "end_date": "2026-04-01",
    }
    assert client_for(users["admin"]).post(BATCHES_URL, payload, format="json").status_code == 400


@pytest.mark.django_db
def test_batch_end_before_start_is_rejected(users, course):
    payload = {
        "code": "BAD",
        "name": "Bad",
        "course": str(course.id),
        "start_date": "2026-04-01",
        "end_date": "2026-01-01",
        **SCHEDULE,
    }
    assert client_for(users["admin"]).post(BATCHES_URL, payload, format="json").status_code == 400


@pytest.mark.django_db
def test_faculty_sees_only_their_batches(users, course):
    mine = make_batch(course, code="MINE")
    mine.faculty.add(users["faculty"])
    make_batch(course, code="OTHER")

    resp = client_for(users["faculty"]).get(BATCHES_URL)
    assert resp.status_code == 200
    codes = (
        {b["code"] for b in resp.json()["results"]}
        if isinstance(resp.json(), dict)
        else {b["code"] for b in resp.json()}
    )
    assert codes == {"MINE"}


@pytest.mark.django_db
def test_mis_cannot_create_batch(users, course):
    payload = {
        "code": "MIS-1",
        "name": "MIS Batch",
        "course": str(course.id),
        "start_date": "2026-01-01",
        "end_date": "2026-04-01",
    }
    # Batch creation is Admin-only under the updated procedure.
    assert client_for(users["mis"]).post(BATCHES_URL, payload, format="json").status_code == 403


@pytest.mark.django_db
def test_draft_batch_deletable_by_admin_started_batch_only_by_super_admin(users, course):
    draft = make_batch(course)
    assert client_for(users["admin"]).delete(f"{BATCHES_URL}{draft.id}/").status_code == 204

    started = make_batch(course, code="STARTED", state=BatchState.ACTIVE)
    # Admin may not delete a batch that has started; Super Admin may.
    assert client_for(users["admin"]).delete(f"{BATCHES_URL}{started.id}/").status_code == 403
    assert client_for(users["super"]).delete(f"{BATCHES_URL}{started.id}/").status_code == 204


@pytest.mark.django_db
def test_cannot_delete_batch_with_certificates(users, course):
    from certification.models import Certificate
    from enrollments.models import Enrollment

    batch = make_batch(course, state=BatchState.COMPLETED)
    enr = Enrollment.objects.create(
        student=users["student"], batch=batch, registration_number="stu"
    )
    Certificate.objects.create(enrollment=enr, certificate_id="CERT-1")

    # Even Super Admin (the only role able to delete a started batch) is blocked by the
    # legal-records guard.
    resp = client_for(users["super"]).delete(f"{BATCHES_URL}{batch.id}/")
    assert resp.status_code == 409
    assert Batch.objects.filter(id=batch.id).exists()


@pytest.mark.django_db
def test_admin_assigns_faculty_and_faculty_cannot(users, course):
    own = make_batch(course, code="OWN")
    own.faculty.add(users["faculty"])

    url = f"{BATCHES_URL}{own.id}/assign-faculty/"
    # Admin assigns faculty.
    resp = client_for(users["admin"]).post(
        url, {"faculty_ids": [str(users["faculty2"].id)]}, format="json"
    )
    assert resp.status_code == 200
    assert users["faculty2"] in own.faculty.all()

    # Faculty may no longer assign faculty — not even on their own batch.
    resp2 = client_for(users["faculty"]).post(
        url, {"faculty_ids": [str(users["faculty2"].id)]}, format="json"
    )
    assert resp2.status_code == 403


@pytest.mark.django_db
def test_assign_rejects_non_faculty_user(users, course):
    batch = make_batch(course)
    resp = client_for(users["admin"]).post(
        f"{BATCHES_URL}{batch.id}/assign-faculty/",
        {"faculty_ids": [str(users["student"].id)]},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_lifecycle_transitions(users, course):
    batch = make_batch(course)
    admin = client_for(users["admin"])
    base = f"{BATCHES_URL}{batch.id}/transition/"

    assert admin.post(base, {"to_state": BatchState.COMPLETED}, format="json").status_code == 400
    assert admin.post(base, {"to_state": BatchState.ACTIVE}, format="json").status_code == 200
    assert admin.post(base, {"to_state": BatchState.COMPLETED}, format="json").status_code == 200
    batch.refresh_from_db()
    assert batch.state == BatchState.COMPLETED


@pytest.mark.django_db
def test_student_cannot_list_batches(users, course):
    assert client_for(users["student"]).get(BATCHES_URL).status_code == 403
