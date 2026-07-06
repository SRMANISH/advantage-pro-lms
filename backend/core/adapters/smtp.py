"""SMTP email adapter — delegates to Django's own EmailMessage/SMTP backend.

Configure via the standard Django EMAIL_* settings (EMAIL_HOST, EMAIL_PORT,
EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, DEFAULT_FROM_EMAIL) — Hostinger's
SMTP (or any provider) works here with no code changes, only env values.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from .base import EmailAdapter

logger = logging.getLogger("lms.adapters")


class SmtpEmailAdapter(EmailAdapter):
    def send(self, to: str, subject: str, body: str, *, html: str | None = None) -> None:
        if not to:
            return
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            to=[to],
        )
        if html:
            message.attach_alternative(html, "text/html")
        try:
            message.send(fail_silently=False)
        except Exception:
            # Never let a provider outage break the request that triggered the email —
            # log loudly so it's visible in monitoring, and let the caller move on.
            logger.exception("SMTP send failed for %s (subject=%r)", to, subject)
