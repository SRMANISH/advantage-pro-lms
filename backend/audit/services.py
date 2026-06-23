"""Helper for recording audit entries from anywhere in the app."""

from __future__ import annotations

from .models import AuditLog


def record_action(
    *,
    actor=None,
    action: str,
    target=None,
    target_type: str = "",
    target_id: str = "",
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Write an audit entry. Pass either a ``target`` model instance or explicit ids."""
    if target is not None and not target_type:
        target_type = target.__class__.__name__
        target_id = str(getattr(target, "pk", ""))
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
        ip_address=ip_address,
    )
