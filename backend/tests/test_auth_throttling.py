"""Every code-verification / credential-change endpoint must be rate limited.

The per-code attempt cap bounds guesses against a *single* code; these throttles bound how
fast an attacker can cycle requests (and new codes) at all. ``test_auth.py`` covers the
login throttle; this covers the endpoints that previously had none.

Note the throttle keys by user when authenticated and by IP otherwise — the built-in
AnonRateThrottle would no-op on the authenticated endpoints below.
"""

import pytest
from rest_framework.test import APIClient

from accounts.models import UserStatus
from accounts.setup import create_setup_token
from core.roles import Role

# One over the configured "otp" rate (20/min) — the last call must be refused.
OVER_LIMIT = 21


@pytest.fixture
def student(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        username="S700",
        password="Str0ng!passLMS",
        role=Role.STUDENT,
        status=UserStatus.ACTIVE,
        email="s700@example.com",
        phone="9876500700",
    )


@pytest.fixture
def pending(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        username="S701",
        password=None,
        role=Role.STUDENT,
        status=UserStatus.PENDING,
        email="s701@example.com",
        phone="9876500701",
    )


def hammer(call):
    """Fire OVER_LIMIT requests and return the final response."""
    last = None
    for _ in range(OVER_LIMIT):
        last = call()
    return last


# --------------------------- account setup ---------------------------


@pytest.mark.django_db
def test_setup_verify_email_is_rate_limited(client, pending):
    token = create_setup_token(pending).token
    last = hammer(
        lambda: client.post(
            "/api/v1/auth/setup/verify-email/",
            {"token": token, "code": "000000"},
            content_type="application/json",
        )
    )
    assert last.status_code == 429


@pytest.mark.django_db
def test_setup_verify_phone_is_rate_limited(client, pending):
    token = create_setup_token(pending).token
    last = hammer(
        lambda: client.post(
            "/api/v1/auth/setup/verify-phone/",
            {"token": token, "code": "000000"},
            content_type="application/json",
        )
    )
    assert last.status_code == 429


@pytest.mark.django_db
def test_setup_complete_is_rate_limited(client, pending):
    token = create_setup_token(pending).token
    last = hammer(
        lambda: client.post(
            "/api/v1/auth/setup/complete/",
            {"token": token, "password": "Str0ng!passLMS"},
            content_type="application/json",
        )
    )
    assert last.status_code == 429


# --------------------------- forgot password ---------------------------


@pytest.mark.django_db
def test_forgot_password_verify_email_is_rate_limited(client, student):
    last = hammer(
        lambda: client.post(
            "/api/v1/auth/password/verify-email/",
            {"token": "nope", "code": "000000"},
            content_type="application/json",
        )
    )
    assert last.status_code == 429


@pytest.mark.django_db
def test_forgot_password_verify_phone_is_rate_limited(client, student):
    last = hammer(
        lambda: client.post(
            "/api/v1/auth/password/verify-phone/",
            {"token": "nope", "code": "000000"},
            content_type="application/json",
        )
    )
    assert last.status_code == 429


@pytest.mark.django_db
def test_forgot_password_reset_is_rate_limited(client, student):
    last = hammer(
        lambda: client.post(
            "/api/v1/auth/password/reset/",
            {"token": "nope", "password": "Str0ng!passLMS"},
            content_type="application/json",
        )
    )
    assert last.status_code == 429


# --------------------------- authenticated endpoints ---------------------------
# These are the ones AnonRateThrottle would silently skip.


@pytest.mark.django_db
def test_change_password_is_rate_limited_per_user(student):
    api = APIClient()
    api.force_authenticate(user=student)
    last = hammer(
        lambda: api.post(
            "/api/v1/auth/password/change/",
            {"old_password": "wrong", "new_password": "Str0ng!passLMS2"},
            format="json",
        )
    )
    assert last.status_code == 429


@pytest.mark.django_db
def test_totp_confirm_is_rate_limited_per_user(db):
    """TOTP confirm takes a 6-digit code — it must not be brute-forceable."""
    from django.contrib.auth import get_user_model

    staff = get_user_model().objects.create_user(
        username="fac9", password="x", role=Role.FACULTY, status=UserStatus.ACTIVE
    )
    api = APIClient()
    api.force_authenticate(user=staff)
    api.post("/api/v1/auth/totp/enroll/", {}, format="json")

    last = hammer(lambda: api.post("/api/v1/auth/totp/confirm/", {"code": "000000"}, format="json"))
    assert last.status_code == 429


@pytest.mark.django_db
def test_throttle_is_scoped_per_user_not_global(db):
    """One user exhausting the limit must not lock everyone else out."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    noisy = User.objects.create_user(
        username="noisy", password="x", role=Role.FACULTY, status=UserStatus.ACTIVE
    )
    quiet = User.objects.create_user(
        username="quiet", password="x", role=Role.FACULTY, status=UserStatus.ACTIVE
    )

    noisy_api = APIClient()
    noisy_api.force_authenticate(user=noisy)
    assert (
        hammer(lambda: noisy_api.post("/api/v1/auth/totp/enroll/", {}, format="json")).status_code
        == 429
    )

    quiet_api = APIClient()
    quiet_api.force_authenticate(user=quiet)
    assert quiet_api.post("/api/v1/auth/totp/enroll/", {}, format="json").status_code != 429
