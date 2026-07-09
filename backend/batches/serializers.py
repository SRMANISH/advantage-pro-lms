from rest_framework import serializers

from accounts.models import User
from core.roles import Role

from .models import WEEKDAYS, Batch, BatchState, Course


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "name", "description", "duration", "fees", "created_at"]
        read_only_fields = ["id", "created_at"]


class FacultyBriefSerializer(serializers.ModelSerializer):
    """Faculty for the assign dropdown — includes skills/certifications so the assigner
    can match the right person to the right course."""

    skills = serializers.CharField(source="faculty_profile.skills", read_only=True, default="")
    certifications = serializers.CharField(
        source="faculty_profile.certifications", read_only=True, default=""
    )

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "skills", "certifications"]
        read_only_fields = fields


class BatchSerializer(serializers.ModelSerializer):
    course_detail = CourseSerializer(source="course", read_only=True)
    faculty_detail = FacultyBriefSerializer(source="faculty", many=True, read_only=True)
    primary_faculty_detail = FacultyBriefSerializer(source="primary_faculty", read_only=True)
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
            "class_days",
            "class_start_time",
            "class_end_time",
            "state",
            "faculty",
            "faculty_detail",
            "primary_faculty",
            "primary_faculty_detail",
            "created_at",
        ]
        read_only_fields = ["id", "state", "primary_faculty", "created_at"]

    def validate_class_days(self, value):
        if not isinstance(value, list) or not all(d in WEEKDAYS for d in value):
            raise serializers.ValidationError(f"class_days must be a subset of {WEEKDAYS}.")
        return value

    def validate(self, attrs):
        start = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end = attrs.get("end_date") or getattr(self.instance, "end_date", None)
        if start and end and end < start:
            raise serializers.ValidationError("end_date cannot be before start_date.")
        # Class days + times are mandatory when creating a batch (req 14). On edit, only
        # validate what's supplied.
        if self.instance is None:
            days = attrs.get("class_days")
            cst = attrs.get("class_start_time")
            cet = attrs.get("class_end_time")
            if not days:
                raise serializers.ValidationError({"class_days": "Select at least one class day."})
            if not cst or not cet:
                raise serializers.ValidationError(
                    {"class_start_time": "Class start and end times are required."}
                )
        cst = attrs.get("class_start_time") or getattr(self.instance, "class_start_time", None)
        cet = attrs.get("class_end_time") or getattr(self.instance, "class_end_time", None)
        if cst and cet and cet <= cst:
            raise serializers.ValidationError(
                {"class_end_time": "Class end time must be after the start time."}
            )
        return attrs


class FacultyAssignSerializer(serializers.Serializer):
    """Assign a primary (lead) faculty and optional soft/support faculty to a batch."""

    primary_faculty = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.FACULTY), required=False, allow_null=True
    )
    faculty_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.FACULTY), many=True, required=False, default=list
    )


class TransitionSerializer(serializers.Serializer):
    to_state = serializers.ChoiceField(choices=BatchState.choices)
