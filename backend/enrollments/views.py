"""Student enrolment: bulk import (all-or-nothing) and a role-scoped list."""

from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.setup import create_setup_token, send_setup_email
from audit.services import record_action
from core.pagination import StandardResultsPagination
from core.permissions import MatrixPermission, has_any_role
from core.permissions_matrix import Action
from core.roles import Role
from core.utils import get_client_ip
from notifications.services import admins_and_mis, notify_many

from .importer import do_import, parse_rows, validate_and_build
from .models import Enrollment
from .serializers import EnrollmentSerializer


def _truthy(value) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


class EnrollmentImportView(APIView):
    """POST a CSV/XLSX. ``dry_run=true`` validates only; otherwise imports atomically."""

    permission_classes = [MatrixPermission]
    required_action = Action.IMPORT_STUDENTS
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = parse_rows(uploaded)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        errors, prepared = validate_and_build(rows)
        if errors:
            return Response(
                {"valid": False, "row_count": len(rows), "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if _truthy(request.data.get("dry_run")):
            return Response({"valid": True, "row_count": len(prepared)})

        students = do_import(prepared)
        # Send each new student their two-step account-setup link.
        for student in students:
            token = create_setup_token(student)
            send_setup_email(student, token)
        record_action(
            actor=request.user,
            action="students_imported",
            target_type="enrollment",
            metadata={"created": len(students)},
            ip_address=get_client_ip(request),
        )
        notify_many(
            admins_and_mis(),
            "students_imported",
            f"{len(students)} student(s) were imported.",
            subject="Students imported",
            channels=("in_app", "email"),
        )
        return Response({"valid": True, "created": len(students)}, status=status.HTTP_201_CREATED)


class EnrollmentListView(ListAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY)]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        user = self.request.user
        qs = Enrollment.objects.select_related("student", "batch")
        if user.role == Role.FACULTY:
            qs = qs.filter(batch__faculty=user)
        batch_id = self.request.query_params.get("batch")
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        return qs
