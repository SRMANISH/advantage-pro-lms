"""Courses, batches, role-scoping, lifecycle, and faculty assignment."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, BatchState, Course
from core.roles import Role

COURSES_URL = "/api/v1/courses/"
BATCHES_URL = "/api/v1/batches/"


def make_user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


@pytest.fixture
def users(db):
    return {
        "super": make_user("sa", Role.SUPER_ADMIN),
        "admin": make_user("ad", Role.ADMIN),
        "faculty": make_user("fac", Role.FACULTY),
        "faculty2": make_user("fac2", Role.FACULTY),
        "student": make_user("stu", Role.STUDENT),
        "counselor": make_user("co", Role.COUNSELOR),
    }


@pytest.fixture
def course(db):
    return Course.objects.create(code="FS", name="Full Stack")


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


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
def test_admin_creates_course_but_faculty_and_student_cannot(users, course):
    payload = {"code": "DS", "name": "Data Science"}
    assert client_for(users["admin"]).post(COURSES_URL, payload).status_code == 201
    assert (
        client_for(users["faculty"]).post(COURSES_URL, {"code": "X", "name": "X"}).status_code
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
    }
    resp = client_for(users["admin"]).post(BATCHES_URL, payload, format="json")
    assert resp.status_code == 201
    assert resp.json()["state"] == BatchState.DRAFT


@pytest.mark.django_db
def test_batch_end_before_start_is_rejected(users, course):
    payload = {
        "code": "BAD",
        "name": "Bad",
        "course": str(course.id),
        "start_date": "2026-04-01",
        "end_date": "2026-01-01",
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
def test_only_super_admin_can_delete_batch(users, course):
    batch = make_batch(course)
    assert client_for(users["admin"]).delete(f"{BATCHES_URL}{batch.id}/").status_code == 403
    assert client_for(users["super"]).delete(f"{BATCHES_URL}{batch.id}/").status_code == 204


@pytest.mark.django_db
def test_faculty_assigns_faculty_to_own_batch_only(users, course):
    own = make_batch(course, code="OWN")
    own.faculty.add(users["faculty"])
    other = make_batch(course, code="NOTOWN")

    url = f"{BATCHES_URL}{own.id}/assign-faculty/"
    resp = client_for(users["faculty"]).post(
        url, {"faculty_ids": [str(users["faculty2"].id)]}, format="json"
    )
    assert resp.status_code == 200
    assert users["faculty2"] in own.faculty.all()

    # Cannot touch a batch they don't teach (queryset-scoped -> 404).
    resp2 = client_for(users["faculty"]).post(
        f"{BATCHES_URL}{other.id}/assign-faculty/",
        {"faculty_ids": [str(users["faculty2"].id)]},
        format="json",
    )
    assert resp2.status_code == 404


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
