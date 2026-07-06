"""Shared abstract models + platform-level configuration models."""

import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """UUID primary key + created/updated timestamps for every domain model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PermissionOverride(TimeStampedModel):
    """Super-Admin-edited replacement for one action's allowed-roles set.

    The code-defined matrix in ``core/permissions_matrix.py`` stays the default; a row
    here replaces the role set for that single action. Deleting the row reverts the
    action to its default. Consulted by ``permissions_matrix.can()`` through a short
    cache, so edits apply platform-wide within seconds without a deploy.
    """

    action = models.CharField(max_length=64, unique=True)
    roles = models.JSONField(default=list)  # list[str] of Role values
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    def __str__(self) -> str:
        return f"{self.action} -> {sorted(self.roles)}"
