from django.conf import settings
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from audit.services import record_action
from core.adapters.registry import get_email, get_sms, get_whatsapp
from core.pagination import StandardResultsPagination
from core.permissions import IsSuperAdmin

from .models import IntegrationSetting, Notification
from .serializers import NotificationSerializer


class NotificationViewSet(ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()  # OpenAPI schema generation (no real user)
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        note = self.get_object()
        note.read = True
        note.save(update_fields=["read", "updated_at"])
        return Response({"ok": True})

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        self.get_queryset().filter(read=False).update(read=True)
        return Response({"ok": True})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(read=False).count()})


class IntegrationSettingSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=IntegrationSetting.Channel.values)
    provider = serializers.CharField(max_length=50, allow_blank=True, default="")
    config = serializers.DictField(required=False, default=dict)
    # Blank secret = "keep the stored one"; a new value overwrites it. Never returned.
    secret = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class ChannelsView(APIView):
    """Super Admin: view and edit the third-party connection behind each channel (req 21)."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        saved = {s.channel: s for s in IntegrationSetting.objects.all()}
        channels = []
        for kind, path in settings.LMS_ADAPTERS.items():
            s = saved.get(kind)
            channels.append(
                {
                    "kind": kind,
                    "adapter": path,
                    "dev_stub": path.startswith("core.adapters.local"),
                    "editable": kind in IntegrationSetting.Channel.values,
                    "provider": s.provider if s else "",
                    "config": s.config if s else {},
                    "secret_set": bool(s and s.secret),  # the value itself is never sent
                }
            )
        return Response({"channels": channels})

    def put(self, request):
        serializer = IntegrationSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        setting, _ = IntegrationSetting.objects.get_or_create(channel=data["channel"])
        setting.provider = data["provider"]
        setting.config = data["config"]
        if data["secret"]:  # only overwrite when a fresh secret is supplied
            setting.secret = data["secret"]
        setting.updated_by = request.user
        setting.save()
        record_action(
            actor=request.user,
            action="integration_updated",
            metadata={"channel": data["channel"], "provider": data["provider"]},
        )
        return Response({"ok": True, "secret_set": bool(setting.secret)})


class ChannelTestSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=["email", "sms", "whatsapp"])
    to = serializers.CharField()
    message = serializers.CharField()


class ChannelTestView(APIView):
    """Super Admin: send a test message through a channel's adapter."""

    permission_classes = [IsSuperAdmin]

    def post(self, request):
        serializer = ChannelTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["channel"] == "email":
            get_email().send(data["to"], "Advantage Pro test", data["message"])
        elif data["channel"] == "sms":
            get_sms().send(data["to"], data["message"])
        else:
            get_whatsapp().send(data["to"], data["message"])
        record_action(
            actor=request.user, action="channel_test", metadata={"channel": data["channel"]}
        )
        return Response({"ok": True})
