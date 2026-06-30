from django.urls import path

from .views import (
    BatchAttendanceView,
    DailyAttendanceView,
    FollowUpStatusView,
    FollowUpView,
    MyAttendanceView,
    ReviewBatchesView,
)

urlpatterns = [
    path("attendance/me/", MyAttendanceView.as_view(), name="attendance-me"),
    path("attendance/batches/", ReviewBatchesView.as_view(), name="attendance-batches"),
    path("attendance/daily/", DailyAttendanceView.as_view(), name="attendance-daily"),
    path("attendance/follow-up/", FollowUpView.as_view(), name="attendance-follow-up"),
    path(
        "attendance/follow-up/status/",
        FollowUpStatusView.as_view(),
        name="attendance-follow-up-status",
    ),
    path("attendance/", BatchAttendanceView.as_view(), name="attendance-batch"),
]
