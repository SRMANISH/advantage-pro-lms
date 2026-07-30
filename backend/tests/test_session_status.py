"""Suspension must end an account's *existing* access, not just block new logins.

Authentication is session-based and login was the only place ``UserStatus`` was ever checked
— ``MatrixPermission``, ``IsSuperAdmin`` and ``has_any_role`` all gate on ``role`` alone. So a
suspended user kept full privileges until their cookie expired, which with Django's two-week
default is close to never in incident terms. ``core.authentication.ActiveSessionAuthentication``
re-checks it per request.

These tests deliberately use a **real cookie session** via the login endpoint rather than
``force_authenticate``: DRF's ``force_authenticate`` sets ``request._force_auth_user`` and
skips the authentication classes entirely, so it cannot exercise this guard at all — a test
written that way passes whether or not the fix is present.
"""

import pytest

from accounts.models import UserStatus
from core.roles import Role

from .helpers import user

ME = "/api/v1/auth/me/"
LOGIN = "/api/v1/auth/login/"
PASSWORD = "Str0ng!passLMS"


def _signed_in(client, username, role):
    """Create an account and give ``client`` a genuine authenticated session for it."""
    account = user(username, role, password=PASSWORD)
    resp = client.post(
        LOGIN,
        {"username": username, "password": PASSWORD, "role": role},
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    return account


@pytest.mark.django_db
def test_suspending_an_account_kills_its_live_session(client):
    """The regression test: one session held across the status change."""
    account = _signed_in(client, "sess_sus", Role.MIS)
    assert client.get(ME).status_code == 200

    account.status = UserStatus.SUSPENDED
    account.save(update_fields=["status"])

    assert client.get(ME).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("status", [UserStatus.DEACTIVATED, UserStatus.PENDING])
def test_other_non_active_statuses_are_refused_too(client, status):
    account = _signed_in(client, "sess_other", Role.MIS)
    assert client.get(ME).status_code == 200

    account.status = status
    account.save(update_fields=["status"])
    assert client.get(ME).status_code == 403


@pytest.mark.django_db
def test_reactivation_restores_access(client):
    account = _signed_in(client, "sess_react", Role.MIS)

    account.status = UserStatus.SUSPENDED
    account.save(update_fields=["status"])
    assert client.get(ME).status_code == 403

    account.status = UserStatus.ACTIVE
    account.save(update_fields=["status"])
    assert client.get(ME).status_code == 200


@pytest.mark.django_db
def test_an_active_session_is_unaffected(client):
    """The guard must not disturb the ordinary path."""
    _signed_in(client, "sess_ok", Role.ADMIN)
    assert client.get(ME).status_code == 200
    assert client.get(ME).status_code == 200  # and keeps working across requests


@pytest.mark.django_db
def test_suspension_blocks_a_privileged_action_not_just_the_profile_endpoint(client):
    """The check lives in authentication, so it covers every view — including matrix-gated
    ones — rather than only where someone remembered to add it."""
    account = _signed_in(client, "sess_priv", Role.SUPER_ADMIN)
    assert client.get("/api/v1/auth/staff/").status_code == 200

    account.status = UserStatus.SUSPENDED
    account.save(update_fields=["status"])
    assert client.get("/api/v1/auth/staff/").status_code == 403
