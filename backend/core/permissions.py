"""DRF permission classes that enforce the matrix server-side."""

from rest_framework.permissions import BasePermission

from .permissions_matrix import can
from .roles import Role


class MatrixPermission(BasePermission):
    """Grant access when the user's role may perform ``view.required_action``.

    Views declare the action they guard::

        class BatchViewSet(ModelViewSet):
            required_action = Action.CREATE_EDIT_BATCH

    A view without ``required_action`` only requires authentication.
    """

    message = "Your role is not permitted to perform this action."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        # A ViewSet maps each action to a matrix action via get_required_action();
        # a plain view may set a single ``required_action``. None => auth is enough.
        if hasattr(view, "get_required_action"):
            action = view.get_required_action()
        else:
            action = getattr(view, "required_action", None)
        if action is None:
            return True
        return can(user.role, action)


class IsSuperAdmin(BasePermission):
    message = "Super Admin access required."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.role == Role.SUPER_ADMIN)


def has_any_role(*roles: str) -> type[BasePermission]:
    """Build a permission class restricting access to the given roles."""
    allowed = frozenset(roles)

    class _HasAnyRole(BasePermission):
        message = "Your role is not permitted to access this resource."

        def has_permission(self, request, view) -> bool:
            user = getattr(request, "user", None)
            return bool(user and user.is_authenticated and user.role in allowed)

    return _HasAnyRole
