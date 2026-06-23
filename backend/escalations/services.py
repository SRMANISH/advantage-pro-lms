"""Escalation rules: incomplete tests and the 50%-attendance rule.

Run on demand (MIS/Admin button) or via the ``run_escalations`` management command
(wired to the scheduler adapter in production). Each alert fires at most once.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from .models import Escalation


def _already(kind: str, student, ref) -> bool:
    return Escalation.objects.filter(kind=kind, student=student, reference_id=str(ref)).exists()


def _mark(kind: str, student, ref) -> None:
    Escalation.objects.create(kind=kind, student=student, reference_id=str(ref))


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
    for test in tests:
        faculty = list(test.batch.faculty.all())
        attempted = set(TestAttempt.objects.filter(test=test).values_list("student_id", flat=True))
        students = User.objects.filter(role=Role.STUDENT, enrollments__batch=test.batch).distinct()
        for student in students:
            if student.id in attempted or _already("test_incomplete", student, test.id):
                continue
            _mark("test_incomplete", student, test.id)
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
    return count


def _escalate_low_attendance() -> int:
    from accounts.models import User
    from attendance.services import student_summary
    from batches.models import Batch, BatchState
    from core.roles import Role
    from notifications.services import notify_many

    mis = list(User.objects.filter(role=Role.MIS))
    counselors = list(User.objects.filter(role=Role.COUNSELOR))
    count = 0
    for batch in Batch.objects.filter(state=BatchState.ACTIVE):
        faculty = list(batch.faculty.all())
        students = User.objects.filter(role=Role.STUDENT, enrollments__batch=batch).distinct()
        for student in students:
            summary = student_summary(student, batch)
            if summary["total"] == 0 or summary["percent"] >= 50:
                continue
            if _already("low_attendance", student, batch.id):
                continue
            _mark("low_attendance", student, batch.id)
            notify_many(
                faculty + counselors + mis,
                "low_attendance",
                f"{student.full_name or student.username} is below 50% attendance in "
                f"{batch.code} ({summary['percent']}%).",
                subject="Low attendance",
                channels=("in_app", "email"),
            )
            count += 1
    return count


def run_escalations() -> dict:
    return {
        "test_reminders": _escalate_incomplete_tests(),
        "attendance_alerts": _escalate_low_attendance(),
    }
