"""Password flows: two-step forgot/reset (email OTP -> phone OTP) and change-password."""

import secrets

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.utils import get_client_ip

from .. import password as password_service
from .. import setup as setup_service
from ..throttling import LoginRateThrottle, OTPRateThrottle


def _reset_token(request):
    return password_service.get_valid_reset_token(request.data.get("token", ""))


class ForgotPasswordStartView(APIView):
    """Step 0: identify the account (email or Registration ID) and send the email OTP."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        ip = get_client_ip(request)
        identifier = request.data.get("identifier", "")
        user = password_service.find_user(identifier)
        record_action(
            actor=user,
            action="password_reset_requested",
            target_type="auth",
            metadata={"found": bool(user)},
            ip_address=ip,
        )
        # Never reveal whether an account exists: the response shape is identical either
        # way (200 + opaque token + masked email). A miss returns a decoy token that isn't
        # backed by any reset, so the OTP steps fail the same as an expired real token.
        if not user:
            return Response(
                {
                    "ok": True,
                    "token": secrets.token_urlsafe(32),
                    "email": setup_service.mask_email(identifier),
                }
            )
        token, code = password_service.start_reset(user)
        data = {"ok": True, "token": token.token, "email": setup_service.mask_email(user.email)}
        if settings.DEBUG:
            data["dev_code"] = code
        return Response(data)


class ForgotPasswordVerifyEmailView(APIView):

    throttle_classes = [OTPRateThrottle]
    permission_classes = [AllowAny]

    def post(self, request):
        token = _reset_token(request)
        if not token:
            return Response(
                {"detail": "Invalid or expired reset session."}, status=status.HTTP_400_BAD_REQUEST
            )
        ok, reason, phone_code = password_service.verify_email(token, request.data.get("code", ""))
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)
        data = {"ok": True, "phone": setup_service.mask_phone(token.user.phone)}
        if settings.DEBUG and phone_code:
            data["dev_code"] = phone_code
        return Response(data)


class ForgotPasswordVerifyPhoneView(APIView):

    throttle_classes = [OTPRateThrottle]
    permission_classes = [AllowAny]

    def post(self, request):
        token = _reset_token(request)
        if not token:
            return Response(
                {"detail": "Invalid or expired reset session."}, status=status.HTTP_400_BAD_REQUEST
            )
        ok, reason = password_service.verify_phone(token, request.data.get("code", ""))
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"ok": True})


class ForgotPasswordCompleteView(APIView):

    throttle_classes = [OTPRateThrottle]
    permission_classes = [AllowAny]

    def post(self, request):
        token = _reset_token(request)
        if not token:
            return Response(
                {"detail": "Invalid or expired reset session."}, status=status.HTTP_400_BAD_REQUEST
            )
        password = request.data.get("password", "")
        try:
            validate_password(password, user=token.user)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        if not password_service.complete_reset(token, password):
            return Response(
                {"detail": "Please verify your email and phone first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record_action(
            actor=token.user, action="password_reset_completed", ip_address=get_client_ip(request)
        )
        return Response({"ok": True})


class ForgotPasswordResendView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        token = _reset_token(request)
        if not token:
            return Response(
                {"detail": "Invalid or expired reset session."}, status=status.HTTP_400_BAD_REQUEST
            )
        code, reason = password_service.resend(token)
        if reason:
            return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)
        data = {"ok": True}
        if settings.DEBUG:
            data["dev_code"] = code
        return Response(data)


class ChangePasswordView(APIView):
    """Logged-in users change their own password."""

    throttle_classes = [OTPRateThrottle]

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.check_password(request.data.get("old_password", "")):
            return Response(
                {"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST
            )
        new_password = request.data.get("new_password", "")
        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        record_action(actor=user, action="password_changed", ip_address=get_client_ip(request))
        return Response({"ok": True})
