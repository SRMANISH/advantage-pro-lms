"""Batch-access helpers shared by content endpoints."""

from batches.models import Batch
from core.roles import Role
from enrollments.models import Enrollment

STAFF = {Role.SUPER_ADMIN, Role.ADMIN, Role.MIS}


def can_access_batch(user, batch: Batch) -> bool:
    if user.role in STAFF:
        return True
    if user.role == Role.FACULTY:
        return batch.faculty.filter(id=user.id).exists()
    if user.role == Role.STUDENT:
        return Enrollment.objects.filter(student=user, batch=batch).exists()
    return False


def accessible_batch_ids(user):
    """Return None for 'all batches', else an iterable of allowed batch ids."""
    if user.role in STAFF:
        return None
    if user.role == Role.FACULTY:
        return Batch.objects.filter(faculty=user).values_list("id", flat=True)
    if user.role == Role.STUDENT:
        return Enrollment.objects.filter(student=user).values_list("batch_id", flat=True)
    return []


def is_video_blocked(student, batch) -> bool:
    """True if the student's video/material access to ``batch`` has been revoked
    (individually by MIS) or closed at course end (by Admin/MIS)."""
    from django.db.models import Q

    from .models import VideoAccessRevocation

    return VideoAccessRevocation.objects.filter(
        Q(student=student, batch__isnull=True)
        | Q(student=student, batch=batch)
        | Q(student__isnull=True, batch=batch)
    ).exists()
