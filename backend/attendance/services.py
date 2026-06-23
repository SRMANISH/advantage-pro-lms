"""Recording and aggregating attendance."""

from __future__ import annotations

from django.utils import timezone

from .models import AttendanceEvent


def record_attendance(student, batch, source: str, reference_id) -> None:
    """Idempotent: re-watching a video / re-counting an item won't double-count."""
    AttendanceEvent.objects.get_or_create(
        student=student,
        source=source,
        reference_id=str(reference_id),
        defaults={"batch": batch, "date": timezone.now().date()},
    )


def batch_total_opportunities(batch) -> int:
    """Total markable items in a batch: videos + tests + tasks (+ live classes later)."""
    from assessments.models import Task, Test
    from content.models import Video

    total = (
        Video.objects.filter(batch=batch).count()
        + Test.objects.filter(batch=batch).count()
        + Task.objects.filter(batch=batch).count()
    )
    try:
        from liveclasses.models import LiveClass

        total += LiveClass.objects.filter(batch=batch).count()
    except ImportError:
        pass
    return total


def student_summary(student, batch) -> dict:
    present = AttendanceEvent.objects.filter(student=student, batch=batch).count()
    total = batch_total_opportunities(batch)
    return {
        "present": present,
        "total": total,
        "percent": round(present / total * 100) if total else 0,
    }
