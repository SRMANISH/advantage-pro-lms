from rest_framework import serializers

from content.access import can_access_batch

from .models import Reply, Thread, ThreadAttachment


class AttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ThreadAttachment
        fields = ["id", "filename", "content_type", "download_url", "created_at"]
        read_only_fields = fields

    def get_download_url(self, obj) -> str:
        return f"/api/v1/attachments/{obj.id}/"


class ReplySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Reply
        fields = ["id", "author_name", "body", "attachments", "created_at"]
        read_only_fields = fields

    def get_author_name(self, obj) -> str:
        return obj.author.full_name or obj.author.username


class ThreadSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    batch_code = serializers.CharField(source="batch.code", read_only=True)
    reply_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Thread
        fields = [
            "id",
            "batch",
            "batch_code",
            "title",
            "body",
            "resolved",
            "status",
            "author_name",
            "reply_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj) -> str:
        return obj.author.full_name or obj.author.username


class ThreadDetailSerializer(ThreadSerializer):
    replies = ReplySerializer(many=True, read_only=True)
    attachments = serializers.SerializerMethodField()

    class Meta(ThreadSerializer.Meta):
        fields = [*ThreadSerializer.Meta.fields, "attachments", "replies"]

    def get_attachments(self, obj):
        # Thread-level attachments only; reply attachments ride along on each reply.
        return AttachmentSerializer(obj.attachments.filter(reply__isnull=True), many=True).data


class ThreadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = ["id", "batch", "title", "body"]
        read_only_fields = ["id"]

    def validate_batch(self, batch):
        if not can_access_batch(self.context["request"].user, batch):
            raise serializers.ValidationError("You cannot post in this batch.")
        return batch


class ReplyCreateSerializer(serializers.Serializer):
    body = serializers.CharField()
