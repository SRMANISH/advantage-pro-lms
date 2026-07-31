"""Failure isolation: one broken dependency must not take the rest down with it."""

import logging
from unittest import mock

import pytest
from django.urls import path
from rest_framework.views import APIView

from core.adapters.base import mask_recipient
from core.roles import Role
from notifications.dispatch import NotificationDeliveryError, deliver_external
from notifications.models import Notification

from .helpers import user

# --------------------------- per-channel isolation ---------------------------


@pytest.fixture
def recipient(db):
    return user("res_stu", Role.STUDENT, email="res@example.com", phone="9876500123")


def _adapters(email=None, sms=None, whatsapp=None):
    """Patch the three registry getters, each returning a mock whose send() may raise."""

    def make(exc):
        m = mock.Mock()
        m.send.side_effect = exc
        return m

    return (
        mock.patch("core.adapters.registry.get_email", return_value=make(email)),
        mock.patch("core.adapters.registry.get_sms", return_value=make(sms)),
        mock.patch("core.adapters.registry.get_whatsapp", return_value=make(whatsapp)),
    )


@pytest.mark.django_db
def test_a_failing_channel_does_not_stop_the_others(recipient, caplog):
    """The regression test. msg91 and whatsapp_cloud only catch RequestException, so a
    KeyError from a malformed config used to escape and abort every channel behind it."""
    e, s, w = _adapters(email=KeyError("bad config"))
    with e as ge, s as gs, w as gw, caplog.at_level(logging.ERROR):
        deliver_external(recipient.id, ["email", "sms", "whatsapp"], "subj", "msg", "test_kind")

    ge.return_value.send.assert_called_once()
    gs.return_value.send.assert_called_once()  # still sent despite the email blowing up
    gw.return_value.send.assert_called_once()


@pytest.mark.django_db
def test_the_failure_log_names_the_channel_and_kind_but_not_the_address(recipient, caplog):
    e, s, w = _adapters(email=RuntimeError("boom"))
    with e, s, w, caplog.at_level(logging.ERROR):
        deliver_external(recipient.id, ["email"], "subj", "msg", "certificate_pending")

    text = caplog.text
    assert "channel=email" in text
    assert "certificate_pending" in text
    assert str(recipient.id) in text  # identifiable...
    assert "res@example.com" not in text  # ...without the address itself


@pytest.mark.django_db
def test_a_partial_failure_is_not_retried(recipient, settings):
    """Re-raising here would make django-q2 replay the whole task and re-send the channels
    that already worked — a duplicate SMS is worse than a missing one."""
    settings.Q_CLUSTER = {**settings.Q_CLUSTER, "sync": False}
    e, s, w = _adapters(email=RuntimeError("boom"))
    with e, s, w:
        deliver_external(recipient.id, ["email", "sms"], "subj", "msg", "k")  # must not raise


@pytest.mark.django_db
def test_a_total_failure_raises_so_the_queue_retries(recipient, settings):
    """Nothing was delivered, so a retry cannot duplicate — and total failure is the signal
    that something systemic (network, credentials) is wrong."""
    settings.Q_CLUSTER = {**settings.Q_CLUSTER, "sync": False}
    e, s, w = _adapters(email=RuntimeError("boom"), sms=RuntimeError("boom"))
    with e, s, w, pytest.raises(NotificationDeliveryError):
        deliver_external(recipient.id, ["email", "sms"], "subj", "msg", "k")


@pytest.mark.django_db
def test_sync_mode_never_raises(recipient, settings):
    """In sync mode this runs inline in the caller's request; raising would turn a provider
    outage into a failed password reset."""
    settings.Q_CLUSTER = {**settings.Q_CLUSTER, "sync": True}
    e, s, w = _adapters(email=RuntimeError("boom"), sms=RuntimeError("boom"))
    with e, s, w:
        deliver_external(recipient.id, ["email", "sms"], "subj", "msg", "k")


