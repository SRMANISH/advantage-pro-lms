"""Certification: student enters Certificate ID; admins trigger reminders."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from batches.models import BatchState
from core.pagination import paginate_rows
from core.permissions import has_any_role
from core.roles import Role
from core.schema import DetailResponse, OkResponse
from enrollments.models import Enrollment

from .models import CertFollowUpStatus, Certificate, CertificateFollowUp

CertFollowUpRoles = has_any_role(Role.ADMIN, Role.MIS)


class CertificationRowSerializer(serializers.Serializer):
    """One completed enrolment and whether its Certificate ID has been entered."""

    enrollment = serializers.UUIDField()
    batch_code = serializers.CharField()
    batch_name = serializers.CharField()
    certificate_id = serializers.CharField(allow_null=True)
    certified = serializers.BooleanField()


class CertFollowUpStatusResponse(serializers.Serializer):
    ok = serializers.BooleanField()
    status = serializers.CharField()


@extend_schema(responses=CertificationRowSerializer(many=True))
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


@extend_schema(
    request=SubmitCertificateSerializer, responses={200: OkResponse, 404: DetailResponse}
)
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


class CertFollowUpRowSerializer(serializers.Serializer):
    """One completed enrolment's certification and follow-up state."""

    enrollment = serializers.UUIDField()
    registration_number = serializers.CharField()
    student_name = serializers.CharField()
    batch_code = serializers.CharField()
    certified = serializers.BooleanField()
    certificate_id = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    reminder_count = serializers.IntegerField()
    last_reminder_at = serializers.DateTimeField(allow_null=True)


@extend_schema(responses=CertFollowUpRowSerializer(many=True))
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
        batch_id = request.query_params.get("batch")
        if batch_id:
            enrollments = enrollments.filter(batch_id=batch_id)

        def row(e):
            cert = getattr(e, "certificate", None)
            fu = getattr(e, "cert_followup", None)
            return {
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

        return paginate_rows(request, enrollments, row, view=self)


class CertFollowUpStatusSerializer(serializers.Serializer):
    enrollment = serializers.UUIDField()
    status = serializers.ChoiceField(choices=CertFollowUpStatus.values)
    note = serializers.CharField(required=False, allow_blank=True, default="")


@extend_schema(
    request=CertFollowUpStatusSerializer,
    responses={200: CertFollowUpStatusResponse, 404: DetailResponse},
)
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
