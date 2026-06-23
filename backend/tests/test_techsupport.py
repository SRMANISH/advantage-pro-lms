"""Tech Support workflow: unanswered-doubt monitor + remind faculty."""

import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment
from forum.models import Reply, Thread

MONITOR = "/api/v1/forum/monitor/"


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
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    fac = user("fac", Role.FACULTY)
    batch.faculty.add(fac)
    ts = user("ts", Role.TECH_SUPPORT)
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "fac": fac, "ts": ts, "student": student}


@pytest.mark.django_db
def test_monitor_lists_unanswered_and_flags_overdue(world):
    fresh = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="New", body="b"
    )
    old = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Old", body="b"
    )
    Thread.objects.filter(id=old.id).update(created_at=timezone.now() - datetime.timedelta(hours=5))
    answered = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Answered", body="b"
    )
    Reply.objects.create(thread=answered, author=world["fac"], body="done")

    resp = client_for(world["ts"]).get(MONITOR)
    assert resp.status_code == 200
    body = resp.json()
    titles = {t["title"]: t for t in body["threads"]}
    assert set(titles) == {"New", "Old"}  # answered excluded
    assert titles["Old"]["overdue"] is True
    assert titles["New"]["overdue"] is False
    assert fresh.title in titles


@pytest.mark.django_db
def test_tech_support_reminds_faculty(world):
    thread = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Help", body="b"
    )
    resp = client_for(world["ts"]).post(f"/api/v1/threads/{thread.id}/remind/")
    assert resp.status_code == 200
    assert world["fac"].notifications.filter(kind="doubt_reminder").exists()


@pytest.mark.django_db
def test_student_cannot_use_monitor_or_remind(world):
    thread = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Help", body="b"
    )
    assert client_for(world["student"]).get(MONITOR).status_code == 403
    assert (
        client_for(world["student"]).post(f"/api/v1/threads/{thread.id}/remind/").status_code == 403
    )
