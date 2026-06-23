from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Rate-limit login attempts per role-page + client IP (rate in settings: 'login')."""

    scope = "login"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        role = request.data.get("role", "-") if hasattr(request, "data") else "-"
        return self.cache_format % {"scope": self.scope, "ident": f"{role}:{ident}"}
