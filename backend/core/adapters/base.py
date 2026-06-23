"""Abstract interfaces for every external integration."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import BinaryIO


class StorageAdapter(ABC):
    """Stores and serves files (videos, notes, task uploads)."""

    @abstractmethod
    def save(self, key: str, fileobj: BinaryIO) -> str:
        """Persist ``fileobj`` under ``key`` and return the stored key."""

    @abstractmethod
    def url(self, key: str, expires_in: int = 3600) -> str:
        """Return a (preferably signed, time-limited) URL to read ``key``."""

    @abstractmethod
    def open(self, key: str) -> BinaryIO:
        """Open the stored object for reading."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the stored object."""


class EmailAdapter(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str, *, html: str | None = None) -> None: ...


class SmsAdapter(ABC):
    @abstractmethod
    def send(self, to: str, message: str) -> None: ...


class WhatsAppAdapter(ABC):
    @abstractmethod
    def send(self, to: str, message: str) -> None: ...


class SchedulerAdapter(ABC):
    """Schedules deferred work (reminders, escalations, certificate follow-ups)."""

    @abstractmethod
    def schedule(self, run_at: datetime, task: str, payload: dict) -> str:
        """Queue ``task`` to run at ``run_at``; return a job id."""

    @abstractmethod
    def cancel(self, job_id: str) -> None: ...
