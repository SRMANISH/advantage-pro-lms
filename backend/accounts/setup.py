"""Two-step account setup: 48h link -> email OTP -> phone OTP -> set password.

Codes are CSPRNG, stored only as HMAC-SHA256, compared in constant time, and expire
quickly with an attempt cap. Sends go through the email/SMS adapters (console in dev).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.adapters.registry import get_email, get_sms

from .models import OTPCode, SetupToken, User, UserStatus

OTP_TTL = timedelta(minutes=10)
SETUP_TTL = timedelta(hours=48)
MAX_ATTEMPTS = 5


def _hash_code(user_id, purpose: str, code: str) -> str:
    msg = f"{user_id}:{purpose}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email or ""
    name, domain = email.split("@", 1)
    return f"{name[0]}***@{domain}" if name else f"***@{domain}"


def mask_phone(phone: str) -> str:
    return f"***{phone[-3:]}" if phone else ""


def create_setup_token(user: User) -> SetupToken:
    SetupToken.objects.filter(user=user).delete()
    return SetupToken.objects.create(
        user=user,
        token=secrets.token_urlsafe(32),
        expires_at=timezone.now() + SETUP_TTL,
    )


def setup_url(token: SetupToken) -> str:
    return f"{settings.FRONTEND_URL}/setup/{token.token}"


def get_valid_token(token_str: str) -> SetupToken | None:
    return (
        SetupToken.objects.select_related("user")
        .filter(token=token_str, used=False, expires_at__gt=timezone.now())
        .first()
    )


def send_setup_email(user: User, token: SetupToken) -> None:
    get_email().send(
        user.email or "(no email on file)",
        "Set up your Advantage Pro account",
        f"Welcome! Set up your account within 48 hours: {setup_url(token)}",
    )


def _issue_otp(user: User, purpose: str) -> str:
    OTPCode.objects.filter(user=user, purpose=purpose, consumed=False).delete()
    code = f"{secrets.randbelow(1_000_000):06d}"
    OTPCode.objects.create(
        user=user,
        purpose=purpose,
        code_hash=_hash_code(user.id, purpose, code),
        expires_at=timezone.now() + OTP_TTL,
    )
    return code


def _verify(user: User, purpose: str, code: str) -> tuple[bool, str]:
    otp = (
        OTPCode.objects.filter(user=user, purpose=purpose, consumed=False)
        .order_by("-created_at")
        .first()
    )
    if otp is None or otp.expires_at < timezone.now():
        return False, "Code expired — request a new one."
    if otp.attempts >= MAX_ATTEMPTS:
        return False, "Too many attempts — request a new code."
    otp.attempts += 1
    if hmac.compare_digest(otp.code_hash, _hash_code(user.id, purpose, code)):
        otp.consumed = True
        otp.save(update_fields=["consumed", "attempts", "updated_at"])
        return True, ""
    otp.save(update_fields=["attempts", "updated_at"])
    return False, "Incorrect code."


def start_setup(token: SetupToken) -> str:
    """Send the email OTP. Returns the code (used only to surface in DEBUG)."""
    code = _issue_otp(token.user, OTPCode.Purpose.EMAIL)
    get_email().send(token.user.email or "(none)", "Your verification code", f"Email code: {code}")
    return code


def verify_email(token: SetupToken, code: str) -> tuple[bool, str, str | None]:
    ok, reason = _verify(token.user, OTPCode.Purpose.EMAIL, code)
    if not ok:
        return False, reason, None
    token.email_verified = True
    token.save(update_fields=["email_verified", "updated_at"])
    phone_code = _issue_otp(token.user, OTPCode.Purpose.PHONE)
    get_sms().send(token.user.phone or "(none)", f"Your phone code: {phone_code}")
    return True, "", phone_code


def verify_phone(token: SetupToken, code: str) -> tuple[bool, str]:
    if not token.email_verified:
        return False, "Verify your email first."
    ok, reason = _verify(token.user, OTPCode.Purpose.PHONE, code)
    if ok:
        token.phone_verified = True
        token.save(update_fields=["phone_verified", "updated_at"])
    return ok, reason


def complete_setup(token: SetupToken, password: str) -> bool:
    if not (token.email_verified and token.phone_verified):
        return False
    user = token.user
    user.set_password(password)
    user.status = UserStatus.ACTIVE
    user.save(update_fields=["password", "status"])
    token.used = True
    token.save(update_fields=["used", "updated_at"])
    return True
