"""Staff TOTP enrollment and management. Login-time enforcement lives in views/auth.py."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.permissions import IsSuperAdmin
from core.roles import Role
from core.schema import CodeRequest, DetailResponse, OkResponse, PasswordRequest
from core.utils import get_client_ip

from .. import totp as totp_service
from ..models import TOTPDevice, User
from ..throttling import OTPRateThrottle, VerificationRateThrottle


class IsStaffUser(BasePermission):
    """Any authenticated non-student account — matches StaffAccountsView's definition."""

    message = "Two-factor authentication is for staff accounts."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.role != Role.STUDENT)


class TOTPEnrolledResponse(serializers.Serializer):
    """``{"enabled": bool}`` — whether a confirmed authenticator is on the account."""

    enabled = serializers.BooleanField()


class TOTPSecretResponse(serializers.Serializer):
    """The shared secret and otpauth:// URI, returned once at enrollment."""

    secret = serializers.CharField()
    otpauth_url = serializers.CharField()


@extend_schema(responses=TOTPEnrolledResponse)
class TOTPStatusView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        device = TOTPDevice.objects.filter(user=request.user).first()
        return Response({"enabled": bool(device and device.confirmed)})


@extend_schema(request=None, responses={200: TOTPSecretResponse, 400: DetailResponse})
class TOTPEnrollView(APIView):
    """Start (or restart) enrollment: issues a pending secret + QR provisioning URI."""

    throttle_classes = [OTPRateThrottle]

    permission_classes = [IsStaffUser]

    def post(self, request):
        try:
            device = totp_service.get_or_create_pending(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"secret": device.secret, "otpauth_url": totp_service.provisioning_uri(device)}
        )


@extend_schema(
    request=CodeRequest, responses={200: OkResponse, 400: DetailResponse, 429: DetailResponse}
)
class TOTPConfirmView(APIView):
    """Verify the first code from the authenticator app and enable 2FA."""

    throttle_classes = [OTPRateThrottle, VerificationRateThrottle]

    permission_classes = [IsStaffUser]

    def post(self, request):
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if not device:
            return Response(
                {"detail": "Start enrollment first."}, status=status.HTTP_400_BAD_REQUEST
            )
        if totp_service.attempts_exhausted(device):
            # Distinguish "spent" from "wrong" — otherwise a user who has locked the device
            # keeps retyping correct codes and getting "Invalid code" with no way forward.
            return Response(
                {"detail": "Too many incorrect codes. Restart enrollment to get a new secret."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if not totp_service.confirm(device, request.data.get("code", "")):
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)
        record_action(actor=request.user, action="totp_enabled", ip_address=get_client_ip(request))
        return Response({"ok": True})


@extend_schema(request=PasswordRequest, responses={200: OkResponse, 400: DetailResponse})
class TOTPDisableView(APIView):
    """Turn 2FA off — requires the current password as confirmation."""

    throttle_classes = [OTPRateThrottle]

    permission_classes = [IsStaffUser]

    def post(self, request):
        if not request.user.check_password(request.data.get("password", "")):
            return Response(
                {"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST
            )
        TOTPDevice.objects.filter(user=request.user).delete()
        record_action(actor=request.user, action="totp_disabled", ip_address=get_client_ip(request))
        return Response({"ok": True})


@extend_schema(
    request=None,
    responses={200: OkResponse, 403: DetailResponse, 404: DetailResponse},
)
class TOTPResetView(APIView):
    """Super Admin clears a staff member's 2FA lockout.

    Without this the attempt cap has no way out. Five mistyped codes — or a phone whose clock
    has drifted past the ±1 step window — and the account is locked out of its own second
    factor permanently, recoverable only from a database shell. That is not a security
    property, it is an outage.

    Clears the counter only. The user keeps their existing authenticator entry, so they are
    not re-enrolling; and ``last_used_step`` is deliberately left in place, since resetting it
    would re-open the replay window this is not meant to touch.

    Super-Admin-only and audited: whoever can lift a 2FA lockout can, with the password, reach
    the account.
    """

    permission_classes = [IsSuperAdmin]

    def post(self, request, pk=None):
        target = User.objects.filter(id=pk).first()
        if not target:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        cleared = totp_service.reset_attempts(target)
        record_action(
            actor=request.user,
            action="totp_lockout_reset",
            target=target,
            metadata={"was_locked": cleared},
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})
