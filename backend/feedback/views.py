"""Feedback endpoints: students submit; only Super Admin reads (req 20)."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.permissions import IsSuperAdmin
from core.roles import Role
from core.utils import get_client_ip

from .models import Feedback
from .serializers import FeedbackCreateSerializer, FeedbackSerializer


class FeedbackCreateView(APIView):
    """A student sends private feedback to management -> Super Admin WhatsApp + in-app."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != Role.STUDENT:
            return Response({"detail": "Only students can send feedback here."}, status=403)
        serializer = FeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from accounts.models import User
        from enrollments.models import Enrollment
        from notifications.services import notify_many

        enr = (
            Enrollment.objects.filter(student=request.user)
            .select_related("batch", "batch__course")
            .first()
        )
        feedback = Feedback.objects.create(
            student=request.user,
            subject=serializer.validated_data["subject"],
            message=serializer.validated_data["message"],
            registration_number=enr.registration_number if enr else request.user.username,
            batch_code=enr.batch.code if enr else "",
            course_name=enr.batch.course.name if enr else "",
        )
        # Deliver to Super Admin(s) — WhatsApp + in-app — with the student context. No one
        # else can see this; it's read via the Super-Admin-only inbox below.
        who = request.user.full_name or request.user.username
        context = " · ".join(
            filter(None, [feedback.course_name, feedback.batch_code, feedback.registration_number])
        )
        notify_many(
            list(User.objects.filter(role=Role.SUPER_ADMIN)),
            "management_feedback",
            f"Feedback from {who} ({context}):\n{feedback.subject}\n{feedback.message}",
            subject="New feedback to management",
            channels=("in_app", "whatsapp"),
        )
        record_action(
            actor=request.user,
            action="feedback_submitted",
            target=feedback,
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True}, status=201)


class FeedbackListView(APIView):
    """Super Admin's private feedback inbox. No other role can read feedback."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(FeedbackSerializer(Feedback.objects.all(), many=True).data)
