"""Role-aware dashboard summary for each portal's home screen."""

from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from batches.models import Batch, BatchState, Course
from core.roles import Role
from enrollments.models import Enrollment


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = user.role

        if role == Role.STUDENT:
            enrollments = (
                Enrollment.objects.filter(student=user)
                .select_related("batch", "batch__course")
                .prefetch_related("batch__faculty")
            )
            batches = [
                {
                    "id": str(e.batch_id),
                    "code": e.batch.code,
                    "name": e.batch.name,
                    "course": e.batch.course.name,
                    "state": e.batch.state,
                    "start_date": e.batch.start_date,
                    "end_date": e.batch.end_date,
                    "faculty": [f.full_name or f.username for f in e.batch.faculty.all()],
                }
                for e in enrollments
            ]
            return Response({"role": role, "batches": batches})

        if role == Role.FACULTY:
            qs = (
                Batch.objects.filter(faculty=user)
                .select_related("course")
                .annotate(student_count=Count("enrollments"))
            )
            batches = [
                {
                    "id": str(b.id),
                    "code": b.code,
                    "name": b.name,
                    "course": b.course.name,
                    "state": b.state,
                    "student_count": b.student_count,
                }
                for b in qs
            ]
            return Response(
                {
                    "role": role,
                    "totals": {
                        "batches": len(batches),
                        "students": sum(b["student_count"] for b in batches),
                    },
                    "batches": batches,
                }
            )

        if role in {Role.SUPER_ADMIN, Role.ADMIN, Role.MIS}:
            return Response(
                {
                    "role": role,
                    "totals": {
                        "batches": Batch.objects.count(),
                        "active_batches": Batch.objects.filter(state=BatchState.ACTIVE).count(),
                        "students": Enrollment.objects.count(),
                        "courses": Course.objects.count(),
                    },
                }
            )

        if role == Role.COUNSELOR:
            return Response(
                {
                    "role": role,
                    "totals": {
                        "students": Enrollment.objects.count(),
                        "batches": Batch.objects.count(),
                    },
                }
            )

        return Response({"role": role, "totals": {}})
