"""SMTP email adapter — delegates to Django's own EmailMessage/SMTP backend.

Configure via the standard Django EMAIL_* settings (EMAIL_HOST, EMAIL_PORT,
EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, DEFAULT_FROM_EMAIL) — Hostinger's
SMTP (or any provider) works here with no code changes, only env values.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from .base import EmailAdapter, mask_recipient

logger = logging.getLogger("lms.adapters")


class SmtpEmailAdapter(EmailAdapter):
    def send(self, to: str, subject: str, body: str, *, html: str | None = None) -> None:
        if not to:
            return
        # SA-saved SMTP connection (Channels page) first, then Django's EMAIL_* env settings.
        from core.integrations import integration_config

        cfg = integration_config("email")
        c = cfg["config"]
        from_email = c.get("from_email") or getattr(settings, "DEFAULT_FROM_EMAIL", None)
        connection = None
        if cfg["secret"] or c.get("host") or c.get("username"):
            connection = get_connection(
                host=c.get("host") or getattr(settings, "EMAIL_HOST", ""),
                port=int(c.get("port") or getattr(settings, "EMAIL_PORT", 587)),
                username=c.get("username") or getattr(settings, "EMAIL_HOST_USER", ""),
                password=cfg["secret"] or getattr(settings, "EMAIL_HOST_PASSWORD", ""),
                use_tls=bool(c.get("use_tls", getattr(settings, "EMAIL_USE_TLS", True))),
            )
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[to],
            connection=connection,
        )
        if html:
            message.attach_alternative(html, "text/html")
        try:
            message.send(fail_silently=False)
        except Exception:
            # Never let a provider outage break the request that triggered the email —
            # log loudly so it's visible in monitoring, and let the caller move on.
            logger.exception("SMTP send failed: to=%s subject=%r", mask_recipient(to), subject)
