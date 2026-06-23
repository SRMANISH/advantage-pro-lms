"""Attendance read APIs: a student's own summary and a per-batch roster."""

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from audit.services import record_action
from batches.models import Batch
from core.permissions import has_any_role
from core.roles import Role
from core.utils import get_client_ip
from enrollments.models import Enrollment
from notifications.services import notify

from .services import student_summary

ReviewRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.COUNSELOR, Role.FACULTY)
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
        batch_id = request.query_params.get("batch")
        if not batch_id:
            return Response({"detail": "batch query param required."}, status=400)
        batch = Batch.objects.filter(id=batch_id).first()
        if not batch:
            return Response({"detail": "Batch not found."}, status=404)
        if (
            request.user.role == Role.FACULTY
            and not batch.faculty.filter(id=request.user.id).exists()
        ):
            return Response({"detail": "Not your batch."}, status=403)

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
