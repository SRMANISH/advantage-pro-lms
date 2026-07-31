"""Response serializers for the plain ``APIView``s that return hand-built dicts.

Most of this API is built from DRF generics and viewsets, where drf-spectacular can infer the
response from ``serializer_class``. A layer of small action endpoints is not — they return
``Response({...})`` directly, and spectacular emitted "unable to guess serializer" for each,
listing the endpoint in the schema with no response body at all.

These are declaration-only: they exist so ``@extend_schema(responses=...)`` has something
concrete to point at, and are never used to validate or render. Keeping them here rather than
inline in each view means the recurring shapes (``{"ok": true}``, ``{"detail": "..."}``) are
defined once and stay consistent.
"""

from __future__ import annotations

from rest_framework import serializers


class OkResponse(serializers.Serializer):
    """``{"ok": true}`` — the acknowledgement returned by most action endpoints."""

    ok = serializers.BooleanField()


class DetailResponse(serializers.Serializer):
    """``{"detail": "..."}`` — a human-readable message, used for errors and confirmations."""

    detail = serializers.CharField()


class CountResponse(serializers.Serializer):
    """``{"count": n}`` — an unread/pending tally."""

    count = serializers.IntegerField()


class TokenResponse(serializers.Serializer):
    """A step in the account-setup / password-reset flows.

    ``dev_code`` is only ever populated when ``DEBUG`` is on, so local flows can be completed
    without a real email or SMS. It is absent in production.
    """

    token = serializers.CharField()
    stage = serializers.CharField(required=False)
    dev_code = serializers.CharField(required=False, allow_blank=True)


# --------------------------- recurring request bodies ---------------------------
# Declaration-only, same as the responses above: these endpoints validate by hand or via a
# service, so these exist purely so the schema documents what to send.


class CodeRequest(serializers.Serializer):
    """A 6-digit verification code."""

    code = serializers.CharField(max_length=10)


class PasswordRequest(serializers.Serializer):
    """The caller's current password, used to confirm a sensitive change."""

    password = serializers.CharField(write_only=True)


class TokenCodeRequest(serializers.Serializer):
    """A flow token plus the code that was emailed or texted."""

    token = serializers.CharField()
    code = serializers.CharField(max_length=10)


class TokenPasswordRequest(serializers.Serializer):
    """A flow token plus the new password to set."""

    token = serializers.CharField()
    password = serializers.CharField(write_only=True)
