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


def queue_external(user_id, channels, subject: str, message: str) -> None:
    """Send the external channels for one user — inline in sync mode, else via the queue."""
    wanted = [c for c in channels if c in _EXTERNAL]
    if not wanted:
        return
    if _sync_mode():
        deliver_external(user_id, wanted, subject, message)
        return
    from django_q.tasks import async_task

    async_task(
        "notifications.dispatch.deliver_external",
        user_id,
        wanted,
        subject,
        message,
        task_name="notify-external",
    )


def deliver_external(user_id, channels, subject: str, message: str) -> None:
    """Worker entry point: load the user and hit each configured provider adapter."""
    from accounts.models import User
    from core.adapters.registry import get_email, get_sms, get_whatsapp

    user = User.objects.filter(id=user_id).first()
    if user is None:
        return
    if "email" in channels and user.email:
        get_email().send(user.email, subject, message)
    if "sms" in channels and user.phone:
        get_sms().send(user.phone, message)
    if "whatsapp" in channels and user.phone:
        get_whatsapp().send(user.phone, message)


def _sync_mode() -> bool:
    return bool(getattr(settings, "Q_CLUSTER", {}).get("sync", True))
