"""Deletion of records that other records depend on.

Two layers, and they cover different callers. ``BatchViewSet.perform_destroy`` gives a clear
409 to a Super Admin using the API. ``Certificate.enrollment`` being PROTECT stops every other
caller — a shell, a data migration, an endpoint written later — and the Django admin no longer
offers a delete button at all for the three entities whose deletion cascades furthest.
"""

import datetime

import pytest
from django.contrib import admin as django_admin
from django.db.models import ProtectedError

from accounts.models import User
from batches.models import Batch, BatchState, Course
from certification.models import Certificate
from core.roles import Role
from enrollments.models import Enrollment

from .helpers import client_for, user


@pytest.fixture
def certified(db):
    course = Course.objects.create(code="DP", name="DP")
    batch = Batch.objects.create(
        code="DP-1",
        name="DP-1",
        course=course,
        start_date=datetime.date.today() - datetime.timedelta(days=60),
        end_date=datetime.date.today() - datetime.timedelta(days=1),
        state=BatchState.COMPLETED,
    )
    student = user("dp_stu", Role.STUDENT)
    enrollment = Enrollment.objects.create(
        student=student, batch=batch, registration_number="dp_stu"
    )
    Certificate.objects.create(enrollment=enrollment, certificate_id="ADV-DP-001")
    return {"course": course, "batch": batch, "student": student}


# --------------------------- the unguarded API path ---------------------------


@pytest.mark.django_db
def test_deleting_a_course_returns_409_not_500(certified):
    """CourseViewSet has no perform_destroy guard, so the PROTECT fires raw.

    `Batch.course` has been PROTECT all along, so this delete was *already* refused — but as
    an unhandled ProtectedError, i.e. a 500 telling the user the server was broken rather than
    that the operation is not allowed. That is what the handler change fixes.
    """
    sa = user("dp_sa", Role.SUPER_ADMIN)

    resp = client_for(sa).delete(f"/api/v1/courses/{certified['course'].id}/")

    assert resp.status_code == 409, resp.content
    assert "batches" in str(resp.data["detail"]).lower()
    assert "errors" in resp.data  # the standard envelope, same as every other error
    assert Course.objects.filter(pk=certified["course"].pk).exists()


@pytest.mark.django_db
def test_the_error_names_the_blocking_model_but_not_the_rows(certified):
    """Actionable without leaking other people's records."""
    sa = user("dp_sa2", Role.SUPER_ADMIN)
    resp = client_for(sa).delete(f"/api/v1/courses/{certified['course'].id}/")

    body = str(resp.data)
    assert "batches" in body.lower()
    assert "DP-1" not in body  # no batch codes, no certificate IDs, no student names


@pytest.mark.django_db
def test_the_message_pluralises_the_model_name_properly(certified):
    """The message is user-facing, and Django's default pluraliser produced "batchs"."""
    sa = user("dp_sa5", Role.SUPER_ADMIN)
    body = str(client_for(sa).delete(f"/api/v1/courses/{certified['course'].id}/").data)
    assert "batchs" not in body
    assert "batches" in body


@pytest.mark.django_db
def test_deleting_an_enrolment_with_a_certificate_also_gives_409(certified):
    """The certificate PROTECT reached through the same handler, via a different model."""
    from enrollments.models import Enrollment as E

    with pytest.raises(ProtectedError):
        E.objects.get(batch=certified["batch"]).delete()


@pytest.mark.django_db
def test_a_course_with_nothing_depending_on_it_still_deletes(db):
    """The guard must not make ordinary cleanup impossible."""
    sa = user("dp_sa3", Role.SUPER_ADMIN)
    course = Course.objects.create(code="DP9", name="DP9")

    assert client_for(sa).delete(f"/api/v1/courses/{course.id}/").status_code == 204
    assert not Course.objects.filter(pk=course.pk).exists()


@pytest.mark.django_db
def test_a_draft_batch_with_enrolments_but_no_certificates_still_deletes(db):
    """Confirms the layer added here did not tighten batch deletion beyond its intent."""
    sa = user("dp_sa4", Role.SUPER_ADMIN)
    course = Course.objects.create(code="DP8", name="DP8")
    batch = Batch.objects.create(
        code="DP-8",
        name="DP-8",
        course=course,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=30),
        state=BatchState.DRAFT,
    )
    student = user("dp_stu8", Role.STUDENT)
    Enrollment.objects.create(student=student, batch=batch, registration_number="dp_stu8")

    assert client_for(sa).delete(f"/api/v1/batches/{batch.id}/").status_code == 204
    assert not Batch.objects.filter(pk=batch.pk).exists()


@pytest.mark.django_db
def test_the_database_still_refuses_a_direct_delete(certified):
    """The API layer is convenience; this is the guarantee."""
    with pytest.raises(ProtectedError):
        certified["course"].delete()


# --------------------------- the admin path ---------------------------


@pytest.mark.parametrize("model", [User, Batch, Course])
def test_admin_offers_no_delete_for_the_far_cascading_models(model):
    site_admin = django_admin.site._registry[model]
    assert site_admin.has_delete_permission(None) is False
    assert site_admin.has_delete_permission(None, obj=None) is False


@pytest.mark.django_db
@pytest.mark.parametrize("model", [User, Batch, Course])
def test_the_bulk_delete_action_is_gone(model, rf):
    """Pinned rather than assumed: Django removes `delete_selected` when the delete permission
    is denied, but that is framework behaviour this relies on — if it ever changed, a superuser
    could still cascade fifty rows away from a list view."""
    request = rf.get("/admin/")
    request.user = User.objects.create_superuser(
        username=f"dp_root_{model.__name__}", password="x", email="r@example.com"
    )
    actions = django_admin.site._registry[model].get_actions(request)
    assert "delete_selected" not in actions


@pytest.mark.django_db
def test_admin_can_still_edit_what_it_can_no_longer_delete():
    """Closing deletion must not close administration."""
    root = User.objects.create_superuser(username="dp_root2", password="x", email="r2@example.com")
    request = type("R", (), {"user": root, "method": "GET", "GET": {}})()
    for model in (User, Batch, Course):
        site_admin = django_admin.site._registry[model]
        assert site_admin.has_change_permission(request) is True
        assert site_admin.has_add_permission(request) is True
