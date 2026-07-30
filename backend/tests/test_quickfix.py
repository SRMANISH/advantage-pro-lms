"""Quick-fix batch (FUNCTIONAL_REVIEW.md §5): R-01, R-04, R-09, R-11, R-14."""

import datetime

import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from attendance.models import AttendanceEvent, AttendanceSource
from attendance.services import (
    login_present_days,
    record_login_attendance,
    student_summary,
)
from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment
from liveclasses.models import LiveClass, LiveClassStatus
from liveclasses.services import active_live_class_for_student
from performance.services import batch_performance_cached


def user(username, role, **extra):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE, **extra
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


# ---------- R-04: cancelled class must not open the device-approval window ----------


@pytest.mark.django_db
def test_cancelled_class_does_not_count_as_active(db):
    from django.utils import timezone

    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="B1",
        name="B",
        course=course,
        state=BatchState.ACTIVE,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 1),
    )
    fac = user("prof", Role.FACULTY)
    batch.faculty.add(fac)
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")

    # A class in session *now* but cancelled — must not be treated as active.
    LiveClass.objects.create(
        batch=batch,
        title="Cancelled now",
        scheduled_at=timezone.now() - datetime.timedelta(minutes=10),
        meeting_link="https://meet.example/x",
        status=LiveClassStatus.CANCELLED,
        created_by=fac,
    )
    assert active_live_class_for_student(student) is None


# ---------- R-09: attendance percentage cannot exceed 100 after course end ----------


@pytest.mark.django_db
def test_post_completion_logins_do_not_inflate_attendance():
    course = Course.objects.create(code="FS", name="Full Stack")
    # A short, already-finished batch: 3-day window.
    batch = Batch.objects.create(
        code="B1",
        name="B",
        course=course,
        state=BatchState.COMPLETED,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 1, 3),
    )
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")

    # Log in on all 3 in-window days plus two post-completion days (certificate visits).
    for day in (
        datetime.date(2026, 1, 1),
        datetime.date(2026, 1, 2),
        datetime.date(2026, 1, 3),
        datetime.date(2026, 6, 1),  # after end_date
        datetime.date(2026, 6, 2),
    ):
        AttendanceEvent.objects.create(
            student=student,
            batch=batch,
            source=AttendanceSource.LOGIN,
            reference_id=f"{batch.id}:{day.isoformat()}",
            date=day,
        )

    # Present-days are bounded to the window (3), not 5.
    assert login_present_days(student, batch) == 3
    summary = student_summary(student, batch)
    assert summary["percent"] <= 100


@pytest.mark.django_db
def test_completed_batch_does_not_record_new_login_attendance():
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="B1",
        name="B",
        course=course,
        state=BatchState.COMPLETED,
        start_date=datetime.date(2020, 1, 1),
        end_date=datetime.date(2020, 3, 1),
    )
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")

    created = record_login_attendance(student)
    assert created == 0
    assert not AttendanceEvent.objects.filter(batch=batch, source=AttendanceSource.LOGIN).exists()


# ---------- R-01: forgot-password start does not reveal account existence ----------


@pytest.mark.django_db
def test_forgot_password_start_is_not_an_enumeration_oracle():
    user("realuser", Role.ADMIN, email="real@example.com")
    c = APIClient()

    hit = c.post(
        "/api/v1/auth/password/forgot/", {"identifier": "realuser"}, content_type="application/json"
    )
    miss = c.post(
        "/api/v1/auth/password/forgot/",
        {"identifier": "ghost@example.com"},
        content_type="application/json",
    )
    # Same status and same body keys either way — no existence signal.
    assert hit.status_code == miss.status_code == 200
    assert set(hit.json()) >= {"ok", "token", "email"}
    assert set(miss.json()) >= {"ok", "token", "email"}


# ---------- R-11: batch board is cached (one computation per TTL) ----------


@pytest.mark.django_db
def test_batch_performance_is_cached_within_ttl():
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="B1",
        name="B",
        course=course,
        state=BatchState.ACTIVE,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 1),
    )
    s1 = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=s1, batch=batch, registration_number="S1")

    first = batch_performance_cached(batch)
    assert len(first) == 1
    assert cache.get(f"perf-board:{batch.id}") is not None

    # Add a student after the first (cached) call — the cached board must not change yet.
    s2 = user("S2", Role.STUDENT)
    Enrollment.objects.create(student=s2, batch=batch, registration_number="S2")
    assert len(batch_performance_cached(batch)) == 1  # served from cache


# ---------- R-14: seed_demo repairs a drifted demo account ----------


@pytest.mark.django_db
def test_seed_demo_repairs_drifted_account_role():
    # Simulate drift: admin1 exists but its role was changed to MIS during testing.
    User.objects.create_user(
        username="admin1", password="x", role=Role.MIS, status=UserStatus.SUSPENDED
    )
    # Django's test runner forces DEBUG=False, so the seeder's production guard applies
    # here — pass --force the way a developer seeding a demo box would.
    call_command("seed_demo", "--force")
    admin1 = User.objects.get(username="admin1")
    assert admin1.role == Role.ADMIN
    assert admin1.status == UserStatus.ACTIVE
