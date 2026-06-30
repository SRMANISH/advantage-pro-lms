from rest_framework import serializers

from content.access import can_access_batch

from .models import Reply, Thread


class ReplySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Reply
        fields = ["id", "author_name", "body", "created_at"]
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

    class Meta(ThreadSerializer.Meta):
        fields = [*ThreadSerializer.Meta.fields, "replies"]


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
