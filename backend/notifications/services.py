"""Provider-agnostic notification service: in-app (sync) + email/SMS/WhatsApp (queued)."""

from __future__ import annotations

from .dispatch import queue_external
from .models import Notification

# Notifications must be sent AFTER the surrounding transaction commits, never inside it.
#
# An in-app row would roll back with the transaction, but an email, SMS or WhatsApp already
# handed to a provider cannot be unsent — so a rolled-back operation would leave the user
# holding a message about something that never happened. All current callers get this right
# by calling notify()/notify_many() *after* their `with transaction.atomic():` block closes;
# a caller that genuinely must notify from inside one should wrap it:
#
#     transaction.on_commit(lambda: notify(user, kind, message))
#
# The queue itself is a second line of defence, not a substitute: django-q2 is configured
# with the ORM broker, so an enqueued task rolls back with the transaction that created it
# (see config/settings/base.py). That protection disappears the moment the broker changes.


def notify(user, kind, message, *, link="", subject=None, channels=("in_app",)):
    """Deliver a notification to one user.

    The in-app row is written synchronously so the notification bell updates at once; the
    external channels (email/SMS/WhatsApp) are handed to the queue (see ``dispatch``) so a
    large fan-out never blocks the request and gets retries on provider failure.
    """
    note = None
    if "in_app" in channels:
        note = Notification.objects.create(recipient=user, kind=kind, message=message, link=link)
    queue_external(user.id, channels, subject or kind, message, kind)
    return note


def notify_many(users, kind, message, **kwargs):
    return [notify(u, kind, message, **kwargs) for u in users]


def admins_and_mis():
    from accounts.models import User
    from core.roles import Role

    return list(User.objects.filter(role__in=[Role.ADMIN, Role.MIS]))


def batch_student_users(batch):
    from accounts.models import User

    return list(User.objects.filter(enrollments__batch=batch))
