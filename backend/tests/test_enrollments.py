"""Student bulk import: all-or-nothing validation and atomic creation."""

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment

IMPORT_URL = "/api/v1/enrollments/import/"
HEADER = "registration_number,name,email,phone,batch,course,faculty"


@pytest.fixture
def setup(db):
    admin = User.objects.create_user(
        username="adm", password="x", role=Role.ADMIN, status=UserStatus.ACTIVE
    )
    fac = User.objects.create_user(
        username="prof", password="x", role=Role.FACULTY, status=UserStatus.ACTIVE
    )
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="FS-1",
        name="FS One",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    return {"admin": admin, "fac": fac, "course": course, "batch": batch}


def csv_file(*rows: str) -> SimpleUploadedFile:
    content = "\n".join([HEADER, *rows]).encode("utf-8")
    return SimpleUploadedFile("students.csv", content, content_type="text/csv")


def admin_client(setup):
    c = APIClient()
    c.force_authenticate(user=setup["admin"])
    return c


@pytest.mark.django_db
def test_valid_import_creates_pending_students(setup):
    rows = [
        "S001,Asha Rao,asha@example.com,9876543210,FS-1,FS,prof",
        "S002,Ravi Kumar,ravi@example.com,9876500000,FS-1,FS,prof",
    ]
    resp = admin_client(setup).post(IMPORT_URL, {"file": csv_file(*rows)}, format="multipart")
    assert resp.status_code == 201
    assert resp.json()["created"] == 2
    assert Enrollment.objects.count() == 2
    student = User.objects.get(username="S001")
    assert student.role == Role.STUDENT
    assert student.status == UserStatus.PENDING


@pytest.mark.django_db
def test_dry_run_validates_without_creating(setup):
    rows = ["S010,Maya N,maya@example.com,9876543210,FS-1,FS,prof"]
    resp = admin_client(setup).post(
        IMPORT_URL, {"file": csv_file(*rows), "dry_run": "true"}, format="multipart"
    )
    assert resp.status_code == 200
    assert resp.json() == {"valid": True, "row_count": 1}
    assert User.objects.filter(username="S010").count() == 0


@pytest.mark.django_db
def test_one_bad_row_rejects_whole_file(setup):
    rows = [
        "S100,Good One,good@example.com,9876543210,FS-1,FS,prof",
        "S101,Bad Email,not-an-email,9876543210,FS-1,FS,prof",
    ]
    resp = admin_client(setup).post(IMPORT_URL, {"file": csv_file(*rows)}, format="multipart")
    assert resp.status_code == 400
    body = resp.json()
    assert body["valid"] is False
    assert any(e["field"] == "email" for e in body["errors"])
    # All-or-nothing: nothing was written.
    assert Enrollment.objects.count() == 0
    assert User.objects.filter(username__in=["S100", "S101"]).count() == 0


@pytest.mark.django_db
def test_duplicate_registration_within_file_is_rejected(setup):
    rows = [
        "DUP,One,one@example.com,9876543210,FS-1,FS,prof",
        "DUP,Two,two@example.com,9876543210,FS-1,FS,prof",
    ]
    resp = admin_client(setup).post(IMPORT_URL, {"file": csv_file(*rows)}, format="multipart")
    assert resp.status_code == 400
    assert any(e["field"] == "registration_number" for e in resp.json()["errors"])


@pytest.mark.django_db
def test_unknown_batch_is_rejected(setup):
    rows = ["S200,Name,n@example.com,9876543210,NOPE,FS,prof"]
    resp = admin_client(setup).post(IMPORT_URL, {"file": csv_file(*rows)}, format="multipart")
    assert resp.status_code == 400
    assert any(e["field"] == "batch" for e in resp.json()["errors"])


@pytest.mark.django_db
def test_faculty_cannot_import(setup):
    c = APIClient()
    c.force_authenticate(user=setup["fac"])
    rows = ["S300,Name,n@example.com,9876543210,FS-1,FS,prof"]
    resp = c.post(IMPORT_URL, {"file": csv_file(*rows)}, format="multipart")
    assert resp.status_code == 403
