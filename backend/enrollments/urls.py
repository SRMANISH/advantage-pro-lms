from django.urls import path

from .views import EnrollmentImportView, EnrollmentListView

urlpatterns = [
    path("enrollments/", EnrollmentListView.as_view(), name="enrollment-list"),
    path("enrollments/import/", EnrollmentImportView.as_view(), name="enrollment-import"),
]
