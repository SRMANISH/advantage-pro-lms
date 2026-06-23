from django.urls import path

from .views import (
    BatchAttendanceView,
    FollowUpView,
    MyAttendanceView,
    ReviewBatchesView,
)

urlpatterns = [
    path("attendance/me/", MyAttendanceView.as_view(), name="attendance-me"),
    path("attendance/batches/", ReviewBatchesView.as_view(), name="attendance-batches"),
    path("attendance/follow-up/", FollowUpView.as_view(), name="attendance-follow-up"),
    path("attendance/", BatchAttendanceView.as_view(), name="attendance-batch"),
]
