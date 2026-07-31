"""Video & material APIs: upload (faculty), list (role-scoped), gated streaming, progress."""

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from attendance.services import record_attendance
from audit.services import record_action
from batches.models import Batch
from core.permissions import MatrixPermission, has_any_role
from core.permissions_matrix import Action
from core.roles import Role
from core.schema import DetailResponse, OkResponse
from core.utils import get_client_ip
from notifications.services import batch_student_users, notify_many

from .access import accessible_batch_ids, is_video_blocked
from .delivery import deliver
from .models import Material, Video, VideoAccessRevocation, VideoProgress
from .serializers import (
    MaterialSerializer,
    MaterialUploadSerializer,
    ProgressSerializer,
    VideoSerializer,
    VideoUploadSerializer,
)

ContentRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY, Role.STUDENT)


def _scoped(qs, user):
    ids = accessible_batch_ids(user)
    return qs if ids is None else qs.filter(batch_id__in=list(ids))


class VideoViewSet(viewsets.ModelViewSet):
    permission_classes = [ContentRoles, MatrixPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    _ACTIONS = {
        "create": Action.UPLOAD_VIDEOS,
        "update": Action.UPLOAD_VIDEOS,
        "partial_update": Action.UPLOAD_VIDEOS,
        "destroy": Action.UPLOAD_VIDEOS,
    }

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    def get_serializer_class(self):
        return VideoUploadSerializer if self.action == "create" else VideoSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Video.objects.none()  # OpenAPI schema generation (no real request)
        from django.db.models import Prefetch

        qs = Video.objects.select_related("batch", "uploaded_by")
        user = self.request.user
        # Prefetch just this student's progress rows so the serializer's `progress` field
        # is a list lookup, not one query per video (N+1).
        if user.role == Role.STUDENT:
            qs = qs.prefetch_related(
                Prefetch(
                    "progresses",
                    queryset=VideoProgress.objects.filter(student=user),
                    to_attr="my_progress",
                )
            )
        batch = self.request.query_params.get("batch")
        if batch:
            qs = qs.filter(batch_id=batch)
        return _scoped(qs, user)

    def perform_create(self, serializer):
        video = serializer.save()
        record_action(
            actor=self.request.user,
            action="video_uploaded",
            target=video,
            ip_address=get_client_ip(self.request),
        )
        notify_many(
            batch_student_users(video.batch),
            "new_video",
            f"New video added: {video.title}",
            link="/student/videos",
            channels=("in_app",),
        )

    @action(detail=True, methods=["get"])
    def play(self, request, pk=None):
        video = self.get_object()
        if request.user.role == Role.STUDENT and is_video_blocked(request.user, video.batch):
            return Response(
                {"detail": "Your video access for this course has been closed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return deliver(request, video.storage_key, video.content_type)

    @action(detail=True, methods=["post"])
    def progress(self, request, pk=None):
        video = self.get_object()
        if request.user.role == Role.STUDENT and is_video_blocked(request.user, video.batch):
            return Response(
                {"detail": "Your video access for this course has been closed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        completed = data["percent"] >= 80
        VideoProgress.objects.update_or_create(
            video=video,
            student=request.user,
            defaults={
                "percent": data["percent"],
                "watched_seconds": data["watched_seconds"],
                "last_position": data["last_position"],
                "completed": completed,
            },
        )
        if completed:
            record_attendance(request.user, video.batch, "video", video.id)
        return Response({"ok": True, "completed": completed})


class MaterialViewSet(viewsets.ModelViewSet):
    permission_classes = [ContentRoles, MatrixPermission]
    parser_classes = [MultiPartParser, FormParser]

    _ACTIONS = {
        "create": Action.UPLOAD_NOTES,
        "update": Action.UPLOAD_NOTES,
        "partial_update": Action.UPLOAD_NOTES,
        "destroy": Action.UPLOAD_NOTES,
    }

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    def get_serializer_class(self):
        return MaterialUploadSerializer if self.action == "create" else MaterialSerializer

    def get_queryset(self):
        qs = Material.objects.select_related("batch")
        batch = self.request.query_params.get("batch")
        if batch:
            qs = qs.filter(batch_id=batch)
        return _scoped(qs, self.request.user)

    @action(detail=True, methods=["get"])
    def view(self, request, pk=None):
        material = self.get_object()
        if request.user.role == Role.STUDENT and is_video_blocked(request.user, material.batch):
            return Response(
                {"detail": "Your access for this course has been closed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return deliver(request, material.storage_key, material.content_type)


@extend_schema(request=None, responses={200: OkResponse, 404: DetailResponse})
class RevokeVideoAccessView(APIView):
    """MIS revokes an individual student's video access (optionally per batch)."""

    permission_classes = [MatrixPermission]
    required_action = Action.REVOKE_VIDEO_INDIVIDUAL

    def post(self, request):
        student = User.objects.filter(id=request.data.get("student_id"), role=Role.STUDENT).first()
        if not student:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        batch = None
        if request.data.get("batch_id"):
            batch = Batch.objects.filter(id=request.data["batch_id"]).first()
            if not batch:
                return Response({"detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)
        VideoAccessRevocation.objects.get_or_create(
            student=student,
            batch=batch,
            defaults={"revoked_by": request.user, "reason": request.data.get("reason", "")},
        )
        record_action(
            actor=request.user,
            action="video_access_revoked",
            target=student,
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})


@extend_schema(request=None, responses={200: OkResponse, 404: DetailResponse})
class RestoreVideoAccessView(APIView):
    """MIS restores a previously revoked individual student's video access."""

    permission_classes = [MatrixPermission]
    required_action = Action.REVOKE_VIDEO_INDIVIDUAL

    def post(self, request):
        student = User.objects.filter(id=request.data.get("student_id"), role=Role.STUDENT).first()
        if not student:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        qs = VideoAccessRevocation.objects.filter(student=student)
        if request.data.get("batch_id"):
            qs = qs.filter(batch_id=request.data["batch_id"])
        qs.delete()
        record_action(
            actor=request.user,
            action="video_access_restored",
            target=student,
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})


@extend_schema(request=None, responses={200: OkResponse, 404: DetailResponse})
class CloseCourseVideoAccessView(APIView):
    """Admin or MIS close a whole batch's video access at course end."""

    permission_classes = [MatrixPermission]
    required_action = Action.CLOSE_COURSE_VIDEO_ACCESS

    def post(self, request):
        batch = Batch.objects.filter(id=request.data.get("batch_id")).first()
        if not batch:
            return Response({"detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)
        VideoAccessRevocation.objects.get_or_create(
            student=None,
            batch=batch,
            defaults={"revoked_by": request.user, "reason": "course-end closure"},
        )
        record_action(
            actor=request.user,
            action="course_video_access_closed",
            target=batch,
            ip_address=get_client_ip(request),
        )
        return Response({"ok": True})
