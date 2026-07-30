"""Tasks: deadline + late flag, one submission, faculty grading & feedback."""

import datetime
import shutil
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from assessments.models import Task, TaskSubmission
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment
from .helpers import client_for, user

TASKS_URL = "/api/v1/tasks/"


@pytest.fixture(autouse=True)
def _media(settings):
    media = Path(settings.BASE_DIR) / ".pytest_media_tasks"
    settings.MEDIA_ROOT = media
    yield
    shutil.rmtree(media, ignore_errors=True)


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


def make_task(batch, deadline=None):
    return Task.objects.create(batch=batch, title="Essay", deadline=deadline)


@pytest.mark.django_db
def test_faculty_creates_task(world):
    resp = client_for(world["fac"]).post(
        TASKS_URL,
        {"batch": str(world["batch"].id), "title": "Essay", "description": "Write it"},
        format="json",
    )
    assert resp.status_code == 201
    assert Task.objects.filter(title="Essay").exists()


@pytest.mark.django_db
def test_on_time_submission_not_late(world):
    task = make_task(world["batch"])  # no deadline
    resp = client_for(world["student"]).post(
        f"{TASKS_URL}{task.id}/submit/", {"text": "my answer"}, format="json"
    )
    assert resp.status_code == 201
    assert resp.json()["is_late"] is False


@pytest.mark.django_db
def test_late_submission_is_flagged(world):
    past = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
    task = make_task(world["batch"], deadline=past)
    resp = client_for(world["student"]).post(
        f"{TASKS_URL}{task.id}/submit/", {"text": "late answer"}, format="json"
    )
    assert resp.status_code == 201
    assert resp.json()["is_late"] is True
    assert TaskSubmission.objects.get(task=task).is_late is True


@pytest.mark.django_db
def test_only_one_submission(world):
    task = make_task(world["batch"])
    sc = client_for(world["student"])
    assert sc.post(f"{TASKS_URL}{task.id}/submit/", {"text": "a"}, format="json").status_code == 201
    assert sc.post(f"{TASKS_URL}{task.id}/submit/", {"text": "b"}, format="json").status_code == 400


@pytest.mark.django_db
def test_faculty_grades_and_student_sees_feedback(world):
    task = make_task(world["batch"])
    client_for(world["student"]).post(
        f"{TASKS_URL}{task.id}/submit/", {"text": "answer"}, format="json"
    )
    submission = TaskSubmission.objects.get(task=task)

    grade = client_for(world["fac"]).post(
        f"/api/v1/task-submissions/{submission.id}/grade/",
        {"score": 8, "feedback": "Good work"},
        format="json",
    )
    assert grade.status_code == 200

    listing = client_for(world["student"]).get(TASKS_URL).json()
    mine = listing[0]["my_submission"]
    assert mine["score"] == 8
    assert mine["feedback"] == "Good work"


@pytest.mark.django_db
def test_student_cannot_grade(world):
    task = make_task(world["batch"])
    client_for(world["student"]).post(
        f"{TASKS_URL}{task.id}/submit/", {"text": "answer"}, format="json"
    )
    submission = TaskSubmission.objects.get(task=task)
    resp = client_for(world["student"]).post(
        f"/api/v1/task-submissions/{submission.id}/grade/",
        {"score": 10},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_file_submission_round_trip(world):
    task = make_task(world["batch"])
    sc = client_for(world["student"])
    upload = SimpleUploadedFile("answer.txt", b"hello answer", content_type="text/plain")
    assert (
        sc.post(f"{TASKS_URL}{task.id}/submit/", {"file": upload}, format="multipart").status_code
        == 201
    )
    submission = TaskSubmission.objects.get(task=task)
    resp = client_for(world["fac"]).get(f"/api/v1/task-submissions/{submission.id}/file/")
    assert resp.status_code == 200
