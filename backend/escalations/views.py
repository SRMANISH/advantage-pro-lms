from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.permissions import has_any_role
from core.roles import Role
from core.utils import get_client_ip

from .services import run_escalations


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
