"""Device policy: first-login bind, new-device block + approval, course-end closure."""

import datetime

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.device import handle_device_login
from accounts.models import DeviceBinding, DeviceChangeRequest, User, UserStatus
from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment
from liveclasses.models import LiveClass

LOGIN = "/api/v1/auth/login/"
REQUESTS = "/api/v1/auth/devices/requests/"


def active_class(batch):
    """A live class in session right now for the batch."""
    return LiveClass.objects.create(
        batch=batch,
        title="Live Now",
        scheduled_at=timezone.now(),
        meeting_link="https://meet.example.com/now",
    )


def decide(staff, req_id, decision="approve", reason=""):
    c = APIClient()
    c.force_authenticate(user=staff)
    return c.post(
        f"{REQUESTS}{req_id}/decide/", {"decision": decision, "reason": reason}, format="json"
    )


def mis_user():
    return User.objects.create_user(
        username="mis", password="x", role=Role.MIS, status=UserStatus.ACTIVE
    )


def make_student(username="stu", password="x"):
    return User.objects.create_user(
        username=username, password=password, role=Role.STUDENT, status=UserStatus.ACTIVE
    )


def login(username, device_id, password="x"):
    return APIClient().post(
        LOGIN,
        {"username": username, "password": password, "role": Role.STUDENT, "device_id": device_id},
        format="json",
    )


@pytest.fixture
def world(db):
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="B1",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 4, 1),
        state=BatchState.ACTIVE,
    )
    fac = User.objects.create_user(
        username="fac", password="x", role=Role.FACULTY, status=UserStatus.ACTIVE
    )
    batch.faculty.add(fac)
    student = make_student()
    Enrollment.objects.create(student=student, batch=batch, registration_number="stu")
    return {"batch": batch, "fac": fac, "student": student}


@pytest.mark.django_db
def test_first_login_binds_device(world):
    assert login("stu", "device-A").status_code == 200
    # Same device works again.
    assert login("stu", "device-A").status_code == 200


@pytest.mark.django_db
def test_first_bind_is_race_safe(world):
    """The load test hit an IntegrityError when two first-logins from the same device
    raced the OneToOne bind. get_or_create means the second resolves to the same row —
    both succeed, exactly one binding exists (no 500)."""
    from accounts.device import handle_device_login
    from accounts.models import DeviceBinding

    ok1, _ = handle_device_login(world["student"], "device-A")
    ok2, _ = handle_device_login(world["student"], "device-A")
    assert ok1 and ok2
    assert DeviceBinding.objects.filter(user=world["student"]).count() == 1


@pytest.mark.django_db
def test_new_device_is_blocked_and_raises_request(world):
    assert login("stu", "device-A").status_code == 200
    resp = login("stu", "device-B")
    assert resp.status_code == 403
    assert "new device" in resp.json()["detail"].lower()
    assert DeviceChangeRequest.objects.filter(user=world["student"], status="pending").exists()


@pytest.mark.django_db
def test_faculty_approves_during_live_class(world):
    login("stu", "device-A")
    active_class(world["batch"])  # a class is in session
    login("stu", "device-B")  # raised during class -> routed to faculty
    req = DeviceChangeRequest.objects.get(user=world["student"], status="pending")
    assert req.during_class is True

    decided = decide(world["fac"], req.id, reason="Verified in class")
    assert decided.status_code == 200
    req.refresh_from_db()
    assert req.approver_role == Role.FACULTY
    assert login("stu", "device-B").status_code == 200


@pytest.mark.django_db
def test_faculty_cannot_approve_outside_class(world):
    login("stu", "device-A")
    login("stu", "device-B")  # no class in session
    req = DeviceChangeRequest.objects.get(user=world["student"], status="pending")
    assert decide(world["fac"], req.id).status_code == 403


@pytest.mark.django_db
def test_mis_approves_outside_class(world):
    login("stu", "device-A")
    login("stu", "device-B")  # no class in session -> routed to MIS
    req = DeviceChangeRequest.objects.get(user=world["student"], status="pending")
    assert req.during_class is False

    assert decide(mis_user(), req.id).status_code == 200
    assert login("stu", "device-B").status_code == 200


@pytest.mark.django_db
def test_mis_cannot_approve_during_class(world):
    login("stu", "device-A")
    active_class(world["batch"])
    login("stu", "device-B")
    req = DeviceChangeRequest.objects.get(user=world["student"], status="pending")
    assert decide(mis_user(), req.id).status_code == 403


