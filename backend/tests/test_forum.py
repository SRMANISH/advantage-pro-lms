"""Doubt forum: posting, replies, resolve, scoping, and search."""

import datetime

import pytest

from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment
from forum.models import Thread
from .helpers import client_for, user

THREADS = "/api/v1/threads/"


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
    other = Batch.objects.create(
        code="B2",
        name="B2",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    fac = user("fac", Role.FACULTY)
    batch.faculty.add(fac)
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "other": other, "fac": fac, "student": student}


@pytest.mark.django_db
def test_student_posts_doubt_and_faculty_notified(world):
    resp = client_for(world["student"]).post(
        THREADS,
        {
            "batch": str(world["batch"].id),
            "title": "How do hooks work?",
            "body": "Explain useState",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert Thread.objects.filter(title="How do hooks work?").exists()
    assert world["fac"].notifications.filter(kind="new_doubt").exists()


@pytest.mark.django_db
def test_faculty_replies_and_student_notified(world):
    thread = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Q", body="b"
    )
    resp = client_for(world["fac"]).post(
        f"{THREADS}{thread.id}/reply/", {"body": "Here's the answer"}, format="json"
    )
    assert resp.status_code == 200
    assert thread.replies.count() == 1
    assert world["student"].notifications.filter(kind="doubt_reply").exists()


@pytest.mark.django_db
def test_author_can_resolve(world):
    thread = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Q", body="b"
    )
    resp = client_for(world["student"]).post(f"{THREADS}{thread.id}/resolve/")
    assert resp.status_code == 200
    thread.refresh_from_db()
    assert thread.resolved is True
    assert thread.status == "resolved"


@pytest.mark.django_db
def test_tech_support_can_reply_and_marks_answered(world):
    ts = user("ts", Role.TECH_SUPPORT)
    thread = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Q", body="b"
    )
    resp = client_for(ts).post(
        f"{THREADS}{thread.id}/reply/", {"body": "Try clearing cache"}, format="json"
    )
    assert resp.status_code == 200
    thread.refresh_from_db()
    assert thread.replies.count() == 1
    assert thread.status == "answered"


@pytest.mark.django_db
def test_tech_support_can_escalate(world):
    ts = user("ts", Role.TECH_SUPPORT)
    thread = Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Q", body="b"
    )
    resp = client_for(ts).post(f"{THREADS}{thread.id}/escalate/")
    assert resp.status_code == 200
    thread.refresh_from_db()
    assert thread.status == "escalated"
    assert world["fac"].notifications.filter(kind="doubt_escalated").exists()


@pytest.mark.django_db
def test_forum_is_scoped_to_own_batch(world):
    Thread.objects.create(batch=world["batch"], author=world["student"], title="Mine", body="b")
    other_student = user("stu2", Role.STUDENT)
    Enrollment.objects.create(
        student=other_student, batch=world["other"], registration_number="stu2"
    )
    Thread.objects.create(batch=world["other"], author=other_student, title="Hidden", body="b")

    titles = {t["title"] for t in client_for(world["student"]).get(THREADS).json()["results"]}
    assert titles == {"Mine"}


@pytest.mark.django_db
def test_keyword_search(world):
    Thread.objects.create(
        batch=world["batch"], author=world["student"], title="Routing question", body="x"
    )
    Thread.objects.create(
        batch=world["batch"], author=world["student"], title="State management", body="y"
    )
    resp = client_for(world["fac"]).get(f"{THREADS}?q=routing")
    titles = [t["title"] for t in resp.json()["results"]]
    assert titles == ["Routing question"]
