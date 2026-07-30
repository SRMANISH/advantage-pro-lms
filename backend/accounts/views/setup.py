"""Two-step account setup: email link -> email OTP -> phone OTP -> password."""

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.permissions import has_any_role
from core.roles import Role
from core.utils import get_client_ip

from .. import setup as setup_service
from ..models import User


def _resolve_token(request):
    return setup_service.get_valid_token(request.data.get("token", ""))


class SetupStartView(APIView):
    """Open the setup link -> send the email OTP."""

    permission_classes = [AllowAny]

    def post(self, request):
        token = _resolve_token(request)
        if not token:
            return Response(
                {"detail": "Invalid or expired setup link."}, status=status.HTTP_400_BAD_REQUEST
            )
        code, reason = setup_service.start_setup(token)
        if code is None:
            return Response({"detail": reason}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        data = {"ok": True, "email": setup_service.mask_email(token.user.email)}
        if settings.DEBUG:
            data["dev_code"] = code
        return Response(data)


class SetupVerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = _resolve_token(request)
        if not token:
            return Response(
                {"detail": "Invalid or expired setup link."}, status=status.HTTP_400_BAD_REQUEST
            )
        ok, reason, phone_code = setup_service.verify_email(token, request.data.get("code", ""))
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)
        data = {"ok": True, "phone": setup_service.mask_phone(token.user.phone)}
        if settings.DEBUG and phone_code:
            data["dev_code"] = phone_code
        return Response(data)


class SetupVerifyPhoneView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = _resolve_token(request)
        if not token:
            return Response(
                {"detail": "Invalid or expired setup link."}, status=status.HTTP_400_BAD_REQUEST
            )
        ok, reason = setup_service.verify_phone(token, request.data.get("code", ""))
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"ok": True})


class SetupCompleteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = _resolve_token(request)
        if not token:
            return Response(
                {"detail": "Invalid or expired setup link."}, status=status.HTTP_400_BAD_REQUEST
            )
        password = request.data.get("password", "")
        try:
            validate_password(password, user=token.user)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        if not setup_service.complete_setup(token, password):
            return Response(
                {"detail": "Please verify your email and phone first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record_action(
            actor=token.user,
            action="account_setup_completed",
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})


class SetupResendView(APIView):
    """Admin/MIS/Super Admin: (re)issue a setup link for a pending student."""

    permission_classes = [has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS)]

    def post(self, request):
        student = User.objects.filter(id=request.data.get("student_id"), role=Role.STUDENT).first()
        if not student:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        token = setup_service.create_setup_token(student)
        setup_service.send_setup_email(student, token)
        record_action(
            actor=request.user,
            action="setup_link_issued",
            target=student,
            ip_address=get_client_ip(request),
        )
        data = {"ok": True}
        if settings.DEBUG:
            data["url"] = setup_service.setup_url(token)
        return Response(data)
