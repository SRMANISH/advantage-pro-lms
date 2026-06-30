"""Authentication endpoints: role-bound login, logout, current user, CSRF priming."""

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.services import record_login_attendance
from audit.services import record_action
from core.permissions import has_any_role
from core.roles import Role
from core.utils import get_client_ip
from notifications.services import admins_and_mis, notify_many

from . import device
from . import password as password_service
from . import setup as setup_service
from .models import DeviceChangeRequest, User, UserStatus
from .serializers import DeviceRequestSerializer, LoginSerializer, UserSerializer
from .throttling import LoginRateThrottle


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
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        role = serializer.validated_data["role"]
        ip = get_client_ip(request)

        user = authenticate(request, username=username, password=password)
        # Role-bound: the account must match the portal it signed in through.
        # Generic message — never reveal whether it was the password or the role.
        if user is None or user.role != role:
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
        code = setup_service.start_setup(token)
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
        record_action(actor=token.user, action="account_setup_completed")
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


# Device-change approval: Faculty (during a live class) and MIS (outside class hours).
def _reset_token(request):
    return password_service.get_valid_reset_token(request.data.get("token", ""))


class ForgotPasswordStartView(APIView):
    """Step 0: identify the account (email or Registration ID) and send the email OTP."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        ip = get_client_ip(request)
        user = password_service.find_user(request.data.get("identifier", ""))
        record_action(
            actor=user,
            action="password_reset_requested",
            target_type="auth",
            metadata={"found": bool(user)},
            ip_address=ip,
        )
        if not user:
            return Response(
                {"detail": "No active account found for that email or Registration ID."},
                status=status.HTTP_404_NOT_FOUND,
            )
        token, code = password_service.start_reset(user)
        data = {"ok": True, "token": token.token, "email": setup_service.mask_email(user.email)}
        if settings.DEBUG:
            data["dev_code"] = code
        return Response(data)


class ForgotPasswordVerifyEmailView(APIView):
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


DeviceManageRoles = has_any_role(Role.FACULTY, Role.MIS)


def _faculty_can_decide(staff, student) -> bool:
    if staff.role != Role.FACULTY:
        return True
    return student.enrollments.filter(batch__faculty=staff).exists()


def _window_block(decider, student) -> str | None:
    """Return an error message if the decider is acting outside their allowed window.

    Faculty may decide only during one of their live classes the student is in; MIS may
    decide only when no class is in session. Returns None when the action is allowed.
    """
    from liveclasses.services import (
        active_live_class_for_student,
        is_live_class_active_for_faculty_student,
    )

    if decider.role == Role.FACULTY:
        if not is_live_class_active_for_faculty_student(decider, student):
            return "Faculty can approve a device change only during your live class."
    elif decider.role == Role.MIS:
        if active_live_class_for_student(student) is not None:
            return (
                "A class is in session — device changes during class are approved by the faculty."
            )
    return None


class DeviceRequestListView(APIView):
    """Pending new-device requests (faculty see only their students')."""

    permission_classes = [DeviceManageRoles]

    def get(self, request):
        qs = DeviceChangeRequest.objects.select_related("user").filter(
            status=DeviceChangeRequest.Status.PENDING
        )
        if request.user.role == Role.FACULTY:
            qs = qs.filter(user__enrollments__batch__faculty=request.user).distinct()
        return Response(DeviceRequestSerializer(qs, many=True).data)


class DeviceRequestDecideView(APIView):
    permission_classes = [DeviceManageRoles]

    def post(self, request, pk=None):
        req = (
            DeviceChangeRequest.objects.select_related("user")
            .filter(id=pk, status=DeviceChangeRequest.Status.PENDING)
            .first()
        )
        if not req:
            return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)
        if not _faculty_can_decide(request.user, req.user):
            return Response({"detail": "Not your student."}, status=status.HTTP_403_FORBIDDEN)
        window_error = _window_block(request.user, req.user)
        if window_error:
            return Response({"detail": window_error}, status=status.HTTP_403_FORBIDDEN)

        decision = request.data.get("decision")
        reason = request.data.get("reason", "")
        if decision == "approve":
            device.approve_request(req, request.user, reason)
        elif decision == "reject":
            device.reject_request(req, request.user, reason)
        else:
            return Response({"detail": "decision must be approve or reject."}, status=400)
        record_action(
            actor=request.user,
            action=f"device_{decision}",
            target=req.user,
            metadata={"approver_role": request.user.role, "during_class": req.during_class},
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})
