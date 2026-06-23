"""Provider-agnostic notification service: in-app + email/SMS/WhatsApp via adapters."""

from __future__ import annotations

from core.adapters.registry import get_email, get_sms, get_whatsapp

from .models import Notification


def notify(user, kind, message, *, link="", subject=None, channels=("in_app",)):
    """Deliver a notification to one user across the requested channels."""
    note = None
    if "in_app" in channels:
        note = Notification.objects.create(recipient=user, kind=kind, message=message, link=link)
    if "email" in channels and getattr(user, "email", ""):
        get_email().send(user.email, subject or kind, message)
    if "sms" in channels and getattr(user, "phone", ""):
        get_sms().send(user.phone, message)
    if "whatsapp" in channels and getattr(user, "phone", ""):
        get_whatsapp().send(user.phone, message)
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
