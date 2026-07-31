"""Read-modify-write paths that two people can hit at once.

A caveat that shapes every test here: **``select_for_update`` is a silent no-op on SQLite.**
Django omits the ``FOR UPDATE`` clause rather than raising, so the local suite cannot prove
the lock itself — only PostgreSQL, which production runs, actually serialises those rows.

That is exactly why the two paths where a duplicate is user-visible (a device decision, a
weekly certificate chase-up) are guarded by *conditional UPDATEs* instead: one statement the
database applies to one row or none, identical on both backends, and therefore genuinely
exercised below.
"""

import datetime

import pytest
from django.utils import timezone

from accounts.device import approve_request, reject_request
from accounts.models import DeviceBinding, DeviceChangeRequest
from attendance.models import FollowUpStatus
from attendance.services import set_followup
from batches.models import Batch, BatchState, Course
from certification.models import CertificateFollowUp
from certification.services import run_certificate_reminders
from core.roles import Role
from enrollments.models import Enrollment
from notifications.models import Notification

from .helpers import client_for, user

# --------------------------- device decisions ---------------------------


@pytest.fixture
def pending_request(db):
    student = user("race_stu", Role.STUDENT)
    DeviceBinding.objects.create(user=student, device_id="old-device")
    req = DeviceChangeRequest.objects.create(
        user=student,
        new_device_id="new-device",
        old_device_id="old-device",
        status=DeviceChangeRequest.Status.PENDING,
    )
    return req


@pytest.mark.django_db
def test_only_the_first_decision_wins(pending_request):
    """Two approvers acting on the same request: the second must be told, not silently
    overwrite the first — and the student must not be notified twice."""
    first = user("race_ts1", Role.TECH_SUPPORT)
    second = user("race_ts2", Role.TECH_SUPPORT)

    assert approve_request(pending_request, first, "ok") is True
    # `pending_request` is now a stale in-memory copy, exactly as a concurrent request holds.
    assert approve_request(pending_request, second, "also ok") is False

    pending_request.refresh_from_db()
    assert pending_request.decided_by_id == first.id  # first decision stands
    assert (
        Notification.objects.filter(recipient=pending_request.user, kind="device_approved").count()
        == 1
    )


@pytest.mark.django_db
def test_reject_cannot_overturn_an_approval(pending_request):
    """The dangerous direction: a late reject must not undo a completed approval, which would
    leave the student bound to a device their record says was refused."""
    approver = user("race_ap", Role.TECH_SUPPORT)
    rejecter = user("race_rj", Role.TECH_SUPPORT)

    assert approve_request(pending_request, approver, "") is True
    assert reject_request(pending_request, rejecter, "too late") is False

    pending_request.refresh_from_db()
    assert pending_request.status == DeviceChangeRequest.Status.APPROVED
    assert DeviceBinding.objects.get(user=pending_request.user).device_id == "new-device"


@pytest.mark.django_db
def test_the_api_reports_a_conflict_rather_than_pretending_it_worked(pending_request):
    staff = user("race_ts3", Role.TECH_SUPPORT)
    other = user("race_ts4", Role.TECH_SUPPORT)
    url = f"/api/v1/auth/devices/requests/{pending_request.id}/decide/"

    first = client_for(staff).post(url, {"decision": "approve"}, format="json")
    assert first.status_code == 200

    second = client_for(other).post(url, {"decision": "reject"}, format="json")
    # 404 (the queryset filters on PENDING) or 409 (it got past that and lost the claim) are
    # both honest answers; silently reporting success is not.
    assert second.status_code in (404, 409), second.content


@pytest.mark.django_db
def test_an_invalid_decision_is_rejected_before_anything_is_claimed(pending_request):
    staff = user("race_ts5", Role.TECH_SUPPORT)
    resp = client_for(staff).post(
        f"/api/v1/auth/devices/requests/{pending_request.id}/decide/",
        {"decision": "maybe"},
        format="json",
    )
    assert resp.status_code == 400
    pending_request.refresh_from_db()
    assert pending_request.status == DeviceChangeRequest.Status.PENDING  # untouched


# --------------------------- certificate reminders ---------------------------


@pytest.fixture
def uncertified(db):
    course = Course.objects.create(code="RC", name="RC")
    batch = Batch.objects.create(
        code="RC-1",
        name="RC-1",
        course=course,
        start_date=datetime.date.today() - datetime.timedelta(days=60),
        end_date=datetime.date.today() - datetime.timedelta(days=1),
        state=BatchState.COMPLETED,
    )
    student = user("race_cert", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="race_cert")
    return student


@pytest.mark.django_db
def test_overlapping_reminder_runs_send_once(uncertified):
    """The regression test. Both runs happen inside the same week, as a retried cron would."""
    assert run_certificate_reminders() == 1
    assert run_certificate_reminders() == 0

    assert (
        Notification.objects.filter(recipient=uncertified, kind="certificate_pending").count() == 1
    )
    followup = CertificateFollowUp.objects.get(enrollment__student=uncertified)
    assert followup.reminder_count == 1


@pytest.mark.django_db
def test_the_claim_survives_the_notification_row_being_deleted(uncertified):
    """The dedup must live in the claim, not in "have we got a notification for this?"."""
    assert run_certificate_reminders() == 1
    Notification.objects.filter(recipient=uncertified).delete()
    assert run_certificate_reminders() == 0


@pytest.mark.django_db
def test_a_reminder_is_sent_again_once_the_week_has_passed(uncertified):
    assert run_certificate_reminders() == 1

    followup = CertificateFollowUp.objects.get(enrollment__student=uncertified)
    CertificateFollowUp.objects.filter(pk=followup.pk).update(
        last_reminder_at=timezone.now() - datetime.timedelta(days=8)
    )

    assert run_certificate_reminders() == 1
    followup.refresh_from_db()
    assert followup.reminder_count == 2  # incremented in the database, not read-modify-written


# --------------------------- absence follow-up ---------------------------


@pytest.mark.django_db
def test_set_followup_upserts_without_losing_the_note(db):
    course = Course.objects.create(code="RF", name="RF")
    batch = Batch.objects.create(
        code="RF-1",
        name="RF-1",
        course=course,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=30),
        state=BatchState.ACTIVE,
    )
    student = user("race_fu", Role.STUDENT)
    counselor = user("race_co", Role.COUNSELOR)

    set_followup(student, batch, FollowUpStatus.CONTACTED, owner=counselor, note="Called once")
    again = set_followup(student, batch, FollowUpStatus.RESOLVED)

    assert again.status == FollowUpStatus.RESOLVED
    assert again.note == "Called once"  # an empty note must not blank an existing one
    assert again.owner_id == counselor.id  # nor should omitting owner clear it
