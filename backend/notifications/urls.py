from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChannelsView, ChannelTestView, NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("settings/channels/", ChannelsView.as_view(), name="settings-channels"),
    path("settings/channels/test/", ChannelTestView.as_view(), name="settings-channels-test"),
    *router.urls,
]
