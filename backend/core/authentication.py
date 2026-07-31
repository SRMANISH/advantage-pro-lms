"""Authentication that re-checks account status on every request.

Login refuses a non-ACTIVE account (``accounts/views/auth.py``), but that is a check made
*once*, at sign-in. Authentication here is session-based, and nothing downstream looked at
``status`` again: ``MatrixPermission``, ``IsSuperAdmin`` and ``has_any_role`` all gate on
``role`` alone. So suspending an account did not end the session it already had — the user
kept full access until the cookie expired, which with Django's two-week default is close to
never in incident terms.

Suspension exists to cut off a compromised or misbehaving account *now*, so the check belongs
at the authentication layer rather than in each permission class: it then applies to every
view automatically, including ones written later that forget about it.
"""

from __future__ import annotations

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import authentication, exceptions


class ActiveSessionAuthentication(authentication.SessionAuthentication):
    """Session auth that rejects any account no longer in good standing.

    PENDING is refused too: an account mid-setup has no business holding a session, and if one
    somehow exists it should not carry privileges.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, auth = result

        # Imported lazily — this module is referenced from settings, which is loaded before
        # the app registry is ready.
        from accounts.models import UserStatus

        status = getattr(user, "status", None)
        if status != UserStatus.ACTIVE:
            raise exceptions.AuthenticationFailed(
                "This account is no longer active. Please contact the office."
            )
        return user, auth


class ActiveSessionAuthenticationScheme(OpenApiAuthenticationExtension):
    """Teach drf-spectacular about the authentication class above.

    Without this, every view logs "could not resolve authenticator" during schema generation
    — 85 warnings across the API, purely because the authenticator is a subclass it has no
    extension for. It is registered by import side-effect, which is why drf_spectacular
    discovers it: the module is referenced from DEFAULT_AUTHENTICATION_CLASSES.

    The wire protocol is unchanged from DRF's own SessionAuthentication (a session cookie),
    so the emitted security scheme is the same; only the status re-check differs, and that is
    behaviour rather than transport.
    """

    target_class = "core.authentication.ActiveSessionAuthentication"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.SESSION_COOKIE_NAME,
        }
