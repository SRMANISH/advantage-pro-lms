from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from content.access import can_access_batch
from core.roles import Role

from .models import CheckIn, LiveClass


class LiveClassSerializer(serializers.ModelSerializer):
    batch_code = serializers.CharField(source="batch.code", read_only=True)
    checked_in = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = LiveClass
        fields = [
            "id",
            "batch",
            "batch_code",
            "title",
            "scheduled_at",
            "duration_minutes",
            "platform",
            "meeting_link",
            "status",
            "cancel_reason",
            "checked_in",
            "created_at",
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_checked_in(self, obj):
        user = self.context["request"].user
        if user.role != Role.STUDENT:
            return None
        return CheckIn.objects.filter(live_class=obj, student=user).exists()

    def get_duration_minutes(self, obj) -> int:
        return int(getattr(settings, "LIVE_CLASS_DURATION_MINUTES", 120))


class LiveClassWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveClass
        fields = ["id", "batch", "title", "scheduled_at", "platform", "meeting_link"]
        read_only_fields = ["id"]

    def validate_batch(self, batch):
        if not can_access_batch(self.context["request"].user, batch):
            raise serializers.ValidationError("You cannot schedule for this batch.")
        return batch
