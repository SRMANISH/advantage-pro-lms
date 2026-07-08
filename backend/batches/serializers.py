from rest_framework import serializers

from accounts.models import User
from core.roles import Role

from .models import Batch, BatchState, Course


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "name", "description", "duration", "fees", "created_at"]
        read_only_fields = ["id", "created_at"]


class FacultyBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "full_name"]
        read_only_fields = fields


class BatchSerializer(serializers.ModelSerializer):
    course_detail = CourseSerializer(source="course", read_only=True)
    faculty_detail = FacultyBriefSerializer(source="faculty", many=True, read_only=True)
    faculty = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.FACULTY), many=True, required=False
    )

    class Meta:
        model = Batch
        fields = [
            "id",
            "code",
            "name",
            "course",
            "course_detail",
            "start_date",
            "end_date",
            "state",
            "faculty",
            "faculty_detail",
            "created_at",
        ]
        read_only_fields = ["id", "state", "created_at"]

    def validate(self, attrs):
        start = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end = attrs.get("end_date") or getattr(self.instance, "end_date", None)
        if start and end and end < start:
            raise serializers.ValidationError("end_date cannot be before start_date.")
        return attrs


class FacultyAssignSerializer(serializers.Serializer):
    faculty_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.FACULTY), many=True
    )


class TransitionSerializer(serializers.Serializer):
    to_state = serializers.ChoiceField(choices=BatchState.choices)
