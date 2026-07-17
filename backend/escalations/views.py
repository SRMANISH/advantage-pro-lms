from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.pagination import paginate_rows
from core.permissions import has_any_role
from core.roles import Role
from core.utils import get_client_ip

from .models import Escalation
from .services import run_escalations

ReviewRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.COUNSELOR)


class RunEscalationsView(APIView):
    """Trigger the escalation scan now (production runs it on a schedule)."""

    permission_classes = [has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS)]

    def post(self, request):
        result = run_escalations()
        record_action(
            actor=request.user,
            action="escalations_run",
            metadata=result,
            ip_address=get_client_ip(request),
        )
        return Response(result)


class EscalationListView(APIView):
    """Batch-wise escalation ledger (req 23): filter with ``?batch=<id>``."""

    permission_classes = [ReviewRoles]

    def get(self, request):
        rows = Escalation.objects.select_related("student", "batch")
        batch_id = request.query_params.get("batch")
        if batch_id:
            rows = rows.filter(batch_id=batch_id)
        return paginate_rows(
            request,
            rows,
            lambda e: {
                "id": str(e.id),
                "kind": e.kind,
                "student_name": e.student.full_name or e.student.username,
                "registration_number": e.student.username,
                "batch_code": e.batch.code if e.batch else "",
                "reference_id": e.reference_id,
                "created_at": e.created_at,
            },
            view=self,
        )
