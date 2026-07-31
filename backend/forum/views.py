"""Doubt forum APIs: per-batch threads, replies, resolve, keyword search."""

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from batches.models import Batch
from content.access import can_access_batch
from content.delivery import deliver
from core.adapters.registry import get_storage
from core.pagination import StandardResultsPagination, paginate_rows
from core.permissions import has_any_role
from core.roles import Role
from core.schema import DetailResponse
from core.uploads import storage_name, validate_upload
from enrollments.models import Enrollment
from notifications.services import notify, notify_many

from .models import Reply, Thread, ThreadAttachment, ThreadStatus
from .serializers import (
    ReplyCreateSerializer,
    ThreadCreateSerializer,
    ThreadDetailSerializer,
    ThreadSerializer,
)


def _store_attachment(thread, reply, upload, user) -> None:
    """Validate + persist one uploaded file as a forum attachment."""
    validate_upload(upload, "document")
    key = f"forum/{storage_name(upload)}"
    get_storage().save(key, upload)
    ThreadAttachment.objects.create(
        thread=thread,
        reply=reply,
        storage_key=key,
        filename=upload.name,
        content_type=getattr(upload, "content_type", "") or "application/octet-stream",
        uploaded_by=user,
    )


# Updated procedure: forum is Tech Support / Faculty / Student — MIS has no forum access.
# Students ask; only Faculty and Tech Support respond (students cannot reply). The
# response-window SLA (FORUM_RESPONSE_WINDOW_HOURS, default 3h) applies to both responder
# roles, and both see the waiting time on every open doubt.
ForumRoles = has_any_role(Role.TECH_SUPPORT, Role.FACULTY, Role.STUDENT)
ALL_FORUM = {Role.TECH_SUPPORT}  # read every batch's forum
MONITOR_ROLES = {Role.TECH_SUPPORT}
RESPONDER_ROLES = {Role.FACULTY, Role.TECH_SUPPORT}


def _can_reply(user, thread) -> bool:
    # Only responders may reply: Tech Support across all batches; Faculty within theirs.
    if user.role == Role.TECH_SUPPORT:
        return True
    return user.role == Role.FACULTY and can_access_batch(user, thread.batch)


def _forum_batch_ids(user):
    """None => all batches; else the batches whose forum the user may read."""
    if user.role in ALL_FORUM:
        return None
    if user.role == Role.FACULTY:
        return Batch.objects.filter(faculty=user).values_list("id", flat=True)
    if user.role == Role.STUDENT:
        return Enrollment.objects.filter(student=user).values_list("batch_id", flat=True)
    return []


