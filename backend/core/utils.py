"""Small shared helpers."""

from __future__ import annotations

from django.conf import settings


def get_client_ip(request) -> str | None:
    """Best-effort client IP, honouring ``X-Forwarded-For`` only as far as it is trustworthy.

    ``X-Forwarded-For`` is client-supplied. Our nginx front end uses
    ``$proxy_add_x_forwarded_for``, which *appends* the real peer address to whatever the
    client sent — so the header reads ``<anything the client made up>, <real IP>``, and only
    the **rightmost** entries were written by infrastructure we control. Reading the leftmost
    entry (the previous behaviour) returns a value the caller chose, which would let anyone
    forge the IP recorded on audit rows, login events and device-change requests.

    ``TRUSTED_PROXY_COUNT`` is how many proxies sit in front of Django: 1 for the documented
    nginx topology, 2 if a CDN or load balancer is added ahead of it. With N proxies the
    Nth-from-the-right entry is the address the outermost trusted hop actually observed. It
    defaults to 0 — Django exposed directly, header ignored — because guessing high is the
    unsafe direction: it starts trusting entries the client wrote.
    """
    proxies = int(getattr(settings, "TRUSTED_PROXY_COUNT", 0))
    remote_addr = request.META.get("REMOTE_ADDR")
    if proxies <= 0:
        return remote_addr

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if not forwarded:
        return remote_addr
    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    if not parts:
        return remote_addr
    # Count in from the right, clamped: a client can lengthen the header, but it cannot push
    # its own value past the entries our proxies appended after it.
    return parts[-min(proxies, len(parts))]
