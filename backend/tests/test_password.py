"""Forgot-password (two-step email + phone OTP) and change-password."""

import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserStatus
from core.roles import Role

FORGOT = "/api/v1/auth/password/forgot/"
VERIFY_EMAIL = "/api/v1/auth/password/verify-email/"
VERIFY_PHONE = "/api/v1/auth/password/verify-phone/"
RESET = "/api/v1/auth/password/reset/"
CHANGE = "/api/v1/auth/password/change/"
LOGIN = "/api/v1/auth/login/"

OLD = "Old!passLMS123"
NEW = "New!passLMS456"


@pytest.fixture
def student(db):
    return get_user_model().objects.create_user(
        username="REG1",
        password=OLD,
        role=Role.STUDENT,
        status=UserStatus.ACTIVE,
        email="s@example.com",
        phone="+919876543210",
    )


@pytest.mark.django_db
def test_forgot_password_requires_both_email_and_phone_otp(client, student, settings):
    settings.DEBUG = True  # surfaces dev_code so the test can read the OTPs
    # Start by Registration ID.
    start = client.post(FORGOT, {"identifier": "REG1"}, content_type="application/json")
    assert start.status_code == 200
    body = start.json()
    token = body["token"]
    email_code = body["dev_code"]  # exposed only in DEBUG

    # Cannot reset before verifying.
    early = client.post(RESET, {"token": token, "password": NEW}, content_type="application/json")
    assert early.status_code == 400

    # Verify email -> get phone code.
    ve = client.post(
        VERIFY_EMAIL, {"token": token, "code": email_code}, content_type="application/json"
    )
    assert ve.status_code == 200
    phone_code = ve.json()["dev_code"]

    # Verify phone.
    vp = client.post(
        VERIFY_PHONE, {"token": token, "code": phone_code}, content_type="application/json"
    )
    assert vp.status_code == 200

    # Now reset succeeds and the new password works.
    done = client.post(RESET, {"token": token, "password": NEW}, content_type="application/json")
    assert done.status_code == 200
    assert (
        client.post(
            LOGIN,
            {"username": "REG1", "password": NEW, "role": Role.STUDENT, "device_id": "d1"},
            content_type="application/json",
        ).status_code
        == 200
    )


@pytest.mark.django_db
def test_forgot_password_wrong_email_code_rejected(client, student):
    token = client.post(
        FORGOT, {"identifier": "s@example.com"}, content_type="application/json"
    ).json()["token"]
    bad = client.post(
        VERIFY_EMAIL, {"token": token, "code": "000000"}, content_type="application/json"
    )
    assert bad.status_code == 400


@pytest.mark.django_db
def test_forgot_password_unknown_account(client, db):
    resp = client.post(FORGOT, {"identifier": "nobody"}, content_type="application/json")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_change_password_for_logged_in_user(client, student):
    client.force_login(student)
    bad = client.post(
        CHANGE, {"old_password": "wrong", "new_password": NEW}, content_type="application/json"
    )
    assert bad.status_code == 400
    ok = client.post(
        CHANGE, {"old_password": OLD, "new_password": NEW}, content_type="application/json"
    )
    assert ok.status_code == 200
    student.refresh_from_db()
    assert student.check_password(NEW)
