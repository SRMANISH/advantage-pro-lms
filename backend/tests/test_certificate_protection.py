"""A certificate must survive any deletion path, not just the one that checks for it.

`BatchViewSet.perform_destroy` refuses to delete a batch that has certificates. That guard is
real, but it is an application check on a single code path: a shell
`Batch.objects.filter(...).delete()`, a data migration, or a future endpoint that deletes an
enrolment would all cascade straight through and destroy the institute's only record that a
student completed the course. `Certificate.enrollment` is PROTECT so the database refuses
regardless of who is asking.
"""

import datetime

import pytest
from django.db.models import ProtectedError

from batches.models import Batch, BatchState, Course
from certification.models import Certificate
from core.roles import Role
from enrollments.models import Enrollment

from .helpers import client_for, user


@pytest.fixture
def certified(db):
    """A batch with one enrolled, certified student."""
    course = Course.objects.create(code="CP", name="CP")
    batch = Batch.objects.create(
        code="CP-1",
        name="CP-1",
        course=course,
        start_date=datetime.date.today() - datetime.timedelta(days=60),
        end_date=datetime.date.today() - datetime.timedelta(days=1),
        state=BatchState.COMPLETED,
    )
    student = user("cert_stu", Role.STUDENT)
    enrollment = Enrollment.objects.create(
        student=student, batch=batch, registration_number="cert_stu"
    )
    Certificate.objects.create(enrollment=enrollment, certificate_id="ADV-2026-001")
    return {"batch": batch, "enrollment": enrollment, "student": student}


@pytest.mark.django_db
def test_the_database_refuses_to_cascade_a_certificate_away(certified):
    """The regression test: deleting the batch directly, bypassing the view entirely."""
    with pytest.raises(ProtectedError):
        certified["batch"].delete()

    assert Certificate.objects.filter(certificate_id="ADV-2026-001").exists()
    assert Batch.objects.filter(pk=certified["batch"].pk).exists()  # nothing half-deleted


@pytest.mark.django_db
def test_deleting_the_enrolment_directly_is_refused_too(certified):
    with pytest.raises(ProtectedError):
        certified["enrollment"].delete()
    assert Certificate.objects.filter(certificate_id="ADV-2026-001").exists()


@pytest.mark.django_db
def test_the_api_still_returns_its_own_clear_error_not_a_500(certified):
    """The view's own check must keep running *first*, so a Super Admin gets an explanation
    rather than an unhandled ProtectedError."""
    sa = user("cert_sa", Role.SUPER_ADMIN)
    resp = client_for(sa).delete(f"/api/v1/batches/{certified['batch'].id}/")

    # 409, not 400: the request is well-formed, it conflicts with the batch's state.
    assert resp.status_code == 409, resp.content
    assert "certificate" in str(resp.data).lower()
    assert Batch.objects.filter(pk=certified["batch"].pk).exists()


@pytest.mark.django_db
def test_a_batch_without_certificates_is_still_deletable(db):
    """The guard must not make ordinary cleanup impossible — a mistaken draft batch, with
    attendance and submissions but no certificate, must still go."""
    course = Course.objects.create(code="CP2", name="CP2")
    batch = Batch.objects.create(
        code="CP-2",
        name="CP-2",
        course=course,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=30),
        state=BatchState.DRAFT,
    )
    student = user("nocert_stu", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="nocert_stu")

    batch.delete()
    assert not Batch.objects.filter(pk=batch.pk).exists()
    assert not Enrollment.objects.filter(student=student).exists()  # cascade still works
