"""The real provider adapters: SMTP email and WhatsApp Cloud.

These are the implementations that run in production — ``test_adapters.py`` covers the
registry and the local dev stubs. Outbound SMTP/HTTP is mocked; what's asserted is the
contract: credentials resolve DB-first-then-env (req 21), the right payload is built, an
unconfigured channel stays silent, and a provider outage never propagates into the request
that triggered it.
"""

import pytest
import requests
from django.core import mail

from accounts.models import User, UserStatus
from core.adapters.smtp import SmtpEmailAdapter
from core.adapters.whatsapp_cloud import WhatsAppCloudAdapter
from core.roles import Role
from notifications.models import IntegrationSetting


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


def save_connection(channel, provider, config, secret):
    """Persist an SA-edited connection the way the Channels endpoint does."""
    from core.crypto import encrypt_secret
    from core.integrations import invalidate_integration_config

    IntegrationSetting.objects.update_or_create(
        channel=channel,
        defaults={"provider": provider, "config": config, "secret": encrypt_secret(secret)},
    )
    invalidate_integration_config()


# --------------------------- SMTP email adapter ---------------------------


@pytest.mark.django_db
def test_smtp_sends_through_the_django_backend(db):
    SmtpEmailAdapter().send("s1@example.com", "Welcome", "Your account is ready.")

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == ["s1@example.com"]
    assert sent.subject == "Welcome"
    assert "account is ready" in sent.body


@pytest.mark.django_db
def test_smtp_attaches_an_html_alternative(db):
    SmtpEmailAdapter().send("s1@example.com", "Hi", "plain text", html="<p>rich</p>")

    assert mail.outbox[0].alternatives == [("<p>rich</p>", "text/html")]


@pytest.mark.django_db
def test_smtp_ignores_a_blank_recipient(db):
    SmtpEmailAdapter().send("", "Subject", "Body")

    assert mail.outbox == []


@pytest.mark.django_db
def test_smtp_uses_the_saved_db_connection_over_env(db, monkeypatch):
    """req 21: an SA-saved SMTP connection is what actually gets dialled."""
    save_connection(
        "email",
        "smtp",
        {"host": "smtp.saved.example", "port": 2525, "username": "saved-user", "use_tls": False},
        "saved-password",
    )
    captured = {}

    def fake_get_connection(**kwargs):
        captured.update(kwargs)
        return None  # None => EmailMessage falls back to the locmem test backend

    monkeypatch.setattr("core.adapters.smtp.get_connection", fake_get_connection)
    SmtpEmailAdapter().send("s1@example.com", "Subject", "Body")

    assert captured["host"] == "smtp.saved.example"
    assert captured["port"] == 2525
    assert captured["username"] == "saved-user"
    assert captured["password"] == "saved-password"
    assert captured["use_tls"] is False


@pytest.mark.django_db
def test_smtp_failure_never_breaks_the_caller(db, monkeypatch):
    """A provider outage must not bubble into the request that triggered the email."""

    def boom(self):
        raise OSError("smtp down")

    monkeypatch.setattr("core.adapters.smtp.EmailMultiAlternatives.send", boom)
    SmtpEmailAdapter().send("s1@example.com", "Subject", "Body")  # must not raise


# --------------------------- WhatsApp Cloud adapter ---------------------------


@pytest.mark.django_db
def test_whatsapp_sends_a_text_message(db, monkeypatch, settings):
    settings.WHATSAPP_ACCESS_TOKEN = "env-token"
    settings.WHATSAPP_PHONE_NUMBER_ID = "111222"
    settings.WHATSAPP_TEMPLATE_NAME = ""
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(url=url, json=json, headers=headers)
        return FakeResponse()

    monkeypatch.setattr("core.adapters.whatsapp_cloud.requests.post", fake_post)
    WhatsAppCloudAdapter().send("+919876500000", "Your class starts soon.")

    assert "111222/messages" in captured["url"]
    assert captured["headers"]["Authorization"] == "Bearer env-token"
    assert captured["json"]["type"] == "text"
    assert captured["json"]["to"] == "919876500000"  # leading + stripped
    assert captured["json"]["text"]["body"] == "Your class starts soon."


