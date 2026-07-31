"""Live class APIs: schedule (Admin/MIS), list (scoped), join + check-in (student)."""

from datetime import timedelta

from django.utils import timezone
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

from .models import CheckIn, LiveClass, LiveClassStatus
from .serializers import LiveClassSerializer, LiveClassWriteSerializer
from .services import notify_cancellation

LiveRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY, Role.STUDENT)


class LiveClassViewSet(viewsets.ModelViewSet):
    permission_classes = [LiveRoles, MatrixPermission]

    _ACTIONS = {
        "create": Action.SCHEDULE_LIVE_CLASSES,
        "update": Action.SCHEDULE_LIVE_CLASSES,
        "partial_update": Action.SCHEDULE_LIVE_CLASSES,
        "destroy": Action.SCHEDULE_LIVE_CLASSES,
        "cancel": Action.SCHEDULE_LIVE_CLASSES,
    }

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    def get_serializer_class(self):
        return LiveClassWriteSerializer if self.action == "create" else LiveClassSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LiveClass.objects.none()  # OpenAPI schema generation (no real request)
        qs = LiveClass.objects.select_related("batch")
        batch = self.request.query_params.get("batch")
        if batch:
            qs = qs.filter(batch_id=batch)
        user = self.request.user
        # Prefetch the student's own check-ins so the serializer's checked_in flag is a
        # list lookup, not one query per class (N+1).
        if user.role == Role.STUDENT:
            from django.db.models import Prefetch

            qs = qs.prefetch_related(
                Prefetch(
                    "checkins",
                    queryset=CheckIn.objects.filter(student=user),
                    to_attr="my_checkins",
                )
            )
        ids = accessible_batch_ids(user)
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

    @action(detail=False, methods=["get"], url_path="weekly-schedule")
    def weekly_schedule(self, request):
        """Recurring weekly class slots (batch.class_days/times) for the caller's batches.
        Feeds the student calendar so regular classes show, not just ad-hoc live classes."""
        from batches.models import Batch, BatchState

        ids = accessible_batch_ids(request.user)
        qs = Batch.objects.exclude(state=BatchState.DRAFT).exclude(class_days=[])
        if ids is not None:
            qs = qs.filter(id__in=list(ids))
        return Response(
            [
                {
                    "batch_code": b.code,
                    "class_days": b.class_days,
                    "start_time": (
                        b.class_start_time.strftime("%H:%M") if b.class_start_time else None
                    ),
                    "end_time": b.class_end_time.strftime("%H:%M") if b.class_end_time else None,
                    "start_date": b.start_date,
                    "end_date": b.end_date,
                }
                for b in qs
            ]
        )

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        if request.user.role != Role.STUDENT:
            return Response({"detail": "Only students check in."}, status=status.HTTP_403_FORBIDDEN)
        live = self.get_object()
        if live.status == LiveClassStatus.CANCELLED:
            return Response(
                {"detail": "This class was cancelled."}, status=status.HTTP_400_BAD_REQUEST
            )
        CheckIn.objects.get_or_create(live_class=live, student=request.user)
        record_attendance(request.user, live.batch, "live", live.id)
        return Response({"ok": True, "meeting_link": live.meeting_link})

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        # get_object() is queryset-scoped, so Faculty can only cancel their own batches'
        # classes (matrix restricts this action to Faculty).
        live = self.get_object()
        if live.status == LiveClassStatus.CANCELLED:
            return Response({"detail": "Already cancelled."}, status=status.HTTP_400_BAD_REQUEST)
        # Cancelling with <24h notice needs an explicit confirmation (the procedure asks for
        # a day's notice) and is recorded as short-notice for accountability.
        short_notice = live.scheduled_at <= timezone.now() + timedelta(hours=24)
        confirmed = str(request.data.get("confirm_short_notice", "")).lower() in {
            "1",
            "true",
            "yes",
        }
        if short_notice and not confirmed:
            return Response(
                {
                    "detail": "This class starts in less than 24 hours. Confirm the "
                    "short-notice cancellation — students will be notified immediately.",
                    "short_notice": True,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        live.status = LiveClassStatus.CANCELLED
        live.cancelled_at = timezone.now()
        live.cancel_reason = request.data.get("reason", "")
        live.save(update_fields=["status", "cancelled_at", "cancel_reason", "updated_at"])
        notify_cancellation(live)
        record_action(
            actor=request.user,
            action="live_class_cancelled",
            target=live,
            metadata={"short_notice": short_notice},
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})
