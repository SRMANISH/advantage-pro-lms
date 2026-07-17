"""Escalation rules: incomplete tests and the 50%-attendance rule.

Run on demand (MIS/Admin button) or via the ``run_escalations`` management command
(wired to the scheduler adapter in production). Each alert fires at most once.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from .models import Escalation


def _escalate_incomplete_tests() -> int:
    from accounts.models import User
    from assessments.models import Test, TestAttempt
    from batches.models import BatchState
    from core.roles import Role
    from notifications.services import notify, notify_many

    now = timezone.now()
    mis = list(User.objects.filter(role=Role.MIS))
    tests = (
        Test.objects.filter(batch__state=BatchState.ACTIVE)
        .filter(Q(open_at__isnull=True) | Q(open_at__lte=now))
        .select_related("batch")
    )
    count = 0
    new_rows = []
    for test in tests:
        faculty = list(test.batch.faculty.all())
        attempted = set(TestAttempt.objects.filter(test=test).values_list("student_id", flat=True))
        # One query for who's already been escalated for this test (was a get_or_create
        # per student — the ledger write is now a single bulk_create below).
        already = set(
            Escalation.objects.filter(
                kind="test_incomplete", reference_id=str(test.id)
            ).values_list("student_id", flat=True)
        )
        students = User.objects.filter(role=Role.STUDENT, enrollments__batch=test.batch).distinct()
        for student in students:
            if student.id in attempted or student.id in already:
                continue
            new_rows.append(
                Escalation(
                    kind="test_incomplete",
                    student=student,
                    reference_id=str(test.id),
                    batch=test.batch,
                )
            )
            notify(
                student,
                "test_incomplete",
                f"Reminder: you have not completed the test '{test.title}'.",
                link="/student/tests",
                subject="Incomplete test",
                channels=("in_app", "email"),
            )
            notify_many(
                faculty + mis,
                "test_incomplete_staff",
                f"{student.full_name or student.username} has not completed '{test.title}'.",
                channels=("in_app",),
            )
            count += 1
    # ignore_conflicts keeps overlapping runs from crashing on the unique constraint.
    Escalation.objects.bulk_create(new_rows, ignore_conflicts=True)
    return count


def _escalate_low_attendance() -> int:
    from accounts.models import User
    from attendance.services import batch_attendance_summaries
    from batches.models import Batch, BatchState
    from core.roles import Role
    from notifications.services import notify_many

    mis = list(User.objects.filter(role=Role.MIS))
    counselors = list(User.objects.filter(role=Role.COUNSELOR))
    count = 0
    new_rows = []
    for batch in Batch.objects.filter(state=BatchState.ACTIVE):
        faculty = list(batch.faculty.all())
        students = list(User.objects.filter(role=Role.STUDENT, enrollments__batch=batch).distinct())
        summaries = batch_attendance_summaries(batch, students)  # one query for the batch
        already = set(
            Escalation.objects.filter(
                kind="low_attendance", reference_id=str(batch.id)
            ).values_list("student_id", flat=True)
        )
        for student in students:
            summary = summaries.get(student.id, {"total": 0, "percent": 0})
            if summary["total"] == 0 or summary["percent"] >= 50:
                continue
            if student.id in already:
                continue
            new_rows.append(
                Escalation(
                    kind="low_attendance",
                    student=student,
                    reference_id=str(batch.id),
                    batch=batch,
                )
            )
            notify_many(
                faculty + counselors + mis,
                "low_attendance",
                f"{student.full_name or student.username} is below 50% attendance in "
                f"{batch.code} ({summary['percent']}%).",
                subject="Low attendance",
                channels=("in_app", "email"),
            )
            count += 1
    Escalation.objects.bulk_create(new_rows, ignore_conflicts=True)
    return count


def run_escalations() -> dict:
    return {
        "test_reminders": _escalate_incomplete_tests(),
        "attendance_alerts": _escalate_low_attendance(),
    }