@pytest.mark.django_db
def test_whatsapp_uses_a_template_when_one_is_configured(db, monkeypatch, settings):
    settings.WHATSAPP_ACCESS_TOKEN = "env-token"
    settings.WHATSAPP_PHONE_NUMBER_ID = "111222"
    settings.WHATSAPP_TEMPLATE_NAME = "class_reminder"
    settings.WHATSAPP_TEMPLATE_LANG = "en"
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(json=json)
        return FakeResponse()

    monkeypatch.setattr("core.adapters.whatsapp_cloud.requests.post", fake_post)
    WhatsAppCloudAdapter().send("919876500000", "Starts in 15 minutes.")

    body = captured["json"]
    assert body["type"] == "template"
    assert body["template"]["name"] == "class_reminder"
    assert body["template"]["language"]["code"] == "en"
    assert body["template"]["components"][0]["parameters"][0]["text"] == "Starts in 15 minutes."


@pytest.mark.django_db
def test_whatsapp_prefers_the_saved_db_connection(db, monkeypatch, settings):
    settings.WHATSAPP_ACCESS_TOKEN = "env-token"
    settings.WHATSAPP_PHONE_NUMBER_ID = "env-phone"
    save_connection(
        "whatsapp",
        "whatsapp_cloud",
        {"phone_number_id": "db-phone", "template_name": ""},
        "db-token",
    )
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(url=url, headers=headers)
        return FakeResponse()

    monkeypatch.setattr("core.adapters.whatsapp_cloud.requests.post", fake_post)
    WhatsAppCloudAdapter().send("919876500000", "Hello")

    assert "db-phone/messages" in captured["url"]
    assert captured["headers"]["Authorization"] == "Bearer db-token"


@pytest.mark.django_db
def test_whatsapp_stays_silent_when_unconfigured(db, monkeypatch, settings):
    settings.WHATSAPP_ACCESS_TOKEN = ""
    settings.WHATSAPP_PHONE_NUMBER_ID = ""
    called = False

    def fake_post(*_args, **_kwargs):
        nonlocal called
        called = True
        return FakeResponse()

    monkeypatch.setattr("core.adapters.whatsapp_cloud.requests.post", fake_post)
    WhatsAppCloudAdapter().send("919876500000", "Hello")

    assert called is False, "must not call the provider without credentials"


@pytest.mark.django_db
def test_whatsapp_failure_never_breaks_the_caller(db, monkeypatch, settings):
    settings.WHATSAPP_ACCESS_TOKEN = "env-token"
    settings.WHATSAPP_PHONE_NUMBER_ID = "111222"

    def boom(*_args, **_kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr("core.adapters.whatsapp_cloud.requests.post", boom)
    WhatsAppCloudAdapter().send("919876500000", "Hello")  # must not raise


@pytest.mark.django_db
def test_whatsapp_logs_but_survives_a_provider_error_response(db, monkeypatch, settings):
    settings.WHATSAPP_ACCESS_TOKEN = "env-token"
    settings.WHATSAPP_PHONE_NUMBER_ID = "111222"

    monkeypatch.setattr(
        "core.adapters.whatsapp_cloud.requests.post",
        lambda *_a, **_k: FakeResponse(status_code=401, text="invalid token"),
    )
    WhatsAppCloudAdapter().send("919876500000", "Hello")  # must not raise


@pytest.mark.django_db
def test_a_user_with_no_phone_never_triggers_a_provider_call(db, monkeypatch, settings):
    """Guards the real-world case: notify() fans out to a user with a blank phone."""
    settings.WHATSAPP_ACCESS_TOKEN = "env-token"
    settings.WHATSAPP_PHONE_NUMBER_ID = "111222"
    student = User.objects.create_user(
        username="S9", password="x", role=Role.STUDENT, status=UserStatus.ACTIVE, phone=""
    )
    called = False

    def fake_post(*_args, **_kwargs):
        nonlocal called
        called = True
        return FakeResponse()

    monkeypatch.setattr("core.adapters.whatsapp_cloud.requests.post", fake_post)
    WhatsAppCloudAdapter().send(student.phone, "Hello")

    assert called is False
