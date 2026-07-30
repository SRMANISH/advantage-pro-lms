"""req 21: Super-Admin-editable third-party connections (masked secrets)."""

import pytest

from core.roles import Role
from notifications.models import IntegrationSetting
from .helpers import client_for, user

URL = "/api/v1/settings/channels/"


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
    assert row.provider == "whatsapp_cloud"
    # Stored encrypted at rest — the column is not the plaintext, but decrypts back to it.
    assert row.secret != "super-secret-token"
    assert row.decrypt_secret() == "super-secret-token"

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
    assert row.decrypt_secret() == "keep-me" and row.config == {"sender": "ADVPRO"}


@pytest.mark.django_db
def test_only_super_admin_can_edit_connections(db):
    for role in (Role.ADMIN, Role.MIS, Role.FACULTY, Role.STUDENT):
        resp = client_for(user(f"u_{role}", role)).put(
            URL, {"channel": "email", "provider": "smtp"}, format="json"
        )
        assert resp.status_code == 403


@pytest.mark.django_db
def test_integration_config_is_db_first_with_env_fallback(db):
    from core.integrations import integration_config

    # No row saved -> empty (the adapter then falls back to env settings).
    assert integration_config("whatsapp") == {"provider": "", "config": {}, "secret": ""}

    client_for(user("sa", Role.SUPER_ADMIN)).put(
        URL,
        {
            "channel": "whatsapp",
            "provider": "whatsapp_cloud",
            "config": {"phone_number_id": "123"},
            "secret": "tok",
        },
        format="json",
    )
    # The save invalidated the cache, so the config reflects it (secret decrypted).
    cfg = integration_config("whatsapp")
    assert cfg["provider"] == "whatsapp_cloud"
    assert cfg["config"] == {"phone_number_id": "123"}
    assert cfg["secret"] == "tok"


@pytest.mark.django_db
def test_sms_adapter_uses_the_saved_db_connection(db, monkeypatch):
    """req 21 wired for real: the MSG91 adapter sends with the SA-saved key/sender,
    not just env settings."""
    from core.adapters.msg91 import Msg91SmsAdapter

    client_for(user("sa", Role.SUPER_ADMIN)).put(
        URL,
        {
            "channel": "sms",
            "provider": "msg91",
            "config": {"sender_id": "ADVPRO", "route": "4"},
            "secret": "live-authkey",
        },
        format="json",
    )

    captured = {}

    class _Resp:
        status_code = 200
        text = ""

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        captured["json"] = json
        return _Resp()

    monkeypatch.setattr("core.adapters.msg91.requests.post", fake_post)
    Msg91SmsAdapter().send("9876500000", "Hello")

    assert captured["headers"]["authkey"] == "live-authkey"
    assert captured["json"]["sender"] == "ADVPRO"
