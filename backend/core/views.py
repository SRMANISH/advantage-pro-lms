"""Super Admin permission-matrix editor (MANAGE_SETTINGS).

The code matrix stays the default; these endpoints create/remove per-action overrides
(``core.models.PermissionOverride``). Every change is audited and takes effect within the
matrix cache TTL (seconds) across all workers.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from core.utils import get_client_ip

from .models import PermissionOverride
from .permissions import MatrixPermission
from .permissions_matrix import (
    ALL_ACTIONS,
    LOCKED_SA_ACTIONS,
    MATRIX,
    Action,
    invalidate_matrix_cache,
    roles_for,
)
from .roles import Role


class MatrixView(APIView):
    """The full effective matrix: defaults, current roles, and override state."""

    permission_classes = [MatrixPermission]
    required_action = Action.MANAGE_SETTINGS

    def get(self, request):
        overridden = set(PermissionOverride.objects.values_list("action", flat=True))
        rows = [
            {
                "action": action,
                "roles": sorted(roles_for(action)),
                "default_roles": sorted(MATRIX.get(action, frozenset())),
                "overridden": action in overridden,
            }
            for action in ALL_ACTIONS
        ]
        return Response(
            {
                "roles": [{"value": r.value, "label": r.label} for r in Role],
                "locked_super_admin_actions": sorted(LOCKED_SA_ACTIONS),
                "rows": rows,
            }
        )


class MatrixActionView(APIView):
    """Replace (PUT) or reset (DELETE) one action's allowed-roles set."""

    permission_classes = [MatrixPermission]
    required_action = Action.MANAGE_SETTINGS

    def put(self, request, action):
        if action not in MATRIX:
            return Response({"detail": "Unknown action."}, status=status.HTTP_404_NOT_FOUND)
        raw = request.data.get("roles")
        if not isinstance(raw, list) or not all(r in Role.values for r in raw):
            return Response(
                {"detail": "Roles must be a list of valid role values."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        roles = sorted(set(raw))
        if action in LOCKED_SA_ACTIONS and Role.SUPER_ADMIN not in roles:
            return Response(
                {"detail": "Super Admin cannot be removed from this action (lockout guard)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        default = MATRIX[action]
        if set(roles) == set(default):
            # Saving the default is a reset — keep the table free of no-op rows.
            PermissionOverride.objects.filter(action=action).delete()
            overridden = False
        else:
            PermissionOverride.objects.update_or_create(
                action=action, defaults={"roles": roles, "updated_by": request.user}
            )
            overridden = True
        invalidate_matrix_cache()
        record_action(
            actor=request.user,
            action="permission_matrix_changed",
            target_type="permission",
            target_id=action,
            metadata={"roles": roles, "overridden": overridden},
            ip_address=get_client_ip(request),
        )
        return Response(
            {
                "action": action,
                "roles": sorted(roles_for(action)),
                "default_roles": sorted(default),
                "overridden": overridden,
            }
        )

    def delete(self, request, action):
        if action not in MATRIX:
            return Response({"detail": "Unknown action."}, status=status.HTTP_404_NOT_FOUND)
        PermissionOverride.objects.filter(action=action).delete()
        invalidate_matrix_cache()
        record_action(
            actor=request.user,
            action="permission_matrix_reset",
            target_type="permission",
            target_id=action,
            ip_address=get_client_ip(request),
        )
        return Response(
            {
                "action": action,
                "roles": sorted(roles_for(action)),
                "default_roles": sorted(MATRIX[action]),
                "overridden": False,
            }
        )