class ThreadViewSet(viewsets.ModelViewSet):
    permission_classes = [ForumRoles]
    pagination_class = StandardResultsPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == "create":
            return ThreadCreateSerializer
        if self.action == "retrieve":
            return ThreadDetailSerializer
        return ThreadSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Thread.objects.none()  # OpenAPI schema generation (no real user)
        qs = Thread.objects.select_related("batch", "author")
        if self.action == "retrieve":
            qs = qs.prefetch_related("replies__author", "replies__attachments", "attachments")
        if self.action == "list":
            qs = qs.annotate(reply_count=Count("replies", distinct=True))
        batch = self.request.query_params.get("batch")
        if batch:
            qs = qs.filter(batch_id=batch)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))
        ids = _forum_batch_ids(self.request.user)
        qs = qs if ids is None else qs.filter(batch_id__in=list(ids))
        # Stable ordering so pagination is deterministic (newest doubts first).
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        # Validate any attachment before persisting so a bad file rejects the whole post.
        upload = self.request.FILES.get("file")
        with transaction.atomic():
            thread = serializer.save(author=self.request.user)
            if upload:
                _store_attachment(thread, None, upload, self.request.user)
        record_action(actor=self.request.user, action="doubt_posted", target=thread)
        notify_many(
            list(thread.batch.faculty.all()),
            "new_doubt",
            f"New doubt in {thread.batch.code}: {thread.title}",
            link="/faculty/forum",
            channels=("in_app",),
        )

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        thread = self.get_object()
        if not _can_reply(request.user, thread):
            return Response({"detail": "You cannot reply here."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReplyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = request.FILES.get("file")
        with transaction.atomic():
            reply = Reply.objects.create(
                thread=thread, author=request.user, body=serializer.validated_data["body"]
            )
            if upload:
                _store_attachment(thread, reply, upload, request.user)
        # A reply from a responder (faculty/TS/MIS) marks the doubt answered.
        if thread.status == ThreadStatus.OPEN and request.user.role in RESPONDER_ROLES:
            thread.status = ThreadStatus.ANSWERED
            thread.save(update_fields=["status", "updated_at"])
        if thread.author_id != request.user.id:
            notify(
                thread.author,
                "doubt_reply",
                f"New reply to your doubt '{thread.title}'.",
                link="/student/forum",
                channels=("in_app",),
            )
        return Response(ThreadDetailSerializer(thread, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        thread = self.get_object()
        is_faculty_of_batch = thread.batch.faculty.filter(id=request.user.id).exists()
        is_author = thread.author_id == request.user.id
        if not (is_faculty_of_batch or is_author or request.user.role == Role.TECH_SUPPORT):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        thread.resolved = True
        thread.status = ThreadStatus.RESOLVED
        thread.save(update_fields=["resolved", "status", "updated_at"])
        return Response(ThreadSerializer(thread, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        """Tech Support / batch faculty escalate an unresolved doubt."""
        thread = self.get_object()
        is_faculty_of_batch = thread.batch.faculty.filter(id=request.user.id).exists()
        if not (is_faculty_of_batch or request.user.role == Role.TECH_SUPPORT):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        thread.status = ThreadStatus.ESCALATED
        thread.save(update_fields=["status", "updated_at"])
        notify_many(
            list(thread.batch.faculty.all()),
            "doubt_escalated",
            f"Doubt escalated in {thread.batch.code}: '{thread.title}'.",
            link="/faculty/forum",
            subject="Doubt escalated",
            channels=("in_app", "email"),
        )
        record_action(actor=request.user, action="doubt_escalated", target=thread)
        return Response(ThreadSerializer(thread, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def remind(self, request, pk=None):
        """Tech Support (or admins) nudge the batch faculty to answer a doubt."""
        if request.user.role not in MONITOR_ROLES:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        thread = self.get_object()
        notify_many(
            list(thread.batch.faculty.all()),
            "doubt_reminder",
            f"Please respond to the doubt '{thread.title}' in {thread.batch.code}.",
            link="/faculty/forum",
            subject="Doubt awaiting reply",
            channels=("in_app", "email"),
        )
        record_action(actor=request.user, action="doubt_reminder_sent", target=thread)
        return Response({"ok": True})


@extend_schema(responses=OpenApiTypes.OBJECT)
class ForumMonitorView(APIView):
    """Tech Support doubt dashboard: unanswered doubts, overdue flags, and status
    counts (new, unanswered, faculty-response-pending, answered-by-TS). MIS has no
    forum access under the updated procedure."""

    permission_classes = [has_any_role(Role.TECH_SUPPORT)]

    def get(self, request):
        window = settings.FORUM_RESPONSE_WINDOW_HOURS
        now = timezone.now()
        unanswered = (
            Thread.objects.exclude(status=ThreadStatus.RESOLVED)
            .annotate(rc=Count("replies"))
            .filter(rc=0)
            .select_related("batch", "author")
            .order_by("created_at")
        )

        def row(t):
            hours = (now - t.created_at).total_seconds() / 3600
            return {
                "id": str(t.id),
                "title": t.title,
                "batch_code": t.batch.code,
                "author_name": t.author.full_name or t.author.username,
                "status": t.status,
                "hours_waiting": round(hours, 1),
                "overdue": hours >= window,
                "faculty_pending": hours >= window,
                "created_at": t.created_at,
            }

        counts = {
            "open": Thread.objects.filter(status=ThreadStatus.OPEN).count(),
            "answered": Thread.objects.filter(status=ThreadStatus.ANSWERED).count(),
            "escalated": Thread.objects.filter(status=ThreadStatus.ESCALATED).count(),
            "resolved": Thread.objects.filter(status=ThreadStatus.RESOLVED).count(),
            "answered_by_ts": Thread.objects.filter(replies__author__role=Role.TECH_SUPPORT)
            .distinct()
            .count(),
        }
        # Paginated: the unanswered queue is unbounded and this dashboard is the one place
        # it is read in full. ``counts`` and ``window_hours`` describe the whole dataset, so
        # they ride alongside the page rather than inside it.
        return paginate_rows(
            request,
            unanswered,
            row,
            view=self,
            extra={"window_hours": window, "counts": counts},
        )


@extend_schema(responses=OpenApiTypes.OBJECT)
class ForumBatchesView(APIView):
    """Batches the user can post a doubt in (for the New-doubt picker)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == Role.TECH_SUPPORT:
            qs = Batch.objects.all()
        elif user.role == Role.FACULTY:
            qs = Batch.objects.filter(faculty=user)
        elif user.role == Role.STUDENT:
            qs = Batch.objects.filter(enrollments__student=user).distinct()
        else:
            qs = Batch.objects.none()  # MIS/Admin/SA have no forum under the procedure
        return Response([{"id": str(b.id), "code": b.code, "name": b.name} for b in qs])


@extend_schema(
    responses={(200, "application/octet-stream"): OpenApiTypes.BINARY, 404: DetailResponse}
)
class AttachmentDownloadView(APIView):
    """Serve a forum attachment, gated by the same batch access as the forum itself."""

    permission_classes = [ForumRoles]

    def get(self, request, pk):
        att = ThreadAttachment.objects.select_related("thread__batch").filter(pk=pk).first()
        if not att:
            return Response({"detail": "Attachment not found."}, status=status.HTTP_404_NOT_FOUND)
        user = request.user
        # Tech Support / MIS see every batch's forum; others need normal batch access.
        if user.role not in ALL_FORUM and not can_access_batch(user, att.thread.batch):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        # Images render inline (req 3a: they show inside the thread); other files download.
        is_image = (att.content_type or "").startswith("image/")
        return deliver(
            request,
            att.storage_key,
            att.content_type or "application/octet-stream",
            disposition="inline" if is_image else "attachment",
            filename=att.filename,
        )