@pytest.mark.django_db
def test_notify_still_writes_the_in_app_row_when_every_provider_is_down(recipient, settings):
    """The in-app bell is the fallback channel and must survive a provider outage."""
    settings.Q_CLUSTER = {**settings.Q_CLUSTER, "sync": True}
    from notifications.services import notify

    e, s, w = _adapters(email=RuntimeError("x"), sms=RuntimeError("x"), whatsapp=RuntimeError("x"))
    with e, s, w:
        notify(recipient, "k", "body", channels=("in_app", "email", "sms"))

    assert Notification.objects.filter(recipient=recipient, kind="k").exists()


# --------------------------- recipient masking ---------------------------


@pytest.mark.parametrize(
    "raw,expected_absent",
    [
        ("asha.nair@example.com", "asha.nair"),
        ("9876500123", "9876500"),
        ("a@b.com", "a@b.com"),
    ],
)
def test_masking_hides_the_identifying_part(raw, expected_absent):
    masked = mask_recipient(raw)
    assert expected_absent not in masked or masked == "(none)"


def test_masking_keeps_enough_to_correlate():
    assert mask_recipient("asha.nair@example.com").endswith("@example.com")
    assert mask_recipient("9876500123").endswith("0123")
    assert mask_recipient("") == "(none)"
    assert mask_recipient(None) == "(none)"  # type: ignore[arg-type]


# --------------------------- readiness probe ---------------------------


@pytest.mark.django_db
def test_readiness_reports_ready_when_both_dependencies_answer(client):
    resp = client.get("/api/v1/ready/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.django_db
def test_readiness_returns_503_and_names_the_failed_dependency(client):
    with mock.patch("core.health.cache.set", side_effect=RuntimeError("redis down")):
        resp = client.get("/api/v1/ready/")
    assert resp.status_code == 503
    assert resp.json()["failed"] == ["cache"]


@pytest.mark.django_db
def test_readiness_catches_a_cache_that_silently_drops_writes(client):
    """A get()-only probe would pass against a cache that stores nothing."""
    with mock.patch("core.health.cache.get", return_value=None):
        resp = client.get("/api/v1/ready/")
    assert resp.status_code == 503
    assert "cache" in resp.json()["failed"]


@pytest.mark.django_db
def test_liveness_stays_static_so_a_database_blip_does_not_restart_every_container(client):
    with mock.patch("core.health._check_database", return_value="database"):
        assert client.get("/api/v1/health/").status_code == 200


# --------------------------- unhandled 500s ---------------------------


class _Exploding(APIView):
    permission_classes: list = []

    def get(self, request):
        # A database-flavoured message, to prove none of it reaches the client.
        raise RuntimeError('duplicate key value violates unique constraint "users_email_key"')


urlpatterns = [path("api/v1/_boom/", _Exploding.as_view())]


@pytest.mark.django_db
def test_an_unhandled_error_returns_the_standard_envelope_not_html(client, settings):
    """Django's default 500 is an HTML page. The frontend's error handling reads `detail`
    from JSON, so an HTML body means the user sees nothing at all."""
    settings.DEBUG = False
    settings.ROOT_URLCONF = __name__

    resp = client.get("/api/v1/_boom/")

    assert resp.status_code == 500
    assert resp["Content-Type"].startswith("application/json")
    body = resp.json()
    assert set(body) == {"detail", "errors"}  # same shape as every other error


@pytest.mark.django_db
def test_the_500_body_leaks_no_internals(client, settings):
    settings.DEBUG = False
    settings.ROOT_URLCONF = __name__

    body = client.get("/api/v1/_boom/").content.decode()

    for leak in (
        "duplicate key",
        "unique constraint",
        "users_email_key",
        "RuntimeError",
        "Traceback",
        "core/exceptions.py",
    ):
        assert leak not in body, f"leaked: {leak}"


@pytest.mark.django_db
def test_the_error_is_still_logged_so_sentry_sees_it(client, settings, caplog):
    """Load-bearing: returning a Response stops DRF re-raising, so Django never fires
    got_request_exception and Sentry's Django integration goes blind. The ERROR log is what
    keeps it reported."""
    settings.DEBUG = False
    settings.ROOT_URLCONF = __name__

    with caplog.at_level(logging.ERROR, logger="lms.api"):
        client.get("/api/v1/_boom/")

    assert any(r.levelno >= logging.ERROR and r.exc_info for r in caplog.records)
