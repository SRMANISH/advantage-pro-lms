"""Smoke tests for the scheduled command entrypoints.

The underlying services are tested in their own modules; these cover the thin management
commands themselves — the code cron actually invokes in production, which previously had
no coverage at all. Each asserts the command runs, reports, and honours the cron lock.
"""

import datetime
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from accounts.models import User, UserStatus
from attendance.models import AttendanceEvent, AttendanceSource
from audit.models import AuditLog
from batches.models import Batch, BatchState, Course
from core.cron import cron_lock
from core.roles import Role
from enrollments.models import Enrollment
from liveclasses.models import LiveClass
from notifications.models import Notification

# Every scheduled command, with the lock name it takes. run_escalations is covered in
# test_cron_lock.py; the rest had 0% coverage before this file.
COMMANDS = [
    ("send_due_reminders", "send_due_reminders"),
    ("send_absence_reminders", "send_absence_reminders"),
    ("send_certificate_reminders", "send_certificate_reminders"),
    ("send_engagement_reminders", "send_engagement_reminders"),
    ("purge_old_data", "purge_old_data"),
]


def run(command: str, *args) -> str:
    out = StringIO()
    call_command(command, *args, stdout=out)
    return out.getvalue()


@pytest.fixture
def world(db):
    """A live batch with one enrolled student — enough for every command to do real work."""
    course = Course.objects.create(code="FS", name="Full Stack")
    today = timezone.localdate()
    batch = Batch.objects.create(
        code="FS-1",
        name="B",
        course=course,
        state=BatchState.ACTIVE,
        start_date=today - datetime.timedelta(days=10),
        end_date=today + datetime.timedelta(days=30),
    )
    student = User.objects.create_user(
        username="S1", password="x", role=Role.STUDENT, status=UserStatus.ACTIVE
    )
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")
    return {"batch": batch, "student": student}


@pytest.mark.parametrize("command,_lock", COMMANDS)
@pytest.mark.django_db
def test_command_runs_and_reports(world, command, _lock):
    output = run(command)
    assert output.strip(), f"{command} produced no output"


@pytest.mark.parametrize("command,lock", COMMANDS)
@pytest.mark.django_db
def test_command_skips_quietly_when_lock_is_held(world, command, lock):
    """Overlapping cron runs must skip, not double-fire."""
    with cron_lock(lock):
        output = run(command)
    assert "already running" in output.lower()


@pytest.mark.django_db
def test_send_due_reminders_sends_for_a_class_starting_within_the_hour(world):
    LiveClass.objects.create(
        batch=world["batch"],
        title="Hooks",
        scheduled_at=timezone.now() + datetime.timedelta(minutes=50),
        meeting_link="https://meet.example.com/x",
    )
    output = run("send_due_reminders")
    assert "reminder" in output.lower()
    assert Notification.objects.filter(recipient=world["student"]).exists()


@pytest.mark.django_db
def test_send_absence_reminders_notifies_a_student_who_did_not_log_in(world):
    output = run("send_absence_reminders")
    assert "reminder" in output.lower()
    assert Notification.objects.filter(recipient=world["student"], kind="absence_reminder").exists()

    # Idempotent: a student who has logged in today is not chased.
    Notification.objects.all().delete()
    AttendanceEvent.objects.create(
        student=world["student"],
        batch=world["batch"],
        source=AttendanceSource.LOGIN,
        date=timezone.localdate(),
        reference_id=str(timezone.localdate()),
    )
    run("send_absence_reminders")
    assert not Notification.objects.filter(
        recipient=world["student"], kind="absence_reminder"
    ).exists()


@pytest.mark.django_db
def test_purge_old_data_dry_run_reports_without_deleting(world):
    AuditLog.objects.create(actor=world["student"], action="ancient_action")
    AuditLog.objects.update(created_at=timezone.now() - datetime.timedelta(days=5000))

    dry = run("purge_old_data", "--dry-run")
    assert "would purge" in dry.lower()
    assert AuditLog.objects.count() == 1, "--dry-run must not delete"

    real = run("purge_old_data")
    assert "purged" in real.lower()
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db
def test_purge_old_data_never_touches_academic_records(world):
    """Retention removes activity data only — enrolments and attendance must survive."""
    AttendanceEvent.objects.create(
        student=world["student"],
        batch=world["batch"],
        source=AttendanceSource.LOGIN,
        date=timezone.localdate() - datetime.timedelta(days=4000),
        reference_id="old",
    )
    AttendanceEvent.objects.update(created_at=timezone.now() - datetime.timedelta(days=5000))

    run("purge_old_data")

    assert AttendanceEvent.objects.count() == 1
    assert Enrollment.objects.count() == 1
