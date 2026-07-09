from django.urls import path

from .views import EnrollmentImportView, EnrollmentListView
from .welcome import (
    GoodiesRegisterView,
    GoodiesSentView,
    WelcomeMeView,
    WelcomeSubmitView,
)

urlpatterns = [
    path("enrollments/", EnrollmentListView.as_view(), name="enrollment-list"),
    path("enrollments/import/", EnrollmentImportView.as_view(), name="enrollment-import"),
    path("welcome/me/", WelcomeMeView.as_view(), name="welcome-me"),
    path("welcome/submit/", WelcomeSubmitView.as_view(), name="welcome-submit"),
    path("welcome/register/", GoodiesRegisterView.as_view(), name="goodies-register"),
    path("welcome/goodies/", GoodiesSentView.as_view(), name="goodies-sent"),
]
