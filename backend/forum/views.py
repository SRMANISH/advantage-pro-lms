"""Doubt forum APIs: per-batch threads, replies, resolve, keyword search."""

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_action
from batches.models import Batch
from content.access import can_access_batch
from core.permissions import has_any_role
from core.roles import Role
from enrollments.models import Enrollment
from notifications.services import notify, notify_many

from .models import Reply, Thread
from .serializers import (
    ReplyCreateSerializer,
    ThreadCreateSerializer,
    ThreadDetailSerializer,
    ThreadSerializer,
)

ForumRoles = has_any_role(
    Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.TECH_SUPPORT, Role.FACULTY, Role.STUDENT
)
ALL_FORUM = {Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.TECH_SUPPORT}
MONITOR_ROLES = {Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.TECH_SUPPORT}


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

    def get_serializer_class(self):
        if self.action == "create":
            return ThreadCreateSerializer
        if self.action == "retrieve":
            return ThreadDetailSerializer
        return ThreadSerializer

    def get_queryset(self):
        qs = Thread.objects.select_related("batch", "author")
        if self.action == "retrieve":
            qs = qs.prefetch_related("replies__author")
        if self.action == "list":
            qs = qs.annotate(reply_count=Count("replies", distinct=True))
        batch = self.request.query_params.get("batch")
        if batch:
            qs = qs.filter(batch_id=batch)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))
        ids = _forum_batch_ids(self.request.user)
        return qs if ids is None else qs.filter(batch_id__in=list(ids))

    def perform_create(self, serializer):
        thread = serializer.save(author=self.request.user)
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
        if not can_access_batch(request.user, thread.batch):
            return Response({"detail": "You cannot reply here."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReplyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        Reply.objects.create(
            thread=thread, author=request.user, body=serializer.validated_data["body"]
        )
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
        if not (
            is_faculty_of_batch or is_author or request.user.role in {Role.SUPER_ADMIN, Role.ADMIN}
        ):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        thread.resolved = True
        thread.save(update_fields=["resolved", "updated_at"])
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


class ForumMonitorView(APIView):
    """Unanswered doubts (Tech Support monitor), with an overdue flag past the window."""

    permission_classes = [has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.TECH_SUPPORT)]

    def get(self, request):
        window = settings.FORUM_RESPONSE_WINDOW_HOURS
        now = timezone.now()
        threads = (
            Thread.objects.filter(resolved=False)
            .annotate(rc=Count("replies"))
            .filter(rc=0)
            .select_related("batch", "author")
            .order_by("created_at")
        )
        rows = []
        for t in threads:
            hours = (now - t.created_at).total_seconds() / 3600
            rows.append(
                {
                    "id": str(t.id),
                    "title": t.title,
                    "batch_code": t.batch.code,
                    "author_name": t.author.full_name or t.author.username,
                    "hours_waiting": round(hours, 1),
                    "overdue": hours >= window,
                    "created_at": t.created_at,
                }
            )
        return Response({"window_hours": window, "threads": rows})


class ForumBatchesView(APIView):
    """Batches the user can post a doubt in (for the New-doubt picker)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role in {Role.SUPER_ADMIN, Role.ADMIN, Role.MIS}:
            qs = Batch.objects.all()
        elif user.role == Role.FACULTY:
            qs = Batch.objects.filter(faculty=user)
        elif user.role == Role.STUDENT:
            qs = Batch.objects.filter(enrollments__student=user).distinct()
        else:
            qs = Batch.objects.none()
        return Response([{"id": str(b.id), "code": b.code, "name": b.name} for b in qs])