@pytest.mark.django_db
def test_faculty_only_sees_their_students_requests(world):
    login("stu", "device-A")
    login("stu", "device-B")
    fac_client = APIClient()
    fac_client.force_authenticate(user=world["fac"])
    resp = fac_client.get(REQUESTS)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    other_fac = User.objects.create_user(
        username="fac2", password="x", role=Role.FACULTY, status=UserStatus.ACTIVE
    )
    other_client = APIClient()
    other_client.force_authenticate(user=other_fac)
    assert other_client.get(REQUESTS).json() == []


@pytest.mark.django_db
def test_course_end_blocks_device_change_but_not_bound_device(world):
    assert login("stu", "device-A").status_code == 200  # bind
    world["batch"].state = BatchState.COMPLETED
    world["batch"].save()
    # Bound device still works (to enter the Certificate ID).
    assert login("stu", "device-A").status_code == 200
    # But a device change is closed after course end.
    resp = login("stu", "device-B")
    assert resp.status_code == 403
    assert "ended" in resp.json()["detail"].lower()


# --------------------------- concurrency ---------------------------
# The application calls get_or_create, but that is check-then-insert: two tabs, a retried
# request, or two workers can each see "no pending request" and each raise one, producing
# two approval cards for one device. The guarantee therefore lives in a partial unique
# index on (user, new_device_id) WHERE status='pending'.


def _bound_student(username="devrace"):
    """A student with a device already bound, so the next login is a *change* request."""
    student = User.objects.create_user(
        username=username, password="x", role=Role.STUDENT, status=UserStatus.ACTIVE
    )
    DeviceBinding.objects.create(user=student, device_id="original-device")
    return student


@pytest.mark.django_db
def test_overlapping_new_device_logins_collapse_into_one_request():
    student = _bound_student()

    first = handle_device_login(student, "new-device")
    second = handle_device_login(student, "new-device")

    assert first[0] is False and second[0] is False  # both blocked, as they must be
    assert (
        DeviceChangeRequest.objects.filter(
            user=student, new_device_id="new-device", status=DeviceChangeRequest.Status.PENDING
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_database_refuses_a_second_pending_request_for_the_same_device():
    """The real assertion: the constraint is enforced by the database, not by app logic.

    Without this, the test above would still pass on the strength of get_or_create alone
    and the race would remain wide open under genuine concurrency.
    """
    student = _bound_student("devrace2")
    DeviceChangeRequest.objects.create(
        user=student, new_device_id="dup", status=DeviceChangeRequest.Status.PENDING
    )
    # atomic() so the failed insert rolls back to a savepoint instead of poisoning the
    # surrounding test transaction.
    with pytest.raises(IntegrityError), transaction.atomic():
        DeviceChangeRequest.objects.create(
            user=student, new_device_id="dup", status=DeviceChangeRequest.Status.PENDING
        )


@pytest.mark.django_db
def test_a_rejected_device_can_be_requested_again():
    """The constraint is scoped to PENDING on purpose — a student whose request was declined
    (wrong moment, approver unavailable) must be able to ask again, and the historical
    decided rows must stay on file for audit."""
    student = _bound_student("devrace3")
    DeviceChangeRequest.objects.create(
        user=student, new_device_id="retry", status=DeviceChangeRequest.Status.REJECTED
    )

    allowed, message = handle_device_login(student, "retry")

    assert allowed is False and message  # still blocked pending approval
    assert DeviceChangeRequest.objects.filter(user=student, new_device_id="retry").count() == 2
    assert DeviceChangeRequest.objects.filter(
        user=student, new_device_id="retry", status=DeviceChangeRequest.Status.PENDING
    ).exists()


@pytest.mark.django_db
def test_losing_the_insert_race_does_not_break_the_login(monkeypatch):
    """The narrow window get_or_create cannot absorb: we lose the insert, and by the time it
    re-reads the winning row that request has already been decided — so its status=PENDING
    lookup finds nothing and the IntegrityError surfaces. The student must still get the
    ordinary 'pending approval' message rather than a 500."""
    student = _bound_student("devrace4")

    def boom(*args, **kwargs):
        raise IntegrityError("duplicate key value violates unique constraint")

    monkeypatch.setattr(DeviceChangeRequest.objects, "get_or_create", boom)

    allowed, message = handle_device_login(student, "raced-device")

    assert allowed is False
    assert "approve" in message.lower()
