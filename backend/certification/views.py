"""Certification: student enters Certificate ID; admins trigger reminders."""

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from batches.models import BatchState
from core.permissions import has_any_role
from core.roles import Role
from enrollments.models import Enrollment

from .models import CertFollowUpStatus, Certificate, CertificateFollowUp

CertFollowUpRoles = has_any_role(Role.ADMIN, Role.MIS)


class CertificationMeView(APIView):
    """A student's completed courses and their certificate status."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        enrollments = (
            Enrollment.objects.filter(student=request.user, batch__state=BatchState.COMPLETED)
            .select_related("batch")
            .prefetch_related("certificate")
        )
        rows = []
        for e in enrollments:
            cert = getattr(e, "certificate", None)
            rows.append(
                {
                    "enrollment": str(e.id),
                    "batch_code": e.batch.code,
                    "batch_name": e.batch.name,
                    "certificate_id": cert.certificate_id if cert else None,
                    "certified": cert is not None,
                }
            )
        return Response(rows)


class SubmitCertificateSerializer(serializers.Serializer):
    enrollment = serializers.UUIDField()
    certificate_id = serializers.CharField(max_length=100)


class SubmitCertificateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubmitCertificateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = Enrollment.objects.filter(
            id=serializer.validated_data["enrollment"],
            student=request.user,
            batch__state=BatchState.COMPLETED,
        ).first()
        if not enrollment:
            return Response({"detail": "No completed enrolment found."}, status=404)
        Certificate.objects.update_or_create(
            enrollment=enrollment,
            defaults={"certificate_id": serializer.validated_data["certificate_id"]},
        )
        record_action(actor=request.user, action="certificate_entered", target=enrollment)
        return Response({"ok": True})


class CertificateFollowUpListView(APIView):
    """MIS/Admin dashboard: certificate-pending vs completed students + follow-up state."""

    permission_classes = [CertFollowUpRoles]

    def get(self, request):
        enrollments = (
            Enrollment.objects.filter(batch__state=BatchState.COMPLETED)
            .select_related("student", "batch")
            .prefetch_related("certificate", "cert_followup")
            .order_by("batch__code", "registration_number")
        )
        rows = []
        for e in enrollments:
            cert = getattr(e, "certificate", None)
            fu = getattr(e, "cert_followup", None)
            rows.append(
                {
                    "enrollment": str(e.id),
                    "registration_number": e.registration_number,
                    "student_name": e.student.full_name or e.student.username,
                    "batch_code": e.batch.code,
                    "certified": cert is not None,
                    "certificate_id": cert.certificate_id if cert else None,
                    "follow_up_status": fu.status if fu else CertFollowUpStatus.PENDING,
                    "reminder_count": fu.reminder_count if fu else 0,
                    "last_reminder_at": fu.last_reminder_at if fu else None,
                }
            )
        return Response(rows)


class CertFollowUpStatusSerializer(serializers.Serializer):
    enrollment = serializers.UUIDField()
    status = serializers.ChoiceField(choices=CertFollowUpStatus.values)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class CertFollowUpStatusView(APIView):
    """MIS/Admin set the follow-up status for a student's certificate."""

    permission_classes = [CertFollowUpRoles]

    def post(self, request):
        serializer = CertFollowUpStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = Enrollment.objects.filter(id=serializer.validated_data["enrollment"]).first()
        if not enrollment:
            return Response({"detail": "Enrolment not found."}, status=404)
        followup, _ = CertificateFollowUp.objects.get_or_create(enrollment=enrollment)
        followup.status = serializer.validated_data["status"]
        followup.owner = request.user
        if serializer.validated_data["note"]:
            followup.note = serializer.validated_data["note"]
        followup.save()
        record_action(
            actor=request.user,
            action="cert_followup_status",
            target=enrollment,
            metadata={"status": followup.status},
        )
        return Response({"ok": True, "status": followup.status})
