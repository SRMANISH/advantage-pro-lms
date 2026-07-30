"""In-video upsell: next-course prompt using the student's employment."""

import datetime

import pytest

from accounts.models import User, UserStatus
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment

from .helpers import client_for

URL = "/api/v1/upsell/"


def student(username="stu"):
    return User.objects.create_user(
        username=username, password="x", role=Role.STUDENT, status=UserStatus.ACTIVE
    )


@pytest.fixture
def world(db):
    fs = Course.objects.create(code="FS", name="Full Stack")
    Course.objects.create(code="DS", name="Data Science")  # the "next" course
    batch = Batch.objects.create(
        code="FS-1",
        name="B",
        course=fs,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    return {"fs": fs, "batch": batch}


@pytest.mark.django_db
def test_prompt_uses_company_and_lists_other_courses(world):
    s = student()
    Enrollment.objects.create(
        student=s, batch=world["batch"], registration_number="stu", employment_company="Infosys"
    )
    resp = client_for(s).get(URL)
    assert resp.status_code == 200
    prompt = resp.json()["prompt"]
    assert "Infosys" in prompt["message"]
    codes = {c["code"] for c in prompt["courses"]}
    assert codes == {"DS"}  # excludes the enrolled FS course


@pytest.mark.django_db
def test_generic_message_without_company(world):
    s = student("stu2")
    Enrollment.objects.create(student=s, batch=world["batch"], registration_number="stu2")
    prompt = client_for(s).get(URL).json()["prompt"]
    assert "Advantage Pro" in prompt["message"]


@pytest.mark.django_db
def test_no_prompt_when_no_other_courses(db):
    only = Course.objects.create(code="ONLY", name="Only")
    batch = Batch.objects.create(
        code="O-1",
        name="B",
        course=only,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    s = student("stu3")
    Enrollment.objects.create(student=s, batch=batch, registration_number="stu3")
    assert client_for(s).get(URL).json()["prompt"] is None
