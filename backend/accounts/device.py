"""Device policy: first login binds the device; changes need faculty approval.

Per the plan a student is tied to the device they first sign in from. A login from a
new device is blocked and the student's faculty are alerted to approve the change.
(The 'only during a live class' constraint connects fully once live classes land.)
"""

from __future__ import annotations

from django.utils import timezone

from notifications.services import notify, notify_many

from .models import DeviceBinding, DeviceChangeRequest


def _student_faculty(student):
    from core.roles import Role

    from .models import User

    return list(
        User.objects.filter(role=Role.FACULTY, batches__enrollments__student=student).distinct()
    )


def course_ended(student) -> bool:
    """True if the student is enrolled and every one of their batches is completed."""
    from batches.models import BatchState
    from enrollments.models import Enrollment

    states = list(Enrollment.objects.filter(student=student).values_list("batch__state", flat=True))
    return bool(states) and all(s == BatchState.COMPLETED for s in states)


def handle_device_login(student, device_id: str, course_ended: bool = False) -> tuple[bool, str]:
    """Bind on first login; allow on match; otherwise block + raise an approval request.

    After the course ends the bound device still works (so the student can log in to
    enter their Certificate ID), but device *changes* are closed.
    """
    if not device_id:
        return False, "Device identifier missing — please try again."

    binding = DeviceBinding.objects.filter(user=student).first()
    if binding is None:
        DeviceBinding.objects.create(user=student, device_id=device_id)
        return True, ""
    if binding.device_id == device_id:
        return True, ""

    if course_ended:
        return False, "Your course has ended — device changes are closed."

    request, created = DeviceChangeRequest.objects.get_or_create(
        user=student,
        new_device_id=device_id,
        status=DeviceChangeRequest.Status.PENDING,
    )
    if created:
        notify_many(
            _student_faculty(student),
            "new_device",
            f"{student.full_name or student.username} tried to sign in from a new device — "
            "approval needed.",
            subject="New-device sign-in",
            channels=("in_app", "email"),
        )
    return (
        False,
        "This is a new device. Your faculty must approve the change before you can sign in here.",
    )


def approve_request(request, decided_by) -> None:
    binding, _ = DeviceBinding.objects.get_or_create(
        user=request.user, defaults={"device_id": request.new_device_id}
    )
    binding.device_id = request.new_device_id
    binding.save(update_fields=["device_id", "updated_at"])
    request.status = DeviceChangeRequest.Status.APPROVED
    request.decided_by = decided_by
    request.decided_at = timezone.now()
    request.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
    notify(
        request.user,
        "device_approved",
        "Your new device was approved — you can sign in now.",
        subject="Device approved",
        channels=("in_app", "email"),
    )


def reject_request(request, decided_by) -> None:
    request.status = DeviceChangeRequest.Status.REJECTED
    request.decided_by = decided_by
    request.decided_at = timezone.now()
    request.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
    notify(
        request.user,
        "device_rejected",
        "Your new-device sign-in request was declined.",
        channels=("in_app",),
    )
