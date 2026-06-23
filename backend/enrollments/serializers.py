from rest_framework import serializers

from .models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_status = serializers.CharField(source="student.status", read_only=True)
    email = serializers.CharField(source="student.email", read_only=True)
    phone = serializers.CharField(source="student.phone", read_only=True)
    batch_code = serializers.CharField(source="batch.code", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "student",
            "registration_number",
            "student_name",
            "student_status",
            "email",
            "phone",
            "batch",
            "batch_code",
            "employment_company",
            "created_at",
        ]
        read_only_fields = fields
