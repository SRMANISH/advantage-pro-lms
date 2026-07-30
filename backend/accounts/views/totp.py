"""Staff TOTP enrollment and management. Login-time enforcement lives in views/auth.py."""

from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.roles import Role
from core.utils import get_client_ip

from .. import totp as totp_service
from ..models import TOTPDevice
from ..throttling import OTPRateThrottle


class IsStaffUser(BasePermission):
    """Any authenticated non-student account — matches StaffAccountsView's definition."""

    message = "Two-factor authentication is for staff accounts."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.role != Role.STUDENT)


class TOTPStatusView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        device = TOTPDevice.objects.filter(user=request.user).first()
        return Response({"enabled": bool(device and device.confirmed)})


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


class TOTPConfirmView(APIView):
    """Verify the first code from the authenticator app and enable 2FA."""

    throttle_classes = [OTPRateThrottle]

    permission_classes = [IsStaffUser]

    def post(self, request):
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if not device:
            return Response(
                {"detail": "Start enrollment first."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not totp_service.confirm(device, request.data.get("code", "")):
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)
        record_action(actor=request.user, action="totp_enabled", ip_address=get_client_ip(request))
        return Response({"ok": True})


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
