"""Liveness and readiness probes.

The two answer different questions and must not be conflated.

**Liveness** (``/api/v1/health/``, unchanged) asks "is this process running?" It is
deliberately static: if it consulted the database, a database blip would make every container
look dead and an orchestrator would restart them all — turning a recoverable dependency
outage into an outage of the application too.

**Readiness** (``/api/v1/ready/``) asks "can this process actually serve a request?" That
means the things every request needs: the database, and the cache that backs sessions and
every rate limit. A container that cannot reach either should be taken out of the load
balancer's rotation but left running.
"""

from __future__ import annotations

import logging
import uuid

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger("lms.health")


def health(_request):
    """Liveness: static by design. See the module docstring."""
    return JsonResponse({"status": "ok", "service": "advantage-pro-lms"})


def _check_database() -> str | None:
    """Cheapest possible round-trip that proves a usable connection. Returns an error label."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Readiness: database check failed")
        return "database"
    return None


def _check_cache() -> str | None:
    """Write-then-read, not just a read: a misconfigured cache can return None for everything
    and look healthy to a get()-only probe. The key is unique per call so concurrent probes
    from several containers cannot mask each other."""
    key = f"readiness:{uuid.uuid4()}"
    try:
        cache.set(key, "1", timeout=10)
        if cache.get(key) != "1":
            logger.error("Readiness: cache round-trip returned the wrong value")
            return "cache"
        cache.delete(key)
    except Exception:
        logger.exception("Readiness: cache check failed")
        return "cache"
    return None


def readiness(_request):
    """503 with the failing dependencies named, so an operator sees which one is down."""
    failed = [name for name in (_check_database(), _check_cache()) if name]
    if failed:
        return JsonResponse(
            {"status": "unavailable", "failed": failed},
            status=503,
        )
    return JsonResponse({"status": "ready", "checks": ["database", "cache"]})
