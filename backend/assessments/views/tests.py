"""Test APIs: build (faculty), take (student), one attempt.

MCQ tests auto-grade on submit; file/colab tests store the student's artefact (an Excel
workbook, a Colab notebook link) for the faculty to grade by hand out of the test's
max_score.
"""

import uuid

from django.db import IntegrityError, transaction
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
from core.uploads import validate_upload
from core.utils import get_client_ip
from notifications.services import batch_student_users, notify, notify_many

from ..models import AttemptAnswer, Test, TestAttempt, TestKind
from ..serializers import (
    GradeSerializer,
    SubmitSerializer,
    TestArtefactSubmitSerializer,
    TestAttemptSerializer,
    TestListSerializer,
    TestTakeSerializer,
    TestWriteSerializer,
)
from ._base import AssessmentRoles


class TestViewSet(viewsets.ModelViewSet):
    permission_classes = [AssessmentRoles, MatrixPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    _ACTIONS = {
        "create": Action.CREATE_TESTS,
        "update": Action.CREATE_TESTS,
        "partial_update": Action.CREATE_TESTS,
        "destroy": Action.CREATE_TESTS,
        "submit": Action.SUBMIT_TASKS_TESTS,
        "attempts": Action.CREATE_TESTS,
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
        # Optional faculty-provided starter sheet (e.g. the Excel workbook to fill in).
        upload = self.request.FILES.get("resource")
        if upload:
            validate_upload(upload, "document")
            key = f"tests/resources/{uuid.uuid4()}/{upload.name}"
            get_storage().save(key, upload)
            test.resource_key = key
            test.resource_content_type = getattr(upload, "content_type", "") or ""
            test.save(update_fields=["resource_key", "resource_content_type", "updated_at"])
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
        # Fast path for the common (non-racing) repeat-submit; the unique constraint is the
        # actual guarantee — two simultaneous submits can both pass this, but only one
        # create() wins and the loser gets the same friendly response, not an IntegrityError.
        if TestAttempt.objects.filter(test=test, student=request.user).exists():
            return Response({"detail": "You have already attempted this test."}, status=400)

        if test.kind == TestKind.MCQ:
            return self._submit_mcq(request, test)
        return self._submit_artefact(request, test)

    def _submit_mcq(self, request, test):
        serializer = SubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chosen = {a["question"]: a["choice"] for a in serializer.validated_data["answers"]}

        questions = list(test.questions.prefetch_related("choices"))
        try:
            with transaction.atomic():
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
        except IntegrityError:
            return Response({"detail": "You have already attempted this test."}, status=400)
        record_attendance(request.user, test.batch, "test", test.id)
        record_action(actor=request.user, action="test_submitted", target=test)
        return Response({"score": correct, "total": len(questions)}, status=status.HTTP_201_CREATED)

    def _submit_artefact(self, request, test):
        serializer = TestArtefactSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        upload = data.get("file")
        link = (data.get("link") or "").strip()
        if test.kind == TestKind.FILE and not upload:
            return Response({"detail": "Upload your file to submit."}, status=400)
        if test.kind == TestKind.COLAB and not link:
            return Response({"detail": "Paste your Colab / notebook link to submit."}, status=400)

        attempt = TestAttempt(
            test=test,
            student=request.user,
            score=0,
            total=test.max_score,
            graded=False,
            link=link,
        )
        if upload:
            key = f"tests/{uuid.uuid4()}/{upload.name}"
            get_storage().save(key, upload)
            attempt.file_key = key
            attempt.content_type = getattr(upload, "content_type", "") or ""
        try:
            attempt.save()
        except IntegrityError:
            return Response({"detail": "You have already attempted this test."}, status=400)
        record_attendance(request.user, test.batch, "test", test.id)
        record_action(actor=request.user, action="test_submitted", target=test)
        return Response({"ok": True, "graded": False}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def resource(self, request, pk=None):
        """Download the faculty-provided starter sheet (students fill it and re-upload)."""
        test = self.get_object()
        if not test.resource_key:
            return Response({"detail": "No resource file."}, status=status.HTTP_404_NOT_FOUND)
        return deliver(
            request,
            test.resource_key,
            test.resource_content_type or "application/octet-stream",
            disposition="attachment",
            filename=test.resource_key.split("/")[-1] or "resource",
        )

    @action(detail=True, methods=["get"])
    def attempts(self, request, pk=None):
        """Faculty: every student's attempt (for grading file/colab submissions)."""
        test = self.get_object()
        rows = test.attempts.select_related("student").order_by("student__username")
        return Response(TestAttemptSerializer(rows, many=True).data)


class TestAttemptViewSet(viewsets.GenericViewSet):
    queryset = TestAttempt.objects.select_related("test", "test__batch", "student")
    permission_classes = [AssessmentRoles, MatrixPermission]

    _ACTIONS = {"grade": Action.CREATE_TESTS}

    def get_required_action(self):
        return self._ACTIONS.get(self.action)

    @action(detail=True, methods=["post"])
    def grade(self, request, pk=None):
        attempt = self.get_object()
        if not can_access_batch(request.user, attempt.test.batch):
            return Response({"detail": "Not your batch."}, status=status.HTTP_403_FORBIDDEN)
        serializer = GradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt.score = min(serializer.validated_data["score"], attempt.total)
        attempt.feedback = serializer.validated_data.get("feedback", "")
        attempt.graded = True
        attempt.save(update_fields=["score", "feedback", "graded", "updated_at"])
        notify(
            attempt.student,
            "test_graded",
            f"Your test '{attempt.test.title}' has been graded.",
            link="/student/tests",
            channels=("in_app", "email"),
        )
        record_action(actor=request.user, action="test_attempt_graded", target=attempt)
        return Response({"ok": True})

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        attempt = self.get_object()
        is_owner = attempt.student_id == request.user.id
        # Owner-only for students; staff/faculty with batch access may fetch any to grade.
        is_reviewer = request.user.role != Role.STUDENT and can_access_batch(
            request.user, attempt.test.batch
        )
        if not (is_owner or is_reviewer):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if not attempt.file_key:
            return Response({"detail": "No file."}, status=status.HTTP_404_NOT_FOUND)
        return deliver(
            request, attempt.file_key, attempt.content_type or "application/octet-stream"
        )
