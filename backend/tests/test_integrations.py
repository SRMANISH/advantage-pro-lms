"""req 21: Super-Admin-editable third-party connections (masked secrets)."""

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from core.roles import Role
from notifications.models import IntegrationSetting

URL = "/api/v1/settings/channels/"


def user(username, role):
    return User.objects.create_user(
        username=username, password="x", role=role, status=UserStatus.ACTIVE
    )


def client_for(u):
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
def test_super_admin_saves_connection_and_secret_is_masked(db):
    sa = user("sa", Role.SUPER_ADMIN)
    saved = client_for(sa).put(
        URL,
        {
            "channel": "whatsapp",
            "provider": "whatsapp_cloud",
            "config": {"phone_number_id": "12345"},
            "secret": "super-secret-token",
        },
        format="json",
    )
    assert saved.status_code == 200 and saved.json()["secret_set"] is True

    row = IntegrationSetting.objects.get(channel="whatsapp")
    assert row.provider == "whatsapp_cloud" and row.secret == "super-secret-token"

    # GET exposes provider/config + secret_set, but never the secret value itself.
    body = client_for(sa).get(URL).json()
    whatsapp = next(c for c in body["channels"] if c["kind"] == "whatsapp")
    assert whatsapp["provider"] == "whatsapp_cloud"
    assert whatsapp["config"] == {"phone_number_id": "12345"}
    assert whatsapp["secret_set"] is True
    assert "secret" not in whatsapp


@pytest.mark.django_db
def test_blank_secret_keeps_the_stored_one(db):
    sa = user("sa", Role.SUPER_ADMIN)
    c = client_for(sa)
    c.put(URL, {"channel": "sms", "provider": "msg91", "secret": "keep-me"}, format="json")
    # Update the config only (no new secret) -> the stored secret survives.
    c.put(
        URL, {"channel": "sms", "provider": "msg91", "config": {"sender": "ADVPRO"}}, format="json"
    )
    row = IntegrationSetting.objects.get(channel="sms")
    assert row.secret == "keep-me" and row.config == {"sender": "ADVPRO"}


@pytest.mark.django_db
def test_only_super_admin_can_edit_connections(db):
    for role in (Role.ADMIN, Role.MIS, Role.FACULTY, Role.STUDENT):
        resp = client_for(user(f"u_{role}", role)).put(
            URL, {"channel": "email", "provider": "smtp"}, format="json"
        )
        assert resp.status_code == 403
