"""CSV exports: students, attendance, performance — role-scoped per the matrix."""

import csv

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from attendance.services import batch_attendance_summaries
from batches.models import Batch
from core.permissions import has_any_role
from core.roles import Role
from enrollments.models import Enrollment
from performance.services import batch_performance


def _batch_for(request):
    """Resolve ?batch= and enforce faculty-own-batch. Returns (batch, error_response)."""
    batch_id = request.query_params.get("batch")
    if not batch_id:
        return None, Response({"detail": "batch query param required."}, status=400)
    batch = Batch.objects.filter(id=batch_id).first()
    if not batch:
        return None, Response({"detail": "Batch not found."}, status=404)
    if request.user.role == Role.FACULTY and not batch.faculty.filter(id=request.user.id).exists():
        return None, Response({"detail": "Not your batch."}, status=403)
    return batch, None


def _csv(filename: str, header: list[str], rows) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return response


class StudentsReport(APIView):
    permission_classes = [has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY)]

    def get(self, request):
        batch, error = _batch_for(request)
        if error:
            return error
        enrollments = Enrollment.objects.filter(batch=batch).select_related("student")
        rows = (
            (
                e.registration_number,
                e.student.full_name,
                e.student.email,
                e.student.phone,
                e.student.status,
            )
            for e in enrollments
        )
        return _csv(
            f"students_{batch.code}.csv",
            ["Registration ID", "Name", "Email", "Phone", "Status"],
            rows,
        )


class AttendanceReport(APIView):
    permission_classes = [
        has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.COUNSELOR, Role.FACULTY)
    ]

    def get(self, request):
        batch, error = _batch_for(request)
        if error:
            return error
        students = list(User.objects.filter(enrollments__batch=batch).distinct())
        summaries = batch_attendance_summaries(batch, students)  # one grouped query
        rows = []
        for s in students:
            summary = summaries.get(s.id, {"present": 0, "total": 0, "percent": 0})
            rows.append(
                (s.username, s.full_name, summary["present"], summary["total"], summary["percent"])
            )
        return _csv(
            f"attendance_{batch.code}.csv",
            ["Registration ID", "Name", "Present", "Total", "Percent"],
            rows,
        )


class PerformanceReport(APIView):
    permission_classes = [
        has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.COUNSELOR, Role.FACULTY)
    ]

    def get(self, request):
        batch, error = _batch_for(request)
        if error:
            return error
        rows = (
            (
                r["rank"],
                r["registration_number"],
                r["student_name"],
                r["test_pct"],
                r["task_pct"],
                r["video_pct"],
                r["attendance_pct"],
                r["overall"],
            )
            for r in batch_performance(batch)
        )
        return _csv(
            f"performance_{batch.code}.csv",
            [
                "Rank",
                "Registration ID",
                "Name",
                "Tests %",
                "Tasks %",
                "Videos %",
                "Attendance %",
                "Overall %",
            ],
            rows,
        )
