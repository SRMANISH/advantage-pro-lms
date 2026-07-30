"""Cron overlap guard: concurrent runs of the same job don't double-fire."""

import datetime

import pytest
from django.core.management import call_command

from batches.models import Batch, BatchState, Course
from core.cron import LockHeld, cron_lock
from core.roles import Role
from enrollments.models import Enrollment
from escalations.models import Escalation
from escalations.services import run_escalations

from .helpers import user


@pytest.mark.django_db
def test_cron_lock_blocks_concurrent_holder():
    with cron_lock("some_job"):
        with pytest.raises(LockHeld):
            with cron_lock("some_job"):
                pass  # pragma: no cover - must raise before entering


@pytest.mark.django_db
def test_cron_lock_releases_after_the_block():
    with cron_lock("some_job"):
        pass
    with cron_lock("some_job"):  # does not raise — released cleanly
        pass


@pytest.mark.django_db
def test_management_command_skips_quietly_when_locked(capsys):
    with cron_lock("run_escalations"):
        call_command("run_escalations")
    out = capsys.readouterr().out
    assert "already running" in out


@pytest.mark.django_db
def test_escalation_ledger_bulk_create_is_race_safe():
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="FS-1",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 6, 1),
    )
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")

    # The batched ledger writes via bulk_create(ignore_conflicts=True); a second
    # "overlapping" run inserting the same (kind, student, reference_id) must not raise
    # IntegrityError and must not create a duplicate row.
    rows = [
        Escalation(kind="low_attendance", student=student, reference_id=str(batch.id), batch=batch)
    ]
    Escalation.objects.bulk_create(rows, ignore_conflicts=True)
    Escalation.objects.bulk_create(
        [Escalation(kind="low_attendance", student=student, reference_id=str(batch.id))],
        ignore_conflicts=True,
    )
    assert (
        Escalation.objects.filter(
            kind="low_attendance", student=student, reference_id=str(batch.id)
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_run_escalations_is_idempotent_across_back_to_back_runs():
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="FS-1",
        name="B",
        course=course,
        state=BatchState.ACTIVE,
        start_date=datetime.date(2020, 1, 1),  # long elapsed window -> attendance well below 50%
        end_date=datetime.date(2026, 6, 1),
    )
    student = user("S1", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="S1")
    user("mis", Role.MIS)

    first = run_escalations()
    second = run_escalations()
    assert first["attendance_alerts"] == 1
    assert second["attendance_alerts"] == 0  # already escalated — no duplicate, no crash
