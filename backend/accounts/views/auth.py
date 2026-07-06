"""Authentication endpoints: role-bound login, logout, current user, CSRF priming."""

from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.services import record_login_attendance
from audit.services import record_action
from core.roles import Role
from core.utils import get_client_ip
from notifications.services import admins_and_mis, notify_many

from .. import device
from .. import totp as totp_service
from ..models import TOTPDevice, User, UserStatus
from ..serializers import LoginSerializer, UserSerializer
from ..throttling import LoginRateThrottle


def _alert_admins_first_login(user) -> None:
    """Notify Admin + MIS (in-app + email) that a user signed in for the first time."""
    notify_many(
        admins_and_mis(),
        "first_login",
        f"{user.full_name or user.username} ({user.role}) signed in for the first time.",
        subject="First login",
        channels=("in_app", "email"),
    )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFView(APIView):
    """Sets the CSRF cookie so the SPA can send X-CSRFToken on later writes."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set"})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["username"].strip()
        password = serializer.validated_data["password"]
        role = serializer.validated_data.get("role") or None
        ip = get_client_ip(request)

        # Unified sign-in: the identifier may be a Login ID / Registration ID or an email.
        # Email is intentionally non-unique (one person may hold an account per course), so
        # an ambiguous email must fall back to the Registration ID.
        username = identifier
        if "@" in identifier and not User.objects.filter(username=identifier).exists():
            matches = list(User.objects.filter(email__iexact=identifier)[:2])
            if len(matches) == 1:
                username = matches[0].username
            elif len(matches) > 1:
                return Response(
                    {
                        "detail": "This email is linked to more than one account — "
                        "please sign in with your Registration ID."
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        user = authenticate(request, username=username, password=password)
        # Role-bound portals: when a role is supplied the account must match it.
        # Generic message — never reveal whether it was the password or the role.
        if user is None or (role is not None and user.role != role):
            record_action(
                action="login_failed",
                target_type="auth",
                metadata={"username": username, "role": role},
                ip_address=ip,
            )
            return Response(
                {"detail": "Invalid credentials for this portal."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.status != UserStatus.ACTIVE:
            record_action(
                actor=user,
                action="login_blocked",
                metadata={"status": user.status},
                ip_address=ip,
            )
            return Response(
                {"detail": "This account is not active."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Optional staff 2FA: students are never prompted. An unconfirmed device (an
        # abandoned enrollment) is never consulted, so it can't lock anyone out.
        if user.role != Role.STUDENT:
            totp = TOTPDevice.objects.filter(user=user, confirmed=True).first()
            if totp:
                code = serializer.validated_data.get("totp_code", "")
                if not totp_service.verify(totp, code):
                    record_action(
                        actor=user,
                        action="login_totp_required" if not code else "login_totp_failed",
                        ip_address=ip,
                    )
                    detail = (
                        "Enter the 6-digit code from your authenticator app."
                        if not code
                        else "Invalid authenticator code."
                    )
                    return Response(
                        {"detail": detail, "totp_required": True},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

        # Device policy applies to students: bound device always works (so a finished
        # student can still log in to certify); device *changes* close at course end.
        if user.role == Role.STUDENT:
            ok, reason = device.handle_device_login(
                user,
                serializer.validated_data.get("device_id", ""),
                course_ended=device.course_ended(user),
            )
            if not ok:
                record_action(actor=user, action="login_blocked_device", ip_address=ip)
                return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)

        is_first_login = user.last_login is None
        auth_login(request, user)
        record_action(actor=user, action="login_success", ip_address=ip)
        # Login-based attendance: a student is present today in each enrolled batch.
        if user.role == Role.STUDENT:
            record_login_attendance(user, serializer.validated_data.get("device_id", ""))
        if is_first_login:
            record_action(actor=user, action="first_login", ip_address=ip)
            _alert_admins_first_login(user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        record_action(actor=request.user, action="logout", ip_address=get_client_ip(request))
        auth_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
