"""Staff TOTP two-factor authentication (RFC 6238) — optional, per account.

Students are never prompted; this is scoped to staff per the audit ("consider TOTP for
staff"). Enrollment is two-step — generate a pending secret, then confirm one valid code —
so a mistyped authenticator app can never lock an account out silently: an unconfirmed
device is never consulted at login (see ``views/auth.py``).
"""

from __future__ import annotations

import hmac

import pyotp
from django.db.models import F, Q
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


def _matching_step(device: TOTPDevice, code: str) -> int | None:
    """The time-step ``code`` is valid for, or None. Checks the same ±1 window as pyotp."""
    totp = pyotp.TOTP(device.secret)
    now_step = int(timezone.now().timestamp()) // totp.interval
    for step in (now_step - 1, now_step, now_step + 1):
        if hmac.compare_digest(totp.at(step * totp.interval), code):
            return step
    return None


def verify(device: TOTPDevice, code: str) -> bool:
    """Check ``code`` against ``device``, allowing ±1 time-step (~30s) of clock drift.

    Enforces two things beyond "is the arithmetic right":

    *Attempt cap* — once ``MAX_ATTEMPTS`` consecutive codes have failed the device refuses to
    verify at all, until a Super Admin resets it (``reset_attempts``) or the user re-enrolls.

    *Replay* — a TOTP code is valid for its entire ~30s step, and the drift window widens that
    to ~90s. A code seen once (over a shoulder, in a screenshot, in a proxy log) could be used
    again inside that window. Each accepted step is recorded and never accepted twice, which
    is what RFC 6238 §5.2 asks for.
    """
    if not code or attempts_exhausted(device):
        return False

    step = _matching_step(device, code)
    if step is not None:
        # Conditional UPDATE, not a read-then-write: two requests replaying the same code
        # concurrently would both see last_used_step as older and both be let through.
        # Filtering on it means the database admits exactly one.
        claimed = TOTPDevice.objects.filter(
            Q(pk=device.pk),
            Q(last_used_step__isnull=True) | Q(last_used_step__lt=step),
        ).update(last_used_step=step, failed_attempts=0, updated_at=timezone.now())
        if not claimed:
            return False  # this step was already spent — a replay
        device.refresh_from_db(fields=["last_used_step", "failed_attempts"])
        return True

    # Claim the attempt atomically so parallel guesses cannot share one slot.
    TOTPDevice.objects.filter(pk=device.pk).update(failed_attempts=F("failed_attempts") + 1)
    device.refresh_from_db(fields=["failed_attempts"])
    return False


def reset_attempts(user: User) -> bool:
    """Clear a lockout for ``user``, keeping their existing authenticator enrolment.

    The recovery path for the cap above, which otherwise has none: five wrong codes and the
    account is locked out of its own second factor with no way back that does not involve a
    database shell. Staff who mistype, or whose phone clock has drifted, hit this routinely.

    Deliberately does *not* touch ``secret`` or ``confirmed`` — the user keeps their existing
    authenticator entry and simply gets their attempts back. Clearing ``last_used_step`` would
    re-open the replay window, so it is left alone.
    """
    return bool(
        TOTPDevice.objects.filter(user=user, failed_attempts__gt=0).update(
            failed_attempts=0, updated_at=timezone.now()
        )
    )


def confirm(device: TOTPDevice, code: str) -> bool:
    """Verify the first code and, on success, mark the device trusted for login."""
    if not verify(device, code):
        return False
    device.confirmed = True
    device.confirmed_at = timezone.now()
    device.save(update_fields=["confirmed", "confirmed_at"])
    return True
