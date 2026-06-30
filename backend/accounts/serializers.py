from rest_framework import serializers

from core.roles import Role

from .models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"}, trim_whitespace=False)
    role = serializers.ChoiceField(choices=Role.choices)
    device_id = serializers.CharField(required=False, allow_blank=True, default="")


class DeviceRequestSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    student_name = serializers.SerializerMethodField()
    registration_number = serializers.CharField(source="user.username", read_only=True)
    during_class = serializers.BooleanField(read_only=True)
    class_context = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_student_name(self, obj) -> str:
        return obj.user.full_name or obj.user.username


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "full_name", "email", "phone", "role", "status"]
        read_only_fields = fields
