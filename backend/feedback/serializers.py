from rest_framework import serializers

from .models import Feedback


class FeedbackCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField()


class FeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = [
            "id",
            "student_name",
            "registration_number",
            "batch_code",
            "course_name",
            "subject",
            "message",
            "created_at",
        ]
        read_only_fields = fields

    def get_student_name(self, obj) -> str:
        return obj.student.full_name or obj.student.username
