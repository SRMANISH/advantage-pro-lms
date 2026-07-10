"""Device policy: first login binds the device; changes need approval.

A student is tied to the device they first sign in from. A login from a new device is
blocked and raises an approval request: during one of the student's live classes, their
Faculty approve it; outside class hours, MIS does. After the student's course ends, the
bound device still works (so they can sign in to look up their Certificate ID), but
device *changes* are closed for good.

On the identifier: a web app *cannot* read a device's hardware MAC address — browsers
deliberately don't expose it. So a device is identified by a stable browser fingerprint
(`device_id`, a FingerprintJS visitorId sent by the client), and the client IP is
captured on the login/approval audit rows for network context. This is a strong
deterrent against casual account sharing, not a hardware-level lock.
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


def _tech_support_users():
    from core.roles import Role

    from .models import User

    return list(User.objects.filter(role=Role.TECH_SUPPORT))


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

    # During a live class the change is approved by Faculty; outside class hours by MIS.
    from liveclasses.services import active_live_class_for_student

    active = active_live_class_for_student(student)
    request, created = DeviceChangeRequest.objects.get_or_create(
        user=student,
        new_device_id=device_id,
        status=DeviceChangeRequest.Status.PENDING,
        defaults={
            "old_device_id": binding.device_id,
            "during_class": active is not None,
            "class_context": active.title if active else "",
        },
    )
    if created:
        who = student.full_name or student.username
        if active:
            notify_many(
                _student_faculty(student),
                "new_device",
                f"{who} tried to sign in from a new device during '{active.title}' — "
                "approve the change during class.",
                subject="New-device sign-in (during class)",
                channels=("in_app", "email"),
            )
            return (
                False,
                "This is a new device. Your faculty can approve the change during the live class.",
            )
        # Outside class hours the notification goes to Tech Support (procedure update:
        # MIS receives no device notifications; they retain silent approval capability).
        notify_many(
            _tech_support_users(),
            "new_device",
            f"{who} tried to sign in from a new device outside class hours — approval needed.",
            subject="New-device sign-in",
            channels=("in_app", "email"),
        )
    return (
        False,
        "This is a new device. Tech Support must approve the change before you can sign in "
        "here (or your faculty, during a live class).",
    )


def approve_request(request, decided_by, reason: str = "") -> None:
    binding, _ = DeviceBinding.objects.get_or_create(
        user=request.user, defaults={"device_id": request.new_device_id}
    )
    binding.device_id = request.new_device_id
    binding.save(update_fields=["device_id", "updated_at"])
    request.status = DeviceChangeRequest.Status.APPROVED
    request.decided_by = decided_by
    request.approver_role = decided_by.role
    request.approval_reason = reason
    request.decided_at = timezone.now()
    request.save(
        update_fields=[
            "status",
            "decided_by",
            "approver_role",
            "approval_reason",
            "decided_at",
            "updated_at",
        ]
    )
    notify(
        request.user,
        "device_approved",
        "Your new device was approved — you can sign in now.",
        subject="Device approved",
        channels=("in_app", "email"),
    )


def reject_request(request, decided_by, reason: str = "") -> None:
    request.status = DeviceChangeRequest.Status.REJECTED
    request.decided_by = decided_by
    request.approver_role = decided_by.role
    request.approval_reason = reason
    request.decided_at = timezone.now()
    request.save(
        update_fields=[
            "status",
            "decided_by",
            "approver_role",
            "approval_reason",
            "decided_at",
            "updated_at",
        ]
    )
    notify(
        request.user,
        "device_rejected",
        "Your new-device sign-in request was declined.",
        channels=("in_app",),
    )
