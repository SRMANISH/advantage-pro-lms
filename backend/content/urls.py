from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CloseCourseVideoAccessView,
    MaterialViewSet,
    RestoreVideoAccessView,
    RevokeVideoAccessView,
    VideoViewSet,
)

router = DefaultRouter()
router.register("videos", VideoViewSet, basename="video")
router.register("materials", MaterialViewSet, basename="material")

urlpatterns = [
    path("video-access/revoke/", RevokeVideoAccessView.as_view(), name="video-access-revoke"),
    path("video-access/restore/", RestoreVideoAccessView.as_view(), name="video-access-restore"),
    path(
        "video-access/close-course/",
        CloseCourseVideoAccessView.as_view(),
        name="video-access-close",
    ),
    *router.urls,
]
