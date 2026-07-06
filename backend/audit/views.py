"""Activity/audit feed — accessible only to Faculty and MIS (updated procedure).

Admin and Super Admin no longer have activity access. Faculty see their own activity
plus actions on their assigned batches; MIS see all activity.
"""

from django.db.models import Q
from rest_framework.generics import ListAPIView

from core.pagination import StandardResultsPagination
from core.permissions import has_any_role
from core.roles import Role

from .models import AuditLog
from .serializers import AuditLogSerializer

ActivityRoles = has_any_role(Role.MIS, Role.FACULTY)


class ActivityLogView(ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [ActivityRoles]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        qs = AuditLog.objects.select_related("actor")
        user = self.request.user
        if user.role == Role.MIS:
            return qs
        # Faculty: own activity + actions targeting their assigned batches.
        from batches.models import Batch

        batch_ids = [
            str(bid) for bid in Batch.objects.filter(faculty=user).values_list("id", flat=True)
        ]
        return qs.filter(Q(actor=user) | Q(target_type="batch", target_id__in=batch_ids))
