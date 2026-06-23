from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ForumBatchesView, ForumMonitorView, ThreadViewSet

router = DefaultRouter()
router.register("threads", ThreadViewSet, basename="thread")

urlpatterns = [
    path("forum/batches/", ForumBatchesView.as_view(), name="forum-batches"),
    path("forum/monitor/", ForumMonitorView.as_view(), name="forum-monitor"),
    *router.urls,
]
