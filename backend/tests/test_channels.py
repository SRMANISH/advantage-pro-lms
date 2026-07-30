"""Channel config visibility + test-send (Super Admin only)."""

import pytest

from core.roles import Role
from .helpers import client_for, user

CHANNELS = "/api/v1/settings/channels/"
TEST = "/api/v1/settings/channels/test/"


@pytest.mark.django_db
def test_super_admin_sees_channels():
    resp = client_for(user("sa", Role.SUPER_ADMIN)).get(CHANNELS)
    assert resp.status_code == 200
    kinds = {c["kind"] for c in resp.json()["channels"]}
    assert {"storage", "email", "sms", "whatsapp", "scheduler"} <= kinds
    # Dev uses local/console stubs.
    assert all(c["dev_stub"] for c in resp.json()["channels"])


@pytest.mark.django_db
def test_admin_cannot_see_channels():
    assert client_for(user("ad", Role.ADMIN)).get(CHANNELS).status_code == 403


@pytest.mark.django_db
def test_super_admin_can_send_test_whatsapp():
    resp = client_for(user("sa", Role.SUPER_ADMIN)).post(
        TEST, {"channel": "whatsapp", "to": "9876543210", "message": "hi"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.django_db
def test_invalid_channel_rejected():
    resp = client_for(user("sa", Role.SUPER_ADMIN)).post(
        TEST, {"channel": "carrier-pigeon", "to": "x", "message": "y"}, format="json"
    )
    assert resp.status_code == 400
