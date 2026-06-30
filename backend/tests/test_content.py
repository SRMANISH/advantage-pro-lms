"""Video upload, role-scoped listing, gated streaming, and progress tracking."""

import datetime
import shutil
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, Course
from content.models import Video, VideoProgress
from core.roles import Role
from enrollments.models import Enrollment

VIDEOS_URL = "/api/v1/videos/"
MATERIALS_URL = "/api/v1/materials/"


@pytest.fixture(autouse=True)
def _media(settings):
    media = Path(settings.BASE_DIR) / ".pytest_media_content"
    settings.MEDIA_ROOT = media
    yield
    shutil.rmtree(media, ignore_errors=True)


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
        name="Batch 1",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    other = Batch.objects.create(
        code="B2",
        name="Batch 2",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
    )
    fac = user("fac", Role.FACULTY)
    batch.faculty.add(fac)
    student = user("stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "other": other, "fac": fac, "student": student}


def mp4(name="lesson.mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42fake-bytes", content_type="video/mp4")


@pytest.mark.django_db
def test_faculty_uploads_video_to_own_batch(world):
    resp = client_for(world["fac"]).post(
        VIDEOS_URL,
        {"batch": str(world["batch"].id), "title": "Lesson 1", "file": mp4()},
        format="multipart",
    )
    assert resp.status_code == 201
    assert Video.objects.filter(batch=world["batch"], title="Lesson 1").exists()


@pytest.mark.django_db
def test_faculty_cannot_upload_to_other_batch(world):
    resp = client_for(world["fac"]).post(
        VIDEOS_URL,
        {"batch": str(world["other"].id), "title": "Nope", "file": mp4()},
        format="multipart",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_student_cannot_upload(world):
    resp = client_for(world["student"]).post(
        VIDEOS_URL,
        {"batch": str(world["batch"].id), "title": "Nope", "file": mp4()},
        format="multipart",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_upload_rejects_disallowed_extension(world):
    bad = SimpleUploadedFile("malware.exe", b"MZ\x90", content_type="application/octet-stream")
    resp = client_for(world["fac"]).post(
        VIDEOS_URL,
        {"batch": str(world["batch"].id), "title": "x", "file": bad},
        format="multipart",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_upload_rejects_mismatched_content_type(world):
    sneaky = SimpleUploadedFile("clip.mp4", b"\x00\x00", content_type="application/x-msdownload")
    resp = client_for(world["fac"]).post(
        VIDEOS_URL,
        {"batch": str(world["batch"].id), "title": "x", "file": sneaky},
        format="multipart",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_upload_rejects_oversized_file(world, settings):
    settings.MAX_VIDEO_UPLOAD_MB = 1
    big = SimpleUploadedFile("big.mp4", b"\x00" * (2 * 1024 * 1024), content_type="video/mp4")
    resp = client_for(world["fac"]).post(
        VIDEOS_URL,
        {"batch": str(world["batch"].id), "title": "x", "file": big},
        format="multipart",
    )
    assert resp.status_code == 400
    assert "too large" in str(resp.json()).lower()


@pytest.mark.django_db
def test_mis_can_upload_note_but_admin_cannot(world):
    # Notes/materials upload is MIS + Faculty only under the updated procedure.
    mis = user("mis", Role.MIS)
    admin = user("adm", Role.ADMIN)
    note = SimpleUploadedFile("notes.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
    note2 = SimpleUploadedFile("notes2.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
    assert (
        client_for(mis)
        .post(
            MATERIALS_URL,
            {"batch": str(world["batch"].id), "title": "Notes", "file": note},
            format="multipart",
        )
        .status_code
        == 201
    )
    assert (
        client_for(admin)
        .post(
            MATERIALS_URL,
            {"batch": str(world["batch"].id), "title": "Nope", "file": note2},
            format="multipart",
        )
        .status_code
        == 403
    )


@pytest.mark.django_db
def test_student_sees_only_their_batch_videos(world):
    Video.objects.create(batch=world["batch"], title="Mine", storage_key="videos/a/x.mp4")
    Video.objects.create(batch=world["other"], title="Hidden", storage_key="videos/b/y.mp4")
    resp = client_for(world["student"]).get(VIDEOS_URL)
    assert resp.status_code == 200
    titles = {v["title"] for v in resp.json()}
    assert titles == {"Mine"}


@pytest.mark.django_db
def test_progress_marks_completed_at_80_percent(world):
    video = Video.objects.create(batch=world["batch"], title="V", storage_key="videos/a/x.mp4")
    resp = client_for(world["student"]).post(
        f"{VIDEOS_URL}{video.id}/progress/",
        {"percent": 85, "watched_seconds": 510, "last_position": 510},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["completed"] is True
    progress = VideoProgress.objects.get(video=video, student=world["student"])
    assert progress.completed is True
    assert progress.last_position == 510


REVOKE = "/api/v1/video-access/revoke/"
CLOSE = "/api/v1/video-access/close-course/"


@pytest.mark.django_db
def test_mis_revokes_individual_video_access(world):
    video = Video.objects.create(batch=world["batch"], title="V", storage_key="videos/a/x.mp4")
    mis = user("mis", Role.MIS)
    # Student can play before revoke is created (file missing is fine — gate is checked first).
    resp = client_for(mis).post(
        REVOKE,
        {"student_id": str(world["student"].id), "batch_id": str(world["batch"].id)},
        format="json",
    )
    assert resp.status_code == 200
    blocked = client_for(world["student"]).get(f"{VIDEOS_URL}{video.id}/play/")
    assert blocked.status_code == 403


@pytest.mark.django_db
def test_admin_and_mis_can_close_course_but_not_faculty(world):
    Video.objects.create(batch=world["batch"], title="V", storage_key="videos/a/x.mp4")
    admin = user("ad", Role.ADMIN)
    mis = user("mis", Role.MIS)
    assert (
        client_for(admin)
        .post(CLOSE, {"batch_id": str(world["batch"].id)}, format="json")
        .status_code
        == 200
    )
    assert (
        client_for(mis).post(CLOSE, {"batch_id": str(world["batch"].id)}, format="json").status_code
        == 200
    )
    # Faculty cannot close course video access.
    assert (
        client_for(world["fac"])
        .post(CLOSE, {"batch_id": str(world["batch"].id)}, format="json")
        .status_code
        == 403
    )


@pytest.mark.django_db
def test_super_admin_cannot_revoke_video_access(world):
    sa = user("sa", Role.SUPER_ADMIN)
    assert (
        client_for(sa)
        .post(REVOKE, {"student_id": str(world["student"].id)}, format="json")
        .status_code
        == 403
    )


@pytest.mark.django_db
def test_course_completion_closes_video_access(world):
    from batches.models import BatchState
    from content.access import is_video_blocked

    world["batch"].state = BatchState.ACTIVE
    world["batch"].save()
    admin = user("ad", Role.ADMIN)
    client_for(admin).post(
        f"/api/v1/batches/{world['batch'].id}/transition/",
        {"to_state": BatchState.COMPLETED},
        format="json",
    )
    assert is_video_blocked(world["student"], world["batch"]) is True


@pytest.mark.django_db
def test_play_streams_with_range_for_authorized_student(world):
    video = (
        client_for(world["fac"])
        .post(
            VIDEOS_URL,
            {"batch": str(world["batch"].id), "title": "Stream me", "file": mp4()},
            format="multipart",
        )
        .json()
    )
    resp = client_for(world["student"]).get(
        f"{VIDEOS_URL}{video['id']}/play/", HTTP_RANGE="bytes=0-3"
    )
    assert resp.status_code == 206
    assert resp["Content-Range"].startswith("bytes 0-3/")
