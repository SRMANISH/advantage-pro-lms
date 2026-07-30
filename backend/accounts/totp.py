"""Staff TOTP two-factor authentication (RFC 6238) — optional, per account.

Students are never prompted; this is scoped to staff per the audit ("consider TOTP for
staff"). Enrollment is two-step — generate a pending secret, then confirm one valid code —
so a mistyped authenticator app can never lock an account out silently: an unconfirmed
device is never consulted at login (see ``views/auth.py``).
"""

from __future__ import annotations

import pyotp
from django.db.models import F
from django.utils import timezone

from .models import TOTPDevice, User

ISSUER = "Advantage Pro"

# Consecutive wrong codes before the device refuses further attempts. Mirrors the email/phone
# OTP cap in ``setup.py``; the throttle in front of the view bounds request *rate*, this
# bounds total guesses against one secret regardless of how the attacker spreads them out.
MAX_ATTEMPTS = 5


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
        # Re-issue rather than expose the same stale secret from an abandoned attempt, and
        # clear the attempt counter — this is a fresh enrollment, not a continued guess.
        device.secret = pyotp.random_base32()
        device.failed_attempts = 0
        device.save(update_fields=["secret", "failed_attempts"])
    return device


def provisioning_uri(device: TOTPDevice) -> str:
    return pyotp.TOTP(device.secret).provisioning_uri(name=device.user.username, issuer_name=ISSUER)


def attempts_exhausted(device: TOTPDevice) -> bool:
    return device.failed_attempts >= MAX_ATTEMPTS


def verify(device: TOTPDevice, code: str) -> bool:
    """Check ``code`` against ``device``, allowing ±1 time-step (~30s) of clock drift.

    Enforces the per-device attempt cap: once ``MAX_ATTEMPTS`` consecutive codes have failed
    the device refuses to verify at all until it is re-enrolled (or, for a confirmed device,
    reset by disabling and re-enabling 2FA). A correct code clears the counter.
    """
    if not code or attempts_exhausted(device):
        return False

    if pyotp.TOTP(device.secret).verify(code, valid_window=1):
        if device.failed_attempts:
            device.failed_attempts = 0
            device.save(update_fields=["failed_attempts", "updated_at"])
        return True

    # Claim the attempt atomically so parallel guesses cannot share one slot.
    TOTPDevice.objects.filter(pk=device.pk).update(failed_attempts=F("failed_attempts") + 1)
    device.refresh_from_db(fields=["failed_attempts"])
    return False


def confirm(device: TOTPDevice, code: str) -> bool:
    """Verify the first code and, on success, mark the device trusted for login."""
    if not verify(device, code):
        return False
    device.confirmed = True
    device.confirmed_at = timezone.now()
    device.save(update_fields=["confirmed", "confirmed_at"])
    return True
