"""Smoke tests for wiring: health endpoint and custom user model."""

import pytest
from django.contrib.auth import get_user_model

from core.roles import Role


def test_health_endpoint(client):
    resp = client.get("/api/v1/health/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.django_db
def test_create_superuser_defaults_to_super_admin_role():
    User = get_user_model()
    user = User.objects.create_superuser(username="root", password="x9f!Qz2playLMS")
    assert user.role == Role.SUPER_ADMIN
    assert user.is_staff and user.is_superuser
    assert user.check_password("x9f!Qz2playLMS")
