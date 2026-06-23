"""Local/dev adapter implementations.

These keep development self-contained (filesystem storage, console-logged messages,
immediate task execution). Production swaps them for Hostinger / 3rd-party adapters via
settings — no call-site changes.
"""

import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from django.conf import settings

from .base import EmailAdapter, SchedulerAdapter, SmsAdapter, StorageAdapter, WhatsAppAdapter

logger = logging.getLogger("lms.adapters")


class LocalStorageAdapter(StorageAdapter):
    def _path(self, key: str) -> Path:
        root = Path(settings.MEDIA_ROOT)
        root.mkdir(parents=True, exist_ok=True)
        return root / key

    def save(self, key: str, fileobj: BinaryIO) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as dst:
            shutil.copyfileobj(fileobj, dst)
        return key

    def url(self, key: str, expires_in: int = 3600) -> str:
        return f"{settings.MEDIA_URL}{key}"

    def open(self, key: str) -> BinaryIO:
        return self._path(key).open("rb")

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class ConsoleEmailAdapter(EmailAdapter):
    def send(self, to: str, subject: str, body: str, *, html: str | None = None) -> None:
        logger.info("EMAIL -> %s | %s | %s", to, subject, body)


class ConsoleSmsAdapter(SmsAdapter):
    def send(self, to: str, message: str) -> None:
        logger.info("SMS -> %s | %s", to, message)


class ConsoleWhatsAppAdapter(WhatsAppAdapter):
    def send(self, to: str, message: str) -> None:
        logger.info("WHATSAPP -> %s | %s", to, message)


class ImmediateScheduler(SchedulerAdapter):
    """Dev scheduler: logs the intent. A real scheduler (django-q2/Celery) replaces it."""

    def schedule(self, run_at: datetime, task: str, payload: dict) -> str:
        job_id = str(uuid.uuid4())
        logger.info("SCHEDULE [%s] %s at %s | %s", job_id, task, run_at.isoformat(), payload)
        return job_id

    def cancel(self, job_id: str) -> None:
        logger.info("CANCEL job %s", job_id)
