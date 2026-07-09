"""Faculty self-service profile: skills + certifications.

A faculty maintains these in their own portal; Super Admin/Admin see them when choosing
faculty for a batch (they ride along on FacultyBriefSerializer).
"""

from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from core.roles import Role

from ..models import FacultyProfile
from ..serializers import FacultyProfileSerializer


class IsFaculty(BasePermission):
    message = "This is a faculty-only feature."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.role == Role.FACULTY)


class FacultyProfileView(APIView):
    """A faculty reads (GET) and updates (PUT) their own skills + certifications."""

    permission_classes = [IsFaculty]

    def get(self, request):
        profile, _ = FacultyProfile.objects.get_or_create(user=request.user)
        return Response(FacultyProfileSerializer(profile).data)

    def put(self, request):
        profile, _ = FacultyProfile.objects.get_or_create(user=request.user)
        serializer = FacultyProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
