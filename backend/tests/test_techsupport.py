"""Tech Support workflow: unanswered-doubt monitor + remind faculty."""

import datetime

import pytest
from django.utils import timezone

from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment
from forum.models import Reply, Thread
from .helpers import client_for, user

MONITOR = "/api/v1/forum/monitor/"


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
    # Paginated envelope: rows under "results", whole-dataset context alongside it.
    titles = {t["title"]: t for t in body["results"]}
    assert set(titles) == {"New", "Old"}  # answered excluded
    assert body["count"] == 2
    assert "counts" in body and "window_hours" in body
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


@pytest.mark.django_db
def test_forum_monitor_is_paginated(world):
    """The unanswered queue is unbounded, and this dashboard is where it is read in full."""
    Thread.objects.bulk_create(
        [
            Thread(batch=world["batch"], author=world["student"], title=f"T{i}", body="b")
            for i in range(30)  # > the 25 default page size
        ]
    )
    ts = client_for(world["ts"])

    first = ts.get(MONITOR).json()
    assert first["count"] == 30
    assert len(first["results"]) == 25
    # Whole-dataset context still rides alongside the page, not inside it.
    assert first["counts"]["open"] == 30
    assert first["window_hours"]

    second = ts.get(MONITOR, {"page": 2}).json()
    assert len(second["results"]) == 5
    assert second["counts"]["open"] == 30  # counts describe everything, not this page
