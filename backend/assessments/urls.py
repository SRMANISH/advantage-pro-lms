from rest_framework.routers import DefaultRouter

from .views import TaskSubmissionViewSet, TaskViewSet, TestViewSet

router = DefaultRouter()
router.register("tests", TestViewSet, basename="test")
router.register("tasks", TaskViewSet, basename="task")
router.register("task-submissions", TaskSubmissionViewSet, basename="task-submission")

urlpatterns = router.urls
