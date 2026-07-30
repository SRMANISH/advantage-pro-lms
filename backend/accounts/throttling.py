from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Rate-limit login attempts per role-page + client IP (rate in settings: 'login')."""

    scope = "login"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        role = request.data.get("role", "-") if hasattr(request, "data") else "-"
        return self.cache_format % {"scope": self.scope, "ident": f"{role}:{ident}"}


class VerificationRateThrottle(SimpleRateThrottle):
    """Per-IP ceiling on code-verification endpoints (rate: 'verification').

    Deliberately keyed on client IP alone, including for authenticated requests: it bounds
    how fast one origin can submit codes at *any* account, which per-user keying does not.
    It is applied alongside ``OTPRateThrottle`` (per-user) rather than instead of it — the
    two answer different questions, and DRF requires every listed throttle to allow the
    request. Neither replaces the per-code/per-device attempt caps in ``setup.py`` and
    ``totp.py``, which are what actually bound total guesses against one secret.
    """

    scope = "verification"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class OTPRateThrottle(SimpleRateThrottle):
    """Tighter cap on code-verification and credential-change endpoints (rate: 'otp').

    Covers the account-setup and password-reset OTP steps plus the TOTP endpoints. Each code
    already has a per-code attempt cap, but that alone does not bound how fast an attacker
    can cycle *new* codes, so this adds a request-rate ceiling on top.

    Keys by user when authenticated and by client IP otherwise. That matters: the built-in
    ``AnonRateThrottle`` returns ``None`` for authenticated requests — i.e. no throttling at
    all — so using it on change-password or TOTP confirm would silently do nothing.
    """

    scope = "otp"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            ident = f"user:{user.pk}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
