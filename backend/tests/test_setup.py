"""Two-step account setup: email OTP -> phone OTP -> password, plus guards."""

import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserStatus
from accounts.setup import create_setup_token
from core.roles import Role

START = "/api/v1/auth/setup/start/"
VERIFY_EMAIL = "/api/v1/auth/setup/verify-email/"
VERIFY_PHONE = "/api/v1/auth/setup/verify-phone/"
COMPLETE = "/api/v1/auth/setup/complete/"


@pytest.fixture
def pending_student(db):
    return get_user_model().objects.create_user(
        username="S900",
        password=None,
        role=Role.STUDENT,
        status=UserStatus.PENDING,
        email="s900@example.com",
        phone="9876543210",
    )


@pytest.mark.django_db
def test_full_setup_flow_activates_and_allows_login(client, pending_student, settings):
    settings.DEBUG = True  # surfaces dev_code so the test can read the OTPs
    token = create_setup_token(pending_student).token

    start = client.post(START, {"token": token}, content_type="application/json")
    assert start.status_code == 200
    email_code = start.json()["dev_code"]  # DEBUG-only convenience

    ve = client.post(
        VERIFY_EMAIL, {"token": token, "code": email_code}, content_type="application/json"
    )
    assert ve.status_code == 200
    phone_code = ve.json()["dev_code"]

    vp = client.post(
        VERIFY_PHONE, {"token": token, "code": phone_code}, content_type="application/json"
    )
    assert vp.status_code == 200

    done = client.post(
        COMPLETE, {"token": token, "password": "Str0ng!passLMS"}, content_type="application/json"
    )
    assert done.status_code == 200

    pending_student.refresh_from_db()
    assert pending_student.status == UserStatus.ACTIVE

    login = client.post(
        "/api/v1/auth/login/",
        {
            "username": "S900",
            "password": "Str0ng!passLMS",
            "role": Role.STUDENT,
            "device_id": "setup-device",
        },
        content_type="application/json",
    )
    assert login.status_code == 200


@pytest.mark.django_db
def test_wrong_email_code_is_rejected(client, pending_student):
    token = create_setup_token(pending_student).token
    client.post(START, {"token": token}, content_type="application/json")
    resp = client.post(
        VERIFY_EMAIL, {"token": token, "code": "000000"}, content_type="application/json"
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_cannot_complete_without_verification(client, pending_student):
    token = create_setup_token(pending_student).token
    resp = client.post(
        COMPLETE, {"token": token, "password": "Str0ng!passLMS"}, content_type="application/json"
    )
    assert resp.status_code == 400
    pending_student.refresh_from_db()
    assert pending_student.status == UserStatus.PENDING


@pytest.mark.django_db
def test_invalid_token_is_rejected(client):
    resp = client.post(START, {"token": "nope"}, content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_weak_password_is_rejected(client, pending_student):
    token_obj = create_setup_token(pending_student)
    token_obj.email_verified = True
    token_obj.phone_verified = True
    token_obj.save()
    resp = client.post(
        COMPLETE, {"token": token_obj.token, "password": "123"}, content_type="application/json"
    )
    assert resp.status_code == 400
