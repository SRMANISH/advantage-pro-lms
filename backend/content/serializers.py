import uuid

from rest_framework import serializers

from core.adapters.registry import get_storage
from core.roles import Role
from core.uploads import validate_upload

from .access import can_access_batch
from .models import Material, Video


class VideoSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.full_name", read_only=True)
    play_url = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            "id",
            "batch",
            "title",
            "description",
            "order",
            "content_type",
            "uploaded_by_name",
            "play_url",
            "progress",
            "created_at",
        ]
        read_only_fields = fields

    def get_play_url(self, obj) -> str:
        return f"/api/v1/videos/{obj.id}/play/"

    def get_progress(self, obj):
        user = self.context["request"].user
        if user.role != Role.STUDENT:
            return None
        p = obj.progresses.filter(student=user).first()
        if not p:
            return {"percent": 0, "completed": False, "last_position": 0}
        return {"percent": p.percent, "completed": p.completed, "last_position": p.last_position}


class VideoUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Video
        fields = ["id", "batch", "title", "description", "order", "file"]
        read_only_fields = ["id"]

    def validate_batch(self, batch):
        if not can_access_batch(self.context["request"].user, batch):
            raise serializers.ValidationError("You cannot upload to this batch.")
        return batch

    def validate_file(self, upload):
        return validate_upload(upload, "video")

    def create(self, validated):
        upload = validated.pop("file")
        key = f"videos/{uuid.uuid4()}/{upload.name}"
        get_storage().save(key, upload)
        validated["storage_key"] = key
        validated["content_type"] = getattr(upload, "content_type", "") or "video/mp4"
        validated["uploaded_by"] = self.context["request"].user
        return super().create(validated)


class ProgressSerializer(serializers.Serializer):
    percent = serializers.IntegerField(min_value=0, max_value=100)
    watched_seconds = serializers.IntegerField(min_value=0, required=False, default=0)
    last_position = serializers.IntegerField(min_value=0, required=False, default=0)


class MaterialSerializer(serializers.ModelSerializer):
    view_url = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = ["id", "batch", "title", "content_type", "view_url", "created_at"]
        read_only_fields = fields

    def get_view_url(self, obj) -> str:
        return f"/api/v1/materials/{obj.id}/view/"


class MaterialUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Material
        fields = ["id", "batch", "title", "file"]
        read_only_fields = ["id"]

    def validate_batch(self, batch):
        if not can_access_batch(self.context["request"].user, batch):
            raise serializers.ValidationError("You cannot upload to this batch.")
        return batch

    def validate_file(self, upload):
        return validate_upload(upload, "document")

    def create(self, validated):
        upload = validated.pop("file")
        key = f"materials/{uuid.uuid4()}/{upload.name}"
        get_storage().save(key, upload)
        validated["storage_key"] = key
        validated["content_type"] = (
            getattr(upload, "content_type", "") or "application/octet-stream"
        )
        validated["uploaded_by"] = self.context["request"].user
        return super().create(validated)
