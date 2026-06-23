"""Role-bound authentication is security-critical — pinned by tests."""

import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserStatus
from core.roles import Role

PASSWORD = "Str0ng!passLMS"
LOGIN_URL = "/api/v1/auth/login/"


@pytest.fixture
def faculty(db):
    return get_user_model().objects.create_user(
        username="fac1", password=PASSWORD, role=Role.FACULTY, status=UserStatus.ACTIVE
    )


def _login(client, username, password, role):
    return client.post(
        LOGIN_URL,
        {"username": username, "password": password, "role": role},
        content_type="application/json",
    )


@pytest.mark.django_db
def test_login_success_returns_role(client, faculty):
    resp = _login(client, "fac1", PASSWORD, Role.FACULTY)
    assert resp.status_code == 200
    assert resp.json()["role"] == Role.FACULTY


@pytest.mark.django_db
def test_login_through_wrong_portal_is_rejected(client, faculty):
    # Correct credentials but wrong role-page must fail (role-bound login).
    resp = _login(client, "fac1", PASSWORD, Role.STUDENT)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_login_with_bad_password_is_rejected(client, faculty):
    resp = _login(client, "fac1", "wrong-password", Role.FACULTY)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_inactive_account_is_blocked(client):
    get_user_model().objects.create_user(
        username="pending1", password=PASSWORD, role=Role.STUDENT, status=UserStatus.PENDING
    )
    resp = _login(client, "pending1", PASSWORD, Role.STUDENT)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_me_requires_authentication(client):
    assert client.get("/api/v1/auth/me/").status_code in (401, 403)


@pytest.mark.django_db
def test_me_after_login_and_logout(client, faculty):
    assert _login(client, "fac1", PASSWORD, Role.FACULTY).status_code == 200

    me = client.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.json()["username"] == "fac1"

    assert client.post("/api/v1/auth/logout/").status_code == 204
    assert client.get("/api/v1/auth/me/").status_code in (401, 403)
