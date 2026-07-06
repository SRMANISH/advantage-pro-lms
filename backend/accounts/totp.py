"""Staff TOTP two-factor authentication (RFC 6238) — optional, per account.

Students are never prompted; this is scoped to staff per the audit ("consider TOTP for
staff"). Enrollment is two-step — generate a pending secret, then confirm one valid code —
so a mistyped authenticator app can never lock an account out silently: an unconfirmed
device is never consulted at login (see ``views/auth.py``).
"""

from __future__ import annotations

import pyotp
from django.utils import timezone

from .models import TOTPDevice, User

ISSUER = "Advantage Pro"


def get_or_create_pending(user: User) -> TOTPDevice:
    """Return the user's TOTP device, (re)issuing a fresh secret while unconfirmed.

    Raises ``ValueError`` if TOTP is already enabled — disable it first to re-enroll.
    """
    device, created = TOTPDevice.objects.get_or_create(
        user=user, defaults={"secret": pyotp.random_base32()}
    )
    if not created:
        if device.confirmed:
            raise ValueError("Two-factor authentication is already enabled.")
        # Re-issue rather than expose the same stale secret from an abandoned attempt.
        device.secret = pyotp.random_base32()
        device.save(update_fields=["secret"])
    return device


def provisioning_uri(device: TOTPDevice) -> str:
    return pyotp.TOTP(device.secret).provisioning_uri(name=device.user.username, issuer_name=ISSUER)


def verify(device: TOTPDevice, code: str) -> bool:
    """Check ``code`` against ``device``, allowing ±1 time-step (~30s) of clock drift."""
    if not code:
        return False
    return pyotp.TOTP(device.secret).verify(code, valid_window=1)


def confirm(device: TOTPDevice, code: str) -> bool:
    """Verify the first code and, on success, mark the device trusted for login."""
    if not verify(device, code):
        return False
    device.confirmed = True
    device.confirmed_at = timezone.now()
    device.save(update_fields=["confirmed", "confirmed_at"])
    return True
