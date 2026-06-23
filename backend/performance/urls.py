from django.urls import path

from .views import BatchPerformanceView, MyPerformanceView

urlpatterns = [
    path("performance/me/", MyPerformanceView.as_view(), name="performance-me"),
    path("performance/", BatchPerformanceView.as_view(), name="performance-batch"),
]
