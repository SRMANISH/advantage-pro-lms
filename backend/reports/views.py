"""CSV exports: students, attendance, performance — role-scoped per the matrix."""

import csv

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from accounts.models import User
from attendance.services import batch_attendance_summaries
from batches.selectors import resolve_batch
from core.permissions import has_any_role
from core.roles import Role
from core.schema import DetailResponse
from enrollments.models import Enrollment
from performance.services import batch_performance

# Excel, LibreOffice and Google Sheets treat a leading =, +, - or @ as the start of a
# formula, and a leading tab/CR can smuggle one past a naive check. Every export below
# carries user-supplied text (student names, follow-up notes) and is opened by staff in a
# spreadsheet, so an unescaped cell is remote code execution on the reader's machine, not a
# cosmetic issue. Prefixing with a single quote makes the cell literal text.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_cell(value):
    """Neutralise spreadsheet formula injection in one cell, leaving the value readable."""
    if not isinstance(value, str):
        return value
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value


def _csv(filename: str, header: list[str], rows) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(header)
    for row in rows:
        writer.writerow([_sanitize_cell(cell) for cell in row])
    return response


@extend_schema(responses={(200, "text/csv"): OpenApiTypes.STR, 400: DetailResponse})
class StudentsReport(APIView):
    permission_classes = [has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY)]

    def get(self, request):
        batch, error = resolve_batch(request, allow_body=False)
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


@extend_schema(responses={(200, "text/csv"): OpenApiTypes.STR, 400: DetailResponse})
class AttendanceReport(APIView):
    permission_classes = [
        has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.COUNSELOR, Role.FACULTY)
    ]

    def get(self, request):
        batch, error = resolve_batch(request, allow_body=False)
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


@extend_schema(responses={(200, "text/csv"): OpenApiTypes.STR, 400: DetailResponse})
class PerformanceReport(APIView):
    permission_classes = [
        has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.COUNSELOR, Role.FACULTY)
    ]

    def get(self, request):
        batch, error = resolve_batch(request, allow_body=False)
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
