"""Staff TOTP 2FA: enrollment, login enforcement, disable, student exclusion."""

import pyotp
import pytest
from rest_framework.test import APIClient

from accounts.models import TOTPDevice
from core.roles import Role
from .helpers import client_for, user

ENROLL = "/api/v1/auth/totp/enroll/"
CONFIRM = "/api/v1/auth/totp/confirm/"
DISABLE = "/api/v1/auth/totp/disable/"
STATUS = "/api/v1/auth/totp/status/"
LOGIN = "/api/v1/auth/login/"


PASSWORD = "Secret123!"  # real logins happen in this module, so it must pass validation


def _enroll_and_confirm(client) -> str:
    """Enroll, confirm with a genuine code, and return the shared secret."""
    secret = client.post(ENROLL, format="json").json()["secret"]
    code = pyotp.TOTP(secret).now()
    resp = client.post(CONFIRM, {"code": code}, format="json")
    assert resp.status_code == 200
    return secret


@pytest.mark.django_db
def test_status_defaults_to_disabled():
    admin = user("adm", Role.ADMIN, password=PASSWORD)
    resp = client_for(admin).get(STATUS)
    assert resp.status_code == 200
    assert resp.json() == {"enabled": False}


@pytest.mark.django_db
def test_enroll_then_confirm_enables_totp():
    admin = user("adm", Role.ADMIN, password=PASSWORD)
    c = client_for(admin)
    enroll = c.post(ENROLL, format="json")
    assert enroll.status_code == 200
    body = enroll.json()
    assert len(body["secret"]) >= 16
    assert body["otpauth_url"].startswith("otpauth://totp/")

    code = pyotp.TOTP(body["secret"]).now()
    confirm = c.post(CONFIRM, {"code": code}, format="json")
    assert confirm.status_code == 200
    assert c.get(STATUS).json() == {"enabled": True}


@pytest.mark.django_db
def test_confirm_with_wrong_code_does_not_enable():
    admin = user("adm", Role.ADMIN, password=PASSWORD)
    c = client_for(admin)
    c.post(ENROLL, format="json")
    resp = c.post(CONFIRM, {"code": "000000"}, format="json")
    assert resp.status_code == 400
    assert c.get(STATUS).json() == {"enabled": False}


@pytest.mark.django_db
def test_reenrolling_while_confirmed_is_rejected():
    admin = user("adm", Role.ADMIN, password=PASSWORD)
    c = client_for(admin)
    _enroll_and_confirm(c)
    resp = c.post(ENROLL, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_student_cannot_use_totp_endpoints():
    student = user("S1", Role.STUDENT, password=PASSWORD)
    c = client_for(student)
    assert c.get(STATUS).status_code == 403
    assert c.post(ENROLL, format="json").status_code == 403


@pytest.mark.django_db
def test_login_without_totp_enabled_is_unaffected():
    user("adm", Role.ADMIN, password=PASSWORD)
    resp = APIClient().post(
        LOGIN, {"username": "adm", "password": "Secret123!"}, content_type="application/json"
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_login_with_totp_enabled_requires_code_then_succeeds():
    admin = user("adm", Role.ADMIN, password=PASSWORD)
    secret = _enroll_and_confirm(client_for(admin))

    # Step 1: password only -> blocked, asks for the code.
    resp = APIClient().post(
        LOGIN, {"username": "adm", "password": "Secret123!"}, content_type="application/json"
    )
    assert resp.status_code == 401
    assert resp.json()["totp_required"] is True

    # Step 2: wrong code -> still blocked.
    resp = APIClient().post(
        LOGIN,
        {"username": "adm", "password": "Secret123!", "totp_code": "000000"},
        content_type="application/json",
    )
    assert resp.status_code == 401

    # Step 3: correct code -> session established.
    resp = APIClient().post(
        LOGIN,
        {"username": "adm", "password": "Secret123!", "totp_code": pyotp.TOTP(secret).now()},
        content_type="application/json",
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_disable_requires_current_password():
    admin = user("adm", Role.ADMIN, password=PASSWORD)
    c = client_for(admin)
    _enroll_and_confirm(c)

    wrong = c.post(DISABLE, {"password": "wrong"}, format="json")
    assert wrong.status_code == 400
    assert c.get(STATUS).json() == {"enabled": True}

    right = c.post(DISABLE, {"password": "Secret123!"}, format="json")
    assert right.status_code == 200
    assert c.get(STATUS).json() == {"enabled": False}
    assert not TOTPDevice.objects.filter(user=admin).exists()


@pytest.mark.django_db
def test_disabling_totp_reverts_login_to_password_only():
    admin = user("adm", Role.ADMIN, password=PASSWORD)
    c = client_for(admin)
    _enroll_and_confirm(c)
    c.post(DISABLE, {"password": "Secret123!"}, format="json")

    resp = APIClient().post(
        LOGIN, {"username": "adm", "password": "Secret123!"}, content_type="application/json"
    )
    assert resp.status_code == 200


# ---------- per-device attempt cap (independent of the request-rate throttle) ----------


@pytest.mark.django_db
def test_totp_confirm_locks_the_device_after_max_attempts():
    """A 6-digit code needs a ceiling an attacker cannot sidestep by rotating IPs, so the
    cap lives on the device itself rather than only in the throttle."""
    from accounts.totp import MAX_ATTEMPTS

    staff = user("fac_cap", Role.FACULTY, password=PASSWORD)
    api = client_for(staff)
    secret = api.post(ENROLL, format="json").json()["secret"]

    for _ in range(MAX_ATTEMPTS):
        assert api.post(CONFIRM, {"code": "000000"}, format="json").status_code == 400

    device = TOTPDevice.objects.get(user=staff)
    assert device.failed_attempts == MAX_ATTEMPTS

    # Even the genuinely correct code is now refused, with a distinct status and a message
    # that tells the user how to recover.
    spent = api.post(CONFIRM, {"code": pyotp.TOTP(secret).now()}, format="json")
    assert spent.status_code == 429
    assert "Restart enrollment" in spent.json()["detail"]
    assert not TOTPDevice.objects.get(user=staff).confirmed


@pytest.mark.django_db
def test_a_correct_code_clears_the_attempt_counter():
    staff = user("fac_clear", Role.FACULTY, password=PASSWORD)
    api = client_for(staff)
    secret = api.post(ENROLL, format="json").json()["secret"]

    api.post(CONFIRM, {"code": "000000"}, format="json")
    assert TOTPDevice.objects.get(user=staff).failed_attempts == 1

    assert api.post(CONFIRM, {"code": pyotp.TOTP(secret).now()}, format="json").status_code == 200
    device = TOTPDevice.objects.get(user=staff)
    assert device.failed_attempts == 0 and device.confirmed


@pytest.mark.django_db
def test_restarting_enrollment_resets_the_cap():
    """The documented recovery path must actually work."""
    from accounts.totp import MAX_ATTEMPTS

    staff = user("fac_reset", Role.FACULTY, password=PASSWORD)
    api = client_for(staff)
    api.post(ENROLL, format="json")
    for _ in range(MAX_ATTEMPTS):
        api.post(CONFIRM, {"code": "000000"}, format="json")
    assert TOTPDevice.objects.get(user=staff).failed_attempts == MAX_ATTEMPTS

    # Re-enrolling issues a fresh secret and clears the counter.
    new_secret = api.post(ENROLL, format="json").json()["secret"]
    assert TOTPDevice.objects.get(user=staff).failed_attempts == 0
    assert (
        api.post(CONFIRM, {"code": pyotp.TOTP(new_secret).now()}, format="json").status_code == 200
    )
