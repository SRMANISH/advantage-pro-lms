"""Faculty schedule conflict detection ("faculty already occupied").

A faculty cannot be assigned to a batch whose weekly class slot clashes with another
non-completed batch they already teach. Two slots clash when they share at least one
weekday AND their time windows overlap. Completed batches never conflict (they no longer
run).
"""

from __future__ import annotations

from .models import Batch, BatchState


def _times_overlap(a_start, a_end, b_start, b_end) -> bool:
    """Half-open interval overlap; missing times are treated as non-conflicting."""
    if not (a_start and a_end and b_start and b_end):
        return False
    return a_start < b_end and b_start < a_end


def faculty_schedule_conflicts(faculty, class_days, start_time, end_time, exclude_batch=None):
    """Return the codes of non-completed batches this faculty teaches whose weekly slot
    clashes with the given (days, start, end). Empty list means the faculty is free.

    Batches without a full schedule (legacy rows, or the target still being set up) can't
    clash and are skipped.
    """
    if not (class_days and start_time and end_time):
        return []
    wanted_days = set(class_days)
    qs = (
        Batch.objects.filter(faculty=faculty)
        .exclude(state=BatchState.COMPLETED)
        .exclude(class_start_time__isnull=True)
    )
    if exclude_batch is not None:
        qs = qs.exclude(id=exclude_batch.id)
    conflicts = []
    for other in qs:
        if wanted_days & set(other.class_days or []) and _times_overlap(
            start_time, end_time, other.class_start_time, other.class_end_time
        ):
            conflicts.append(other.code)
    return conflicts
