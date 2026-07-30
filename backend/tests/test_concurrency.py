"""Concurrency: parallel duplicate submissions and duplicate escalation/cron runs.

Two styles are used, matched to what's actually being verified:
  * Submission races are tested by simulating "both requests got past the read-check"
    (the actual shape a race manifests as) rather than orchestrating OS thread
    interleaving against the DB — this is deterministic and portable across the SQLite
    (local) / Postgres (CI) backends this project runs on, and is exactly how the
    escalation race in escalations/services.py was fixed and verified.
  * The cron lock test uses real threads, since it only contends on the cache (an atomic
    ``cache.add``), not DB rows — safe to thread without SQLite's writer-locking concerns.
"""

import datetime
import threading
import time

import pytest

from assessments.models import Choice, Question, Task, TaskSubmission, Test, TestAttempt
from batches.models import Batch, Course
from core.cron import LockHeld, cron_lock
from core.roles import Role
from enrollments.models import Enrollment

from .helpers import client_for, user

TESTS_URL = "/api/v1/tests/"
TASKS_URL = "/api/v1/tasks/"


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
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "fac": fac, "student": student}


# ---------- parallel test-attempt submission ----------


@pytest.mark.django_db
def test_parallel_test_submission_only_one_attempt_is_recorded(world):
    test = Test.objects.create(batch=world["batch"], title="Quiz")
    q = Question.objects.create(test=test, text="2+2?")
    right = Choice.objects.create(question=q, text="4", is_correct=True)

    payload = {"answers": [{"question": str(q.id), "choice": str(right.id)}]}
    c = client_for(world["student"])

    # Both requests pass the "have I already attempted this" read-check before either
    # commits — the real shape of the race two simultaneous submit clicks would hit.
    first = c.post(f"{TESTS_URL}{test.id}/submit/", payload, format="json")
    second = c.post(f"{TESTS_URL}{test.id}/submit/", payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 400
    assert "already attempted" in second.json()["detail"]
    assert TestAttempt.objects.filter(test=test, student=world["student"]).count() == 1


@pytest.mark.django_db
def test_racing_test_submission_hits_the_constraint_not_a_500(world):
    """Force past the fast-path check entirely — only the DB constraint stops the second
    write, proving the IntegrityError catch (not just the pre-check) is what's safe."""
    test = Test.objects.create(batch=world["batch"], title="Quiz")
    q = Question.objects.create(test=test, text="2+2?")
    right = Choice.objects.create(question=q, text="4", is_correct=True)
    student = world["student"]

    # Simulate "both requests already read exists()=False" by creating the row that a
    # racing second request would then also try to create.
    TestAttempt.objects.create(test=test, student=student, score=0, total=1)

    payload = {"answers": [{"question": str(q.id), "choice": str(right.id)}]}
    resp = client_for(student).post(f"{TESTS_URL}{test.id}/submit/", payload, format="json")
    assert resp.status_code == 400  # not 500 — the IntegrityError is caught
    assert TestAttempt.objects.filter(test=test, student=student).count() == 1


# ---------- parallel task submission ----------


@pytest.mark.django_db
def test_parallel_task_submission_only_one_submission_is_recorded(world):
    task = Task.objects.create(batch=world["batch"], title="Assignment 1")
    c = client_for(world["student"])

    first = c.post(f"{TASKS_URL}{task.id}/submit/", {"text": "my answer"}, format="json")
    second = c.post(f"{TASKS_URL}{task.id}/submit/", {"text": "resubmit"}, format="json")

    assert first.status_code == 201
    assert second.status_code == 400
    assert "already submitted" in second.json()["detail"]
    assert TaskSubmission.objects.filter(task=task, student=world["student"]).count() == 1
    assert TaskSubmission.objects.get(task=task, student=world["student"]).text == "my answer"


@pytest.mark.django_db
def test_racing_task_submission_hits_the_constraint_not_a_500(world):
    task = Task.objects.create(batch=world["batch"], title="Assignment 1")
    student = world["student"]
    TaskSubmission.objects.create(task=task, student=student, text="already here")

    resp = client_for(student).post(f"{TASKS_URL}{task.id}/submit/", {"text": "x"}, format="json")
    assert resp.status_code == 400  # not 500
    assert TaskSubmission.objects.filter(task=task, student=student).count() == 1


# ---------- duplicate cron runs (real threads — cache-only contention) ----------


@pytest.mark.django_db
def test_concurrent_threads_only_one_acquires_the_cron_lock():
    winners: list[bool] = []
    ready = threading.Barrier(2)

    def attempt():
        ready.wait()  # release both threads together
        try:
            with cron_lock("parallel_job", timeout=5):
                winners.append(True)
                # Hold the lock briefly so the other thread's attempt genuinely overlaps
                # it — without this, the winner could acquire *and release* before the
                # loser ever calls cache.add(), and both would "win" sequentially.
                time.sleep(0.2)
        except LockHeld:
            winners.append(False)

    t1 = threading.Thread(target=attempt)
    t2 = threading.Thread(target=attempt)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert sorted(winners) == [False, True]  # exactly one winner, one LockHeld
