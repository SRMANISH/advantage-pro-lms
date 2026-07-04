from django.urls import path

from .views import (
    EngagementMeView,
    GoogleReviewActionView,
    GoogleReviewReportView,
    LinkedInActionView,
    LinkedInReportView,
    NextPlanListView,
    NextPlanView,
    UtilityLinkDetailView,
    UtilityLinksView,
)

urlpatterns = [
    path("engagement/me/", EngagementMeView.as_view(), name="engagement-me"),
    path("engagement/linkedin/", LinkedInActionView.as_view(), name="engagement-linkedin"),
    path("engagement/google-review/", GoogleReviewActionView.as_view(), name="engagement-google"),
    path("engagement/next-plan/", NextPlanView.as_view(), name="engagement-next-plan"),
    path(
        "engagement/reports/linkedin/", LinkedInReportView.as_view(), name="engagement-r-linkedin"
    ),
    path(
        "engagement/reports/google-review/",
        GoogleReviewReportView.as_view(),
        name="engagement-r-google",
    ),
    path("engagement/next-plans/", NextPlanListView.as_view(), name="engagement-next-plans"),
    path("utility-links/", UtilityLinksView.as_view(), name="utility-links"),
    path("utility-links/<uuid:pk>/", UtilityLinkDetailView.as_view(), name="utility-link-detail"),
]
