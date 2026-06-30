"""Per-batch doubt forum: threads and replies."""

from django.conf import settings
from django.db import models

from batches.models import Batch
from core.models import TimeStampedModel


class ThreadStatus(models.TextChoices):
    OPEN = "open", "Open"
    ANSWERED = "answered", "Answered"
    RESOLVED = "resolved", "Resolved"
    ESCALATED = "escalated", "Escalated"


class Thread(TimeStampedModel):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="threads")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads"
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    # ``resolved`` kept as a compatibility flag; ``status`` is the richer lifecycle.
    resolved = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10, choices=ThreadStatus.choices, default=ThreadStatus.OPEN
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:
        return self.title


class Reply(TimeStampedModel):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="thread_replies"
    )
    body = models.TextField()

    class Meta:
        ordering = ["created_at"]
