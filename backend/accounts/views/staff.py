"""Staff account administration: create/list staff, suspend/reactivate, change role."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.permissions import MatrixPermission
from core.permissions_matrix import Action, can
from core.roles import Role
from core.utils import get_client_ip
from notifications.services import notify

from .. import setup as setup_service
from ..models import User, UserStatus
from ..serializers import StaffCreateSerializer, UserSerializer


class StaffAccountsView(APIView):
    """Create and list staff accounts.

    Super Admin may create any staff role; Admin may create Counsellor accounts only
    (Admin never creates Faculty/Admin). New accounts go through the same two-step setup
    (email link -> email OTP -> phone OTP -> password) as students.
    """

    permission_classes = [MatrixPermission]
    required_action = Action.MANAGE_STAFF_ACCOUNTS

    def get(self, request):
        staff = User.objects.exclude(role=Role.STUDENT).order_by("role", "username")
        return Response(UserSerializer(staff, many=True).data)

    def post(self, request):
        serializer = StaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        if request.user.role == Role.ADMIN and role != Role.COUNSELOR:
            return Response(
                {"detail": "Admin can create Counsellor accounts only."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user = User.objects.create(
            username=serializer.validated_data["username"],
            full_name=serializer.validated_data["full_name"],
            email=serializer.validated_data["email"],
            phone=serializer.validated_data["phone"],
            role=role,
            status=UserStatus.PENDING,
        )
        token = setup_service.create_setup_token(user)
        setup_service.send_setup_email(user, token)
        record_action(
            actor=request.user,
            action="staff_account_created",
            target=user,
            metadata={"role": role},
            ip_address=get_client_ip(request),
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserStatusView(APIView):
    """Suspend or reactivate a student or faculty account.

    The required matrix action depends on the *target's* role (SUSPEND_STUDENT vs
    SUSPEND_FACULTY), so it's checked here rather than via a fixed ``required_action``.
    Suspension is enforced at login (only ACTIVE accounts may sign in).
    """

    permission_classes = [IsAuthenticated]

    _ACTION_FOR = {
        Role.STUDENT: Action.SUSPEND_STUDENT,
        Role.FACULTY: Action.SUSPEND_FACULTY,
    }

    def post(self, request, pk):
        target = User.objects.filter(id=pk).first()
        if not target:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        action = self._ACTION_FOR.get(target.role)
        if action is None or not can(request.user.role, action):
            return Response(
                {
                    "detail": "Only student and faculty accounts can be suspended, and not by "
                    "your role."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        suspend = bool(request.data.get("suspend", True))
        if suspend and target.status == UserStatus.PENDING:
            return Response(
                {"detail": "This account hasn't completed setup yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target.status = UserStatus.SUSPENDED if suspend else UserStatus.ACTIVE
        target.save(update_fields=["status"])
        record_action(
            actor=request.user,
            action="user_suspended" if suspend else "user_reactivated",
            target=target,
            ip_address=get_client_ip(request),
        )
        notify(
            target,
            "account_status",
            (
                "Your account has been suspended. Please contact the office."
                if suspend
                else "Your account has been reactivated — welcome back."
            ),
            subject="Account suspended" if suspend else "Account reactivated",
            channels=("in_app", "email"),
        )
        return Response(UserSerializer(target).data)


class UserRoleView(APIView):
    """Super Admin changes a staff account's role (matrix CHANGE_USER_ROLE)."""

    permission_classes = [MatrixPermission]
    required_action = Action.CHANGE_USER_ROLE

    def post(self, request, pk):
        target = User.objects.filter(id=pk).first()
        if not target:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        new_role = request.data.get("role")
        # Roles are for staff; student identity is enrolment-based, so it's out of scope here.
        if new_role not in Role.values or Role.STUDENT in (new_role, target.role):
            return Response(
                {"detail": "Choose a valid staff role (students are managed via enrolment)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        old_role = target.role
        target.role = new_role
        target.save(update_fields=["role"])
        record_action(
            actor=request.user,
            action="user_role_changed",
            target=target,
            metadata={"from": old_role, "to": new_role},
            ip_address=get_client_ip(request),
        )
        notify(
            target,
            "account_role",
            f"Your role has been updated to {Role(new_role).label}.",
            subject="Account role updated",
            channels=("in_app", "email"),
        )
        return Response(UserSerializer(target).data)
