"""P1/P2 audit items: weekend-aware attendance, activity date filter, import cap,
short-notice live-class cancellation."""

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from attendance.models import AttendanceEvent, AttendanceSource
from attendance.services import expected_days, login_present_days
from audit.models import AuditLog
from batches.models import Batch, Course
from core.roles import Role
from enrollments.models import Enrollment
from liveclasses.models import LiveClass
from .helpers import client_for, user


@pytest.fixture
def world(db):
    course = Course.objects.create(code="FS", name="Full Stack")
    # Mon 2026-01-05 .. Sun 2026-01-11 — one exact calendar week.
    batch = Batch.objects.create(
        code="FS-1",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 5),
        end_date=datetime.date(2026, 1, 11),
    )
    faculty = user("prof", Role.FACULTY)
    batch.faculty.add(faculty)
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")
    return {"batch": batch, "faculty": faculty, "student": student}


# ---------- attendance: ATTENDANCE_COUNT_WEEKENDS ----------


@pytest.mark.django_db
def test_expected_days_counts_weekends_by_default(world):
    assert expected_days(world["batch"], upto=datetime.date(2026, 1, 11)) == 7


@pytest.mark.django_db
def test_expected_days_skips_weekends_when_disabled(world, settings):
    settings.ATTENDANCE_COUNT_WEEKENDS = False
    assert expected_days(world["batch"], upto=datetime.date(2026, 1, 11)) == 5


@pytest.mark.django_db
def test_weekend_logins_excluded_from_present_when_disabled(world, settings):
    student, batch = world["student"], world["batch"]
    for day in (datetime.date(2026, 1, 5), datetime.date(2026, 1, 10)):  # Mon + Sat
        AttendanceEvent.objects.create(
            student=student,
            batch=batch,
            source=AttendanceSource.LOGIN,
            reference_id=f"{batch.id}:{day.isoformat()}",
            date=day,
        )
    assert login_present_days(student, batch) == 2
    settings.ATTENDANCE_COUNT_WEEKENDS = False
    assert login_present_days(student, batch) == 1  # Saturday no longer counts


# ---------- activity log: date filter ----------


@pytest.mark.django_db
def test_activity_date_filter(db):
    mis = user("mis", Role.MIS)
    old = AuditLog.objects.create(action="old_event", target_type="batch", target_id="x")
    AuditLog.objects.create(action="new_event", target_type="batch", target_id="y")
    AuditLog.objects.filter(id=old.id).update(
        created_at=timezone.now() - datetime.timedelta(days=30)
    )
    cutoff = (timezone.localdate() - datetime.timedelta(days=7)).isoformat()
    rows = client_for(mis).get(f"/api/v1/activity/?from={cutoff}").json()["results"]
    actions = {r["action"] for r in rows}
    assert "new_event" in actions and "old_event" not in actions


# ---------- import: row cap ----------


@pytest.mark.django_db
def test_import_rejects_too_many_rows(world, settings):
    settings.MAX_IMPORT_ROWS = 2
    admin = user("adm", Role.ADMIN)
    header = "registration_number,name,email,phone,batch,course,faculty\n"
    lines = "".join(
        f"S9{i},Stu {i},s9{i}@example.com,987654321{i},FS-1,FS,prof\n" for i in range(3)
    )
    csv = SimpleUploadedFile("many.csv", (header + lines).encode(), content_type="text/csv")
    resp = client_for(admin).post("/api/v1/enrollments/import/", {"file": csv}, format="multipart")
    assert resp.status_code == 400
    assert "Too many rows" in resp.json()["detail"]


# ---------- live classes: short-notice cancellation ----------


@pytest.mark.django_db
def test_short_notice_cancel_requires_confirmation(world):
    live = LiveClass.objects.create(
        batch=world["batch"],
        title="Soon",
        scheduled_at=timezone.now() + datetime.timedelta(hours=2),
        meeting_link="https://meet.example/x",
        created_by=world["faculty"],
    )
    c = client_for(world["faculty"])
    resp = c.post(f"/api/v1/liveclasses/{live.id}/cancel/", {"reason": "ill"}, format="json")
    assert resp.status_code == 400
    assert resp.json().get("short_notice") is True
    live.refresh_from_db()
    assert live.status != "cancelled"

    resp = c.post(
        f"/api/v1/liveclasses/{live.id}/cancel/",
        {"reason": "ill", "confirm_short_notice": True},
        format="json",
    )
    assert resp.status_code == 200
    live.refresh_from_db()
    assert live.status == "cancelled"


@pytest.mark.django_db
def test_far_out_cancel_needs_no_confirmation(world):
    live = LiveClass.objects.create(
        batch=world["batch"],
        title="Next week",
        scheduled_at=timezone.now() + datetime.timedelta(days=5),
        meeting_link="https://meet.example/y",
        created_by=world["faculty"],
    )
    resp = client_for(world["faculty"]).post(
        f"/api/v1/liveclasses/{live.id}/cancel/", {"reason": "moved"}, format="json"
    )
    assert resp.status_code == 200
