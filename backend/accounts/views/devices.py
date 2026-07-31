"""Device-change approval: Faculty (during a live class) and MIS (outside class hours)."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.permissions import has_any_role
from core.roles import Role
from core.schema import DetailResponse, OkResponse
from core.utils import get_client_ip

from .. import device
from ..models import DeviceChangeRequest
from ..serializers import DeviceRequestSerializer

# Tech Support handles (and is notified about) outside-class device changes; MIS keeps
# the capability but receives no notifications. Faculty decide during their live class.
DeviceManageRoles = has_any_role(Role.FACULTY, Role.TECH_SUPPORT, Role.MIS)


def _faculty_can_decide(staff, student) -> bool:
    if staff.role != Role.FACULTY:
        return True
    return student.enrollments.filter(batch__faculty=staff).exists()


def _window_block(decider, student) -> str | None:
    """Return an error message if the decider is acting outside their allowed window.

    Faculty may decide only during one of their live classes the student is in; Tech
    Support / MIS only when no class is in session. Returns None when allowed.
    """
    from liveclasses.services import (
        active_live_class_for_student,
        is_live_class_active_for_faculty_student,
    )

    if decider.role == Role.FACULTY:
        if not is_live_class_active_for_faculty_student(decider, student):
            return "Faculty can approve a device change only during your live class."
    elif decider.role in {Role.TECH_SUPPORT, Role.MIS}:
        if active_live_class_for_student(student) is not None:
            return (
                "A class is in session — device changes during class are approved by the faculty."
            )
    return None


@extend_schema(responses=DeviceRequestSerializer(many=True))
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


@extend_schema(
    request=None,
    responses={
        200: OkResponse,
        400: DetailResponse,
        403: DetailResponse,
        404: DetailResponse,
        409: DetailResponse,
    },
)
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
        if decision not in ("approve", "reject"):
            return Response({"detail": "Decision must be either approve or reject."}, status=400)

        # The PENDING check in the query above ran outside any transaction, so a faculty
        # member and Tech Support clicking at the same moment would both pass it. The service
        # functions re-assert it as a conditional UPDATE and return False to the loser, so
        # exactly one decision is recorded and the student is notified once.
        decide = device.approve_request if decision == "approve" else device.reject_request
        if not decide(req, request.user, reason):
            return Response(
                {"detail": "This request has already been decided by someone else."},
                status=status.HTTP_409_CONFLICT,
            )
        record_action(
            actor=request.user,
            action=f"device_{decision}",
            target=req.user,
            metadata={"approver_role": request.user.role, "during_class": req.during_class},
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})
