"""Every DRF-handled error response carries a single top-level "detail" string,
whatever exception raised it — field ValidationError, permission, auth, or not-found."""

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from batches.models import Batch, Course
from core.roles import Role


def user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
def test_field_validation_error_has_top_level_detail_and_field_errors():
    sa = user("sa", Role.SUPER_ADMIN)
    # Missing required fields on staff creation -> serializer ValidationError.
    resp = client_for(sa).post("/api/v1/auth/staff/", {}, format="json")
    assert resp.status_code == 400
    body = resp.json()
    assert isinstance(body["detail"], str) and body["detail"]
    assert isinstance(body["errors"], dict) and body["errors"]


@pytest.mark.django_db
def test_permission_denied_keeps_plain_detail_shape():
    mis = user("mis", Role.MIS)
    resp = client_for(mis).get("/api/v1/permissions/matrix/")
    assert resp.status_code == 403
    body = resp.json()
    assert isinstance(body["detail"], str) and body["detail"]
    assert "errors" not in body  # unchanged shape — nothing to flatten


@pytest.mark.django_db
def test_not_found_keeps_plain_detail_shape():
    sa = user("sa", Role.SUPER_ADMIN)
    resp = client_for(sa).put(
        "/api/v1/permissions/matrix/does_not_exist/", {"roles": []}, format="json"
    )
    assert resp.status_code == 404
    assert isinstance(resp.json().get("detail"), str)


@pytest.mark.django_db
def test_unauthenticated_request_gets_detail():
    resp = APIClient().get("/api/v1/notifications/")
    assert resp.status_code in (401, 403)
    assert isinstance(resp.json().get("detail"), str)


@pytest.mark.django_db
def test_upload_validation_error_flattened_to_one_message():
    course = Course.objects.create(code="FS", name="Full Stack")
    batch = Batch.objects.create(
        code="FS-1",
        name="B",
        course=course,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 6, 1),
    )
    fac = user("prof", Role.FACULTY)
    batch.faculty.add(fac)
    evil = SimpleUploadedFile("evil.mp4", b"not a real video", content_type="video/mp4")
    resp = client_for(fac).post(
        "/api/v1/videos/",
        {"batch": str(batch.id), "title": "Bad", "file": evil},
        format="multipart",
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "match its extension" in body["detail"]
