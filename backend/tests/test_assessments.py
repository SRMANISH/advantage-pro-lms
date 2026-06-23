"""MCQ tests: build, auto-grade, one attempt, role rules, hidden answers."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from assessments.models import Choice, Question, Test, TestAttempt
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment

TESTS_URL = "/api/v1/tests/"


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
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "fac": fac, "student": student}


def build_payload(batch):
    return {
        "batch": str(batch.id),
        "title": "Quiz 1",
        "questions": [
            {
                "text": "2 + 2 = ?",
                "choices": [
                    {"text": "3", "is_correct": False},
                    {"text": "4", "is_correct": True},
                ],
            },
            {
                "text": "Capital of France?",
                "choices": [
                    {"text": "Paris", "is_correct": True},
                    {"text": "Rome", "is_correct": False},
                ],
            },
        ],
    }


@pytest.mark.django_db
def test_faculty_creates_test(world):
    resp = client_for(world["fac"]).post(TESTS_URL, build_payload(world["batch"]), format="json")
    assert resp.status_code == 201
    assert Test.objects.filter(title="Quiz 1").count() == 1
    assert Question.objects.count() == 2
    assert Choice.objects.filter(is_correct=True).count() == 2


@pytest.mark.django_db
def test_student_cannot_create_test(world):
    resp = client_for(world["student"]).post(
        TESTS_URL, build_payload(world["batch"]), format="json"
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_student_take_view_hides_correct_answers(world):
    client_for(world["fac"]).post(TESTS_URL, build_payload(world["batch"]), format="json")
    test = Test.objects.get(title="Quiz 1")
    resp = client_for(world["student"]).get(f"{TESTS_URL}{test.id}/")
    assert resp.status_code == 200
    first_choice = resp.json()["questions"][0]["choices"][0]
    assert "is_correct" not in first_choice


@pytest.mark.django_db
def test_auto_grade_and_single_attempt(world):
    client_for(world["fac"]).post(TESTS_URL, build_payload(world["batch"]), format="json")
    test = Test.objects.prefetch_related("questions__choices").get(title="Quiz 1")
    q1, q2 = list(test.questions.all())
    correct_q1 = q1.choices.get(is_correct=True)
    wrong_q2 = q2.choices.get(is_correct=False)

    sc = client_for(world["student"])
    resp = sc.post(
        f"{TESTS_URL}{test.id}/submit/",
        {
            "answers": [
                {"question": str(q1.id), "choice": str(correct_q1.id)},
                {"question": str(q2.id), "choice": str(wrong_q2.id)},
            ]
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json() == {"score": 1, "total": 2}
    assert TestAttempt.objects.filter(test=test, student=world["student"]).count() == 1

    # Second attempt rejected.
    again = sc.post(
        f"{TESTS_URL}{test.id}/submit/",
        {"answers": [{"question": str(q1.id), "choice": str(correct_q1.id)}]},
        format="json",
    )
    assert again.status_code == 400


@pytest.mark.django_db
def test_closed_test_cannot_be_submitted(world):
    test = Test.objects.create(
        batch=world["batch"],
        title="Closed",
        close_at=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )
    q = Question.objects.create(test=test, text="q")
    Choice.objects.create(question=q, text="a", is_correct=True)
    resp = client_for(world["student"]).post(
        f"{TESTS_URL}{test.id}/submit/",
        {"answers": [{"question": str(q.id), "choice": str(q.choices.first().id)}]},
        format="json",
    )
    assert resp.status_code == 400
