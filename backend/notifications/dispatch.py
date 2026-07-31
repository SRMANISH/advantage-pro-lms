"""Async fan-out for the external notification channels.

In-app notifications are written synchronously (the bell must update immediately), but
email / SMS / WhatsApp are pushed to the django-q2 queue so a large fan-out — e.g.
scheduling a class for a 500-student batch — returns instantly instead of making 1,500
blocking provider calls in the request, and gets automatic retries on provider failure
(``Q_CLUSTER["retry"]``).

Dev / CI run with ``Q_CLUSTER["sync"] = True`` (no Redis): we call the deliverer inline so
behaviour is identical and tests need no broker. Prod (Redis set) enqueues to a
``python manage.py qcluster`` worker.
"""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger("lms.notifications")

_EXTERNAL = ("email", "sms", "whatsapp")


def queue_external(user_id, channels, subject: str, message: str, kind: str = "") -> None:
    """Send the external channels for one user — inline in sync mode, else via the queue."""
    wanted = [c for c in channels if c in _EXTERNAL]
    if not wanted:
        return
    if _sync_mode():
        deliver_external(user_id, wanted, subject, message, kind)
        return
    from django_q.tasks import async_task

    async_task(
        "notifications.dispatch.deliver_external",
        user_id,
        wanted,
        subject,
        message,
        kind,
        task_name="notify-external",
    )


class NotificationDeliveryError(RuntimeError):
    """Raised only when *every* attempted channel failed unexpectedly — see below."""


def deliver_external(user_id, channels, subject: str, message: str, kind: str = "") -> None:
    """Worker entry point: load the user and hit each configured provider adapter.

    Each channel is isolated. The adapters already swallow their own provider errors — they
    have to, because setup and password-reset call them straight from the request path and a
    provider outage must not 500 someone resetting their password. But msg91 and
    whatsapp_cloud only catch ``requests.RequestException``: a malformed config raising
    KeyError, or a JSON decode error, escapes and would abort every channel queued after it.
    A student could lose their SMS *and* WhatsApp because the email template had a bad key.

    Re-raise policy. Because the adapters absorb provider failures, this cannot tell a
    successful send from a refused one, so re-raising on "delivery failed" is not achievable
    without changing an adapter contract that exists for good reason. What it *can* see is an
    exception that escaped an adapter — unexpected by definition, and the class worth
    retrying. So it re-raises when **every** attempted channel failed that way, which is both
    the signal that something systemic is wrong and the only case where a django-q2 retry
    cannot produce a duplicate, since nothing was delivered. A partial failure is logged and
    left alone: retrying would re-send the channels that worked.

    Not re-raised in sync mode, where this runs inline in the caller's request.

    ``kind`` defaults so that tasks already queued with the old four-argument signature still
    execute after a deploy.
    """
    from accounts.models import User
    from core.adapters.registry import get_email, get_sms, get_whatsapp

    user = User.objects.filter(id=user_id).first()
    if user is None:
        return

    sends = []
    if "email" in channels and user.email:
        sends.append(("email", lambda: get_email().send(user.email, subject, message)))
    if "sms" in channels and user.phone:
        sends.append(("sms", lambda: get_sms().send(user.phone, message)))
    if "whatsapp" in channels and user.phone:
        sends.append(("whatsapp", lambda: get_whatsapp().send(user.phone, message)))

    failures = []
    for channel, send in sends:
        try:
            send()
        except Exception:
            failures.append(channel)
            # user_id, not the address: this line goes to stdout and on to Sentry, and the
            # recipient's email or phone has no business in either. The id identifies the
            # account for anyone debugging, without putting PII in the log stream.
            logger.exception(
                "Notification delivery failed: channel=%s user_id=%s kind=%s",
                channel,
                user_id,
                kind or "(unset)",
            )

    if sends and len(failures) == len(sends) and not _sync_mode():
        raise NotificationDeliveryError(
            f"All {len(sends)} channel(s) failed for user_id={user_id} kind={kind or '(unset)'}"
        )


def _sync_mode() -> bool:
    return bool(getattr(settings, "Q_CLUSTER", {}).get("sync", True))
