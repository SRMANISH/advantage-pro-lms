"""Data retention: purge old activity data, never academic/legal records."""

import datetime

import pytest
from django.utils import timezone

from accounts.models import User, UserStatus
from audit.models import AuditLog
from certification.models import Certificate
from core.retention import purge_old_data
from notifications.models import Notification


def _age(obj, days):
    """Backdate created_at (auto_now_add) on an already-saved row."""
    type(obj).objects.filter(pk=obj.pk).update(
        created_at=timezone.now() - datetime.timedelta(days=days)
    )


@pytest.mark.django_db
def test_purge_removes_old_audit_and_read_notifications():
    user = User.objects.create_user(
        username="stu", password="x", role="student", status=UserStatus.ACTIVE
    )
    old_audit = AuditLog.objects.create(action="login_success")
    _age(old_audit, 400)
    recent_audit = AuditLog.objects.create(action="login_success")  # within window

    old_read = Notification.objects.create(recipient=user, kind="x", message="m", read=True)
    _age(old_read, 200)
    old_unread = Notification.objects.create(recipient=user, kind="x", message="m", read=False)
    _age(old_unread, 200)

    result = purge_old_data()
    assert result["audit_logs"] == 1
    assert result["notifications"] == 1
    assert AuditLog.objects.filter(pk=recent_audit.pk).exists()
    assert not AuditLog.objects.filter(pk=old_audit.pk).exists()
    # Unread notifications are preserved even when old.
    assert Notification.objects.filter(pk=old_unread.pk).exists()
    assert not Notification.objects.filter(pk=old_read.pk).exists()


@pytest.mark.django_db
def test_purge_dry_run_deletes_nothing():
    old = AuditLog.objects.create(action="x")
    _age(old, 400)
    result = purge_old_data(dry_run=True)
    assert result["audit_logs"] == 1
    assert AuditLog.objects.filter(pk=old.pk).exists()


@pytest.mark.django_db
def test_purge_never_touches_certificates():
    from batches.models import Batch, BatchState, Course
    from enrollments.models import Enrollment

    course = Course.objects.create(code="C", name="C")
    batch = Batch.objects.create(
        code="B",
        name="B",
        course=course,
        start_date=datetime.date(2020, 1, 1),
        end_date=datetime.date(2020, 4, 1),
        state=BatchState.COMPLETED,
    )
    student = User.objects.create_user(
        username="s1", password="x", role="student", status=UserStatus.ACTIVE
    )
    enr = Enrollment.objects.create(student=student, batch=batch, registration_number="s1")
    cert = Certificate.objects.create(enrollment=enr, certificate_id="CERT-1")
    _age(cert, 2000)  # very old, but a legal record

    purge_old_data(audit_days=0, notification_days=0)
    assert Certificate.objects.filter(pk=cert.pk).exists()
