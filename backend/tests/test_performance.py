"""Composite performance metrics + batch ranking."""

import datetime

import pytest

from assessments.models import Choice, Question, Task, Test
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment
from performance.services import batch_performance, student_metrics

from .helpers import client_for, user

ME_URL = "/api/v1/performance/me/"
BATCH_URL = "/api/v1/performance/"


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
    s1 = user("s1", Role.STUDENT)
    s2 = user("s2", Role.STUDENT)
    Enrollment.objects.create(student=s1, batch=batch, registration_number="s1")
    Enrollment.objects.create(student=s2, batch=batch, registration_number="s2")
    return {"batch": batch, "fac": fac, "s1": s1, "s2": s2}


def make_test(batch):
    test = Test.objects.create(batch=batch, title="T")
    q = Question.objects.create(test=test, text="q")
    correct = Choice.objects.create(question=q, text="a", is_correct=True)
    wrong = Choice.objects.create(question=q, text="b", is_correct=False)
    return test, q, correct, wrong


@pytest.mark.django_db
def test_metrics_reflect_engagement(world):
    test, q, correct, _ = make_test(world["batch"])
    Task.objects.create(batch=world["batch"], title="Essay")

    sc = client_for(world["s1"])
    sc.post(
        f"/api/v1/tests/{test.id}/submit/",
        {"answers": [{"question": str(q.id), "choice": str(correct.id)}]},
        format="json",
    )
    metrics = student_metrics(world["s1"], world["batch"])
    assert metrics["test_pct"] == 100
    # Has a task in the batch but did not submit it -> task component 0.
    assert metrics["task_pct"] == 0


@pytest.mark.django_db
def test_batch_ranking(world):
    test, q, correct, wrong = make_test(world["batch"])
    # s1 answers correctly (100%), s2 answers wrong (0%).
    client_for(world["s1"]).post(
        f"/api/v1/tests/{test.id}/submit/",
        {"answers": [{"question": str(q.id), "choice": str(correct.id)}]},
        format="json",
    )
    client_for(world["s2"]).post(
        f"/api/v1/tests/{test.id}/submit/",
        {"answers": [{"question": str(q.id), "choice": str(wrong.id)}]},
        format="json",
    )
    board = batch_performance(world["batch"])
    assert board[0]["registration_number"] == "s1"
    assert board[0]["rank"] == 1
    assert board[0]["overall"] >= board[1]["overall"]


@pytest.mark.django_db
def test_my_performance_includes_rank(world):
    make_test(world["batch"])
    resp = client_for(world["s1"]).get(ME_URL)
    assert resp.status_code == 200
    assert resp.json()[0]["batch"] == "B1"
    assert "rank" in resp.json()[0]


@pytest.mark.django_db
def test_batch_board_requires_staff(world):
    assert client_for(world["fac"]).get(f"{BATCH_URL}?batch={world['batch'].id}").status_code == 200
    assert client_for(world["s1"]).get(f"{BATCH_URL}?batch={world['batch'].id}").status_code == 403
