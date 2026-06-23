"""Root URL configuration."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(_request):
    return JsonResponse({"status": "ok", "service": "advantage-pro-lms"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/", include("batches.urls")),
    path("api/v1/", include("enrollments.urls")),
    path("api/v1/", include("dashboard.urls")),
    path("api/v1/", include("content.urls")),
    path("api/v1/", include("notifications.urls")),
    path("api/v1/", include("assessments.urls")),
    path("api/v1/", include("attendance.urls")),
    path("api/v1/", include("performance.urls")),
    path("api/v1/", include("escalations.urls")),
    path("api/v1/", include("forum.urls")),
    path("api/v1/", include("liveclasses.urls")),
    path("api/v1/", include("certification.urls")),
    path("api/v1/", include("upsell.urls")),
    path("api/v1/", include("reports.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
