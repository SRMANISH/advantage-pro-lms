from django.urls import path

from .views import CertificationMeView, RunCertRemindersView, SubmitCertificateView

urlpatterns = [
    path("certification/me/", CertificationMeView.as_view(), name="certification-me"),
    path("certification/submit/", SubmitCertificateView.as_view(), name="certification-submit"),
    path("certification/remind/", RunCertRemindersView.as_view(), name="certification-remind"),
]
