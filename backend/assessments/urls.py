from rest_framework.routers import DefaultRouter

from .views import TaskSubmissionViewSet, TaskViewSet, TestAttemptViewSet, TestViewSet

router = DefaultRouter()
router.register("tests", TestViewSet, basename="test")
router.register("test-attempts", TestAttemptViewSet, basename="test-attempt")
router.register("tasks", TaskViewSet, basename="task")
router.register("task-submissions", TaskSubmissionViewSet, basename="task-submission")

urlpatterns = router.urls
