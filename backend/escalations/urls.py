from django.urls import path

from .views import RunEscalationsView

urlpatterns = [
    path("escalations/run/", RunEscalationsView.as_view(), name="escalations-run"),
]
