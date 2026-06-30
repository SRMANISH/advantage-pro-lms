from django.urls import path

from .views import (
    CertFollowUpStatusView,
    CertificateFollowUpListView,
    CertificationMeView,
    RunCertRemindersView,
    SubmitCertificateView,
)

urlpatterns = [
    path("certification/me/", CertificationMeView.as_view(), name="certification-me"),
    path("certification/submit/", SubmitCertificateView.as_view(), name="certification-submit"),
    path("certification/remind/", RunCertRemindersView.as_view(), name="certification-remind"),
    path(
        "certification/follow-up/",
        CertificateFollowUpListView.as_view(),
        name="certification-follow-up",
    ),
    path(
        "certification/follow-up/status/",
        CertFollowUpStatusView.as_view(),
        name="certification-follow-up-status",
    ),
]
