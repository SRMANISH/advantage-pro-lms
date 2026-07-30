"""Forum attachments: upload on a doubt, gated download, spoof rejection."""

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment
from forum.models import Thread, ThreadAttachment

from .helpers import client_for, user

THREADS = "/api/v1/threads/"

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def world(db):
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="FS-1",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 1),
    )
    other = Batch.objects.create(
        code="FS-2",
        name="B2",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 1),
    )
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")
    outsider = user("S9", Role.STUDENT)
    Enrollment.objects.create(student=outsider, batch=other, registration_number="S9")
    return {"batch": batch, "student": student, "outsider": outsider}


@pytest.mark.django_db
def test_student_posts_doubt_with_screenshot(world):
    png = SimpleUploadedFile("error.png", PNG, content_type="image/png")
    resp = client_for(world["student"]).post(
        THREADS,
        {"batch": str(world["batch"].id), "title": "Crash", "body": "see image", "file": png},
        format="multipart",
    )
    assert resp.status_code == 201
    thread = Thread.objects.get(title="Crash")
    att = ThreadAttachment.objects.get(thread=thread)
    assert att.filename == "error.png"

    # The author can download it.
    dl = client_for(world["student"]).get(f"/api/v1/attachments/{att.id}/")
    assert dl.status_code == 200


@pytest.mark.django_db
def test_attachment_download_is_batch_scoped(world):
    png = SimpleUploadedFile("error.png", PNG, content_type="image/png")
    client_for(world["student"]).post(
        THREADS,
        {"batch": str(world["batch"].id), "title": "Crash", "body": "x", "file": png},
        format="multipart",
    )
    att = ThreadAttachment.objects.first()
    # A student from another batch cannot download it.
    resp = client_for(world["outsider"]).get(f"/api/v1/attachments/{att.id}/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_spoofed_attachment_rejected(world):
    evil = SimpleUploadedFile("error.png", b"<html>not a png</html>", content_type="image/png")
    resp = client_for(world["student"]).post(
        THREADS,
        {"batch": str(world["batch"].id), "title": "Crash", "body": "x", "file": evil},
        format="multipart",
    )
    assert resp.status_code == 400
    assert not Thread.objects.filter(title="Crash").exists()  # atomic: nothing persisted
