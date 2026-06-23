from rest_framework import serializers

from content.access import can_access_batch
from core.roles import Role

from .models import CheckIn, LiveClass


class LiveClassSerializer(serializers.ModelSerializer):
    batch_code = serializers.CharField(source="batch.code", read_only=True)
    checked_in = serializers.SerializerMethodField()

    class Meta:
        model = LiveClass
        fields = [
            "id",
            "batch",
            "batch_code",
            "title",
            "scheduled_at",
            "platform",
            "meeting_link",
            "checked_in",
            "created_at",
        ]
        read_only_fields = fields

    def get_checked_in(self, obj):
        user = self.context["request"].user
        if user.role != Role.STUDENT:
            return None
        return CheckIn.objects.filter(live_class=obj, student=user).exists()


class LiveClassWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveClass
        fields = ["id", "batch", "title", "scheduled_at", "platform", "meeting_link"]
        read_only_fields = ["id"]

    def validate_batch(self, batch):
        if not can_access_batch(self.context["request"].user, batch):
            raise serializers.ValidationError("You cannot schedule for this batch.")
        return batch
