"""MCQ test APIs: build (faculty), list/take (role-scoped), one auto-graded attempt."""

import uuid

from django.db.models import Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from attendance.services import record_attendance
from audit.services import record_action
from content.access import accessible_batch_ids, can_access_batch
from content.views import _stream
from core.adapters.registry import get_storage
from core.permissions import MatrixPermission, has_any_role
from core.permissions_matrix import Action
from core.roles import Role
from core.utils import get_client_ip
from notifications.services import batch_student_users, notify, notify_many

from .models import AttemptAnswer, Task, TaskSubmission, Test, TestAttempt
from .serializers import (
    GradeSerializer,
    SubmissionSerializer,
    SubmitSerializer,
    TaskSerializer,
    TaskSubmitSerializer,
    TaskWriteSerializer,
    TestListSerializer,
    TestTakeSerializer,
    TestWriteSerializer,
)

AssessmentRoles = has_any_role(Role.SUPER_ADMIN, Role.ADMIN, Role.MIS, Role.FACULTY, Role.STUDENT)


class TestViewSet(viewsets.ModelViewSet):
    permission_classes = [AssessmentRoles, MatrixPermission]

    _ACTIONS = {
        "create": Action.CREATE_TESTS,
        "update": Action.CREATE_TESTS,
        "partial_update": Action.CREATE_TESTS,
        "destroy": Action.CREATE_TESTS,
        "submit": Action.SUBMIT_TASKS_TESTS,
    }

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    def get_serializer_class(self):
        if self.action == "create":
            return TestWriteSerializer
        if self.action == "retrieve":
            return TestTakeSerializer
        return TestListSerializer

    def get_queryset(self):
        qs = Test.objects.select_related("batch")
        if self.action in {"list"}:
            qs = qs.annotate(
                question_count=Count("questions", distinct=True),
                attempt_count=Count("attempts", distinct=True),
            )
        batch = self.request.query_params.get("batch")
        if batch:
            qs = qs.filter(batch_id=batch)
        ids = accessible_batch_ids(self.request.user)
        return qs if ids is None else qs.filter(batch_id__in=list(ids))

    def perform_create(self, serializer):
        test = serializer.save()
        record_action(
            actor=self.request.user,
            action="test_created",
            target=test,
            ip_address=get_client_ip(self.request),
        )
        notify_many(
            batch_student_users(test.batch),
            "new_test",
            f"New test: {test.title}",
            link="/student/tests",
            channels=("in_app",),
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        test = self.get_object()
        now = timezone.now()
        if test.open_at and now < test.open_at:
            return Response({"detail": "This test is not open yet."}, status=400)
        if test.close_at and now > test.close_at:
            return Response({"detail": "This test has closed."}, status=400)
        if TestAttempt.objects.filter(test=test, student=request.user).exists():
            return Response({"detail": "You have already attempted this test."}, status=400)

        serializer = SubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chosen = {a["question"]: a["choice"] for a in serializer.validated_data["answers"]}

        questions = list(test.questions.prefetch_related("choices"))
        attempt = TestAttempt.objects.create(
            test=test, student=request.user, score=0, total=len(questions)
        )
        correct = 0
        for q in questions:
            choice = None
            chosen_id = chosen.get(q.id)
            if chosen_id:
                choice = next((c for c in q.choices.all() if c.id == chosen_id), None)
                if choice and choice.is_correct:
                    correct += 1
            AttemptAnswer.objects.create(attempt=attempt, question=q, choice=choice)
        attempt.score = correct
        attempt.save(update_fields=["score", "updated_at"])
        record_attendance(request.user, test.batch, "test", test.id)
        record_action(actor=request.user, action="test_submitted", target=test)
        return Response({"score": correct, "total": len(questions)}, status=status.HTTP_201_CREATED)


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
        ids = accessible_batch_ids(self.request.user)
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
            key = f"tasks/{uuid.uuid4()}/{upload.name}"
            get_storage().save(key, upload)
            submission.file_key = key
            submission.content_type = getattr(upload, "content_type", "") or ""
        submission.save()
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
        if not (is_owner or can_access_batch(request.user, submission.task.batch)):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if not submission.file_key:
            return Response({"detail": "No file."}, status=status.HTTP_404_NOT_FOUND)
        fileobj = get_storage().open(submission.file_key)
        return _stream(
            fileobj,
            submission.content_type or "application/octet-stream",
            request.headers.get("Range"),
        )
