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

from django.db import IntegrityError, transaction
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

    # get_or_create (not filter-then-create) so two simultaneous first logins can't both
    # pass the None check and have the second crash on the OneToOne unique constraint —
    # surfaced by the load test. The DB decides the winner; the loser reads the bound row.
    binding, created = DeviceBinding.objects.get_or_create(
        user=student, defaults={"device_id": device_id}
    )
    if created or binding.device_id == device_id:
        return True, ""

    if course_ended:
        return False, "Your course has ended — device changes are closed."

    # During a live class the change is approved by Faculty; outside class hours by MIS.
    from liveclasses.services import active_live_class_for_student

    active = active_live_class_for_student(student)
    # A partial unique index on (user, new_device_id) WHERE status='pending' backs this:
    # get_or_create on its own is check-then-insert, so two tabs (or a retried request)
    # would each see "no pending request" and each raise one — two approval cards for one
    # device. With the constraint the database picks a single winner and get_or_create
    # re-reads the loser's row, so only one notification goes out.
    try:
        _, created = DeviceChangeRequest.objects.get_or_create(
            user=student,
            new_device_id=device_id,
            status=DeviceChangeRequest.Status.PENDING,
            defaults={
                "old_device_id": binding.device_id,
                "during_class": active is not None,
                "class_context": active.title if active else "",
            },
        )
    except IntegrityError:
        # Narrow but real: we lost the insert race and the winning request was approved or
        # rejected before get_or_create could read it back, so its re-``get`` (which filters
        # on status=PENDING) found nothing and re-raised. A request was still raised for this
        # device — treat it as existing rather than 500-ing on the student's login.
        created = False
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


def _claim(request, decided_by, reason: str, new_status: str) -> bool:
    """Move a PENDING request to ``new_status``, returning False if someone else got there first.

    A single conditional UPDATE filtered on ``status=PENDING`` is the whole guarantee: the
    database applies it to one row or none, so exactly one caller can win. That matters
    because the view's earlier "is it pending?" read happened outside any transaction — a
    faculty member and Tech Support clicking at the same moment would both pass it, both
    write a decision, and both notify the student.

    A conditional UPDATE rather than ``select_for_update`` for the claim itself, because it
    holds no lock across the surrounding work and — unlike row locking, which Django silently
    omits on SQLite — it behaves identically on both backends, so the test suite actually
    exercises the guarantee it is asserting.
    """
    claimed = DeviceChangeRequest.objects.filter(
        pk=request.pk, status=DeviceChangeRequest.Status.PENDING
    ).update(
        status=new_status,
        decided_by=decided_by,
        approver_role=decided_by.role,
        approval_reason=reason,
        decided_at=timezone.now(),
        updated_at=timezone.now(),
    )
    if not claimed:
        return False
    # Keep the in-memory instance consistent for the caller's audit record.
    request.refresh_from_db()
    return True


def approve_request(request, decided_by, reason: str = "") -> bool:
    """Approve and bind the device. False if the request was already decided by someone else."""
    with transaction.atomic():
        if not _claim(request, decided_by, reason, DeviceChangeRequest.Status.APPROVED):
            return False
        # select_for_update on the binding: the claim above serialises approvals of *this*
        # request, but the same user could have a second request for a different device being
        # approved concurrently, and both would write the one binding row.
        binding, created = DeviceBinding.objects.select_for_update().get_or_create(
            user=request.user, defaults={"device_id": request.new_device_id}
        )
        if not created:
            binding.device_id = request.new_device_id
            binding.save(update_fields=["device_id", "updated_at"])
    # Outside the transaction on purpose: an email sent inside would still go out if the
    # block rolled back. Only the caller that won the claim reaches here, so the student is
    # notified exactly once.
    notify(
        request.user,
        "device_approved",
        "Your new device was approved — you can sign in now.",
        subject="Device approved",
        channels=("in_app", "email"),
    )
    return True


def reject_request(request, decided_by, reason: str = "") -> bool:
    """Reject the request. False if it was already decided by someone else."""
    if not _claim(request, decided_by, reason, DeviceChangeRequest.Status.REJECTED):
        return False
    notify(
        request.user,
        "device_rejected",
        "Your new-device sign-in request was declined.",
        channels=("in_app",),
    )
    return True
