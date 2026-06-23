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
