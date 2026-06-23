"""Small shared helpers."""

from __future__ import annotations


def get_client_ip(request) -> str | None:
    """Best-effort client IP, honouring a proxy's X-Forwarded-For."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
