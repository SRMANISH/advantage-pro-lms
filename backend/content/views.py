"""Video & material APIs: upload (faculty), list (role-scoped), gated streaming, progress."""

from django.http import StreamingHttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from attendance.services import record_attendance
from audit.services import record_action
from core.adapters.registry import get_storage
from core.permissions import MatrixPermission, has_any_role
from core.permissions_matrix import Action
from core.roles import Role
from core.utils import get_client_ip
from notifications.services import batch_student_users, notify_many

from .access import accessible_batch_ids
from .models import Material, Video, VideoProgress
from .serializers import (
    MaterialSerializer,
    MaterialUploadSerializer,
    ProgressSerializer,
    VideoSerializer,
    VideoUploadSerializer,
)

ContentRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY, Role.STUDENT)

CHUNK = 8192


def _stream(fileobj, content_type: str, range_header: str | None) -> StreamingHttpResponse:
    """Stream a seekable file, honouring a Range request so <video> can seek."""
    fileobj.seek(0, 2)
    size = fileobj.tell()
    fileobj.seek(0)

    start, end = 0, size - 1
    partial = False
    if range_header and range_header.startswith("bytes="):
        raw = range_header.split("=", 1)[1].split("-")
        start = int(raw[0]) if raw[0] else 0
        end = int(raw[1]) if len(raw) > 1 and raw[1] else size - 1
        end = min(end, size - 1)
        partial = True

    length = end - start + 1
    fileobj.seek(start)

    def chunks():
        remaining = length
        while remaining > 0:
            data = fileobj.read(min(CHUNK, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data

    resp = StreamingHttpResponse(
        chunks(), status=206 if partial else 200, content_type=content_type
    )
    resp["Accept-Ranges"] = "bytes"
    resp["Content-Length"] = str(length)
    resp["Content-Disposition"] = "inline"  # discourage download
    if partial:
        resp["Content-Range"] = f"bytes {start}-{end}/{size}"
    return resp


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
        qs = Video.objects.select_related("batch", "uploaded_by")
        batch = self.request.query_params.get("batch")
        if batch:
            qs = qs.filter(batch_id=batch)
        return _scoped(qs, self.request.user)

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
        fileobj = get_storage().open(video.storage_key)
        return _stream(fileobj, video.content_type, request.headers.get("Range"))

    @action(detail=True, methods=["post"])
    def progress(self, request, pk=None):
        video = self.get_object()
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
        fileobj = get_storage().open(material.storage_key)
        return _stream(fileobj, material.content_type, request.headers.get("Range"))
