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

from .models import Certificate
from .services import run_certificate_reminders


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


class RunCertRemindersView(APIView):
    permission_classes = [has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS)]

    def post(self, request):
        count = run_certificate_reminders()
        record_action(
            actor=request.user, action="certificate_reminders_run", metadata={"count": count}
        )
        return Response({"reminded": count})
