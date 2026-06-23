"""Attendance auto-capture from tests/tasks/videos and aggregation."""

import datetime

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from assessments.models import Choice, Question, Task, Test
from attendance.models import AttendanceEvent
from attendance.services import student_summary
from batches.models import Batch, Course
from content.models import Video
from core.roles import Role
from enrollments.models import Enrollment

ME_URL = "/api/v1/attendance/me/"
BATCH_URL = "/api/v1/attendance/"


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


@pytest.mark.django_db
def test_test_submit_marks_present(world):
    test = Test.objects.create(batch=world["batch"], title="T")
    q = Question.objects.create(test=test, text="q")
    c = Choice.objects.create(question=q, text="a", is_correct=True)
    resp = client_for(world["student"]).post(
        f"/api/v1/tests/{test.id}/submit/",
        {"answers": [{"question": str(q.id), "choice": str(c.id)}]},
        format="json",
    )
    assert resp.status_code == 201
    assert AttendanceEvent.objects.filter(
        student=world["student"], source="test", reference_id=str(test.id)
    ).exists()


@pytest.mark.django_db
def test_task_submit_marks_present(world):
    task = Task.objects.create(batch=world["batch"], title="Essay")
    resp = client_for(world["student"]).post(
        f"/api/v1/tasks/{task.id}/submit/", {"text": "done"}, format="json"
    )
    assert resp.status_code == 201
    assert AttendanceEvent.objects.filter(
        student=world["student"], source="task", reference_id=str(task.id)
    ).exists()


@pytest.mark.django_db
def test_video_80_percent_marks_present(world):
    video = Video.objects.create(batch=world["batch"], title="V", storage_key="videos/x.mp4")
    resp = client_for(world["student"]).post(
        f"/api/v1/videos/{video.id}/progress/",
        {"percent": 90, "watched_seconds": 90, "last_position": 90},
        format="json",
    )
    assert resp.status_code == 200
    assert AttendanceEvent.objects.filter(source="video", reference_id=str(video.id)).exists()


@pytest.mark.django_db
def test_summary_percentage(world):
    # 2 opportunities (1 test + 1 task); student does the task only -> 50%.
    Test.objects.create(batch=world["batch"], title="T")
    task = Task.objects.create(batch=world["batch"], title="Essay")
    client_for(world["student"]).post(
        f"/api/v1/tasks/{task.id}/submit/", {"text": "done"}, format="json"
    )
    summary = student_summary(world["student"], world["batch"])
    assert summary == {"present": 1, "total": 2, "percent": 50}


@pytest.mark.django_db
def test_my_attendance_endpoint(world):
    resp = client_for(world["student"]).get(ME_URL)
    assert resp.status_code == 200
    assert resp.json()[0]["batch"] == "B1"


@pytest.mark.django_db
def test_batch_roster_access(world):
    # Faculty of the batch can see the roster; a student cannot use this endpoint.
    fac_resp = client_for(world["fac"]).get(f"{BATCH_URL}?batch={world['batch'].id}")
    assert fac_resp.status_code == 200
    assert any(r["registration_number"] == "stu" for r in fac_resp.json())
    assert (
        client_for(world["student"]).get(f"{BATCH_URL}?batch={world['batch'].id}").status_code
        == 403
    )
