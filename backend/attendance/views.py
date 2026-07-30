"""Attendance read APIs: a student's own summary and a per-batch roster."""

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from audit.services import record_action
from batches.models import Batch
from batches.selectors import resolve_batch
from core.permissions import has_any_role
from core.roles import Role
from core.utils import get_client_ip
from enrollments.models import Enrollment
from notifications.services import notify

from .models import FollowUpStatus
from .services import daily_roster, is_rest_day, set_followup, student_summary

ReviewRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.COUNSELOR, Role.FACULTY)
# Absentee follow-up is owned by both Counselor and MIS (plus Admin).
FollowUpRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.COUNSELOR)


class MyAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = []
        enrollments = Enrollment.objects.filter(student=request.user).select_related("batch")
        for e in enrollments:
            summary = student_summary(request.user, e.batch)
            rows.append({"batch": e.batch.code, "batch_name": e.batch.name, **summary})
        return Response(rows)


class BatchAttendanceView(APIView):
    permission_classes = [ReviewRoles]

    def get(self, request):
        batch, error = resolve_batch(request, allow_body=False)
        if error:
            return error

        students = User.objects.filter(enrollments__batch=batch).distinct()
        rows = [
            {
                "student": str(s.id),
                "student_name": s.full_name or s.username,
                "registration_number": s.username,
                **student_summary(s, batch),
            }
            for s in students
        ]
        return Response(rows)


class ReviewBatchesView(APIView):
    """Batches the user can review attendance for (for the picker)."""

    permission_classes = [ReviewRoles]

    def get(self, request):
        qs = Batch.objects.all()
        if request.user.role == Role.FACULTY:
            qs = qs.filter(faculty=request.user)
        return Response([{"id": str(b.id), "code": b.code, "name": b.name} for b in qs])


class FollowUpSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    message = serializers.CharField(required=False, allow_blank=True, default="")


class FollowUpView(APIView):
    """Counselor (or admin/MIS) sends a standard absence follow-up to a student."""

    permission_classes = [FollowUpRoles]

    def post(self, request):
        serializer = FollowUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = User.objects.filter(
            id=serializer.validated_data["student_id"], role=Role.STUDENT
        ).first()
        if not student:
            return Response({"detail": "Student not found."}, status=404)

        name = student.full_name or student.username
        message = serializer.validated_data["message"] or (
            f"Hi {name}, we noticed you've missed some sessions. Please catch up on your "
            "videos, tests and tasks, and reach out to us if you need any help. — Advantage Pro"
        )
        notify(
            student,
            "absence_followup",
            message,
            subject="Attendance follow-up",
            channels=("in_app", "email", "sms"),
        )
        record_action(
            actor=request.user,
            action="absence_followup_sent",
            target=student,
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})


class DailyAttendanceView(APIView):
    """Per-day login attendance for a batch: who logged in / who did not, with
    follow-up status. Seen by Counselor and MIS (and Admin/Faculty-own-batch)."""

    permission_classes = [ReviewRoles]

    def get(self, request):
        batch, error = resolve_batch(request)
        if error:
            return error
        day = None
        raw = request.query_params.get("date")
        if raw:
            parsed = parse_date(raw)
            if not parsed:
                return Response({"detail": "Invalid date (use YYYY-MM-DD)."}, status=400)
            day = parsed
        day = day or timezone.localdate()
        rows = daily_roster(batch, day)
        return Response(
            {"date": day.isoformat(), "weekend_excluded": is_rest_day(day), "rows": rows}
        )


class FollowUpStatusSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=FollowUpStatus.values)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class FollowUpStatusView(APIView):
    """Counselor/MIS set or update the follow-up status for an absent student."""

    permission_classes = [FollowUpRoles]

    def post(self, request):
        batch, error = resolve_batch(request)
        if error:
            return error
        serializer = FollowUpStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = User.objects.filter(
            id=serializer.validated_data["student_id"], role=Role.STUDENT
        ).first()
        if not student:
            return Response({"detail": "Student not found."}, status=404)
        followup = set_followup(
            student,
            batch,
            serializer.validated_data["status"],
            owner=request.user,
            note=serializer.validated_data["note"],
        )
        record_action(
            actor=request.user,
            action="absence_followup_status",
            target=student,
            metadata={"batch": str(batch.id), "status": followup.status},
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True, "status": followup.status})
