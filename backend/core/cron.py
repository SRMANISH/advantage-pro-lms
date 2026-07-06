"""Overlap guard for scheduled management commands.

Two cron triggers firing close together (a slow run plus the next scheduled tick, or two
scheduler processes in a multi-instance deploy) must not run the same job concurrently —
escalations/reminders would double-send, and purge could double-count. ``cache.add`` is
atomic on every Django cache backend (LocMemCache and RedisCache alike), which is exactly
the primitive a mutex needs, so this works identically in dev (LocMemCache) and prod
(Redis) with no extra infrastructure.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.core.cache import cache

_PREFIX = "cron-lock:"


class LockHeld(Exception):
    """Raised when another process already holds the named lock."""


@contextmanager
def cron_lock(name: str, timeout: int = 600) -> Iterator[None]:
    """Hold an exclusive lock for ``name`` for the duration of the block.

    Raises :class:`LockHeld` immediately (without blocking) if another run already holds
    it. ``timeout`` is a safety net, not the expected runtime: if a process dies while
    holding the lock, it self-heals after ``timeout`` seconds rather than wedging the job
    forever.
    """
    key = _PREFIX + name
    if not cache.add(key, "1", timeout=timeout):
        raise LockHeld(f"'{name}' is already running elsewhere — skipping this run.")
    try:
        yield
    finally:
        cache.delete(key)
