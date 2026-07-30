"""Task APIs: build (faculty), list/submit (role-scoped), grade + file serve."""

from django.db import IntegrityError
from django.db.models import Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from attendance.services import record_attendance
from audit.services import record_action
from content.access import accessible_batch_ids, can_access_batch
from content.delivery import deliver
from core.adapters.registry import get_storage
from core.permissions import MatrixPermission
from core.permissions_matrix import Action
from core.roles import Role
from core.uploads import storage_name
from core.utils import get_client_ip
from notifications.services import batch_student_users, notify, notify_many

from ..models import Task, TaskSubmission
from ..serializers import (
    GradeSerializer,
    SubmissionSerializer,
    TaskSerializer,
    TaskSubmitSerializer,
    TaskWriteSerializer,
)
from ._base import AssessmentRoles


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [AssessmentRoles, MatrixPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    _ACTIONS = {
        "create": Action.CREATE_TASKS,
        "update": Action.CREATE_TASKS,
        "partial_update": Action.CREATE_TASKS,
        "destroy": Action.CREATE_TASKS,
        "submit": Action.SUBMIT_TASKS_TESTS,
        "submissions": Action.CREATE_TASKS,
    }

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    def get_serializer_class(self):
        return TaskWriteSerializer if self.action == "create" else TaskSerializer

    def get_queryset(self):
        qs = Task.objects.select_related("batch")
        if self.action == "list":
            qs = qs.annotate(submission_count=Count("submissions", distinct=True))
        batch = self.request.query_params.get("batch")
        if batch:
            qs = qs.filter(batch_id=batch)
        user = self.request.user
        # Prefetch the student's own submission per task (serializer my_submission) — no N+1.
        if user.role == Role.STUDENT:
            from django.db.models import Prefetch

            qs = qs.prefetch_related(
                Prefetch(
                    "submissions",
                    queryset=TaskSubmission.objects.filter(student=user),
                    to_attr="my_subs",
                )
            )
        ids = accessible_batch_ids(user)
        return qs if ids is None else qs.filter(batch_id__in=list(ids))

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)
        record_action(
            actor=self.request.user,
            action="task_created",
            target=task,
            ip_address=get_client_ip(self.request),
        )
        notify_many(
            batch_student_users(task.batch),
            "new_task",
            f"New task: {task.title}",
            link="/student/tasks",
            channels=("in_app",),
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        task = self.get_object()
        # Fast path for the common (non-racing) repeat-submit; the unique constraint below
        # is the actual guarantee against two simultaneous submits both getting through.
        if TaskSubmission.objects.filter(task=task, student=request.user).exists():
            return Response({"detail": "You have already submitted this task."}, status=400)
        serializer = TaskSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        late = bool(task.deadline and timezone.now() > task.deadline)
        submission = TaskSubmission(
            task=task, student=request.user, text=data.get("text", ""), is_late=late
        )
        upload = data.get("file")
        if upload:
            key = f"tasks/{storage_name(upload)}"
            get_storage().save(key, upload)
            submission.file_key = key
            submission.content_type = getattr(upload, "content_type", "") or ""
        try:
            submission.save()
        except IntegrityError:
            return Response({"detail": "You have already submitted this task."}, status=400)
        record_attendance(request.user, task.batch, "task", task.id)
        record_action(actor=request.user, action="task_submitted", target=task)
        return Response({"ok": True, "is_late": late}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def submissions(self, request, pk=None):
        task = self.get_object()
        subs = task.submissions.select_related("student")
        return Response(SubmissionSerializer(subs, many=True).data)


class TaskSubmissionViewSet(viewsets.GenericViewSet):
    queryset = TaskSubmission.objects.select_related("task", "task__batch", "student")
    permission_classes = [AssessmentRoles, MatrixPermission]

    _ACTIONS = {"grade": Action.CREATE_TASKS}

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    @action(detail=True, methods=["post"])
    def grade(self, request, pk=None):
        submission = self.get_object()
        if not can_access_batch(request.user, submission.task.batch):
            return Response({"detail": "Not your batch."}, status=status.HTTP_403_FORBIDDEN)
        serializer = GradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission.score = serializer.validated_data["score"]
        submission.feedback = serializer.validated_data.get("feedback", "")
        submission.save(update_fields=["score", "feedback", "updated_at"])
        notify(
            submission.student,
            "task_feedback",
            f"Feedback given on '{submission.task.title}'.",
            link="/student/tasks",
            channels=("in_app", "email"),
        )
        record_action(actor=request.user, action="task_graded", target=submission)
        return Response({"ok": True})

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        submission = self.get_object()
        is_owner = submission.student_id == request.user.id
        # A student may only fetch their OWN file; staff/faculty with batch access may
        # fetch any (to grade). Batchmates must not read each other's submissions.
        is_reviewer = request.user.role != Role.STUDENT and can_access_batch(
            request.user, submission.task.batch
        )
        if not (is_owner or is_reviewer):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if not submission.file_key:
            return Response({"detail": "No file."}, status=status.HTTP_404_NOT_FOUND)
        return deliver(
            request,
            submission.file_key,
            submission.content_type or "application/octet-stream",
        )
