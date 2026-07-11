"""In-app notifications (the bell). Other channels are sent via the adapters."""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Notification(TimeStampedModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=50)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "read"]),
            models.Index(fields=["recipient", "kind"]),  # per-kind dedupe (reminders)
            models.Index(fields=["created_at"]),  # retention sweeps
        ]

    def __str__(self) -> str:
        return f"{self.kind} -> {self.recipient_id}"


class IntegrationSetting(TimeStampedModel):
    """Super-Admin-managed third-party connection settings (req 21).

    One row per channel. ``config`` holds non-secret settings (sender id, host, region);
    ``secret`` holds the API key / password and is never returned to the client — only a
    ``secret_set`` boolean is exposed. The matching provider adapter reads these when it is
    the one selected in ``LMS_ADAPTERS``; the console/dev stubs ignore them.
    """

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        WHATSAPP = "whatsapp", "WhatsApp"
        STORAGE = "storage", "File storage"

    channel = models.CharField(max_length=20, choices=Channel.choices, unique=True)
    provider = models.CharField(max_length=50, blank=True)  # e.g. smtp, msg91, whatsapp_cloud
    config = models.JSONField(default=dict, blank=True)  # non-secret settings
    secret = models.CharField(max_length=255, blank=True)  # API key / password (write-only)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    def __str__(self) -> str:
        return f"{self.channel}:{self.provider or 'unset'}"
