"""Forgot-password: two-step (email OTP -> phone OTP -> new password), plus change-password.

Mirrors the first-login setup security: CSPRNG codes stored as HMAC, short expiry, attempt
cap, and now a resend cap and reset-token expiry. Reuses the OTP helpers from ``setup``.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from core.adapters.registry import get_email, get_sms

from .models import OTPCode, PasswordResetToken, User, UserStatus
from .setup import _issue_otp, _verify

RESET_TTL = timedelta(minutes=30)
MAX_RESENDS = 3


def find_user(identifier: str) -> User | None:
    """Resolve an active account by Registration ID (username) or email."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    return (
        User.objects.filter(
            Q(username=identifier) | Q(email__iexact=identifier), status=UserStatus.ACTIVE
        )
        .order_by("username")
        .first()
    )


def start_reset(user: User) -> tuple[PasswordResetToken, str]:
    PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
    token = PasswordResetToken.objects.create(
        user=user, token=secrets.token_urlsafe(32), expires_at=timezone.now() + RESET_TTL
    )
    code = _issue_otp(user, OTPCode.Purpose.EMAIL)
    get_email().send(user.email or "(none)", "Your password reset code", f"Email code: {code}")
    return token, code


def get_valid_reset_token(token_str: str) -> PasswordResetToken | None:
    return (
        PasswordResetToken.objects.select_related("user")
        .filter(token=token_str, used=False, expires_at__gt=timezone.now())
        .first()
    )


def verify_email(token: PasswordResetToken, code: str) -> tuple[bool, str, str | None]:
    ok, reason = _verify(token.user, OTPCode.Purpose.EMAIL, code)
    if not ok:
        return False, reason, None
    token.email_verified = True
    token.save(update_fields=["email_verified", "updated_at"])
    phone_code = _issue_otp(token.user, OTPCode.Purpose.PHONE)
    get_sms().send(token.user.phone or "(none)", f"Your phone code: {phone_code}")
    return True, "", phone_code


def verify_phone(token: PasswordResetToken, code: str) -> tuple[bool, str]:
    if not token.email_verified:
        return False, "Verify your email first."
    ok, reason = _verify(token.user, OTPCode.Purpose.PHONE, code)
    if ok:
        token.phone_verified = True
        token.save(update_fields=["phone_verified", "updated_at"])
    return ok, reason


def complete_reset(token: PasswordResetToken, password: str) -> bool:
    if not (token.email_verified and token.phone_verified):
        return False
    user = token.user
    user.set_password(password)
    user.save(update_fields=["password"])
    token.used = True
    token.save(update_fields=["used", "updated_at"])
    return True


def resend(token: PasswordResetToken) -> tuple[str | None, str]:
    """Resend the OTP for the current step, respecting the resend cap."""
    if token.resend_count >= MAX_RESENDS:
        return None, "Resend limit reached — please start the reset again."
    token.resend_count += 1
    token.save(update_fields=["resend_count", "updated_at"])
    if token.email_verified:
        code = _issue_otp(token.user, OTPCode.Purpose.PHONE)
        get_sms().send(token.user.phone or "(none)", f"Your phone code: {code}")
    else:
        code = _issue_otp(token.user, OTPCode.Purpose.EMAIL)
        get_email().send(token.user.email or "(none)", "Your password reset code", f"Code: {code}")
    return code, ""
