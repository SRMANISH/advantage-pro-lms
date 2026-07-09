"""Performance read APIs: a student's own record and a per-batch ranked board."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from batches.models import Batch
from core.permissions import has_any_role
from core.roles import Role
from enrollments.models import Enrollment

from .services import batch_performance_cached


class MyPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = []
        enrollments = Enrollment.objects.filter(student=request.user).select_related("batch")
        for e in enrollments:
            board = batch_performance_cached(e.batch)
            mine = next((r for r in board if r["student"] == str(request.user.id)), None)
            if mine:
                rows.append(
                    {
                        "batch": e.batch.code,
                        "batch_name": e.batch.name,
                        "size": len(board),
                        **mine,
                    }
                )
        return Response(rows)


class BatchPerformanceView(APIView):
    permission_classes = [
        has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.COUNSELOR, Role.FACULTY)
    ]

    def get(self, request):
        batch_id = request.query_params.get("batch")
        if not batch_id:
            return Response({"detail": "batch query param required."}, status=400)
        batch = Batch.objects.filter(id=batch_id).first()
        if not batch:
            return Response({"detail": "Batch not found."}, status=404)
        if (
            request.user.role == Role.FACULTY
            and not batch.faculty.filter(id=request.user.id).exists()
        ):
            return Response({"detail": "Not your batch."}, status=403)
        return Response(batch_performance_cached(batch))
