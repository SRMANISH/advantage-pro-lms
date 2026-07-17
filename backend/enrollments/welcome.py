"""Post-enrolment welcome flow (reqs 16/17): address + goodies.

A student answers a two-question popup (is your address on file; have you received your
Advantage Pro goodies). Admin/MIS see the resulting address/goodies register and mark
goodies dispatched. Admins are notified when a student submits a new/updated address.
"""

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from batches.models import BatchState
from core.pagination import paginate_rows
from core.permissions import has_any_role
from core.roles import Role
from core.utils import get_client_ip
from notifications.services import admins_and_mis, notify_many

from .models import Enrollment

RegisterRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS)


class WelcomeMeView(APIView):
    """The student's pending welcome popups — active enrolments not yet answered."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        pending = (
            Enrollment.objects.filter(
                student=request.user,
                welcome_answered=False,
                batch__state=BatchState.ACTIVE,
            )
            .select_related("batch")
            .order_by("batch__code")
        )
        return Response(
            [
                {
                    "enrollment": str(e.id),
                    "batch_code": e.batch.code,
                    "batch_name": e.batch.name,
                    "address": e.address,
                }
                for e in pending
            ]
        )


class WelcomeSubmitSerializer(serializers.Serializer):
    enrollment = serializers.UUIDField()
    address_on_file = serializers.BooleanField()
    goodies_received = serializers.BooleanField()
    address = serializers.CharField(required=False, allow_blank=True, default="")


class WelcomeSubmitView(APIView):
    """Record the student's answers. If the address isn't on file, capture it and alert
    Admin/MIS so goodies can be dispatched."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WelcomeSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        enrollment = Enrollment.objects.filter(id=data["enrollment"], student=request.user).first()
        if not enrollment:
            return Response({"detail": "Enrolment not found."}, status=404)

        new_address = data["address"].strip()
        if not data["address_on_file"] and new_address:
            enrollment.address = new_address
            enrollment.address_confirmed = True
        elif data["address_on_file"]:
            enrollment.address_confirmed = True
        enrollment.goodies_received = data["goodies_received"]
        enrollment.welcome_answered = True
        enrollment.save(
            update_fields=[
                "address",
                "address_confirmed",
                "goodies_received",
                "welcome_answered",
                "updated_at",
            ]
        )
        # Both "no" (needs address + goodies) -> send the address to Admin/MIS.
        if not data["address_on_file"] and not data["goodies_received"]:
            notify_many(
                admins_and_mis(),
                "address_collected",
                f"{request.user.full_name or request.user.username} "
                f"({enrollment.registration_number}) submitted an address for goodies dispatch.",
                link="/admin/goodies",
                subject="Student address for goodies",
                channels=("in_app",),
            )
        record_action(
            actor=request.user,
            action="welcome_answered",
            target=enrollment,
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})


class GoodiesRegisterView(APIView):
    """Admin/MIS register: every enrolment's address + goodies state."""

    permission_classes = [RegisterRoles]

    def get(self, request):
        rows = Enrollment.objects.select_related("student", "batch").order_by(
            "batch__code", "registration_number"
        )
        batch_id = request.query_params.get("batch")
        if batch_id:
            rows = rows.filter(batch_id=batch_id)
        return paginate_rows(
            request,
            rows,
            lambda e: {
                "enrollment": str(e.id),
                "registration_number": e.registration_number,
                "student_name": e.student.full_name or e.student.username,
                "batch_code": e.batch.code,
                "address": e.address,
                "address_confirmed": e.address_confirmed,
                "goodies_received": e.goodies_received,
                "goodies_sent": e.goodies_sent,
            },
            view=self,
        )


class GoodiesSentSerializer(serializers.Serializer):
    enrollment = serializers.UUIDField()
    sent = serializers.BooleanField()


class GoodiesSentView(APIView):
    """Admin/MIS mark a student's goodies dispatched (or not)."""

    permission_classes = [RegisterRoles]

    def post(self, request):
        serializer = GoodiesSentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = Enrollment.objects.filter(id=serializer.validated_data["enrollment"]).first()
        if not enrollment:
            return Response({"detail": "Enrolment not found."}, status=404)
        enrollment.goodies_sent = serializer.validated_data["sent"]
        enrollment.save(update_fields=["goodies_sent", "updated_at"])
        record_action(
            actor=request.user,
            action="goodies_sent" if enrollment.goodies_sent else "goodies_unsent",
            target=enrollment,
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True, "goodies_sent": enrollment.goodies_sent})
