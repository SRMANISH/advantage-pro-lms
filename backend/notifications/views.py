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

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
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


class ChannelsView(APIView):
    """Super Admin: which provider backs each integration channel."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        channels = [
            {
                "kind": kind,
                "adapter": path,
                "dev_stub": path.startswith("core.adapters.local"),
            }
            for kind, path in settings.LMS_ADAPTERS.items()
        ]
        return Response({"channels": channels})


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
