from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BatchViewSet, CourseViewSet, FacultyListView

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="course")
router.register("batches", BatchViewSet, basename="batch")

urlpatterns = [
    path("faculty/", FacultyListView.as_view(), name="faculty-list"),
    *router.urls,
]
