"""Shared batch lookups for view layers.

Lives in ``batches`` rather than ``core`` deliberately: it needs the Batch model, and core
is the layer everything else depends on — importing a domain app into it would invert the
dependency direction the codebase otherwise maintains.
"""

from rest_framework.response import Response

from core.roles import Role

from .models import Batch


def resolve_batch(request, *, allow_body: bool = True):
    """Resolve the requested batch and enforce faculty-own-batch scoping.

    Returns ``(batch, None)`` on success or ``(None, error_response)`` so callers can
    ``if error: return error``. Reads ``?batch=`` and, when ``allow_body`` is set, a
    ``batch`` key in the request body (some endpoints POST it).
    """
    batch_id = request.query_params.get("batch")
    if not batch_id and allow_body:
        batch_id = request.data.get("batch") if hasattr(request, "data") else None
    if not batch_id:
        return None, Response({"detail": "Select a batch first."}, status=400)

    batch = Batch.objects.filter(id=batch_id).first()
    if not batch:
        return None, Response({"detail": "Batch not found."}, status=404)
    if request.user.role == Role.FACULTY and not batch.faculty.filter(id=request.user.id).exists():
        return None, Response({"detail": "Not your batch."}, status=403)
    return batch, None
