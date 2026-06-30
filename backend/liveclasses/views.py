"""Live class APIs: schedule (Admin/MIS), list (scoped), join + check-in (student)."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from attendance.services import record_attendance
from audit.services import record_action
from content.access import accessible_batch_ids
from core.permissions import MatrixPermission, has_any_role
from core.permissions_matrix import Action
from core.roles import Role
from core.utils import get_client_ip
from notifications.services import batch_student_users, notify_many

from .models import CheckIn, LiveClass
from .serializers import LiveClassSerializer, LiveClassWriteSerializer

LiveRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY, Role.STUDENT)


class LiveClassViewSet(viewsets.ModelViewSet):
    permission_classes = [LiveRoles, MatrixPermission]

    _ACTIONS = {
        "create": Action.SCHEDULE_LIVE_CLASSES,
        "update": Action.SCHEDULE_LIVE_CLASSES,
        "partial_update": Action.SCHEDULE_LIVE_CLASSES,
        "destroy": Action.SCHEDULE_LIVE_CLASSES,
    }

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    def get_serializer_class(self):
        return LiveClassWriteSerializer if self.action == "create" else LiveClassSerializer

    def get_queryset(self):
        qs = LiveClass.objects.select_related("batch")
        batch = self.request.query_params.get("batch")
        if batch:
            qs = qs.filter(batch_id=batch)
        ids = accessible_batch_ids(self.request.user)
        return qs if ids is None else qs.filter(batch_id__in=list(ids))

    def perform_create(self, serializer):
        live = serializer.save(created_by=self.request.user)
        record_action(
            actor=self.request.user,
            action="live_class_scheduled",
            target=live,
            ip_address=get_client_ip(self.request),
        )
        # 1h/15m reminders are sent by the `send_due_reminders` cron command, not here.
        notify_many(
            batch_student_users(live.batch),
            "new_live_class",
            f"Live class scheduled: {live.title} ({live.platform}).",
            link="/student/live",
            subject="New live class",
            channels=("in_app", "email", "sms", "whatsapp"),
        )

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        if request.user.role != Role.STUDENT:
            return Response({"detail": "Only students check in."}, status=status.HTTP_403_FORBIDDEN)
        live = self.get_object()
        CheckIn.objects.get_or_create(live_class=live, student=request.user)
        record_attendance(request.user, live.batch, "live", live.id)
        return Response({"ok": True, "meeting_link": live.meeting_link})
