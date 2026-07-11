from django.urls import path

from .views import EscalationListView, RunEscalationsView

urlpatterns = [
    path("escalations/run/", RunEscalationsView.as_view(), name="escalations-run"),
    path("escalations/", EscalationListView.as_view(), name="escalations-list"),
]
