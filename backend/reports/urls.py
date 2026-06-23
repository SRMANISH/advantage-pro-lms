from django.urls import path

from .views import AttendanceReport, PerformanceReport, StudentsReport

urlpatterns = [
    path("reports/students/", StudentsReport.as_view(), name="report-students"),
    path("reports/attendance/", AttendanceReport.as_view(), name="report-attendance"),
    path("reports/performance/", PerformanceReport.as_view(), name="report-performance"),
]
